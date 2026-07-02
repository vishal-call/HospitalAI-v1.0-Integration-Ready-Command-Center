from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
import models

async def get_data_quality_metrics(db: AsyncSession) -> dict:
    now = datetime.utcnow()
    twelve_hours_ago = now - timedelta(hours=12)
    twenty_four_hours_ago = now - timedelta(hours=24)

    # 1. Missing Vitals: Count of admitted patients lacking vitals in the last 12 hours
    patients_res = await db.execute(select(models.Patient.id))
    all_patient_ids = [p for p in patients_res.scalars()]
    
    # Patients who have vitals in the last 12 hours
    recent_vitals_res = await db.execute(
        select(models.PatientVitals.patient_id)
        .where(models.PatientVitals.recorded_at >= twelve_hours_ago)
        .distinct()
    )
    patients_with_vitals = set([p for p in recent_vitals_res.scalars()])
    
    missing_vitals_count = sum(1 for pid in all_patient_ids if pid not in patients_with_vitals)

    # 2. Failed Imports: Count of ImportError records in the last 24 hours
    failed_imports_res = await db.execute(
        select(func.count(models.ImportError.id))
        .where(models.ImportError.created_at >= twenty_four_hours_ago)
    )
    failed_imports_count = failed_imports_res.scalar() or 0

    # 3. Open Reconciliation Issues
    open_issues_res = await db.execute(
        select(func.count(models.ReconciliationIssue.id))
        .where(models.ReconciliationIssue.status == models.IssueStatus.OPEN)
    )
    open_issues_count = open_issues_res.scalar() or 0

    # 4. Data Quality Score
    raw_score = 100 - (missing_vitals_count * 0.5) - (failed_imports_count * 0.1) - (open_issues_count * 0.2)
    data_quality_score = max(0, min(100, raw_score)) # Clamp between 0 and 100

    return {
        "data_quality_score": round(data_quality_score, 1),
        "missing_vitals": missing_vitals_count,
        "failed_imports": failed_imports_count,
        "active_issues": open_issues_count
    }
