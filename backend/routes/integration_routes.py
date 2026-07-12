from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

import schemas
from database import get_db
from services import integration_service, csv_import_service
from models import IntegrationStatus

router = APIRouter(prefix="/api/integrations", tags=["Integrations"])

@router.post("/csv-import/preview")
async def preview_csv_import(
    file: UploadFile = File(...),
    entity_type: str = Form(...)
):
    try:
        preview_data = csv_import_service.parse_and_validate_csv(file, entity_type)
        return JSONResponse(content=preview_data)
    finally:
        await file.close()

@router.post("/csv-import/commit")
async def commit_csv_import(
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Default Integration ID 1 per user request
        commit_data = await csv_import_service.commit_csv_import(db, file, entity_type, integration_id=1)
        return JSONResponse(content=commit_data)
    finally:
        await file.close()

from services.data_quality_service import get_data_quality_metrics
from services.reconciliation_service import get_open_issues, resolve_issue

@router.get("/data-quality")
async def fetch_data_quality_metrics(db: AsyncSession = Depends(get_db)):
    metrics = await get_data_quality_metrics(db)
    return metrics

@router.get("/reconciliation-issues")
async def fetch_reconciliation_issues(db: AsyncSession = Depends(get_db)):
    issues = await get_open_issues(db)
    return [issue.__dict__ for issue in issues] # Note: basic serialization

from pydantic import BaseModel
class ResolutionRequest(BaseModel):
    action: str
    note: str = ""

@router.post("/reconciliation-issues/{id}/resolve")
async def handle_resolve_issue(id: int, req: ResolutionRequest, db: AsyncSession = Depends(get_db)):
    # Assuming user_id = 1 for now (admin)
    try:
        issue = await resolve_issue(db, id, req.action, req.note, user_id=1)
        return {"status": "success", "issue_id": issue.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/", response_model=schemas.IntegrationResponse)
async def create_integration(
    integration_in: schemas.IntegrationCreate,
    db: AsyncSession = Depends(get_db)
):
    return await integration_service.create_integration(db, integration_in)

@router.get("/", response_model=List[schemas.IntegrationResponse])
async def read_integrations(
    db: AsyncSession = Depends(get_db)
):
    return await integration_service.get_integrations(db)

@router.put("/{integration_id}", response_model=schemas.IntegrationResponse)
async def update_integration(
    integration_id: int,
    integration_in: schemas.IntegrationUpdate,
    db: AsyncSession = Depends(get_db)
):
    return await integration_service.update_integration(db, integration_id, integration_in)

@router.patch("/{integration_id}/status", response_model=schemas.IntegrationResponse)
async def change_status(
    integration_id: int,
    status: IntegrationStatus,
    db: AsyncSession = Depends(get_db)
):
    return await integration_service.change_integration_status(db, integration_id, status)

from pydantic import BaseModel, Field
from typing import List
from services.api_key_service import generate_api_key, verify_api_key, get_all_api_keys, revoke_api_key
from fastapi import Header
from services.scoring.policy_service import get_active_policy
from services.scoring.news2_service import calculate_news2
from services.scoring.operational_service import calculate_operational_priority
from services.orchestrator import evaluate_patient_and_recommend
from services.alerts import evaluate_vitals_for_alerts
from services.task_service import auto_generate_task_for_alert
import crud

class ApiKeyCreate(BaseModel):
    name: str
    scopes: List[str]

@router.post("/api-keys")
async def create_api_key(req: ApiKeyCreate, db: AsyncSession = Depends(get_db)):
    raw_key, prefix = await generate_api_key(db, req.name, req.scopes)
    return {"raw_key": raw_key, "prefix": prefix}

@router.get("/api-keys")
async def fetch_api_keys(db: AsyncSession = Depends(get_db)):
    keys = await get_all_api_keys(db)
    return [
        {
            "id": k.id,
            "name": k.name,
            "key_prefix": k.key_prefix,
            "scopes": k.scopes,
            "is_active": k.is_active,
            "created_at": k.created_at,
            "last_used_at": k.last_used_at
        } for k in keys
    ]

@router.post("/api-keys/{key_id}/revoke")
async def revoke_key(key_id: int, db: AsyncSession = Depends(get_db)):
    key = await revoke_api_key(db, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"status": "success"}

class VitalsIngestPayload(BaseModel):
    patient_code: str
    device_id: str
    respiratory_rate: int = Field(..., ge=0, le=100)
    spo2: int = Field(..., ge=0, le=100)
    oxygen_supplement: bool
    temperature: float = Field(..., ge=20.0, le=45.0)
    systolic_bp: int = Field(..., ge=0, le=300)
    diastolic_bp: int = Field(..., ge=0, le=200)
    heart_rate: int = Field(..., ge=0, le=300)
    consciousness_level: str

@router.post("/vitals/ingest")
async def ingest_vitals(
    payload: VitalsIngestPayload,
    x_integration_key: str = Header(None),
    x_idempotency_key: str = Header(None),
    x_correlation_id: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    if not x_integration_key:
        raise HTTPException(status_code=401, detail="Missing X-Integration-Key header")
        
    api_key = await verify_api_key(db, x_integration_key, "vitals.write")
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")

    # Check idempotency
    if x_idempotency_key:
        from sqlalchemy import select
        res = await db.execute(select(models.IntegrationLog).where(models.IntegrationLog.idempotency_key == x_idempotency_key))
        existing_log = res.scalar_one_or_none()
        if existing_log and existing_log.status == models.LogStatus.SUCCESS:
            return {"status": "ok", "message": "Idempotent request ignored"}

    # Resolve Patient
    from sqlalchemy import select
    # Check ExternalIdMapping first
    mapping_res = await db.execute(
        select(models.ExternalIdMapping).where(models.ExternalIdMapping.external_patient_code == payload.patient_code)
    )
    mapping = mapping_res.scalar_one_or_none()
    
    patient = None
    if mapping:
        patient_res = await db.execute(select(models.Patient).where(models.Patient.id == mapping.internal_patient_id))
        patient = patient_res.scalar_one_or_none()
    else:
        # Fallback to direct ID match if they passed an int
        if payload.patient_code.isdigit():
            patient_res = await db.execute(select(models.Patient).where(models.Patient.id == int(payload.patient_code)))
            patient = patient_res.scalar_one_or_none()
            
    if not patient:
        # Log failure
        err_log = models.IntegrationLog(
            integration_name=api_key.name,
            integration_type=models.IntegrationType.API,
            mode=models.IntegrationMode.API_READ_WRITE, # Assuming general mode
            direction=models.LogDirection.INBOUND,
            status=models.LogStatus.FAILED,
            error_summary=f"Patient {payload.patient_code} not found",
            correlation_id=x_correlation_id,
            idempotency_key=x_idempotency_key
        )
        db.add(err_log)
        await db.commit()
        raise HTTPException(status_code=404, detail="Patient not found")
        
    old_score = patient.criticality_score
    
    # Map consciousness_level string to ConsciousnessLevel enum
    cons_level = models.ConsciousnessLevel.ALERT
    if payload.consciousness_level.upper() in ["CVPU", "C", "V", "P", "U"]:
        cons_level = models.ConsciousnessLevel.CVPU

    # Save Vitals
    new_vitals = models.PatientVitals(
        patient_id=patient.id,
        heart_rate=payload.heart_rate,
        resp_rate=payload.respiratory_rate,
        spo2=payload.spo2,
        temperature=payload.temperature,
        systolic_bp=payload.systolic_bp,
        consciousness_level=cons_level,
        oxygen_supplement=payload.oxygen_supplement
    )
    db.add(new_vitals)
    await db.flush()
    
    # Trigger Pipeline
    policy = await get_active_policy(db)
    baseline = await crud.get_patient_baseline(db, patient.id)
    total_score, risk_band, breakdown, red_flags = calculate_news2(new_vitals, policy, baseline=baseline)
    operational_priority = calculate_operational_priority(total_score)
    
    patient.criticality_score = operational_priority
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
    
    if risk_band == models.RiskBand.HIGH or operational_priority >= 8.0:
        patient.status = models.PatientStatus.CRITICAL
    elif risk_band == models.RiskBand.MEDIUM or operational_priority >= 4.0:
        patient.status = models.PatientStatus.SERIOUS
    else:
        patient.status = models.PatientStatus.STABLE
    await db.flush()

    alerts = evaluate_vitals_for_alerts(patient.id, patient.name, old_score, operational_priority, new_vitals.spo2)
    for alert in alerts:
        db.add(alert)
        await db.flush()
        await auto_generate_task_for_alert(db, alert, risk_band)
        alert_event = models.ClinicalEvent(
            patient_id=patient.id,
            event_type=models.ClinicalEventType.ALERT_TRIGGERED,
            description=alert.message,
            event_metadata={"severity": alert.severity, "alert_type": alert.alert_type},
        )
        db.add(alert_event)

    vitals_event = models.ClinicalEvent(
        patient_id=patient.id,
        event_type=models.ClinicalEventType.VITALS_RECORDED,
        description=f"Vitals received via API. Score updated from {old_score:.1f} to {operational_priority:.1f}. Risk Band: {risk_band.value}",
        event_metadata={"vitals": {"hr": new_vitals.heart_rate, "rr": new_vitals.resp_rate, "spo2": new_vitals.spo2}, "old_score": old_score, "new_score": operational_priority, "risk_band": risk_band.value, "clinical_score": total_score},
    )
    db.add(vitals_event)
    await db.flush()

    if risk_band == models.RiskBand.HIGH:
        v_dict = {
            "heart_rate": new_vitals.heart_rate,
            "resp_rate": new_vitals.resp_rate,
            "spo2": new_vitals.spo2
        }
        shadow_mode_enabled = policy.config_json.get("shadow_mode_enabled", False) if policy.config_json else False
        await evaluate_patient_and_recommend(db, patient, v_dict, shadow_mode_enabled=shadow_mode_enabled)

    # Log Success
    success_log = models.IntegrationLog(
        integration_name=api_key.name,
        integration_type=models.IntegrationType.API,
        mode=models.IntegrationMode.API_READ_WRITE, 
        direction=models.LogDirection.INBOUND,
        status=models.LogStatus.SUCCESS,
        records_success=1,
        correlation_id=x_correlation_id,
        idempotency_key=x_idempotency_key
    )
    db.add(success_log)
    await db.commit()
    
    return {"status": "ok", "message": "Vitals ingested successfully"}
