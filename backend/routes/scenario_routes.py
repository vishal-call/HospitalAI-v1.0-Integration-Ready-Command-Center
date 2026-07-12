import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from database import get_db
from services.auth import check_roles
import models
from seed import seed_data

logger = logging.getLogger("HospitalAI-Scenarios")

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])

class ScenarioTriggerPayload(BaseModel):
    scenario: str = Field(..., pattern="^(reset_data|fill_icu|spawn_critical_emergency|spawn_stable_icu|clear_alerts|trigger_chained_chain)$")

@router.post("/trigger")
async def trigger_scenario(
    payload: ScenarioTriggerPayload,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(check_roles([models.UserRole.ADMIN]))
):
    from main import manager
    sc = payload.scenario
    logger.info(f"Triggering demo scenario: {sc} by user {current_user.username}")

    if sc == "reset_data":
        # Wipes and reseeds the database
        await seed_data(db, clear_only=True)
        # Broadcast a clear alert delta so the UI refreshes
        await manager.broadcast({
            "type": "DELTA_REHYDRATION",
            "data": {
                "alerts": [],
                "recommendations": [],
                "transfer_requests": []
            }
        })
        return {"status": "success", "message": "Database reset to clean baseline successfully."}

    elif sc == "fill_icu":
        # Instantly occupies all available ICU beds with dummy patients
        # ICU ward_id is 1
        bed_res = await db.execute(
            select(models.Bed)
            .where(models.Bed.ward_id == 1)
            .where(models.Bed.status == models.BedStatus.AVAILABLE)
        )
        avail_beds = bed_res.scalars().all()
        
        seeded_count = 0
        for idx, bed in enumerate(avail_beds):
            # Create dummy patient
            dummy = models.Patient(
                name=f"Dummy ICU Patient {idx+1}",
                age=60,
                gender="Male",
                admission_reason="Seeded ICU Capacity Strain Case",
                status=models.PatientStatus.SERIOUS,
                criticality_score=5.0,
                current_bed_id=bed.id
            )
            db.add(dummy)
            await db.flush()
            
            bed.status = models.BedStatus.OCCUPIED
            bed.patient_id = dummy.id
            seeded_count += 1
            
            # Broadcast bed update
            await manager.broadcast({
                "type": "BED_UPDATED",
                "data": {
                    "bed_id": bed.id,
                    "ward_id": bed.ward_id,
                    "bed_number": bed.bed_number,
                    "status": bed.status,
                    "patient_id": bed.patient_id,
                    "patient": {
                        "id": dummy.id,
                        "name": dummy.name,
                        "age": dummy.age,
                        "gender": dummy.gender,
                        "status": dummy.status,
                        "criticality_score": dummy.criticality_score,
                    }
                }
            })
            
        await db.commit()
        
        # Trigger an ICU_AT_CAPACITY system alert if ICU is now 100% full
        icu_beds_res = await db.execute(
            select(models.Bed)
            .where(models.Bed.ward_id == 1)
        )
        all_icu_beds = icu_beds_res.scalars().all()
        occupied_count = sum(1 for b in all_icu_beds if b.status == models.BedStatus.OCCUPIED)
        
        if occupied_count >= len(all_icu_beds):
            # Create a capacity alert
            capacity_alert = models.Alert(
                patient_id=None,
                alert_type=models.AlertType.ICU_AT_CAPACITY,
                severity=models.AlertSeverity.CRITICAL,
                message="ICU Ward at high capacity threshold. Monitor available beds for new incoming critical cases."
            )
            db.add(capacity_alert)
            await db.flush()
            
            await manager.broadcast({
                "type": "ALERT_TRIGGERED",
                "data": [{
                    "id": capacity_alert.id,
                    "patient_id": None,
                    "alert_type": capacity_alert.alert_type.value,
                    "severity": capacity_alert.severity.value,
                    "message": capacity_alert.message,
                    "is_acknowledged": False,
                    "created_at": capacity_alert.created_at.isoformat(),
                    "patient": None
                }]
            })
            await db.commit()
            
        return {"status": "success", "message": f"Seeded {seeded_count} dummy patients to occupy the ICU."}

    elif sc == "spawn_critical_emergency":
        # Admits a new patient into the Emergency Ward with SpO2=85 and Heart Rate=135
        # Emergency ward_id is 2
        bed_res = await db.execute(
            select(models.Bed)
            .where(models.Bed.ward_id == 2)
            .where(models.Bed.status == models.BedStatus.AVAILABLE)
            .limit(1)
        )
        avail_bed = bed_res.scalar_one_or_none()
        if not avail_bed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No available beds in Emergency Ward to spawn critical patient."
            )
            
        from services.scoring import calculate_criticality_score
        score = calculate_criticality_score(135, 32, 85) # HR=135, RR=32, SpO2=85 -> EWS 10.0
        
        patient = models.Patient(
            name="Emergency Telemetry Spawn",
            age=72,
            gender="Female",
            admission_reason="Cardiac arrhythmia & hypoxemia",
            status=models.PatientStatus.CRITICAL,
            criticality_score=score,
            current_bed_id=avail_bed.id
        )
        db.add(patient)
        await db.flush()
        
        avail_bed.status = models.BedStatus.OCCUPIED
        avail_bed.patient_id = patient.id
        
        # Evaluate Alerts
        from services.alerts import evaluate_vitals_for_alerts
        alerts = evaluate_vitals_for_alerts(patient.id, patient.name, 0.0, score, 85)
        for alert in alerts:
            db.add(alert)
            await db.flush()
            import crud
            await crud.log_operational_event(
                db,
                patient.id,
                "ALERT_TRIGGERED",
                {
                    "alert_id": alert.id,
                    "alert_type": alert.alert_type.value if hasattr(alert.alert_type, "value") else str(alert.alert_type),
                    "severity": alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
                    "ews_score": score
                }
            )
        
        # Evaluate recommendations
        from services.orchestrator import evaluate_patient_and_recommend
        vitals = {"heart_rate": 135, "resp_rate": 32, "spo2": 85}
        rec = await evaluate_patient_and_recommend(db, patient, vitals)
        
        # Log audit trail
        import crud
        await crud.create_audit_log(
            db,
            action="ADMIT",
            entity_type="patient",
            entity_id=patient.id,
            after_data=crud.serialize_patient(patient),
            user_id=current_user.username
        )
        
        await db.commit()
        
        # Broadcast updates
        broadcast_payload = {
            "type": "PATIENT_ADMITTED",
            "data": {
                "patient_id": patient.id,
                "name": patient.name,
                "status": patient.status.value,
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
        
        if alerts:
            alerts_data = [{
                "id": a.id,
                "patient_id": a.patient_id,
                "alert_type": a.alert_type.value,
                "severity": a.severity.value,
                "message": a.message,
                "is_acknowledged": False,
                "created_at": a.created_at.isoformat(),
                "patient": {
                    "id": patient.id,
                    "name": patient.name,
                    "age": patient.age,
                    "gender": patient.gender,
                    "status": patient.status.value,
                    "criticality_score": patient.criticality_score,
                }
            } for a in alerts]
            await manager.broadcast({
                "type": "ALERT_TRIGGERED",
                "data": alerts_data
            })
            
        return {"status": "success", "message": f"Spawned critical emergency patient {patient.name} in bed {avail_bed.bed_number}."}

    elif sc == "spawn_stable_icu":
        # Modifies an existing ICU patient's vitals to reflect stable EWS score of 2.0
        # Find an occupied ICU patient (ward_id = 1)
        pat_res = await db.execute(
            select(models.Patient)
            .join(models.Bed, models.Patient.id == models.Bed.patient_id)
            .where(models.Bed.ward_id == 1)
            .limit(1)
        )
        patient = pat_res.scalar_one_or_none()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No patients currently in ICU to stabilize."
            )
            
        patient.status = models.PatientStatus.STABLE
        patient.criticality_score = 2.0
        await db.flush()
        
        # Evaluate step-down recommendation (ICU is at capacity check)
        from services.orchestrator import evaluate_patient_and_recommend
        vitals = {"heart_rate": 72, "resp_rate": 16, "spo2": 98}
        rec = await evaluate_patient_and_recommend(db, patient, vitals)
        
        await db.commit()
        
        # Broadcast update
        broadcast_payload = {
            "type": "PATIENT_UPDATED",
            "data": {
                "patient_id": patient.id,
                "name": patient.name,
                "status": patient.status.value,
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
        
        return {"status": "success", "message": f"Stabilized patient {patient.name} (EWS: 2.0). Step-down evaluation triggered."}

    elif sc == "clear_alerts":
        # Acknowledges and resolves all active alerts and recommendations
        # 1. Update all active alerts
        await db.execute(
            text("UPDATE alerts SET is_acknowledged = true WHERE is_acknowledged = false")
        )
        
        # 2. Reject all pending recommendations
        await db.execute(
            text("UPDATE recommendations SET status = 'REJECTED' WHERE status = 'PENDING'")
        )
        
        await db.commit()
        
        # Broadcast delta rehydration to clear client dashboard feeds
        await manager.broadcast({
            "type": "DELTA_REHYDRATION",
            "data": {
                "alerts": [],
                "recommendations": [],
                "transfer_requests": []
            }
        })
        
        return {"status": "success", "message": "All clinical alerts and recommendations successfully cleared."}

    elif sc == "trigger_chained_chain":
        # 1. Reset data to baseline
        await seed_data(db, clear_only=True)
        
        # 2. Get all ICU beds (Ward ID 1)
        icu_beds_res = await db.execute(
            select(models.Bed)
            .where(models.Bed.ward_id == 1)
            .order_by(models.Bed.id.asc())
        )
        icu_beds = icu_beds_res.scalars().all()
        
        # Occupy 11 beds with serious dummy patients, and 1 bed with a stable patient
        for idx, bed in enumerate(icu_beds):
            is_last = (idx == len(icu_beds) - 1)
            p_name = "Chained Stable Patient" if is_last else f"ICU Patient {idx+1}"
            p_status = models.PatientStatus.STABLE if is_last else models.PatientStatus.SERIOUS
            p_score = 2.0 if is_last else 6.0
            
            p = models.Patient(
                name=p_name,
                age=55 + idx,
                gender="Female" if idx % 2 == 0 else "Male",
                admission_reason="ICU Capacity Seeding",
                status=p_status,
                criticality_score=p_score,
                current_bed_id=bed.id
            )
            db.add(p)
            await db.flush()
            
            bed.status = models.BedStatus.OCCUPIED
            bed.patient_id = p.id
            
            # Broadcast bed update
            await manager.broadcast({
                "type": "BED_UPDATED",
                "data": {
                    "bed_id": bed.id,
                    "ward_id": bed.ward_id,
                    "bed_number": bed.bed_number,
                    "status": bed.status.value,
                    "patient_id": bed.patient_id,
                    "patient": {
                        "id": p.id,
                        "name": p.name,
                        "age": p.age,
                        "gender": p.gender,
                        "status": p.status.value,
                        "criticality_score": p.criticality_score,
                    }
                }
            })

        # 3. Get one available General Ward bed for the critical patient to start in
        gw_bed_res = await db.execute(
            select(models.Bed)
            .where(models.Bed.ward_id == 3) # General Ward is Ward 3
            .where(models.Bed.status == models.BedStatus.AVAILABLE)
            .limit(1)
        )
        gw_bed = gw_bed_res.scalar_one_or_none()
        if not gw_bed:
            # DEBUG
            all_gw = await db.execute(select(models.Bed).where(models.Bed.ward_id == 3))
            print("ALL GW BEDS:", all_gw.scalars().all())
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No available General Ward beds to spawn critical patient."
            )
            
        # Admit a patient "Critical Chain Patient" into this GW bed
        critical_patient = models.Patient(
            name="Critical Chain Patient",
            age=68,
            gender="Male",
            admission_reason="Seeded Chained Deterioration Case",
            status=models.PatientStatus.STABLE,
            criticality_score=2.0,
            current_bed_id=gw_bed.id
        )
        db.add(critical_patient)
        await db.flush()
        
        gw_bed.status = models.BedStatus.OCCUPIED
        gw_bed.patient_id = critical_patient.id
        await db.flush()
        
        # Now, log vitals that deteriorate this patient, which triggers the chained recommendation!
        # Vitals: HR=140, RR=32, SpO2=85 -> EWS 10.0
        from services.scoring import calculate_criticality_score
        score = calculate_criticality_score(140, 32, 85)
        old_score = critical_patient.criticality_score
        critical_patient.criticality_score = score
        critical_patient.status = models.PatientStatus.CRITICAL
        await db.flush()
        
        # Evaluate Alerts
        from services.alerts import evaluate_vitals_for_alerts
        alerts = evaluate_vitals_for_alerts(critical_patient.id, critical_patient.name, old_score, score, 85)
        for alert in alerts:
            db.add(alert)
            await db.flush()
            import crud
            await crud.log_operational_event(
                db,
                critical_patient.id,
                "ALERT_TRIGGERED",
                {
                    "alert_id": alert.id,
                    "alert_type": alert.alert_type.value if hasattr(alert.alert_type, "value") else str(alert.alert_type),
                    "severity": alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
                    "ews_score": score
                }
            )
        
        # Evaluate recommendation (which should trigger chained transfer!)
        from services.orchestrator import evaluate_patient_and_recommend
        vitals = {"heart_rate": 140, "resp_rate": 32, "spo2": 85}
        rec = await evaluate_patient_and_recommend(db, critical_patient, vitals)
        
        await db.commit()
        
        # Broadcast delta rehydration to ensure UI is clean and shows the new state
        import crud
        active_alerts = await crud.get_active_alerts(db)
        pending_recs = await crud.get_pending_recommendations(db)
        
        from fastapi.encoders import jsonable_encoder
        await manager.broadcast({
            "type": "DELTA_REHYDRATION",
            "data": {
                "alerts": jsonable_encoder(active_alerts),
                "recommendations": jsonable_encoder(pending_recs),
                "transfer_requests": []
            }
        })
        
        return {"status": "success", "message": "ICU step-down chain scenario successfully triggered."}
