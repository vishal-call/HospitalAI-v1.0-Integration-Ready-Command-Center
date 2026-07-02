import csv
import io
from fastapi import UploadFile
from typing import Dict, Any

from services.data_validation_service import validate_patient_row, validate_vitals_row

def parse_and_validate_csv(file: UploadFile, entity_type: str) -> Dict[str, Any]:
    """
    Parses a CSV file stream and validates rows incrementally based on entity_type.
    Does NOT save to the database. Returns a preview summary.
    """
    total_rows = 0
    valid_count = 0
    invalid_count = 0
    rows = []

    # Choose the correct validation function based on entity_type
    if entity_type.lower() == "patients":
        validate_fn = validate_patient_row
    elif entity_type.lower() == "vitals":
        validate_fn = validate_vitals_row
    else:
        return {
            "total_rows": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "rows": [],
            "error": f"Unsupported entity_type: {entity_type}"
        }

    try:
        # Wrap the SpooledTemporaryFile in a TextIOWrapper for string-based csv processing
        text_stream = io.TextIOWrapper(file.file, encoding="utf-8-sig")
        reader = csv.DictReader(text_stream)
        
        for raw_row in reader:
            total_rows += 1
            
            # Basic sanitization of the row dictionary (strip keys)
            clean_row = {k.strip(): v for k, v in raw_row.items() if k is not None}
            
            validation_result = validate_fn(clean_row)
            
            is_valid = validation_result["is_valid"]
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                
            # Keep the preview payload bounded if the file is massive
            if total_rows <= 100:
                rows.append({
                    "row_number": total_rows,
                    "raw_data": clean_row,
                    "is_valid": is_valid,
                    "errors": validation_result["errors"],
                    "normalized_data": validation_result["normalized_data"]
                })
                
    except Exception as e:
        return {
            "total_rows": total_rows,
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "rows": rows,
            "error": f"Failed to parse CSV: {str(e)}"
        }

    return {
        "total_rows": total_rows,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "rows": rows
    }


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import json
import models
import crud
from services.scoring.policy_service import get_active_policy
from services.scoring.news2_service import calculate_news2
from services.scoring.operational_service import calculate_operational_priority
from services.alerts import evaluate_vitals_for_alerts
from services.task_service import auto_generate_task_for_alert
from services.orchestrator import evaluate_patient_and_recommend

async def commit_csv_import(db: AsyncSession, file: UploadFile, entity_type: str, integration_id: int) -> Dict[str, Any]:
    total_rows = 0
    valid_count = 0
    invalid_count = 0
    errors = []
    
    if entity_type.lower() == "patients":
        validate_fn = validate_patient_row
    elif entity_type.lower() == "vitals":
        validate_fn = validate_vitals_row
    else:
        raise ValueError(f"Unsupported entity_type: {entity_type}")

    text_stream = io.TextIOWrapper(file.file, encoding="utf-8-sig")
    reader = csv.DictReader(text_stream)
    
    policy = await get_active_policy(db)
    
    import_batch = models.ImportBatch(
        integration_id=integration_id,
        file_name=file.filename,
        entity_type=entity_type.lower(),
        status=models.LogStatus.PROCESSING,
        total_rows=0,
        success_rows=0,
        failed_rows=0
    )
    db.add(import_batch)
    await db.flush()

    for raw_row in reader:
        total_rows += 1
        clean_row = {k.strip(): v for k, v in raw_row.items() if k is not None}
        validation_result = validate_fn(clean_row)
        
        if not validation_result["is_valid"]:
            invalid_count += 1
            err = models.ImportError(
                import_batch_id=import_batch.id,
                row_number=total_rows,
                raw_data=clean_row,
                error_message="; ".join(validation_result["errors"])
            )
            db.add(err)
            continue
            
        norm = validation_result["normalized_data"]
        
        if entity_type.lower() == "patients":
            # Check for existing mapping
            res = await db.execute(select(models.ExternalIdMapping).where(models.ExternalIdMapping.external_patient_code == norm["patient_code"]))
            mapping = res.scalar_one_or_none()
            if not mapping:
                patient = models.Patient(
                    name=norm["name"],
                    age=norm.get("age", 0) or 0,
                    gender=norm.get("gender", "UNKNOWN"),
                    admission_reason=norm.get("admission_reason", "Imported")
                )
                db.add(patient)
                await db.flush()
                
                mapping = models.ExternalIdMapping(
                    integration_id=integration_id,
                    external_patient_code=norm["patient_code"],
                    internal_patient_id=patient.id
                )
                db.add(mapping)
            valid_count += 1
            
        elif entity_type.lower() == "vitals":
            # Must have mapping
            res = await db.execute(select(models.ExternalIdMapping).where(models.ExternalIdMapping.external_patient_code == norm["patient_code"]))
            mapping = res.scalar_one_or_none()
            if not mapping:
                invalid_count += 1
                err = models.ImportError(
                    import_batch_id=import_batch.id,
                    row_number=total_rows,
                    raw_data=clean_row,
                    error_message=f"Unknown patient_code: {norm['patient_code']}"
                )
                db.add(err)
                continue
            
            patient_id = mapping.internal_patient_id
            patient_res = await db.execute(select(models.Patient).where(models.Patient.id == patient_id))
            patient = patient_res.scalar_one()
            
            old_score = patient.criticality_score
            baseline = await crud.get_patient_baseline(db, patient.id)
            
            vitals_record = models.PatientVitals(
                patient_id=patient.id,
                heart_rate=norm.get("heart_rate"),
                resp_rate=norm.get("respiratory_rate"),
                spo2=norm.get("spo2"),
                temperature=norm.get("temperature"),
                consciousness_level=models.ConsciousnessLevel.ALERT if norm.get("consciousness_level") == "ALERT" else models.ConsciousnessLevel.CVPU,
                oxygen_supplement=False, # default for csv
                spo2_scale=1
            )
            db.add(vitals_record)
            await db.flush()
            
            total_score, risk_band, breakdown, red_flags = calculate_news2(vitals_record, policy, baseline=baseline)
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
            
            # Evaluate Alerts
            alerts = evaluate_vitals_for_alerts(patient.id, patient.name, old_score, operational_priority, norm.get("spo2"))
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
                description=f"CSV Vitals imported. Score updated from {old_score:.1f} to {operational_priority:.1f}. Risk Band: {risk_band.value}",
                event_metadata={"vitals": {"hr": norm.get("heart_rate"), "rr": norm.get("respiratory_rate"), "spo2": norm.get("spo2")}, "old_score": old_score, "new_score": operational_priority, "risk_band": risk_band.value, "clinical_score": total_score},
            )
            db.add(vitals_event)
            await db.flush()
            
            if risk_band == models.RiskBand.HIGH:
                v_dict = {
                    "heart_rate": norm.get("heart_rate"),
                    "resp_rate": norm.get("respiratory_rate"),
                    "spo2": norm.get("spo2")
                }
                shadow_mode_enabled = policy.config_json.get("shadow_mode_enabled", False) if policy.config_json else False
                await evaluate_patient_and_recommend(db, patient, v_dict, shadow_mode_enabled=shadow_mode_enabled)
                
            valid_count += 1
            
    import_batch.total_rows = total_rows
    import_batch.success_rows = valid_count
    import_batch.failed_rows = invalid_count
    import_batch.status = models.LogStatus.SUCCESS if invalid_count == 0 else models.LogStatus.PARTIAL_SUCCESS if valid_count > 0 else models.LogStatus.FAILED
    
    integration_log = models.IntegrationLog(
        integration_id=integration_id,
        integration_name="System CSV Upload",
        integration_type=models.IntegrationType.CSV,
        mode=models.IntegrationMode.CSV_IMPORT,
        direction=models.LogDirection.INBOUND,
        status=import_batch.status,
        records_received=total_rows,
        records_success=valid_count,
        records_failed=invalid_count,
        started_at=import_batch.created_at,
        finished_at=datetime.utcnow()
    )
    db.add(integration_log)
    
    await db.flush()
    
    return {
        "import_batch_id": import_batch.id,
        "integration_log_id": integration_log.id,
        "total_rows": total_rows,
        "valid_count": valid_count,
        "invalid_count": invalid_count
    }
