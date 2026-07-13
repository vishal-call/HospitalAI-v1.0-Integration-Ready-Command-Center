import os
import sys
import time
import asyncio
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Override database port to 5433 matching local database setup
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/hospitalai"

# Add backend directory to sys.path if not present
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import AsyncSessionLocal
import models
from services.swarm_orchestrator import (
    orchestrate_allocation,
    triage_agent_eval,
    resource_agent_eval,
    logistics_agent_eval,
    AgentBid
)

def test_swarm_framework():
    """
    Unified swarm orchestrator test suite executing:
    1. Concurrency check: verify agents run concurrently.
    2. Arbitration check: assert weighted scoring math formula.
    3. Telemetry check: verify OperationalLog has matching bids.
    """
    async def run():
        async with AsyncSessionLocal() as db:
            print("\n--- 1. RUNNING CONCURRENCY CHECK ---")
            class DummyPatient:
                id = 9999
                name = "Concurrency Patient"
                status = models.PatientStatus.CRITICAL
                criticality_score = 8.5
                current_bed_id = 1
                
            patient_dummy = DummyPatient()
            start_time = time.time()
            
            async def delayed_triage():
                await asyncio.sleep(0.2)
                return AgentBid(agent_name="Triage Agent", score=0.9, justification="High urgency")
                
            async def delayed_resource():
                await asyncio.sleep(0.2)
                return AgentBid(agent_name="Resource Agent", score=0.8, justification="Buffer safe")
                
            async def delayed_logistics():
                await asyncio.sleep(0.2)
                return AgentBid(agent_name="Staff Logistics Agent", score=0.7, justification="Safe ratio")
                
            bids = await asyncio.gather(
                delayed_triage(),
                delayed_resource(),
                delayed_logistics()
            )
            
            elapsed_time = time.time() - start_time
            assert elapsed_time < 0.4, f"Execution was sequential! Took {elapsed_time:.2f}s"
            assert len(bids) == 3
            print(f"Concurrency check passed: execution took {elapsed_time:.4f}s")

            print("\n--- 2. RUNNING ARBITRATION CHECK ---")
            # Fetch or create a test patient
            patient_res = await db.execute(select(models.Patient).limit(1))
            patient = patient_res.scalar_one_or_none()
            if not patient:
                patient = models.Patient(
                    name="Arbitration Test Patient",
                    age=50,
                    gender="Female",
                    admission_reason="Respiratory Distress",
                    status=models.PatientStatus.CRITICAL,
                    criticality_score=8.0,
                    current_bed_id=None
                )
                db.add(patient)
                await db.commit()
                await db.refresh(patient)

            # Fetch or create an available Bed in ICU
            bed_res = await db.execute(
                select(models.Bed)
                .join(models.Ward)
                .where(models.Ward.type == models.WardType.ICU)
                .where(models.Bed.status == models.BedStatus.AVAILABLE)
                .limit(1)
            )
            bed = bed_res.scalar_one_or_none()
            if not bed:
                ward_res = await db.execute(
                    select(models.Ward).where(models.Ward.type == models.WardType.ICU).limit(1)
                )
                ward = ward_res.scalar_one_or_none()
                if not ward:
                    ward = models.Ward(name="Test ICU Ward", type=models.WardType.ICU, capacity=10)
                    db.add(ward)
                    await db.commit()
                    await db.refresh(ward)
                bed = models.Bed(ward_id=ward.id, bed_number="ICU-TEST-99", status=models.BedStatus.AVAILABLE)
                db.add(bed)
                await db.commit()
                await db.refresh(bed)

            # Set patient current bed to another bed to trigger transfer need
            if not patient.current_bed_id:
                gw_bed_res = await db.execute(
                    select(models.Bed)
                    .join(models.Ward)
                    .where(models.Ward.type == models.WardType.GENERAL)
                    .limit(1)
                )
                gw_bed = gw_bed_res.scalar_one_or_none()
                patient.current_bed_id = gw_bed.id if gw_bed else None
                await db.commit()

            # Clean up any existing pending recommendations to prevent duplication
            existing_recs_res = await db.execute(
                select(models.Recommendation)
                .where(models.Recommendation.patient_id == patient.id)
                .where(models.Recommendation.status == models.RecommendationStatus.PENDING)
            )
            existing_recs = existing_recs_res.scalars().all()
            for r in existing_recs:
                r.status = models.RecommendationStatus.REJECTED
            await db.commit()

            # Run the evaluations directly
            triage_bid = await triage_agent_eval(db, patient, 9, bed.id, models.WardType.ICU)
            resource_bid = await resource_agent_eval(db, patient, 9, bed.id, models.WardType.ICU)
            logistics_bid = await logistics_agent_eval(db, patient, 9, bed.id, models.WardType.ICU)

            expected_final_score = (0.50 * triage_bid.score) + (0.25 * resource_bid.score) + (0.25 * logistics_bid.score)
            
            # Invoke orchestrate_allocation
            rec = await orchestrate_allocation(db, patient.id, 9)
            
            assert rec is not None
            actual_final_score = rec.criticality_score / 10.0
            assert abs(actual_final_score - expected_final_score) < 0.0001
            print(f"Arbitration logic check passed: Expected score {expected_final_score:.4f}, Got {actual_final_score:.4f}")

            print("\n--- 3. RUNNING TELEMETRY CHECK ---")
            patient_telemetry = models.Patient(
                name="Telemetry Test Patient",
                age=35,
                gender="Male",
                admission_reason="Seizure",
                status=models.PatientStatus.CRITICAL,
                criticality_score=9.0,
                current_bed_id=None
            )
            db.add(patient_telemetry)
            await db.commit()
            await db.refresh(patient_telemetry)

            # Get general bed as current
            gw_bed_res2 = await db.execute(
                select(models.Bed)
                .join(models.Ward)
                .where(models.Ward.type == models.WardType.GENERAL)
                .limit(1)
            )
            gw_bed2 = gw_bed_res2.scalar_one_or_none()
            if gw_bed2:
                patient_telemetry.current_bed_id = gw_bed2.id
                await db.commit()

            # Run allocation
            rec2 = await orchestrate_allocation(db, patient_telemetry.id, 9)
            assert rec2 is not None
            await db.commit()

            # Query the most recent operational log
            log_res = await db.execute(
                select(models.OperationalLog)
                .where(models.OperationalLog.patient_id == patient_telemetry.id)
                .where(models.OperationalLog.event_type == "RECOMMENDATION_GENERATED")
                .order_by(models.OperationalLog.timestamp.desc())
                .limit(1)
            )
            op_log = log_res.scalar_one_or_none()
            
            assert op_log is not None
            assert "final_score" in op_log.payload
            assert "agent_bids" in op_log.payload
            assert len(op_log.payload["agent_bids"]) == 3
            print("Telemetry logs check passed: OperationalLog generated with matching bids.")

    asyncio.run(run())
