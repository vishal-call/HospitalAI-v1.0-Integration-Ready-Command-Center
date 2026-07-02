from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import models
import crud
from services.scoring.policy_service import get_active_policy
from services.scoring.news2_service import calculate_news2
from services.scoring.operational_service import calculate_operational_priority
from services.alerts import evaluate_vitals_for_alerts
from services.task_service import auto_generate_task_for_alert
from services.orchestrator import evaluate_patient_and_recommend

async def get_open_issues(db: AsyncSession):
    res = await db.execute(
        select(models.ReconciliationIssue)
        .where(models.ReconciliationIssue.status == models.IssueStatus.OPEN)
        .order_by(models.ReconciliationIssue.created_at.desc())
    )
    return res.scalars().all()

async def resolve_issue(db: AsyncSession, issue_id: int, action: str, note: str, user_id: int):
    # Fetch issue
    res = await db.execute(select(models.ReconciliationIssue).where(models.ReconciliationIssue.id == issue_id))
    issue = res.scalar_one_or_none()
    if not issue:
        raise ValueError(f"Issue {issue_id} not found")

    if issue.status != models.IssueStatus.OPEN:
        raise ValueError(f"Issue {issue_id} is already resolved")

    if action == "ACCEPT_EXTERNAL":
        # Hardcoded dynamic updates for allowed entities
        entity_type = issue.entity_type.lower()
        field_name = issue.field_name
        external_value = issue.external_value
        entity_id = int(issue.entity_id) # assuming int IDs for now

        if entity_type == "patient":
            res_patient = await db.execute(select(models.Patient).where(models.Patient.id == entity_id))
            patient = res_patient.scalar_one_or_none()
            if patient:
                if field_name == "name": patient.name = external_value
                elif field_name == "age": patient.age = int(external_value)
                elif field_name == "gender": patient.gender = external_value
                elif field_name == "admission_reason": patient.admission_reason = external_value

        elif entity_type == "patientvitals" or entity_type == "vitals":
            res_vitals = await db.execute(select(models.PatientVitals).where(models.PatientVitals.id == entity_id))
            vitals = res_vitals.scalar_one_or_none()
            if vitals:
                old_score = 0 # fetch patient score to keep track
                patient_res = await db.execute(select(models.Patient).where(models.Patient.id == vitals.patient_id))
                patient = patient_res.scalar_one_or_none()
                if patient:
                    old_score = patient.criticality_score
                    
                # Update vital
                if field_name == "heart_rate": vitals.heart_rate = int(external_value)
                elif field_name == "resp_rate": vitals.resp_rate = int(external_value)
                elif field_name == "spo2": vitals.spo2 = int(external_value)
                elif field_name == "temperature": vitals.temperature = float(external_value)
                
                await db.flush() # ensure vitals update is reflected

                # Re-trigger NEWS2/Orchestrator
                if patient:
                    policy = await get_active_policy(db)
                    baseline = await crud.get_patient_baseline(db, patient.id)
                    total_score, risk_band, breakdown, red_flags = calculate_news2(vitals, policy, baseline=baseline)
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

                    alerts = evaluate_vitals_for_alerts(patient.id, patient.name, old_score, operational_priority, vitals.spo2)
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
                        description=f"Vitals updated via reconciliation. Score updated from {old_score:.1f} to {operational_priority:.1f}. Risk Band: {risk_band.value}",
                        event_metadata={"vitals": {"hr": vitals.heart_rate, "rr": vitals.resp_rate, "spo2": vitals.spo2}, "old_score": old_score, "new_score": operational_priority, "risk_band": risk_band.value, "clinical_score": total_score},
                    )
                    db.add(vitals_event)
                    await db.flush()

                    if risk_band == models.RiskBand.HIGH:
                        v_dict = {
                            "heart_rate": vitals.heart_rate,
                            "resp_rate": vitals.resp_rate,
                            "spo2": vitals.spo2
                        }
                        shadow_mode_enabled = policy.config_json.get("shadow_mode_enabled", False) if policy.config_json else False
                        await evaluate_patient_and_recommend(db, patient, v_dict, shadow_mode_enabled=shadow_mode_enabled)

        elif entity_type == "bed":
            res_bed = await db.execute(select(models.Bed).where(models.Bed.id == entity_id))
            bed = res_bed.scalar_one_or_none()
            if bed:
                if field_name == "status": 
                    # Assuming external_value maps to BedStatus enum
                    bed.status = models.BedStatus[external_value.upper()]
        # Ignore unsupported types intentionally

    issue.status = models.IssueStatus.RESOLVED
    issue.resolution_note = note
    issue.resolved_at = datetime.utcnow()
    issue.resolved_by = user_id
    
    await db.flush()
    return issue
