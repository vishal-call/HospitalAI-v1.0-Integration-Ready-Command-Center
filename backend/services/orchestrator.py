import os
from typing import Optional, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from models import PatientStatus, WardType, BedStatus, RecommendationStatus
from services.scoring import calculate_criticality_score

from datetime import datetime, timedelta

async def evaluate_patient_and_recommend(
    db: AsyncSession,
    patient: models.Patient,
    vitals: Optional[Dict[str, int]],
    shadow_mode_enabled: bool = False
) -> Optional[models.Recommendation]:
    """
    Evaluates patient vitals, calculates criticality, updates patient fields,
    and dynamically routes clinical recommendations to the HITL queue if a transfer is required.
    """
    if vitals is not None:
        hr = vitals.get("heart_rate", 80)
        rr = vitals.get("resp_rate", 16)
        spo2 = vitals.get("spo2", 98)

        # 1. Deterministic scoring
        score = calculate_criticality_score(hr, rr, spo2)
    else:
        score = patient.criticality_score

    
    # 2. Update patient health status metrics
    patient.criticality_score = score
    if score >= 8.0:
        patient.status = PatientStatus.CRITICAL
    elif score >= 4.0:
        patient.status = PatientStatus.SERIOUS
    else:
        patient.status = PatientStatus.STABLE
        
    await db.flush()

    # 3. Determine if transfer is needed based on current bed and ward type
    # First, get the patient's current bed and ward
    if not patient.current_bed_id:
        # Patient is not currently in a bed, no transfer assessment needed (or they are incoming)
        return None
        
    current_bed_result = await db.execute(
        select(models.Bed)
        .options(selectinload(models.Bed.ward))
        .where(models.Bed.id == patient.current_bed_id)
    )
    current_bed = current_bed_result.scalar_one_or_none()
    if not current_bed or not current_bed.ward:
        return None

    current_ward = current_bed.ward
    target_ward_type: Optional[WardType] = None

    # Routing rules:
    # If Critical but not in ICU -> Target ICU
    if patient.status == PatientStatus.CRITICAL and current_ward.type != WardType.ICU:
        target_ward_type = WardType.ICU
    # If Serious but in General Ward -> Target EMERGENCY
    elif patient.status == PatientStatus.SERIOUS and current_ward.type == WardType.GENERAL:
        target_ward_type = WardType.EMERGENCY

    if not target_ward_type:
        # Already in correct ward level or stable
        return None

    # 4. Check if a pending recommendation already exists to prevent duplication
    pending_check = await db.execute(
        select(models.Recommendation)
        .where(models.Recommendation.patient_id == patient.id)
        .where(models.Recommendation.status == RecommendationStatus.PENDING)
    )
    existing_rec = pending_check.scalar_one_or_none()
    if existing_rec:
        return existing_rec

    # 5. Search for an available bed in the target ward type
    target_bed_query = (
        select(models.Bed)
        .join(models.Ward)
        .where(models.Ward.type == target_ward_type)
        .where(models.Bed.status == BedStatus.AVAILABLE)
        .limit(1)
    )
    target_bed_result = await db.execute(target_bed_query)
    target_bed = target_bed_result.scalar_one_or_none()

    if not target_bed:
        # No beds available in target ward. If targeting ICU, evaluate for step-down relocation
        if target_ward_type == WardType.ICU:
            stepdown_rec = await run_icu_step_down_agent(db, patient)
            if stepdown_rec:
                return stepdown_rec
            # If no step-down candidate is found, evaluate for external transfer to partner network
            return await run_inter_hospital_agent(db, patient)
        return None

    # 6. Generate reasoning text (incorporating LLM fallback / Template fallback)
    target_ward_name = "ICU" if target_ward_type == WardType.ICU else "Emergency Department"
    
    # Template-driven reasoning fallback
    reasoning = (
        f"Patient displays heart rate of {hr} bpm, respiratory rate of {rr} breaths/min, "
        f"and oxygen saturation of {spo2}%. This triggers a clinical criticality score of {score}/10.0, "
        f"placing them in a {patient.status.value} condition. Recommend immediate transfer "
        f"from {current_ward.name} to {target_ward_name} for continuous observation."
    )
    
    # Check if a custom LLM key is set (Mock representation of the AI routing agent)
    # In a real environment, we would make a call to Google Gemini / Vertex AI here.
    if os.getenv("GEMINI_API_KEY"):
        # Simulated LLM generation if key is present
        # In a real application, we would call our LLM agent router here.
        pass

    # 7. Create the Recommendation in PENDING state
    expires_at = None if shadow_mode_enabled else datetime.utcnow() + timedelta(minutes=5)
    
    recommendation = models.Recommendation(
        patient_id=patient.id,
        source_bed_id=patient.current_bed_id,
        target_bed_id=target_bed.id,
        status=RecommendationStatus.PENDING,
        criticality_score=score,
        reasoning=reasoning,
        expires_at=expires_at,
        is_shadow=shadow_mode_enabled
    )
    db.add(recommendation)
    await db.flush()

    event_type = models.ClinicalEventType.SHADOW_RECOMMENDATION_GENERATED if shadow_mode_enabled else models.ClinicalEventType.RECOMMENDATION_GENERATED
    gen_event = models.ClinicalEvent(
        patient_id=patient.id,
        event_type=event_type,
        description=f"{'Shadow ' if shadow_mode_enabled else ''}Generated internal transfer recommendation to {target_ward_name}.",
        event_metadata={"recommendation_id": recommendation.id, "target_ward": target_ward_name, "score": score, "is_shadow": shadow_mode_enabled},
    )
    db.add(gen_event)

    return recommendation


async def run_icu_step_down_agent(
    db: AsyncSession,
    incoming_patient: models.Patient
) -> Optional[models.Recommendation]:
    """
    Invoked when ICU is at 100% capacity and a critical patient requires a bed.
    Scans for stable patients currently occupying ICU beds (score <= 3.0).
    If found and a General Ward bed is available, recommends a CHAINED_TRANSFER
    stepping the stable patient down to the GW and moving the critical patient to the ICU.
    """
    # 1. Verify ICU capacity is strictly 100%
    icu_ward_result = await db.execute(
        select(models.Ward)
        .options(selectinload(models.Ward.beds))
        .where(models.Ward.type == models.WardType.ICU)
    )
    icu_ward = icu_ward_result.scalar_one_or_none()
    if not icu_ward:
        return None
        
    occupied_count = sum(1 for bed in icu_ward.beds if bed.status == models.BedStatus.OCCUPIED)
    if occupied_count < icu_ward.capacity:
        # Not at 100% capacity
        return None
        
    # ICU is at 100% capacity!
    # 2. Check if we already have an active ICU_AT_CAPACITY alert to prevent duplicate writes
    alert_check = await db.execute(
        select(models.Alert)
        .where(models.Alert.alert_type == models.AlertType.ICU_AT_CAPACITY)
        .where(models.Alert.is_acknowledged == False)
    )
    existing_alert = alert_check.scalar_one_or_none()
    if not existing_alert:
        capacity_alert = models.Alert(
            patient_id=None,
            alert_type=models.AlertType.ICU_AT_CAPACITY,
            severity=models.AlertSeverity.HIGH,
            message=f"ICU Ward at 100% capacity ({icu_ward.capacity}/{icu_ward.capacity} beds occupied). Step-down evaluations triggered.",
            is_acknowledged=False
        )
        db.add(capacity_alert)
        
    # 3. Find stable patients currently in ICU beds (score <= 3.0)
    stable_patients_query = (
        select(models.Patient)
        .join(models.Bed, models.Patient.id == models.Bed.patient_id)
        .join(models.Ward, models.Bed.ward_id == models.Ward.id)
        .where(models.Ward.type == models.WardType.ICU)
        .where(models.Patient.criticality_score <= 3.0)
        .where(models.Patient.discharged_at == None)
        .order_by(models.Patient.criticality_score.asc()) # pick the most stable first
    )
    stable_res = await db.execute(stable_patients_query)
    stable_patients = stable_res.scalars().all()
    
    if not stable_patients:
        # No stable patients available in ICU for step-down
        return None
        
    stable_patient = stable_patients[0]
    
    # 4. Search for a vacant General Ward bed (type GENERAL)
    gw_bed_query = (
        select(models.Bed)
        .join(models.Ward)
        .where(models.Ward.type == models.WardType.GENERAL)
        .where(models.Bed.status == models.BedStatus.AVAILABLE)
        .limit(1)
    )
    gw_res = await db.execute(gw_bed_query)
    gw_bed = gw_res.scalar_one_or_none()
    
    if not gw_bed:
        # No general ward beds available to receive the step-down patient
        return None
        
    # 5. Check if there is already a pending recommendation for the incoming critical patient
    pending_check = await db.execute(
        select(models.Recommendation)
        .where(models.Recommendation.patient_id == incoming_patient.id)
        .where(models.Recommendation.status == models.RecommendationStatus.PENDING)
    )
    existing_rec = pending_check.scalar_one_or_none()
    if existing_rec:
        return existing_rec

    # Also check if there is a pending recommendation involving the stable patient
    pending_stable_check = await db.execute(
        select(models.Recommendation)
        .where(
            (models.Recommendation.patient_id == stable_patient.id) | 
            (models.Recommendation.chained_patient_id == stable_patient.id)
        )
        .where(models.Recommendation.status == models.RecommendationStatus.PENDING)
    )
    existing_stable_rec = pending_stable_check.scalar_one_or_none()
    if existing_stable_rec:
        return None
        
    # 6. Fetch bed numbers for detailed reasoning
    stable_patient_bed = None
    if stable_patient.current_bed_id:
        stable_bed_res = await db.execute(
            select(models.Bed).where(models.Bed.id == stable_patient.current_bed_id)
        )
        stable_patient_bed = stable_bed_res.scalar_one_or_none()

    incoming_patient_bed = None
    if incoming_patient.current_bed_id:
        incoming_bed_res = await db.execute(
            select(models.Bed).where(models.Bed.id == incoming_patient.current_bed_id)
        )
        incoming_patient_bed = incoming_bed_res.scalar_one_or_none()

    # 7. Generate the pending CHAINED_TRANSFER recommendation
    reasoning = (
        f"Chained Transfer: Step 1: Move stable patient {stable_patient.name} from "
        f"bed {stable_patient_bed.bed_number if stable_patient_bed else 'ICU'} to general ward bed {gw_bed.bed_number}. "
        f"Step 2: Move critical patient {incoming_patient.name} from bed {incoming_patient_bed.bed_number if incoming_patient_bed else 'GW'} "
        f"to the newly freed ICU bed {stable_patient_bed.bed_number if stable_patient_bed else 'ICU'}."
    )
    
    chained_rec = models.Recommendation(
        patient_id=incoming_patient.id,
        source_bed_id=incoming_patient.current_bed_id,
        target_bed_id=stable_patient.current_bed_id,
        chained_patient_id=stable_patient.id,
        chained_target_bed_id=gw_bed.id,
        recommendation_type=models.RecommendationType.CHAINED_TRANSFER,
        status=models.RecommendationStatus.PENDING,
        criticality_score=incoming_patient.criticality_score,
        reasoning=reasoning,
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    db.add(chained_rec)
    await db.flush()
    
    gen_event = models.ClinicalEvent(
        patient_id=incoming_patient.id,
        event_type=models.ClinicalEventType.RECOMMENDATION_GENERATED,
        description=f"Generated CHAINED_TRANSFER recommendation.",
        event_metadata={"recommendation_id": chained_rec.id, "chained_patient_id": stable_patient.id},
    )
    db.add(gen_event)
    
    # Preload relationship attributes for response mapping
    chained_rec.chained_patient = stable_patient
    chained_rec.chained_target_bed = gw_bed
    
    return chained_rec


async def run_inter_hospital_agent(
    db: AsyncSession,
    incoming_patient: models.Patient
) -> Optional[models.Recommendation]:
    """
    Invoked when local ICU is at 100% capacity and no internal step-down is possible.
    Finds the closest partner hospital with available ICU beds, and generates
    a PENDING TransferRequest and Recommendation.
    """
    # 1. Query PartnerHospital table for facilities where icu_beds_available > 0
    # and sort by distance_km (ascending)
    query = (
        select(models.PartnerHospital)
        .where(models.PartnerHospital.icu_beds_available > 0)
        .order_by(models.PartnerHospital.distance_km.asc())
    )
    res = await db.execute(query)
    partners = res.scalars().all()
    
    if not partners:
        # No partner hospitals with available ICU beds
        return None
        
    closest_partner = partners[0]
    
    # 2. Check if a pending recommendation for this patient already exists
    pending_check = await db.execute(
        select(models.Recommendation)
        .where(models.Recommendation.patient_id == incoming_patient.id)
        .where(models.Recommendation.status == models.RecommendationStatus.PENDING)
    )
    existing_rec = pending_check.scalar_one_or_none()
    if existing_rec:
        return existing_rec
        
    # 3. Create a PENDING TransferRequest record
    transfer_request = models.TransferRequest(
        patient_id=incoming_patient.id,
        partner_hospital_id=closest_partner.id,
        reason=f"Local ICU at absolute capacity with no viable step-down candidates.",
        status=models.TransferRequestStatus.PENDING
    )
    db.add(transfer_request)
    await db.flush()
    
    # 4. Generate the Recommendation record linking to the external transfer
    reasoning = (
        f"Local ICU at absolute capacity with no viable step-down candidates. "
        f"Recommend immediate external transfer to {closest_partner.name} "
        f"(Distance: {closest_partner.distance_km:.1f} km) which reports available ICU capacity."
    )
    
    recommendation = models.Recommendation(
        patient_id=incoming_patient.id,
        source_bed_id=incoming_patient.current_bed_id,
        target_bed_id=None, # external transfer has no local target bed
        partner_hospital_id=closest_partner.id,
        status=models.RecommendationStatus.PENDING,
        criticality_score=incoming_patient.criticality_score,
        reasoning=reasoning,
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    db.add(recommendation)
    await db.flush()
    
    gen_event = models.ClinicalEvent(
        patient_id=incoming_patient.id,
        event_type=models.ClinicalEventType.RECOMMENDATION_GENERATED,
        description=f"Generated external transfer recommendation to {closest_partner.name}.",
        event_metadata={"recommendation_id": recommendation.id, "partner_hospital_id": closest_partner.id},
    )
    db.add(gen_event)
    
    # Preload relationship attributes for response mapping
    recommendation.partner_hospital = closest_partner
    
    return recommendation
