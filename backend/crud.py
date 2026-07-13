from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime
from fastapi import HTTPException, status
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.exc import OperationalError, DBAPIError
import json
import structlog
from asgi_correlation_id import correlation_id

import models
import schemas

RETRY_COUNT = 0

def increment_retry_counter(retry_state):
    global RETRY_COUNT
    RETRY_COUNT += 1

def serialize_patient(p: models.Patient) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "age": p.age,
        "status": p.status.value if hasattr(p.status, "value") else str(p.status),
        "criticality_score": p.criticality_score,
        "current_bed_id": p.current_bed_id
    }

def serialize_recommendation(r: models.Recommendation) -> dict:
    res = {
        "id": r.id,
        "patient_id": r.patient_id,
        "status": r.status.value if hasattr(r.status, "value") else str(r.status),
        "criticality_score": r.criticality_score,
        "reasoning": r.reasoning
    }
    if hasattr(r, "recommendation_type") and r.recommendation_type:
        res["recommendation_type"] = r.recommendation_type.value if hasattr(r.recommendation_type, "value") else str(r.recommendation_type)
    if hasattr(r, "chained_patient_id") and r.chained_patient_id:
        res["chained_patient_id"] = r.chained_patient_id
    if hasattr(r, "chained_target_bed_id") and r.chained_target_bed_id:
        res["chained_target_bed_id"] = r.chained_target_bed_id
    return res

def serialize_alert(a: models.Alert) -> dict:
    return {
        "id": a.id,
        "patient_id": a.patient_id,
        "alert_type": a.alert_type.value if hasattr(a.alert_type, "value") else str(a.alert_type),
        "is_acknowledged": a.is_acknowledged
    }

def serialize_bed(b: models.Bed) -> dict:
    return {
        "id": b.id,
        "bed_number": b.bed_number,
        "status": b.status.value if hasattr(b.status, "value") else str(b.status),
        "patient_id": b.patient_id
    }

async def create_audit_log(
    db: AsyncSession,
    action: str,
    entity_type: str,
    entity_id: Optional[int],
    before_data: Optional[dict] = None,
    after_data: Optional[dict] = None,
    user_id: Optional[str] = None
) -> models.AuditLog:
    if not user_id:
        try:
            ctx = structlog.contextvars.get_contextvars()
            user_id = ctx.get("user_id", "anonymous")
        except Exception:
            user_id = "anonymous"
            
    corr_id = correlation_id.get() or "N/A"
    
    before_str = json.dumps(before_data) if before_data else None
    after_str = json.dumps(after_data) if after_data else None
    
    log = models.AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_data=before_str,
        after_data=after_str,
        correlation_id=corr_id
    )
    db.add(log)
    await db.flush()
    return log


async def log_operational_event(
    db: AsyncSession,
    patient_id: Optional[int],
    event_type: str,
    payload: dict
) -> models.OperationalLog:
    import hashlib
    import json
    from datetime import datetime

    # 1. Query the immediately preceding log record ordered by id.desc()
    prev_log_res = await db.execute(
        select(models.OperationalLog)
        .order_by(models.OperationalLog.id.desc())
        .limit(1)
    )
    prev_log = prev_log_res.scalar_one_or_none()
    prev_hash = prev_log.cryptographic_hash if (prev_log and prev_log.cryptographic_hash) else "0" * 64

    # 2. Get current timestamp
    timestamp = datetime.utcnow()
    timestamp_iso = timestamp.isoformat()

    # 3. Format the payload sorted keys for deterministic serialization
    payload_json = json.dumps(payload, sort_keys=True)

    # 4. Construct hash input exactly as: "{prev_hash}|{timestamp_iso}|{event_type}|{payload_json}"
    hash_input = f"{prev_hash}|{timestamp_iso}|{event_type}|{payload_json}"

    # 5. Compute SHA-256 hash
    computed_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

    # 6. Create the log with the computed hash
    log = models.OperationalLog(
        patient_id=patient_id,
        event_type=event_type,
        timestamp=timestamp,
        payload=payload,
        cryptographic_hash=computed_hash
    )
    db.add(log)
    await db.flush()
    return log



async def get_wards(db: AsyncSession) -> List[models.Ward]:
    # Select wards and load their beds to calculate occupied beds count and utilization
    result = await db.execute(
        select(models.Ward).options(selectinload(models.Ward.beds).selectinload(models.Bed.patient))
    )
    wards = result.scalars().all()
    
    # Fetch all staffing records
    staffing_res = await db.execute(select(models.WardStaffing))
    staffing_records = {s.ward_name: s for s in staffing_res.scalars().all()}
    
    # Calculate dynamically for serialization
    for ward in wards:
        occupied = sum(1 for bed in ward.beds if bed.status == models.BedStatus.OCCUPIED)
        ward.occupied_beds_count = occupied
        ward.utilization_rate = round((occupied / ward.capacity) * 100.0, 1) if ward.capacity > 0 else 0.0
        
        # Populate staffing info dynamically
        staff = staffing_records.get(ward.name)
        if staff:
            ward.current_nurses = staff.current_nurses
            ward.max_patient_ratio = staff.max_patient_ratio
        else:
            ward.current_nurses = 0
            ward.max_patient_ratio = 2
        
    return wards

async def get_beds(db: AsyncSession, ward_id: Optional[int] = None) -> List[models.Bed]:
    query = select(models.Bed).options(selectinload(models.Bed.patient))
    if ward_id is not None:
        query = query.where(models.Bed.ward_id == ward_id)
    
    result = await db.execute(query)
    return result.scalars().all()

async def get_patients(db: AsyncSession) -> List[models.Patient]:
    # Fetch active patients (not discharged)
    result = await db.execute(
        select(models.Patient).where(models.Patient.discharged_at == None).order_by(models.Patient.criticality_score.desc())
    )
    return result.scalars().all()

async def admit_patient(db: AsyncSession, payload: schemas.PatientAdmitPayload) -> models.Patient:
    # 1. Find an available bed in the target ward
    bed_result = await db.execute(
        select(models.Bed)
        .where(models.Bed.ward_id == payload.target_ward_id)
        .where(models.Bed.status == models.BedStatus.AVAILABLE)
        .limit(1)
        .with_for_update(nowait=False)
    )
    available_bed = bed_result.scalar_one_or_none()
    
    if not available_bed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No available beds in ward ID {payload.target_ward_id}."
        )
        
    # 2. Compute deterministic score based on vitals (defaulted if not passed)
    # 2. Compute NEWS2 score based on vitals (defaulted if not passed)
    hr = payload.heart_rate or (135 if payload.status == models.PatientStatus.CRITICAL else (115 if payload.status == models.PatientStatus.SERIOUS else 75))
    rr = payload.resp_rate or (32 if payload.status == models.PatientStatus.CRITICAL else (23 if payload.status == models.PatientStatus.SERIOUS else 16))
    spo2 = payload.spo2 or (85 if payload.status == models.PatientStatus.CRITICAL else (93 if payload.status == models.PatientStatus.SERIOUS else 98))
    
    from services.scoring.policy_service import get_active_policy
    from services.scoring.news2_service import calculate_news2
    from services.scoring.operational_service import calculate_operational_priority
    
    policy = await get_active_policy(db)
    
    vitals_record = models.PatientVitals(
        patient_id=0, # Temporary ID
        heart_rate=hr,
        resp_rate=rr,
        spo2=spo2,
        temperature=None,
        systolic_bp=None,
        consciousness_level=models.ConsciousnessLevel.ALERT,
        oxygen_supplement=False,
        spo2_scale=1
    )
    
    total_score, risk_band, breakdown, red_flags = calculate_news2(vitals_record, policy)
    score = calculate_operational_priority(total_score)

    # 3. Create the Patient record
    new_patient = models.Patient(
        name=payload.name,
        age=payload.age,
        gender=payload.gender,
        admission_reason=payload.admission_reason,
        status=payload.status,
        criticality_score=score,
        current_bed_id=available_bed.id
    )
    db.add(new_patient)
    await db.flush() # Flush to populate new_patient.id
    
    # 3.5 Attach actual patient_id to vitals and score records
    vitals_record.patient_id = new_patient.id
    db.add(vitals_record)
    
    score_record = models.ScoreRecord(
        patient_id=new_patient.id,
        policy_id=policy.id,
        clinical_score=total_score,
        risk_band=risk_band,
        operational_priority=score
    )
    db.add(score_record)
    await db.flush()
    
    score_explanation = models.ScoreExplanation(
        score_record_id=score_record.id,
        parameter_breakdown=breakdown,
        red_flags=red_flags
    )
    db.add(score_explanation)

    # 4. Atomically update the Bed status
    available_bed.status = models.BedStatus.OCCUPIED
    available_bed.patient_id = new_patient.id
    
    # 5. Log audit trail and ClinicalEvent
    await create_audit_log(
        db,
        action="ADMIT",
        entity_type="patient",
        entity_id=new_patient.id,
        after_data=serialize_patient(new_patient)
    )
    
    admission_event = models.ClinicalEvent(
        patient_id=new_patient.id,
        event_type=models.ClinicalEventType.ADMISSION,
        description=f"Patient admitted to {payload.admission_reason}. Assigned to bed {available_bed.bed_number}.",
        event_metadata={"vitals": {"hr": hr, "rr": rr, "spo2": spo2}, "score": score, "risk_band": risk_band.value, "clinical_score": total_score},
    )
    db.add(admission_event)
    
    # Commit is handled by the route dependency/context manager
    return new_patient

async def get_pending_recommendations(db: AsyncSession) -> List[models.Recommendation]:
    # Select pending recommendations and load patient, source bed/ward, and target bed/ward relations
    result = await db.execute(
        select(models.Recommendation)
        .options(
            selectinload(models.Recommendation.patient),
            selectinload(models.Recommendation.approved_by),
            selectinload(models.Recommendation.chained_patient),
            selectinload(models.Recommendation.chained_target_bed)
        )
        .where(models.Recommendation.status == models.RecommendationStatus.PENDING)
        .order_by(models.Recommendation.created_at.desc())
    )
    recs = result.scalars().all()
    
    # We also load the target bed, source bed, and partner hospital dynamically
    for rec in recs:
        # Load target bed and ward
        if rec.target_bed_id:
            target_res = await db.execute(
                select(models.Bed).options(selectinload(models.Bed.ward)).where(models.Bed.id == rec.target_bed_id)
            )
            rec.target_bed = target_res.scalar_one_or_none()
        else:
            rec.target_bed = None
            
        # Load source bed and ward
        if rec.source_bed_id:
            source_res = await db.execute(
                select(models.Bed).options(selectinload(models.Bed.ward)).where(models.Bed.id == rec.source_bed_id)
            )
            rec.source_bed = source_res.scalar_one_or_none()
        else:
            rec.source_bed = None

        # Load partner hospital
        if rec.partner_hospital_id:
            partner_res = await db.execute(
                select(models.PartnerHospital).where(models.PartnerHospital.id == rec.partner_hospital_id)
            )
            rec.partner_hospital = partner_res.scalar_one_or_none()
        else:
            rec.partner_hospital = None
            
    return recs

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((OperationalError, DBAPIError)),
    after=increment_retry_counter,
    reraise=True
)
async def action_recommendation(db: AsyncSession, rec_id: int, action: str, user_id: int, payload: Optional[schemas.RecommendationRejectPayload] = None) -> models.Recommendation:
    try:
        # 1. Fetch the recommendation
        rec_result = await db.execute(
            select(models.Recommendation)
            .options(selectinload(models.Recommendation.patient))
            .where(models.Recommendation.id == rec_id)
        )
        recommendation = rec_result.scalar_one_or_none()
        
        if not recommendation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recommendation ID {rec_id} not found."
            )
            
        if recommendation.status != models.RecommendationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflict: Recommendation {rec_id} has already been actioned (current state: {recommendation.status.value})."
            )
            
        # 1.5. Check expiration BEFORE heavy locks
        if recommendation.expires_at and datetime.utcnow() > recommendation.expires_at:
            recommendation.status = models.RecommendationStatus.EXPIRED
            elapsed_seconds = (datetime.utcnow() - recommendation.created_at).total_seconds()
            await log_operational_event(
                db,
                recommendation.patient_id,
                "COORDINATOR_ACTION",
                {
                    "recommendation_id": recommendation.id,
                    "action": "EXPIRED",
                    "response_time_seconds": round(elapsed_seconds, 2)
                }
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recommendation has expired."
            )

        # 2. Update status and approved parameters
        before_data = serialize_recommendation(recommendation)
        recommendation.actioned_by_user_id = user_id
        
        if action == "REJECT":
            recommendation.status = models.RecommendationStatus.REJECTED
            if payload and payload.reason:
                recommendation.override_reason = payload.reason
            after_data = serialize_recommendation(recommendation)
            await create_audit_log(db, "ACTION_REJECT", "recommendation", rec_id, before_data, after_data, str(user_id))
            
            reject_event = models.ClinicalEvent(
                patient_id=recommendation.patient_id,
                event_type=models.ClinicalEventType.RECOMMENDATION_REJECTED,
                description="Clinical recommendation was manually rejected.",
                event_metadata={"recommendation_id": recommendation.id, "override_reason": recommendation.override_reason},
                actor_id=user_id
            )
            db.add(reject_event)

            elapsed_seconds = (datetime.utcnow() - recommendation.created_at).total_seconds()
            await log_operational_event(
                db,
                recommendation.patient_id,
                "COORDINATOR_ACTION",
                {
                    "recommendation_id": recommendation.id,
                    "action": "REJECT",
                    "response_time_seconds": round(elapsed_seconds, 2)
                }
            )

            await db.commit()
            return recommendation
            
        if action == "APPROVE":
            recommendation.approved_by_user_id = user_id
            recommendation.approved_at = datetime.utcnow()
            recommendation.status = models.RecommendationStatus.APPROVED
            
            # If external transfer recommendation
            if recommendation.partner_hospital_id:
                # 1. Update TransferRequest status to APPROVED
                transfer_result = await db.execute(
                    select(models.TransferRequest)
                    .where(models.TransferRequest.patient_id == recommendation.patient_id)
                    .where(models.TransferRequest.partner_hospital_id == recommendation.partner_hospital_id)
                    .where(models.TransferRequest.status == models.TransferRequestStatus.PENDING)
                )
                transfer_req = transfer_result.scalar_one_or_none()
                if transfer_req:
                    transfer_req.status = models.TransferRequestStatus.APPROVED
                
                # 2. Release local source bed
                if recommendation.source_bed_id:
                    source_bed_result = await db.execute(
                        select(models.Bed)
                        .where(models.Bed.id == recommendation.source_bed_id)
                        .with_for_update(nowait=False)
                    )
                    source_bed = source_bed_result.scalar_one_or_none()
                    if source_bed:
                        source_bed.status = models.BedStatus.AVAILABLE
                        source_bed.patient_id = None
                        recommendation.source_bed = source_bed
                
                # 3. Discharge patient from local hospital (set discharged_at and remove current_bed_id)
                recommendation.patient.current_bed_id = None
                recommendation.patient.discharged_at = datetime.utcnow()
                
                # 4. Decrement partner hospital ICU bed count
                partner_result = await db.execute(
                    select(models.PartnerHospital)
                    .where(models.PartnerHospital.id == recommendation.partner_hospital_id)
                    .with_for_update()
                )
                partner = partner_result.scalar_one_or_none()
                if partner:
                    if partner.icu_beds_available > 0:
                        partner.icu_beds_available -= 1
                    recommendation.partner_hospital = partner
                
                after_data = serialize_recommendation(recommendation)
                await create_audit_log(db, "ACTION_APPROVE", "recommendation", rec_id, before_data, after_data, str(user_id))
                
                approve_event = models.ClinicalEvent(
                    patient_id=recommendation.patient_id,
                    event_type=models.ClinicalEventType.RECOMMENDATION_APPROVED,
                    description=f"External transfer to {partner.name if partner else 'Partner Hospital'} approved.",
                    event_metadata={"recommendation_id": recommendation.id, "partner_hospital_id": recommendation.partner_hospital_id},
                    actor_id=user_id
                )
                db.add(approve_event)

                elapsed_seconds = (datetime.utcnow() - recommendation.created_at).total_seconds()
                await log_operational_event(
                    db,
                    recommendation.patient_id,
                    "COORDINATOR_ACTION",
                    {
                        "recommendation_id": recommendation.id,
                        "action": "APPROVE",
                        "response_time_seconds": round(elapsed_seconds, 2)
                    }
                )

                await db.commit()
                return recommendation
            # If chained transfer recommendation
            if hasattr(recommendation, "recommendation_type") and recommendation.recommendation_type == models.RecommendationType.CHAINED_TRANSFER:
                # 1. Lock the beds numerically to prevent deadlocks
                lock_ids = sorted([
                    bid for bid in [
                        recommendation.source_bed_id, 
                        recommendation.target_bed_id, 
                        recommendation.chained_target_bed_id
                    ] if bid is not None
                ])
                
                beds_map = {}
                for bid in lock_ids:
                    bed_res = await db.execute(
                        select(models.Bed).where(models.Bed.id == bid).with_for_update(nowait=False)
                    )
                    beds_map[bid] = bed_res.scalar_one_or_none()
                    
                # 2. Lock recommendation.chained_patient row
                stable_patient_res = await db.execute(
                    select(models.Patient).where(models.Patient.id == recommendation.chained_patient_id).with_for_update()
                )
                stable_patient = stable_patient_res.scalar_one_or_none()
                if not stable_patient:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Chained step-down patient not found."
                    )
                
                # Check target ward bed availability
                gw_bed = beds_map.get(recommendation.chained_target_bed_id)
                if not gw_bed or gw_bed.status != models.BedStatus.AVAILABLE:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Conflict: Chained target general ward bed is no longer AVAILABLE."
                    )
                    
                # Check ICU bed occupancy by the step-down patient
                icu_bed = beds_map.get(recommendation.target_bed_id)
                if not icu_bed or icu_bed.patient_id != recommendation.chained_patient_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Conflict: Chained ICU bed is not occupied by the expected step-down patient."
                    )
                
                # Step 1: Move stable patient to General Ward
                icu_bed.patient_id = None
                icu_bed.status = models.BedStatus.AVAILABLE  # Free up ICU bed
                
                gw_bed.status = models.BedStatus.OCCUPIED
                gw_bed.patient_id = stable_patient.id
                stable_patient.current_bed_id = gw_bed.id
                
                # Step 2: Move critical patient to freed ICU bed
                source_bed = beds_map.get(recommendation.source_bed_id)
                if source_bed:
                    source_bed.status = models.BedStatus.AVAILABLE
                    source_bed.patient_id = None
                    
                icu_bed.status = models.BedStatus.OCCUPIED
                icu_bed.patient_id = recommendation.patient_id
                recommendation.patient.current_bed_id = icu_bed.id
                
                # Eagerly assign helper attributes for serialization output
                recommendation.target_bed = icu_bed
                recommendation.source_bed = source_bed
                recommendation.chained_patient = stable_patient
                recommendation.chained_target_bed = gw_bed
                
                after_data = serialize_recommendation(recommendation)
                await create_audit_log(db, "ACTION_APPROVE_CHAINED", "recommendation", rec_id, before_data, after_data, str(user_id))
                
                approve_event = models.ClinicalEvent(
                    patient_id=recommendation.patient_id,
                    event_type=models.ClinicalEventType.RECOMMENDATION_APPROVED,
                    description=f"Chained transfer approved. Patient escalating to ICU bed.",
                    event_metadata={"recommendation_id": recommendation.id, "type": "CHAINED_TRANSFER"},
                    actor_id=user_id
                )
                db.add(approve_event)

                stepdown_event = models.ClinicalEvent(
                    patient_id=stable_patient.id,
                    event_type=models.ClinicalEventType.TRANSFER_COMPLETED,
                    description=f"Stepped down to General Ward (Chained Transfer).",
                    event_metadata={"recommendation_id": recommendation.id},
                    actor_id=user_id
                )
                db.add(stepdown_event)

                elapsed_seconds = (datetime.utcnow() - recommendation.created_at).total_seconds()
                await log_operational_event(
                    db,
                    recommendation.patient_id,
                    "COORDINATOR_ACTION",
                    {
                        "recommendation_id": recommendation.id,
                        "action": "APPROVE",
                        "response_time_seconds": round(elapsed_seconds, 2)
                    }
                )

                await db.commit()
                return recommendation

            # If standard internal bed transfer recommendation
            target_bed_result = await db.execute(
                select(models.Bed)
                .where(models.Bed.id == recommendation.target_bed_id)
                .with_for_update(nowait=False)
            )
            target_bed = target_bed_result.scalar_one_or_none()
            
            if not target_bed:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Target bed ID {recommendation.target_bed_id} not found."
                )
                
            if target_bed.status != models.BedStatus.AVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Concurrency Conflict: Target bed {target_bed.bed_number} is no longer AVAILABLE (snagged by other operator)."
                )
                
            # Free old source bed if it exists
            if recommendation.source_bed_id:
                source_bed_result = await db.execute(
                    select(models.Bed)
                    .where(models.Bed.id == recommendation.source_bed_id)
                    .with_for_update(nowait=False)
                )
                source_bed = source_bed_result.scalar_one_or_none()
                if source_bed:
                    source_bed.status = models.BedStatus.AVAILABLE
                    source_bed.patient_id = None
                    
            # Occupy target bed
            target_bed.status = models.BedStatus.OCCUPIED
            target_bed.patient_id = recommendation.patient_id
            
            # Update patient current bed
            recommendation.patient.current_bed_id = target_bed.id
            
            # Eagerly assign helper attributes for serialization output
            recommendation.target_bed = target_bed
            recommendation.source_bed = source_bed if recommendation.source_bed_id else None
            
            after_data = serialize_recommendation(recommendation)
            await create_audit_log(db, "ACTION_APPROVE", "recommendation", rec_id, before_data, after_data, str(user_id))
            
            approve_event = models.ClinicalEvent(
                patient_id=recommendation.patient_id,
                event_type=models.ClinicalEventType.RECOMMENDATION_APPROVED,
                description=f"Internal transfer to bed {target_bed.bed_number} approved.",
                event_metadata={"recommendation_id": recommendation.id, "target_bed_id": target_bed.id},
                actor_id=user_id
            )
            db.add(approve_event)

            elapsed_seconds = (datetime.utcnow() - recommendation.created_at).total_seconds()
            await log_operational_event(
                db,
                recommendation.patient_id,
                "COORDINATOR_ACTION",
                {
                    "recommendation_id": recommendation.id,
                    "action": "APPROVE",
                    "response_time_seconds": round(elapsed_seconds, 2)
                }
            )

            await db.commit()
            return recommendation
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action: {action}. Must be APPROVE or REJECT."
        )
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database transaction failed: {e}"
        )


async def get_active_alerts(db: AsyncSession) -> List[models.Alert]:
    result = await db.execute(
        select(models.Alert)
        .options(selectinload(models.Alert.patient))
        .where(models.Alert.status.in_([
            models.AlertStatus.CREATED,
            models.AlertStatus.ASSIGNED,
            models.AlertStatus.ACKNOWLEDGED,
            models.AlertStatus.IN_PROGRESS,
            models.AlertStatus.ESCALATED
        ]))
        .order_by(models.Alert.created_at.desc())
    )
    return result.scalars().all()


async def acknowledge_alert(db: AsyncSession, alert_id: int, user_id: Optional[int] = None) -> models.Alert:
    try:
        result = await db.execute(
            select(models.Alert)
            .options(selectinload(models.Alert.patient))
            .where(models.Alert.id == alert_id)
            .with_for_update()
        )
        alert = result.scalar_one_or_none()
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert ID {alert_id} not found."
            )
        
        before_data = serialize_alert(alert)
        alert.is_acknowledged = True
        alert.status = models.AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = user_id
        alert.acknowledged_at = datetime.utcnow()
        after_data = serialize_alert(alert)
        
        await create_audit_log(
            db,
            action="ACKNOWLEDGE",
            entity_type="alert",
            entity_id=alert_id,
            before_data=before_data,
            after_data=after_data,
            user_id=str(user_id) if user_id else None
        )
        await db.commit()
        return alert
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to acknowledge alert: {e}"
        )


async def resolve_alert(db: AsyncSession, alert_id: int, payload: schemas.AlertResolvePayload, user_id: Optional[int] = None) -> models.Alert:
    try:
        result = await db.execute(
            select(models.Alert)
            .options(selectinload(models.Alert.patient))
            .where(models.Alert.id == alert_id)
            .with_for_update()
        )
        alert = result.scalar_one_or_none()
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert ID {alert_id} not found."
            )
            
        before_data = serialize_alert(alert)
        alert.status = models.AlertStatus.RESOLVED
        alert.resolved_by = user_id or payload.user_id
        alert.resolved_at = datetime.utcnow()
        alert.resolution_note = payload.resolution_note
        after_data = serialize_alert(alert)
        
        await create_audit_log(
            db,
            action="RESOLVE_ALERT",
            entity_type="alert",
            entity_id=alert_id,
            before_data=before_data,
            after_data=after_data,
            user_id=str(alert.resolved_by) if alert.resolved_by else None
        )
        
        # Complete related tasks
        tasks_result = await db.execute(
            select(models.ClinicalTask)
            .where(models.ClinicalTask.alert_id == alert_id)
            .where(models.ClinicalTask.status.in_([models.TaskStatus.PENDING, models.TaskStatus.ASSIGNED, models.TaskStatus.IN_PROGRESS]))
        )
        for task in tasks_result.scalars().all():
            task.status = models.TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.completion_note = "Resolved via alert resolution."
            
        await db.commit()
        return alert
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve alert: {e}"
        )


async def get_notifications(db: AsyncSession, user_id: int, role: str) -> List[models.Notification]:
    from sqlalchemy import or_
    result = await db.execute(
        select(models.Notification)
        .where(
            models.Notification.is_read == False,
            or_(
                models.Notification.recipient_user_id == user_id,
                models.Notification.recipient_role == role
            )
        )
        .order_by(models.Notification.created_at.desc())
    )
    return result.scalars().all()


async def get_partner_hospitals(db: AsyncSession) -> List[models.PartnerHospital]:
    result = await db.execute(
        select(models.PartnerHospital)
        .order_by(models.PartnerHospital.distance_km.asc())
    )
    return result.scalars().all()


async def get_transfer_requests(db: AsyncSession) -> List[models.TransferRequest]:
    result = await db.execute(
        select(models.TransferRequest)
        .options(
            selectinload(models.TransferRequest.patient),
            selectinload(models.TransferRequest.partner_hospital)
        )
        .order_by(models.TransferRequest.created_at.desc())
    )
    return result.scalars().all()


async def update_bed_status(db: AsyncSession, bed_id: int, status_val: models.BedStatus) -> models.Bed:
    try:
        # Lock bed for update
        result = await db.execute(
            select(models.Bed)
            .options(selectinload(models.Bed.patient))
            .where(models.Bed.id == bed_id)
            .with_for_update(nowait=False)
        )
        bed = result.scalar_one_or_none()
        if not bed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bed ID {bed_id} not found."
            )
            
        if status_val != models.BedStatus.OCCUPIED and bed.patient_id is not None:
             raise HTTPException(
                 status_code=status.HTTP_409_CONFLICT,
                 detail="Cannot manually change status of occupied bed. Please discharge or transfer the patient first."
             )
             
        before_data = serialize_bed(bed)
        bed.status = status_val
        after_data = serialize_bed(bed)
        
        await create_audit_log(
            db,
            action="UPDATE_STATUS",
            entity_type="bed",
            entity_id=bed_id,
            before_data=before_data,
            after_data=after_data
        )
        await db.commit()
        return bed
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update bed status: {e}"
        )


async def get_patient_baseline(db: AsyncSession, patient_id: int) -> Optional[models.PatientBaseline]:
    result = await db.execute(
        select(models.PatientBaseline)
        .where(models.PatientBaseline.patient_id == patient_id)
    )
    return result.scalar_one_or_none()


async def create_doctor_feedback(db: AsyncSession, patient_id: int, payload: schemas.DoctorFeedbackCreate, user_id: int) -> models.DoctorFeedback:
    feedback = models.DoctorFeedback(
        patient_id=patient_id,
        score_record_id=payload.score_record_id,
        recommendation_id=payload.recommendation_id,
        feedback_type=payload.feedback_type,
        comment=payload.comment,
        created_by=user_id
    )
    db.add(feedback)
    await db.commit()
    return feedback


async def create_patient_baseline(db: AsyncSession, patient_id: int, payload: schemas.PatientBaselineCreate, user_id: int) -> models.PatientBaseline:
    # Upsert logic since patient_id is unique
    result = await db.execute(
        select(models.PatientBaseline)
        .where(models.PatientBaseline.patient_id == patient_id)
        .with_for_update()
    )
    existing_baseline = result.scalar_one_or_none()
    
    if existing_baseline:
        existing_baseline.baseline_spo2 = payload.baseline_spo2
        existing_baseline.baseline_heart_rate = payload.baseline_heart_rate
        existing_baseline.baseline_systolic_bp = payload.baseline_systolic_bp
        existing_baseline.baseline_respiratory_rate = payload.baseline_respiratory_rate
        existing_baseline.notes = payload.notes
        existing_baseline.approved_by = user_id
        await db.commit()
        return existing_baseline
    else:
        new_baseline = models.PatientBaseline(
            patient_id=patient_id,
            baseline_spo2=payload.baseline_spo2,
            baseline_heart_rate=payload.baseline_heart_rate,
            baseline_systolic_bp=payload.baseline_systolic_bp,
            baseline_respiratory_rate=payload.baseline_respiratory_rate,
            notes=payload.notes,
            approved_by=user_id
        )
        db.add(new_baseline)
        await db.commit()
        return new_baseline
