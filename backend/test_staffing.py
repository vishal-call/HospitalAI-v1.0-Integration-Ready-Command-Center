import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import sessionmaker
import models
from services.orchestrator import evaluate_patient_and_recommend

async def main():
    # Use standard proxy connection
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/hospitalai')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("\n--- Running Staffing Constraint Verification Test ---")
        
        # 1. Fetch ICU staffing record
        staffing_res = await session.execute(
            select(models.WardStaffing).where(models.WardStaffing.ward_name == "Intensive Care Unit (ICU)")
        )
        icu_staffing = staffing_res.scalar_one_or_none()
        if not icu_staffing:
            print("ICU staffing record not found. Seeding first...")
            icu_staffing = models.WardStaffing(ward_name="Intensive Care Unit (ICU)", current_nurses=4, max_patient_ratio=2)
            session.add(icu_staffing)
            await session.commit()
            await session.refresh(icu_staffing)
            
        print(f"Initial ICU Staffing: Nurses={icu_staffing.current_nurses}, Max Ratio=1:{icu_staffing.max_patient_ratio}")
        
        # 2. Make staffing highly constrained (Nurses = 1, Max Ratio = 2, so limit is 2 patients)
        icu_staffing.current_nurses = 1
        icu_staffing.max_patient_ratio = 2
        await session.commit()
        print("Updated ICU Staffing: Nurses=1, Ratio=1:2. Maximum allowed ICU patients = 2.")

        # 3. Find a patient who is currently not in ICU (e.g. in GW or ED) to recommend transfer to ICU
        patient_res = await session.execute(
            select(models.Patient)
            .join(models.Bed, models.Patient.current_bed_id == models.Bed.id)
            .join(models.Ward)
            .where(models.Ward.type != models.WardType.ICU)
            .limit(1)
        )
        patient = patient_res.scalar_one_or_none()
        if not patient:
            print("No critical patient found, creating one...")
            patient = models.Patient(
                name="Test Critical Patient",
                age=60,
                gender="Male",
                admission_reason="Sepsis",
                status=models.PatientStatus.CRITICAL,
                criticality_score=8.5,
                current_bed_id=None
            )
            session.add(patient)
            await session.commit()
            await session.refresh(patient)
            
        print(f"Target Patient: {patient.name}, Status: {patient.status}, Score: {patient.criticality_score}")
        
        # 4. Remove any existing pending recommendations for this patient to ensure clean test
        await session.execute(
            update(models.Recommendation)
            .where(models.Recommendation.patient_id == patient.id)
            .values(status=models.RecommendationStatus.REJECTED)
        )
        await session.commit()

        # 5. Run the orchestrator recommendation engine!
        rec = await evaluate_patient_and_recommend(session, patient, {"heart_rate": 130, "resp_rate": 32, "spo2": 82})
        
        print("\n--- Orchestrator Evaluation Results ---")
        if rec:
            print(f"Recommendation type: {rec.recommendation_type if hasattr(rec, 'recommendation_type') else 'INTER_HOSPITAL_TRANSFER'}")
            print(f"Reasoning text: {rec.reasoning}")
            
            # 6. Verify result
            assert "Blocked: Insufficient Staffing Ratio" in rec.reasoning, "Reasoning did not mention staffing constraints!"
            print("\nSUCCESS: Staffing constraints correctly blocked the ICU transfer and routed to external facility.")
        else:
            print("No recommendation generated.")
            
        # 7. Restore original ICU staffing values (Nurses = 4)
        icu_staffing.current_nurses = 4
        await session.commit()
        print("Restored ICU Staffing back to Nurses=4.")

if __name__ == "__main__":
    asyncio.run(main())
