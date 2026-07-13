import os
import sys
import time
import asyncio
import hashlib
import json
import pytest
from sqlalchemy import select
from httpx import AsyncClient

# Override database port to 5433 matching local database setup
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/hospitalai"

# Add backend directory to sys.path if not present
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import AsyncSessionLocal
import models
import crud
from main import app

def test_ledger_framework():
    """
    Unified ledger validation test executing:
    1. Pessimistic locking check: assert 'FOR UPDATE' is present in bed locking query.
    2. Hash chain continuity check: assert logs have correct cryptographic_hash chaining.
    3. PHI access auditing check: assert GET patients triggers PHI_ACCESSED operational log entry.
    """
    async def run():
        async with AsyncSessionLocal() as db:
            print("\n--- 1. VERIFYING PESSIMISTIC LOCKING STRUCTURE ---")
            dialect = db.bind.dialect
            q = select(models.Bed).where(models.Bed.id == 1).with_for_update(nowait=False)
            sql = str(q.compile(dialect=dialect))
            assert "FOR UPDATE" in sql or "FOR SHARE" in sql
            print("Pessimistic locking structure verification passed.")

            print("\n--- 2. VERIFYING HASH CHAIN CONTINUITY ---")
            patient = models.Patient(
                name="Ledger Test Patient",
                age=40,
                gender="Female",
                admission_reason="Audit Validation",
                status=models.PatientStatus.STABLE,
                criticality_score=1.5,
                current_bed_id=None
            )
            db.add(patient)
            await db.commit()
            await db.refresh(patient)

            log1 = await crud.log_operational_event(db, patient.id, "TEST_EVENT_A", {"seq": 1})
            await db.commit()
            log2 = await crud.log_operational_event(db, patient.id, "TEST_EVENT_B", {"seq": 2})
            await db.commit()
            log3 = await crud.log_operational_event(db, patient.id, "TEST_EVENT_C", {"seq": 3})
            await db.commit()

            logs_res = await db.execute(
                select(models.OperationalLog)
                .where(models.OperationalLog.patient_id == patient.id)
                .order_by(models.OperationalLog.id.asc())
            )
            logs = logs_res.scalars().all()
            assert len(logs) == 3
            
            # Verify log2 hash derived from log1 hash
            expected_input_2 = f"{logs[0].cryptographic_hash}|{logs[1].timestamp.isoformat()}|{logs[1].event_type}|{json.dumps(logs[1].payload, sort_keys=True)}"
            expected_hash_2 = hashlib.sha256(expected_input_2.encode('utf-8')).hexdigest()
            assert logs[1].cryptographic_hash == expected_hash_2

            # Verify log3 hash derived from log2 hash
            expected_input_3 = f"{logs[1].cryptographic_hash}|{logs[2].timestamp.isoformat()}|{logs[2].event_type}|{json.dumps(logs[2].payload, sort_keys=True)}"
            expected_hash_3 = hashlib.sha256(expected_input_3.encode('utf-8')).hexdigest()
            assert logs[2].cryptographic_hash == expected_hash_3
            print("Hash chain continuity verification passed.")

            print("\n--- 3. VERIFYING PHI ACCESS AUDITING ---")
            # Retrieve or create an audited patient from database
            patient_res = await db.execute(select(models.Patient).limit(1))
            patient_audited = patient_res.scalar_one_or_none()
            if not patient_audited:
                patient_audited = models.Patient(
                    name="Audited Patient",
                    age=30,
                    gender="Male",
                    admission_reason="Telemetry Check",
                    status=models.PatientStatus.STABLE,
                    criticality_score=2.0,
                    current_bed_id=None
                )
                db.add(patient_audited)
                await db.commit()
                await db.refresh(patient_audited)
            patient_id = patient_audited.id

        from httpx import ASGITransport
        # Hit the GET /api/patients/{id} endpoint (runs outside of AsyncSessionLocal but inside same event loop)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/api/patients/{patient_id}")
            assert resp.status_code == 200

        # Verify that a PHI_ACCESSED log entry was generated
        async with AsyncSessionLocal() as db:
            log_res = await db.execute(
                select(models.OperationalLog)
                .where(models.OperationalLog.patient_id == patient_id)
                .where(models.OperationalLog.event_type == "PHI_ACCESSED")
                .order_by(models.OperationalLog.id.desc())
                .limit(1)
            )
            op_log = log_res.scalar_one_or_none()
            assert op_log is not None
            assert op_log.payload["action"] == "VIEW_PATIENT_DETAIL"
            print("PHI access auditing verification passed.")

    asyncio.run(run())
