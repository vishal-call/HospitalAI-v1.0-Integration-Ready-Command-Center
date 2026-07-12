from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import logging
from typing import Optional, Tuple, Dict, Any

import models
import schemas
import crud
from database import get_db
from services.api_key_service import verify_api_key

logger = logging.getLogger("HospitalAI-Interop")

router = APIRouter(prefix="/api/interop", tags=["Interoperability"])

def parse_hl7_message(raw_msg: str) -> Tuple[Optional[int], Dict[str, Any]]:
    """Parse standard pipe-delimited HL7 v2 ORU^R01 Observation Message."""
    lines = [line.strip() for line in raw_msg.replace("\r", "\n").split("\n") if line.strip()]
    patient_id = None
    vitals = {}

    for line in lines:
        fields = line.split("|")
        if not fields:
            continue
        segment_id = fields[0]

        if segment_id == "PID":
            # PID|1||PATIENT_ID||...
            p_id = None
            if len(fields) > 3 and fields[3]:
                p_id = fields[3]
            elif len(fields) > 2 and fields[2]:
                p_id = fields[2]
            
            if p_id:
                if "^" in p_id:
                    p_id = p_id.split("^")[0]
                try:
                    patient_id = int(p_id)
                except ValueError:
                    pass

        elif segment_id == "OBX":
            # OBX|1|NM|8867-4^Heart Rate^LN||72|bpm|||||F
            if len(fields) > 5:
                obs_id = fields[3].lower()
                obs_val_str = fields[5]

                # If blood pressure composite is present as text value
                if "bp" in obs_id or "blood pressure" in obs_id or "8480-6" in obs_id or "8462-4" in obs_id:
                    if "/" in obs_val_str:
                        sys_dia = obs_val_str.split("/")
                        try:
                            vitals["systolic_bp"] = int(sys_dia[0])
                            vitals["diastolic_bp"] = int(sys_dia[1])
                        except ValueError:
                            pass
                        continue

                try:
                    obs_val = float(obs_val_str)
                except ValueError:
                    continue

                if "heart rate" in obs_id or "8867-4" in obs_id or "hr" == obs_id or "heart_rate" in obs_id:
                    vitals["heart_rate"] = int(obs_val)
                elif "resp" in obs_id or "respiratory" in obs_id or "9279-1" in obs_id or "rr" == obs_id or "resp_rate" in obs_id:
                    vitals["resp_rate"] = int(obs_val)
                elif "spo2" in obs_id or "oxygen saturation" in obs_id or "2708-6" in obs_id or "oxygen_saturation" in obs_id:
                    vitals["spo2"] = int(obs_val)
                elif "temp" in obs_id or "temperature" in obs_id or "8310-5" in obs_id:
                    vitals["temperature"] = obs_val
                elif "systolic" in obs_id or "8480-6" in obs_id:
                    vitals["systolic_bp"] = int(obs_val)
                elif "diastolic" in obs_id or "8462-4" in obs_id:
                    vitals["diastolic_bp"] = int(obs_val)

    return patient_id, vitals

def parse_fhir_observation(data: Dict[str, Any]) -> Tuple[Optional[int], Dict[str, Any]]:
    """Parse HL7 FHIR JSON Observation resource."""
    patient_id = None
    vitals = {}

    # Extract Patient ID from subject
    subject = data.get("subject", {})
    ref = subject.get("reference", "")
    if ref and "/" in ref:
        parts = ref.split("/")
        if parts[0].lower() == "patient":
            try:
                patient_id = int(parts[1])
            except ValueError:
                pass
    else:
        ident = subject.get("identifier", {})
        val = ident.get("value")
        if val:
            try:
                patient_id = int(val)
            except ValueError:
                pass

    def parse_component(comp: Dict[str, Any]):
        code_data = comp.get("code", {})
        codings = code_data.get("coding", [])
        codes = [c.get("code", "").lower() for c in codings]
        displays = [c.get("display", "").lower() for c in codings]

        val_qty = comp.get("valueQuantity", {})
        val = val_qty.get("value")
        if val is None:
            val = comp.get("valueInteger")
            if val is None:
                val = comp.get("valueString")

        if val is not None:
            try:
                val_num = float(val)
            except ValueError:
                return

            matched = False
            for code in codes:
                if "8867-4" in code:
                    vitals["heart_rate"] = int(val_num); matched = True
                elif "9279-1" in code:
                    vitals["resp_rate"] = int(val_num); matched = True
                elif "2708-6" in code:
                    vitals["spo2"] = int(val_num); matched = True
                elif "8310-5" in code:
                    vitals["temperature"] = val_num; matched = True
                elif "8480-6" in code:
                    vitals["systolic_bp"] = int(val_num); matched = True
                elif "8462-4" in code:
                    vitals["diastolic_bp"] = int(val_num); matched = True

            if not matched:
                for display in displays:
                    if "heart rate" in display or "hr" == display or "heart_rate" in display:
                        vitals["heart_rate"] = int(val_num)
                    elif "resp" in display or "respiratory" in display or "rr" == display or "resp_rate" in display:
                        vitals["resp_rate"] = int(val_num)
                    elif "spo2" in display or "oxygen saturation" in display:
                        vitals["spo2"] = int(val_num)
                    elif "temp" in display or "temperature" in display:
                        vitals["temperature"] = val_num
                    elif "systolic" in display:
                        vitals["systolic_bp"] = int(val_num)
                    elif "diastolic" in display:
                        vitals["diastolic_bp"] = int(val_num)

    # Handle composite or single FHIR formats
    components = data.get("component", [])
    if components:
        for comp in components:
            parse_component(comp)
    else:
        parse_component(data)

    return patient_id, vitals

@router.post("/hl7/observation", response_model=schemas.PatientResponse)
async def ingest_clinical_observation(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_integration_key: Optional[str] = Header(None, alias="X-Integration-Key"),
    db: AsyncSession = Depends(get_db)
):
    """Secure endpoint to ingest legacy HL7 ORU^R01 or modern FHIR Observation webhook payloads."""
    # 1. Authenticate Request
    auth_header = request.headers.get("Authorization")
    key = x_api_key or x_integration_key
    if not key and auth_header and auth_header.startswith("Bearer "):
        key = auth_header.split(" ", 1)[1]

    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API credentials. Provide X-API-Key or Bearer token."
        )

    # Allow custom secret for internal testing convenience
    if key != "TEST_SECRET_HL7":
        api_key = await verify_api_key(db, key, "clinical_ingestion")
        if not api_key:
            api_key = await verify_api_key(db, key, "vitals.write")
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or inactive API credentials."
            )

    # 2. Extract Body and Parse Message
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8").strip()

    is_json = False
    json_data = None
    try:
        json_data = json.loads(body_str)
        is_json = True
    except json.JSONDecodeError:
        pass

    if is_json and json_data:
        patient_id, parsed_vitals = parse_fhir_observation(json_data)
    else:
        patient_id, parsed_vitals = parse_hl7_message(body_str)

    if not patient_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to parse patient ID from message payload."
        )

    # 3. Resolve Patient
    patient_res = await db.execute(
        select(models.Patient).where(models.Patient.id == patient_id)
    )
    patient = patient_res.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient ID {patient_id} not found."
        )

    old_score = patient.criticality_score

    # 4. Fallback missing values to latest DB metrics or clinical defaults
    latest_vitals_res = await db.execute(
        select(models.PatientVitals)
        .where(models.PatientVitals.patient_id == patient.id)
        .order_by(models.PatientVitals.recorded_at.desc())
        .limit(1)
    )
    latest_v = latest_vitals_res.scalar_one_or_none()

    hr = parsed_vitals.get("heart_rate") or (latest_v.heart_rate if latest_v else 75)
    rr = parsed_vitals.get("resp_rate") or (latest_v.resp_rate if latest_v else 16)
    spo2 = parsed_vitals.get("spo2") or (latest_v.spo2 if latest_v else 98)
    temp = parsed_vitals.get("temperature") or (latest_v.temperature if latest_v else 37.0)
    sbp = parsed_vitals.get("systolic_bp") or (latest_v.systolic_bp if latest_v else 120)
    dbp = parsed_vitals.get("diastolic_bp") or 80
    consciousness = latest_v.consciousness_level if latest_v else models.ConsciousnessLevel.ALERT
    oxygen_supp = latest_v.oxygen_supplement if latest_v else False
    scale = latest_v.spo2_scale if latest_v else 1

    # 5. Compute NEWS2 Score & Update Patient Status
    from services.scoring.policy_service import get_active_policy
    from services.scoring.news2_service import calculate_news2
    from services.scoring.operational_service import calculate_operational_priority

    policy = await get_active_policy(db)
    baseline = await crud.get_patient_baseline(db, patient.id)

    vitals_record = models.PatientVitals(
        patient_id=patient.id,
        heart_rate=hr,
        resp_rate=rr,
        spo2=spo2,
        temperature=temp,
        systolic_bp=sbp,
        consciousness_level=consciousness,
        oxygen_supplement=oxygen_supp,
        spo2_scale=scale
    )
    db.add(vitals_record)
    await db.flush()

    total_score, risk_band, breakdown, red_flags = calculate_news2(vitals_record, policy, baseline=baseline)
    operational_priority = calculate_operational_priority(total_score)
    new_score = operational_priority
    patient.criticality_score = new_score

    score_record = models.ScoreRecord(
        patient_id=patient.id,
        policy_id=policy.id,
        clinical_score=total_score,
        risk_band=risk_band,
        operational_priority=operational_priority
    )
    db.add(score_record)
    await db.flush()

    score_explanation = models.ScoreExplanation(
        score_record_id=score_record.id,
        parameter_breakdown=breakdown,
        red_flags=red_flags
    )
    db.add(score_explanation)
    await db.flush()

    if risk_band == models.RiskBand.HIGH or new_score >= 8.0:
        patient.status = models.PatientStatus.CRITICAL
    elif risk_band == models.RiskBand.MEDIUM or new_score >= 4.0:
        patient.status = models.PatientStatus.SERIOUS
    else:
        patient.status = models.PatientStatus.STABLE

    await db.flush()

    # 6. Evaluate Alerts
    from services.alerts import evaluate_vitals_for_alerts
    from services.task_service import auto_generate_task_for_alert
    alerts = evaluate_vitals_for_alerts(patient.id, patient.name, old_score, new_score, spo2)
    for alert in alerts:
        db.add(alert)
        await db.flush()
        await auto_generate_task_for_alert(db, alert, risk_band)
        await crud.log_operational_event(
            db,
            patient.id,
            "ALERT_TRIGGERED",
            {
                "alert_id": alert.id,
                "alert_type": alert.alert_type.value if hasattr(alert.alert_type, "value") else str(alert.alert_type),
                "severity": alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
                "ews_score": new_score
            }
        )
        alert_event = models.ClinicalEvent(
            patient_id=patient.id,
            event_type=models.ClinicalEventType.ALERT_TRIGGERED,
            description=alert.message,
            event_metadata={"severity": alert.severity, "alert_type": alert.alert_type},
        )
        db.add(alert_event)

    await db.flush()

    # Log Vitals Event
    vitals_event = models.ClinicalEvent(
        patient_id=patient.id,
        event_type=models.ClinicalEventType.VITALS_RECORDED,
        description=f"Interop vitals ingested. Score updated from {old_score:.1f} to {new_score:.1f}. Risk Band: {risk_band.value}",
        event_metadata={"vitals": {"hr": hr, "rr": rr, "spo2": spo2}, "old_score": old_score, "new_score": new_score, "risk_band": risk_band.value, "clinical_score": total_score},
    )
    db.add(vitals_event)
    await db.flush()

    # 7. Evaluate Recommendations (Orchestrator)
    rec = None
    if risk_band == models.RiskBand.HIGH:
        from services.orchestrator import evaluate_patient_and_recommend
        vitals_dict = {"heart_rate": hr, "resp_rate": rr, "spo2": spo2}
        shadow_mode_enabled = policy.config_json.get("shadow_mode_enabled", False)
        rec = await evaluate_patient_and_recommend(db, patient, vitals_dict, shadow_mode_enabled=shadow_mode_enabled)

    capacity_alerts = [obj for obj in db.new if isinstance(obj, models.Alert) and obj.patient_id is None]

    # 8. WebSocket Broadcast
    from main import manager
    broadcast_payload = {
        "type": "PATIENT_UPDATED",
        "data": {
            "patient_id": patient.id,
            "name": patient.name,
            "status": patient.status,
            "criticality_score": patient.criticality_score,
            "bed_id": patient.current_bed_id
        }
    }
    if rec:
        broadcast_payload["recommendation"] = {
            "id": rec.id,
            "patient_name": patient.name,
            "score": rec.criticality_score,
            "reasoning": rec.reasoning
        }
    await manager.broadcast(broadcast_payload)

    # Broadcast Alerts
    triggered_alerts = alerts + capacity_alerts
    if triggered_alerts:
        alerts_data = []
        for alert in triggered_alerts:
            await db.flush()
            alert_dict = {
                "id": alert.id,
                "patient_id": alert.patient_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "is_acknowledged": alert.is_acknowledged,
                "created_at": alert.created_at.isoformat(),
                "patient": {
                    "id": patient.id,
                    "name": patient.name,
                    "age": patient.age,
                    "gender": patient.gender,
                    "admission_reason": patient.admission_reason,
                    "status": patient.status,
                    "criticality_score": patient.criticality_score,
                    "current_bed_id": patient.current_bed_id,
                    "admitted_at": patient.admitted_at.isoformat(),
                    "discharged_at": patient.discharged_at.isoformat() if patient.discharged_at else None
                } if alert.patient_id is not None else None
            }
            alerts_data.append(alert_dict)

        await manager.broadcast({
            "type": "ALERT_TRIGGERED",
            "data": alerts_data
        })

    return patient
