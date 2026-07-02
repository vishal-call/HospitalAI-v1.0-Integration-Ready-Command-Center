from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from models import ClinicalTask, TaskStatus, Alert, RiskBand
from services.sla_service import get_active_sla_policy

async def auto_generate_task_for_alert(db: AsyncSession, alert: Alert, risk_band: str) -> ClinicalTask:
    """
    Generate a task for an alert, set the SLA based on the active policy,
    and attach the SLA deadline to the alert itself.
    """
    risk_band_val = risk_band.value if hasattr(risk_band, "value") else risk_band
    sla_policy = await get_active_sla_policy(db, risk_band_val)
    
    # If no active policy, default to 15 min acknowledge, 30 min resolve
    ack_minutes = 15
    resolve_minutes = 30
    escalate_role = "NURSE"
    
    if sla_policy:
        ack_minutes = sla_policy.acknowledge_within_minutes
        resolve_minutes = sla_policy.resolve_within_minutes
        escalate_role = sla_policy.escalate_to_role
    
    now = datetime.utcnow()
    sla_due = now + timedelta(minutes=resolve_minutes)
    
    # Update alert with SLA
    alert.sla_due_at = sla_due
    db.add(alert)
    
    # Generate ClinicalTask
    task = ClinicalTask(
        patient_id=alert.patient_id,
        alert_id=alert.id,
        task_type="Review Patient Vitals",
        status=TaskStatus.PENDING,
        assigned_to_role="NURSE", # initial response usually nurse
        due_at=now + timedelta(minutes=ack_minutes)
    )
    
    db.add(task)
    return task
