import asyncio
import logging
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from database import engine, AsyncSessionLocal, Base
from models import User, Patient, Ward, Bed, Recommendation, Alert, PartnerHospital, UserRole, PatientStatus, WardType, BedStatus, AlertType, AlertSeverity, WardStaffing

from services.auth import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HospitalAI-Seeder")

from sqlalchemy import text

async def seed_data(db: Optional[AsyncSession] = None, clear_only: bool = False):
    if db is None:
        async with engine.begin() as conn:
            if clear_only:
                logger.info("Truncating existing tables...")
                try:
                    await conn.execute(text("""
                        TRUNCATE TABLE audit_logs, alerts, recommendations, transfer_requests, patients, beds, partner_hospitals, users, idempotency_keys, wards, ward_staffing RESTART IDENTITY CASCADE;
                    """))
                except Exception as e:
                    logger.exception("Failed to truncate tables, falling back to drop:")
                    await conn.run_sync(Base.metadata.drop_all)
                    await conn.run_sync(Base.metadata.create_all)
            else:
                logger.info("Terminating active database connections...")
                try:
                    await conn.execute(text("""
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = 'hospitalai' AND pid <> pg_backend_pid()
                    """))
                except Exception as e:
                    logger.warning(f"Could not terminate other DB connections: {e}")
                    
                logger.info("Dropping existing tables...")
                await conn.execute(text("DROP SCHEMA public CASCADE"))
                await conn.execute(text("CREATE SCHEMA public"))
                logger.info("Creating tables...")
                await conn.run_sync(Base.metadata.create_all)
    else:
        if clear_only:
            logger.info("Clearing dynamic tables on active session...")
            await db.execute(text("UPDATE beds SET status='AVAILABLE', patient_id=NULL"))
            await db.execute(text("DELETE FROM audit_logs"))
            await db.execute(text("DELETE FROM alerts"))
            await db.execute(text("DELETE FROM recommendations"))
            await db.execute(text("DELETE FROM transfer_requests"))
            await db.execute(text("DELETE FROM idempotency_keys"))
            await db.execute(text("DELETE FROM patients"))

    if db is None:
        session_ctx = AsyncSessionLocal()
        session = await session_ctx.__aenter__()
        tx = await session.begin()
    else:
        session = db
        tx = None
        
    try:
        if not clear_only:
            logger.info("Seeding users...")
            
            # Check if static data already exists
            user_exists = await session.execute(text("SELECT id FROM users LIMIT 1"))
            if not user_exists.scalar_one_or_none():
                default_hashed_password = hash_password("password123")
                
                admin = User(
                    username="admin",
                    email="admin@hospitalai.com",
                    hashed_password=default_hashed_password,
                    role=UserRole.ADMIN,
                    is_active=True
                )
                coordinator = User(
                    username="coordinator",
                    email="coord@hospitalai.com",
                    hashed_password=default_hashed_password,
                    role=UserRole.COORDINATOR,
                    is_active=True
                )
                doctor = User(
                    username="doctor",
                    email="doctor@hospitalai.com",
                    hashed_password=default_hashed_password,
                    role=UserRole.DOCTOR,
                    is_active=True
                )
                nurse = User(
                    username="nurse",
                    email="nurse@hospitalai.com",
                    hashed_password=default_hashed_password,
                    role=UserRole.NURSE,
                    is_active=True
                )
                session.add_all([admin, coordinator, doctor, nurse])
    
                logger.info("Seeding Wards...")
                icu = Ward(name="Intensive Care Unit (ICU)", type=WardType.ICU, capacity=12)
                emergency = Ward(name="Emergency Department", type=WardType.EMERGENCY, capacity=14)
                general = Ward(name="General Ward", type=WardType.GENERAL, capacity=30)
                session.add_all([icu, emergency, general])
                
                logger.info("Seeding Ward Staffing ratios...")
                icu_staff = WardStaffing(ward_name="Intensive Care Unit (ICU)", current_nurses=10, max_patient_ratio=2)
                ed_staff = WardStaffing(ward_name="Emergency Department", current_nurses=10, max_patient_ratio=2)
                general_staff = WardStaffing(ward_name="General Ward", current_nurses=20, max_patient_ratio=2)
                session.add_all([icu_staff, ed_staff, general_staff])
                
                # Flush to get Ward IDs
                await session.flush()
    
                logger.info("Seeding Beds...")
                icu_beds = []
                for i in range(1, 13):
                    bed = Bed(ward_id=icu.id, bed_number=f"ICU-{100 + i:03d}", status=BedStatus.AVAILABLE)
                    icu_beds.append(bed)
                    session.add(bed)
    
                ed_beds = []
                for i in range(1, 15):
                    bed = Bed(ward_id=emergency.id, bed_number=f"ED-{200 + i:03d}", status=BedStatus.AVAILABLE)
                    ed_beds.append(bed)
                    session.add(bed)
    
                general_beds = []
                for i in range(1, 31):
                    bed = Bed(ward_id=general.id, bed_number=f"GW-{300 + i:03d}", status=BedStatus.AVAILABLE)
                    general_beds.append(bed)
                    session.add(bed)
    
                # Flush to get Bed IDs
                await session.flush()
    
                logger.info("Seeding Partner Hospitals...")
                ph1 = PartnerHospital(
                    name="St. Jude Medical Center",
                    location="North District",
                    distance_km=5.2,
                    icu_beds_available=4,
                    general_beds_available=15
                )
                ph2 = PartnerHospital(
                    name="Mercy General Hospital",
                    location="East Valley",
                    distance_km=12.8,
                    icu_beds_available=2,
                    general_beds_available=22
                )
                ph3 = PartnerHospital(
                    name="Metro Health Clinic",
                    location="South Hub",
                    distance_km=25.0,
                    icu_beds_available=0,
                    general_beds_available=8
                )
                session.add_all([ph1, ph2, ph3])
                await session.flush()
            else:
                logger.info("Static data already exists, fetching existing Wards and Beds...")
                from sqlalchemy import select
                wards_res = await session.execute(select(Ward))
                wards_list = wards_res.scalars().all()
                icu = next(w for w in wards_list if w.type == WardType.ICU)
                emergency = next(w for w in wards_list if w.type == WardType.EMERGENCY)
                general = next(w for w in wards_list if w.type == WardType.GENERAL)
                
                beds_res = await session.execute(select(Bed).order_by(Bed.id))
                beds_list = beds_res.scalars().all()
                icu_beds = [b for b in beds_list if b.ward_id == icu.id]
                ed_beds = [b for b in beds_list if b.ward_id == emergency.id]
                general_beds = [b for b in beds_list if b.ward_id == general.id]

            logger.info("Seeding Patients with specific boundary conditions...")
            patients_to_add = [
                # --- Stable boundary edge case (Score exact 3.9) ---
                Patient(
                    name="John Stable-Edge",
                    age=35,
                    gender="Male",
                    admission_reason="Mild dehydration & observation",
                    status=PatientStatus.STABLE,
                    criticality_score=3.9,
                    admitted_at=datetime.utcnow()
                ),
                # General Stable Patients
                Patient(
                    name="Alice Smith",
                    age=28,
                    gender="Female",
                    admission_reason="Post-op recovery (appendectomy)",
                    status=PatientStatus.STABLE,
                    criticality_score=1.5,
                    admitted_at=datetime.utcnow()
                ),
                Patient(
                    name="David Jones",
                    age=45,
                    gender="Male",
                    admission_reason="Hypertension monitoring",
                    status=PatientStatus.STABLE,
                    criticality_score=2.8,
                    admitted_at=datetime.utcnow()
                ),
                Patient(
                    name="Emma Brown",
                    age=62,
                    gender="Female",
                    admission_reason="Diabetes management & insulin adjustment",
                    status=PatientStatus.STABLE,
                    criticality_score=3.2,
                    admitted_at=datetime.utcnow()
                ),
                Patient(
                    name="George Wilson",
                    age=50,
                    gender="Male",
                    admission_reason="Gastroenteritis symptoms",
                    status=PatientStatus.STABLE,
                    criticality_score=0.8,
                    admitted_at=datetime.utcnow()
                ),
                Patient(
                    name="Sophia Miller",
                    age=19,
                    gender="Female",
                    admission_reason="Laceration repair & observation",
                    status=PatientStatus.STABLE,
                    criticality_score=1.2,
                    admitted_at=datetime.utcnow()
                ),

                # --- Serious boundary edge cases (Lower exact 4.0, Upper exact 7.9) ---
                Patient(
                    name="Sarah Serious-Lower",
                    age=54,
                    gender="Female",
                    admission_reason="Pneumonia with moderate fever",
                    status=PatientStatus.SERIOUS,
                    criticality_score=4.0,
                    admitted_at=datetime.utcnow()
                ),
                Patient(
                    name="Michael Serious-Upper",
                    age=67,
                    gender="Male",
                    admission_reason="Congestive heart failure exacerbation",
                    status=PatientStatus.SERIOUS,
                    criticality_score=7.9,
                    admitted_at=datetime.utcnow()
                ),
                # General Serious Patients
                Patient(
                    name="Olivia Taylor",
                    age=42,
                    gender="Female",
                    admission_reason="Severe asthma attack (responding to treatment)",
                    status=PatientStatus.SERIOUS,
                    criticality_score=5.5,
                    admitted_at=datetime.utcnow()
                ),
                Patient(
                    name="William Davis",
                    age=71,
                    gender="Male",
                    admission_reason="Acute cholecystitis",
                    status=PatientStatus.SERIOUS,
                    criticality_score=6.2,
                    admitted_at=datetime.utcnow()
                ),
                Patient(
                    name="James Martinez",
                    age=59,
                    gender="Male",
                    admission_reason="Post-op recovery (total hip arthroplasty)",
                    status=PatientStatus.SERIOUS,
                    criticality_score=4.8,
                    admitted_at=datetime.utcnow()
                ),
                Patient(
                    name="Linda Anderson",
                    age=66,
                    gender="Female",
                    admission_reason="Pyelonephritis with mild sepsis watch",
                    status=PatientStatus.SERIOUS,
                    criticality_score=6.9,
                    admitted_at=datetime.utcnow()
                ),
                Patient(
                    name="Richard Thomas",
                    age=73,
                    gender="Male",
                    admission_reason="Exacerbation of COPD",
                    status=PatientStatus.SERIOUS,
                    criticality_score=7.1,
                    admitted_at=datetime.utcnow()
                ),

                # --- Critical boundary edge cases (Lower exact 8.0, Upper max 10.0) ---
                Patient(
                    name="Robert Critical-Lower",
                    age=60,
                    gender="Male",
                    admission_reason="Sepsis with hypotension, requiring fluid resuscitation",
                    status=PatientStatus.CRITICAL,
                    criticality_score=8.0,
                    admitted_at=datetime.utcnow()
                ),
                Patient(
                    name="Jane Critical-Upper",
                    age=78,
                    gender="Female",
                    admission_reason="Active respiratory distress profile, intubated",
                    status=PatientStatus.CRITICAL,
                    criticality_score=10.0,
                    admitted_at=datetime.utcnow()
                ),
                # General Critical Patients
                Patient(
                    name="Elizabeth White",
                    age=69,
                    gender="Female",
                    admission_reason="Acute myocardial infarction (post-angioplasty)",
                    status=PatientStatus.CRITICAL,
                    criticality_score=8.8,
                    admitted_at=datetime.utcnow()
                ),
                Patient(
                    name="Charles Harris",
                    age=51,
                    gender="Male",
                    admission_reason="Traumatic brain injury (subdural hematoma watch)",
                    status=PatientStatus.CRITICAL,
                    criticality_score=9.2,
                    admitted_at=datetime.utcnow()
                ),
                Patient(
                    name="Patricia Clark",
                    age=83,
                    gender="Female",
                    admission_reason="Diabetic ketoacidosis with altered mental state",
                    status=PatientStatus.CRITICAL,
                    criticality_score=8.5,
                    admitted_at=datetime.utcnow()
                ),
                Patient(
                    name="Thomas Lewis",
                    age=47,
                    gender="Male",
                    admission_reason="Severe multi-trauma (post-MVA)",
                    status=PatientStatus.CRITICAL,
                    criticality_score=9.6,
                    admitted_at=datetime.utcnow()
                ),
                Patient(
                    name="Barbara Lee",
                    age=58,
                    gender="Female",
                    admission_reason="Acute pancreatitis with system organ failure risk",
                    status=PatientStatus.CRITICAL,
                    criticality_score=9.0,
                    admitted_at=datetime.utcnow()
                ),
            ]

            session.add_all(patients_to_add)
            await session.flush()

            logger.info("Admitting patients to beds (allocating occupied state atomically)...")
            
            # Admit critical patients to ICU beds
            critical_patients = [p for p in patients_to_add if p.status == PatientStatus.CRITICAL]
            for idx, p in enumerate(critical_patients):
                if idx < len(icu_beds):
                    bed = icu_beds[idx]
                    bed.status = BedStatus.OCCUPIED
                    bed.patient_id = p.id
                    p.current_bed_id = bed.id
                    logger.info(f"Admitted critical patient {p.name} to bed {bed.bed_number}")

            # Admit serious patients to Emergency Department beds
            serious_patients = [p for p in patients_to_add if p.status == PatientStatus.SERIOUS]
            for idx, p in enumerate(serious_patients):
                if idx < len(ed_beds):
                    bed = ed_beds[idx]
                    bed.status = BedStatus.OCCUPIED
                    bed.patient_id = p.id
                    p.current_bed_id = bed.id
                    logger.info(f"Admitted serious patient {p.name} to bed {bed.bed_number}")

            # Admit stable patients to General Ward beds
            stable_patients = [p for p in patients_to_add if p.status == PatientStatus.STABLE]
            for idx, p in enumerate(stable_patients):
                if idx < len(general_beds):
                    bed = general_beds[idx]
                    bed.status = BedStatus.OCCUPIED
                    bed.patient_id = p.id
                    p.current_bed_id = bed.id
                    logger.info(f"Admitted stable patient {p.name} to bed {bed.bed_number}")

            # Seed initial active alerts
            logger.info("Seeding initial active alerts...")
            
            # Find Jane and Michael in the database
            jane = next(p for p in patients_to_add if p.name == "Jane Critical-Upper")
            michael = next(p for p in patients_to_add if p.name == "Michael Serious-Upper")
            
            alert_1 = Alert(
                patient_id=jane.id,
                alert_type=AlertType.LOW_OXYGEN,
                severity=AlertSeverity.CRITICAL,
                message=f"Jane Critical-Upper displays severe hypoxaemia (SpO2: 85%). Immediate clinical assessment required.",
                is_acknowledged=False
            )
            
            alert_2 = Alert(
                patient_id=michael.id,
                alert_type=AlertType.SCORE_SPIKE,
                severity=AlertSeverity.HIGH,
                message=f"Michael Serious-Upper EWS score spiked by 2.3 points (previous: 5.6 -> current: 7.9). Monitor closely for deterioration.",
                is_acknowledged=False
            )
            
            alert_3 = Alert(
                patient_id=None,
                alert_type=AlertType.ICU_AT_CAPACITY,
                severity=AlertSeverity.HIGH,
                message=f"ICU Ward at high capacity threshold. Monitor available beds for new incoming critical cases.",
                is_acknowledged=False
            )
            
            session.add_all([alert_1, alert_2, alert_3])

        if tx is not None:
            await tx.commit()
            logger.info("Database transaction committed successfully!")
    finally:
        if db is None:
            await session_ctx.__aexit__(None, None, None)

if __name__ == "__main__":
    logger.info("Initializing database seeding...")
    asyncio.run(seed_data())
    logger.info("Database seeding completed successfully.")
