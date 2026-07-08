import asyncio
import json
import logging
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
import crud
import schemas
import models
from routes.auth_routes import router as auth_router
from services.auth import check_roles

from services.logging_config import configure_logging
import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import Request

# Configure structured logging
configure_logging()
logger = structlog.get_logger("HospitalAI-Backend")

# Persistent Idempotency Engine
import hashlib

def generate_body_hash(payload) -> str:
    if payload is None:
        return ""
    if hasattr(payload, "model_dump_json"):
        body_bytes = payload.model_dump_json().encode("utf-8")
    elif hasattr(payload, "json"):
        body_bytes = payload.json().encode("utf-8")
    elif isinstance(payload, dict):
        body_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    elif isinstance(payload, str):
        body_bytes = payload.encode("utf-8")
    else:
        body_bytes = str(payload).encode("utf-8")
    return hashlib.sha256(body_bytes).hexdigest()

async def check_idempotency_db(db: AsyncSession, key: str, request_hash: str) -> Optional[dict]:
    if not key:
        return None
    from sqlalchemy import select
    res = await db.execute(
        select(models.IdempotencyKey).where(models.IdempotencyKey.id == key)
    )
    cached = res.scalar_one_or_none()
    if cached:
        if cached.request_body_hash != request_hash:
            logger.warning(f"Idempotency key mismatch for key: {key}", key=key)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key conflict: request payload does not match original request."
            )
        if cached.expires_at > datetime.utcnow():
            logger.info(f"Idempotency cache hit for key: {key}", key=key)
            return {
                "status_code": cached.status_code,
                "content": cached.response_body
            }
        else:
            await db.delete(cached)
    return None

async def save_idempotency_db(db: AsyncSession, key: str, request_hash: str, response_body: dict, status_code: int, endpoint: str):
    if not key:
        return
    from sqlalchemy import select
    res = await db.execute(
        select(models.IdempotencyKey).where(models.IdempotencyKey.id == key)
    )
    existing = res.scalar_one_or_none()
    if existing:
        return
    expires_at = datetime.utcnow() + timedelta(hours=24)
    new_key = models.IdempotencyKey(
        id=key,
        request_body_hash=request_hash,
        response_body=response_body,
        status_code=status_code,
        endpoint=endpoint,
        expires_at=expires_at
    )
    db.add(new_key)
    logger.info(f"Cached response in DB for idempotency key: {key}", key=key)

app = FastAPI(
    title="HospitalAI Command Center API",
    description="Real-time clinical operations coordinator, scoring engine, and recommendation platform.",
    version="1.0.0"
)

# Correlation ID Middleware (forces/extracts X-Correlation-ID headers)
app.add_middleware(CorrelationIdMiddleware, header_name="X-Correlation-ID")

from starlette.types import ASGIApp, Scope, Receive, Send

# ASGI middleware to bind HTTP metadata and authenticated user to the logger context
# This avoids the Starlette BaseHTTPMiddleware asyncpg state-switching bug.
class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        structlog.contextvars.clear_contextvars()
        
        # Simple cookie parsing from headers
        user_id = "anonymous"
        headers = dict(scope.get("headers", []))
        cookie_header = headers.get(b"cookie", b"").decode("utf-8")
        
        cookies = {}
        for cookie in cookie_header.split(";"):
            if "=" in cookie:
                k, v = cookie.strip().split("=", 1)
                cookies[k] = v
                
        token = cookies.get("auth_token")
        if token:
            from services.auth import decode_access_token
            payload = decode_access_token(token)
            if payload:
                user_id = payload.get("sub", "anonymous")

        structlog.contextvars.bind_contextvars(
            method=scope.get("method"),
            path=scope.get("path"),
            user_id=user_id
        )
        await self.app(scope, receive, send)

app.add_middleware(RequestLoggingMiddleware)

# Configure CORS for next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://172.21.128.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],  # Next.js local port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Authentication Routes
app.include_router(auth_router)

from routes.scenario_routes import router as scenario_router
from routes.integration_routes import router as integration_router

app.include_router(scenario_router)
app.include_router(integration_router)

# WebSocket Connection Manager for live dashboard updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: dict):
        logger.info(f"Broadcasting message to {len(self.active_connections)} clients: {message}")
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to client, disconnecting: {e}")
                self.disconnect(connection)

manager = ConnectionManager()

# Background task to send mock real-time data updates to the dashboard for visual verification
async def broadcast_dashboard_updates():
    import random
    
    occupancy_rates = {
        "ICU": 85.0,
        "GENERAL": 60.0,
        "EMERGENCY": 72.0
    }
    
    while True:
        if manager.active_connections:
            for ward in occupancy_rates:
                occupancy_rates[ward] = min(100.0, max(0.0, occupancy_rates[ward] + random.uniform(-2.0, 2.0)))
            
            payload = {
                "type": "OCCUPANCY_METRICS",
                "data": {
                    "icu_rate": round(occupancy_rates["ICU"], 1),
                    "general_rate": round(occupancy_rates["GENERAL"], 1),
                    "emergency_rate": round(occupancy_rates["EMERGENCY"], 1),
                    "total_beds_occupied": random.randint(120, 140),
                    "total_beds_available": random.randint(40, 60),
                    "pending_approvals": random.randint(2, 6)
                }
            }
            await manager.broadcast(payload)
        await asyncio.sleep(5)

async def send_websocket_heartbeat():
    while True:
        await asyncio.sleep(20)
        # Ping all active connections to clean up dropped clients
        for connection in list(manager.active_connections):
            try:
                # Send JSON Ping message to the client
                await connection.send_json({"type": "PING"})
            except Exception as e:
                logger.warning(f"WebSocket heartbeat transmission failed, disconnecting client: {e}")
                manager.disconnect(connection)

async def background_escalation_worker():
    from database import AsyncSessionLocal
    from sqlalchemy import select
    import models
    while True:
        try:
            async with AsyncSessionLocal() as db:
                now = datetime.utcnow()
                result = await db.execute(
                    select(models.Alert).where(
                        models.Alert.status.in_([models.AlertStatus.ACKNOWLEDGED, models.AlertStatus.IN_PROGRESS]),
                        models.Alert.sla_due_at < now
                    )
                )
                expired_alerts = result.scalars().all()
                for alert in expired_alerts:
                    alert.status = models.AlertStatus.ESCALATED
                    
                    escalation = models.AlertEscalation(
                        alert_id=alert.id,
                        from_role=alert.assigned_to_role,
                        to_role="DOCTOR",
                        reason=f"SLA Breach. Due at {alert.sla_due_at.isoformat()} but was not resolved."
                    )
                    db.add(escalation)
                    
                    notification = models.Notification(
                        recipient_role="DOCTOR",
                        type="ESCALATION",
                        title=f"Escalated Alert: {alert.alert_type.value if hasattr(alert.alert_type, 'value') else alert.alert_type}",
                        message=f"Alert for Patient {alert.patient_id} breached SLA and has been escalated."
                    )
                    db.add(notification)
                    
                if expired_alerts:
                    await db.commit()
                    await manager.broadcast({
                        "type": "ALERTS_ESCALATED",
                        "data": {"count": len(expired_alerts)}
                    })
        except Exception as e:
            logger.error(f"Background escalation worker failed: {e}")
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_dashboard_updates())
    asyncio.create_task(send_websocket_heartbeat())
    asyncio.create_task(background_escalation_worker())
    
    # Seed default ScoringPolicy if not exists
    from database import AsyncSessionLocal
    from sqlalchemy import select
    import models
    from services.sla_service import seed_default_sla_policies
    from tenacity import AsyncRetrying, stop_after_attempt, wait_fixed
    
    logger.info("Starting database connectivity check and default configuration seeding...")
    
    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(10),
            wait=wait_fixed(1.5),
            reraise=True
        ):
            with attempt:
                async with AsyncSessionLocal() as db:
                    res = await db.execute(select(models.ScoringPolicy).where(models.ScoringPolicy.is_active == True))
                    active_policy = res.scalar_one_or_none()
                    if not active_policy:
                        default_policy = models.ScoringPolicy(
                            name="NEWS2-Adult-Standard",
                            version="v1.0",
                            config_json={},
                            is_active=True
                        )
                        db.add(default_policy)
                        await db.commit()
                        logger.info("Seeded default active ScoringPolicy: NEWS2-Adult-Standard v1.0")
                        
                    await seed_default_sla_policies(db)
    except Exception as e:
        logger.error(f"Critical error: Failed to connect to database after 10 attempts during startup: {e}")
        raise e
            
    logger.info("Application startup complete. Live dashboard broadcaster initialized.")

@app.get("/")
async def root():
    return {"message": "Welcome to HospitalAI API v1.0 (Integration Ready)"}

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "HospitalAI"}

# --- REST Endpoints ---

@app.get("/api/wards", response_model=List[schemas.WardResponse])
async def get_wards(db: AsyncSession = Depends(get_db)):
    """Retrieve all hospital wards along with dynamic capacity telemetry."""
    return await crud.get_wards(db)

@app.get("/api/beds", response_model=List[schemas.BedResponse])
async def get_beds(ward_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    """List beds, optionally filtering by parent ward ID."""
    return await crud.get_beds(db, ward_id=ward_id)

@app.get("/api/patients", response_model=List[schemas.PatientResponse])
async def get_patients(db: AsyncSession = Depends(get_db)):
    """Retrieve all currently active admitted patients."""
    return await crud.get_patients(db)

@app.post("/api/patients/admit", response_model=schemas.PatientResponse)
async def admit_patient(
    payload: schemas.PatientAdmitPayload, 
    db: AsyncSession = Depends(get_db),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key")
):
    """Admit a patient, assigning an available bed atomically within a database transaction."""
    body_hash = ""
    if x_idempotency_key:
        body_hash = generate_body_hash(payload)
        cached = await check_idempotency_db(db, x_idempotency_key, body_hash)
        if cached:
            return JSONResponse(status_code=cached["status_code"], content=cached["content"])

    patient = await crud.admit_patient(db, payload)
    
    # 1. Dynamically run transfer assessment (Orchestration)
    hr = payload.heart_rate or (135 if payload.status == schemas.PatientStatus.CRITICAL else (115 if payload.status == schemas.PatientStatus.SERIOUS else 75))
    rr = payload.resp_rate or (32 if payload.status == schemas.PatientStatus.CRITICAL else (23 if payload.status == schemas.PatientStatus.SERIOUS else 16))
    spo2 = payload.spo2 or (85 if payload.status == schemas.PatientStatus.CRITICAL else (93 if payload.status == schemas.PatientStatus.SERIOUS else 98))
    
    vitals = {"heart_rate": hr, "resp_rate": rr, "spo2": spo2}
    
    from services.orchestrator import evaluate_patient_and_recommend
    from services.scoring.policy_service import get_active_policy
    
    policy = await get_active_policy(db)
    shadow_mode_enabled = policy.config_json.get("shadow_mode_enabled", False) if policy else False
    rec = await evaluate_patient_and_recommend(db, patient, vitals, shadow_mode_enabled=shadow_mode_enabled)
    
    # 2. Broadcast the admission update via WebSockets
    broadcast_payload = {
        "type": "PATIENT_ADMITTED",
        "data": {
            "patient_id": patient.id,
            "name": patient.name,
            "status": patient.status,
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
    
    if x_idempotency_key:
        res_data = jsonable_encoder(patient)
        await save_idempotency_db(db, x_idempotency_key, body_hash, res_data, 200, "/api/patients/admit")
        
    return patient

# --- Intelligence & HITL Recommendation Queue routes ---

@app.get("/api/recommendations/pending", response_model=List[schemas.RecommendationDetailResponse])
async def get_pending_recommendations(db: AsyncSession = Depends(get_db)):
    """Retrieve all pending clinical relocation recommendations requiring HITL review."""
    return await crud.get_pending_recommendations(db)

@app.post("/api/recommendations/{id}/action", response_model=schemas.RecommendationDetailResponse)
async def action_recommendation(
    id: int, 
    payload: schemas.RecommendationActionPayload, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(check_roles([models.UserRole.DOCTOR, models.UserRole.COORDINATOR]))
):
    """Execute human staff approval/rejection overrides atomically inside a database transaction."""
    rec = await crud.action_recommendation(db, id, payload.action, current_user.id)
    
    # Broadcast event via WebSockets to keep dashboard screens synced immediately
    await manager.broadcast({
        "type": "RECOMMENDATION_ACTIONED",
        "data": {
            "recommendation_id": rec.id,
            "action": payload.action,
            "patient_id": rec.patient_id,
            "patient_name": rec.patient.name,
            "status": rec.status
        }
    })
    
    return rec


@app.post("/api/recommendations/{id}/reject", response_model=schemas.RecommendationDetailResponse)
async def reject_recommendation(
    id: int,
    payload: schemas.RecommendationRejectPayload,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(check_roles([models.UserRole.DOCTOR, models.UserRole.COORDINATOR]))
):
    """Reject a recommendation with a required minimum 10-char reason."""
    rec = await crud.action_recommendation(db, id, "REJECT", current_user.id, payload=payload)
    
    await manager.broadcast({
        "type": "RECOMMENDATION_REJECTED",
        "data": {
            "recommendation_id": rec.id,
            "action": "REJECT",
            "patient_id": rec.patient_id,
            "patient_name": rec.patient.name,
            "status": rec.status.value if hasattr(rec.status, "value") else str(rec.status),
            "override_reason": rec.override_reason
        }
    })
    
    return rec


@app.post("/api/recommendations/{id}/regenerate", response_model=schemas.RecommendationDetailResponse)
async def regenerate_recommendation(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(check_roles([models.UserRole.DOCTOR, models.UserRole.COORDINATOR]))
):
    """Regenerate an expired recommendation using current patient vitals (vitals=None logic)."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    rec_result = await db.execute(
        select(models.Recommendation).options(selectinload(models.Recommendation.patient)).where(models.Recommendation.id == id)
    )
    rec = rec_result.scalar_one_or_none()
    if not rec:
         raise HTTPException(status_code=404, detail="Recommendation not found")
    if rec.status != models.RecommendationStatus.EXPIRED:
         raise HTTPException(status_code=400, detail="Only expired recommendations can be regenerated.")
         
    from services.orchestrator import evaluate_patient_and_recommend
    from services.scoring.policy_service import get_active_policy
    policy = await get_active_policy(db)
    shadow_mode_enabled = policy.config_json.get("shadow_mode_enabled", False)
    new_rec = await evaluate_patient_and_recommend(db, rec.patient, None, shadow_mode_enabled=shadow_mode_enabled)
    if not new_rec:
         raise HTTPException(status_code=400, detail="Patient no longer requires recommendation.")
         
    await manager.broadcast({
        "type": "RECOMMENDATION_REGENERATED",
        "data": {
            "old_id": rec.id,
            "new_recommendation": {
                "id": new_rec.id,
                "patient_name": rec.patient.name,
                "score": new_rec.criticality_score,
                "reasoning": new_rec.reasoning
            }
        }
    })
    return new_rec


@app.get("/api/alerts", response_model=List[schemas.AlertResponse])
async def get_alerts(db: AsyncSession = Depends(get_db)):
    """Retrieve all active unacknowledged alerts."""
    return await crud.get_active_alerts(db)


@app.post("/api/alerts/{id}/acknowledge", response_model=schemas.AlertResponse)
async def acknowledge_alert(
    id: int, 
    payload: schemas.AlertAcknowledgePayload, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(check_roles([models.UserRole.DOCTOR, models.UserRole.COORDINATOR, models.UserRole.NURSE]))
):
    """Acknowledge an active clinical alert."""
    alert = await crud.acknowledge_alert(db, id, user_id=current_user.id)
    
    # Broadcast event via WebSockets to keep dashboard synced
    await manager.broadcast({
        "type": "ALERT_ACKNOWLEDGED",
        "data": {
            "alert_id": alert.id,
            "status": alert.status.value if hasattr(alert.status, "value") else str(alert.status)
        }
    })
    
    return alert

@app.post("/api/alerts/{id}/resolve", response_model=schemas.AlertResponse)
async def resolve_alert(
    id: int, 
    payload: schemas.AlertResolvePayload, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(check_roles([models.UserRole.DOCTOR, models.UserRole.COORDINATOR, models.UserRole.NURSE]))
):
    """Resolve an active clinical alert."""
    alert = await crud.resolve_alert(db, id, payload, user_id=current_user.id)
    
    # Broadcast event via WebSockets to keep dashboard synced
    await manager.broadcast({
        "type": "ALERT_RESOLVED",
        "data": {
            "alert_id": alert.id,
            "status": alert.status.value if hasattr(alert.status, "value") else str(alert.status)
        }
    })
    
    return alert


@app.post("/api/patients/{id}/vitals", response_model=schemas.PatientResponse)
async def log_vitals(
    id: int, 
    payload: schemas.VitalsPayload, 
    db: AsyncSession = Depends(get_db),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key")
):
    """Log new vitals for a patient, compute score, evaluate alerts, and run orchestrator transfer reviews."""
    body_hash = ""
    if x_idempotency_key:
        body_hash = generate_body_hash(payload)
        cached = await check_idempotency_db(db, x_idempotency_key, body_hash)
        if cached:
            return JSONResponse(status_code=cached["status_code"], content=cached["content"])

    from sqlalchemy import select
    import models
    
    patient_res = await db.execute(
        select(models.Patient)
        .where(models.Patient.id == id)
    )
    patient = patient_res.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient ID {id} not found."
        )
        
    old_score = patient.criticality_score
    
    # 2. Compute NEWS2 Score & Update Patient Status
    from services.scoring.policy_service import get_active_policy
    from services.scoring.news2_service import calculate_news2
    from services.scoring.operational_service import calculate_operational_priority
    
    policy = await get_active_policy(db)
    baseline = await crud.get_patient_baseline(db, patient.id)
    
    vitals_record = models.PatientVitals(
        patient_id=patient.id,
        heart_rate=payload.heart_rate,
        resp_rate=payload.resp_rate,
        spo2=payload.spo2,
        temperature=payload.temperature,
        systolic_bp=payload.systolic_bp,
        consciousness_level=payload.consciousness_level,
        oxygen_supplement=payload.oxygen_supplement,
        spo2_scale=payload.spo2_scale
    )
    db.add(vitals_record)
    await db.flush()
    
    total_score, risk_band, breakdown, red_flags = calculate_news2(vitals_record, policy, baseline=baseline)
    operational_priority = calculate_operational_priority(total_score)
    
    new_score = operational_priority
    patient.criticality_score = new_score
    
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
    await db.flush()
    
    if risk_band == models.RiskBand.HIGH or new_score >= 8.0:
        patient.status = models.PatientStatus.CRITICAL
    elif risk_band == models.RiskBand.MEDIUM or new_score >= 4.0:
        patient.status = models.PatientStatus.SERIOUS
    else:
        patient.status = models.PatientStatus.STABLE
        
    await db.flush()
    
    # 3. Evaluate Alerts
    from services.alerts import evaluate_vitals_for_alerts
    from services.task_service import auto_generate_task_for_alert
    alerts = evaluate_vitals_for_alerts(patient.id, patient.name, old_score, new_score, payload.spo2)
    for alert in alerts:
        db.add(alert)
        await db.flush() # Flush to get ID for task
        await auto_generate_task_for_alert(db, alert, risk_band)
        alert_event = models.ClinicalEvent(
            patient_id=patient.id,
            event_type=models.ClinicalEventType.ALERT_TRIGGERED,
            description=alert.message,
            event_metadata={"severity": alert.severity, "alert_type": alert.alert_type},
        )
        db.add(alert_event)
        
    await db.flush()

    # Log Vitals Event
    vitals_event = models.ClinicalEvent(
        patient_id=patient.id,
        event_type=models.ClinicalEventType.VITALS_RECORDED,
        description=f"Vitals recorded. Score updated from {old_score:.1f} to {new_score:.1f}. Risk Band: {risk_band.value}",
        event_metadata={"vitals": {"hr": payload.heart_rate, "rr": payload.resp_rate, "spo2": payload.spo2}, "old_score": old_score, "new_score": new_score, "risk_band": risk_band.value, "clinical_score": total_score},
    )
    db.add(vitals_event)
    await db.flush()
    
    # 4. Evaluate Recommendation
    rec = None
    if risk_band == models.RiskBand.HIGH:
        from services.orchestrator import evaluate_patient_and_recommend
        vitals = {
            "heart_rate": payload.heart_rate,
            "resp_rate": payload.resp_rate,
            "spo2": payload.spo2
        }
        shadow_mode_enabled = policy.config_json.get("shadow_mode_enabled", False)
        rec = await evaluate_patient_and_recommend(db, patient, vitals, shadow_mode_enabled=shadow_mode_enabled)
    
    # Check if a capacity alert was generated during orchestrator run
    capacity_alerts = [obj for obj in db.new if isinstance(obj, models.Alert) and obj.patient_id is None]
    
    # 5. Broadcast updates via Websocket
    # Broadcast patient updated status first
    broadcast_payload = {
        "type": "PATIENT_UPDATED",
        "data": {
            "patient_id": patient.id,
            "name": patient.name,
            "status": patient.status,
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

    # Broadcast alerts if triggered
    triggered_alerts = alerts + capacity_alerts
    if triggered_alerts:
        alerts_data = []
        for alert in triggered_alerts:
            # Ensure ID is populated
            await db.flush()
            alert_dict = {
                "id": alert.id,
                "patient_id": alert.patient_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "is_acknowledged": alert.is_acknowledged,
                "created_at": alert.created_at.isoformat(),
                "patient": {
                    "id": patient.id,
                    "name": patient.name,
                    "age": patient.age,
                    "gender": patient.gender,
                    "admission_reason": patient.admission_reason,
                    "status": patient.status,
                    "criticality_score": patient.criticality_score,
                    "current_bed_id": patient.current_bed_id,
                    "admitted_at": patient.admitted_at.isoformat(),
                    "discharged_at": patient.discharged_at.isoformat() if patient.discharged_at else None
                } if alert.patient_id is not None else None
            }
            alerts_data.append(alert_dict)
            
        await manager.broadcast({
            "type": "ALERT_TRIGGERED",
            "data": alerts_data
        })
        
    if x_idempotency_key:
        res_data = jsonable_encoder(patient)
        await save_idempotency_db(db, x_idempotency_key, body_hash, res_data, 200, f"/api/patients/{id}/vitals")
        
    return patient


@app.get("/api/partner-hospitals", response_model=List[schemas.PartnerHospitalResponse])
async def get_partner_hospitals(db: AsyncSession = Depends(get_db)):
    """Retrieve partner hospitals list with available capacities and distances."""
    return await crud.get_partner_hospitals(db)


@app.get("/api/transfers", response_model=List[schemas.TransferRequestResponse])
async def get_transfers(db: AsyncSession = Depends(get_db)):
    """Retrieve historical and pending inter-hospital transfer requests."""
    return await crud.get_transfer_requests(db)


@app.post("/api/beds/{id}/status", response_model=schemas.BedResponse)
async def update_bed_status(
    id: int,
    payload: schemas.BedStatusUpdatePayload,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(check_roles([models.UserRole.DOCTOR, models.UserRole.COORDINATOR, models.UserRole.NURSE]))
):
    """Manually update a bed's status (e.g. from CLEANING to AVAILABLE)."""
    bed = await crud.update_bed_status(db, id, payload.status)
    
    # Broadcast bed update event via WebSockets
    await manager.broadcast({
        "type": "BED_UPDATED",
        "data": {
            "bed_id": bed.id,
            "ward_id": bed.ward_id,
            "bed_number": bed.bed_number,
            "status": bed.status,
            "patient_id": bed.patient_id,
            "patient": jsonable_encoder(bed.patient) if bed.patient else None
        }
    })
    
    return bed


@app.get("/api/audit-logs", response_model=List[schemas.AuditLogResponse])
async def get_audit_logs(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    correlation_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(check_roles([models.UserRole.ADMIN]))
):
    """Retrieve system action audit logs with administrative access."""
    from sqlalchemy import select
    import models
    query = select(models.AuditLog)
    if user_id:
        query = query.where(models.AuditLog.user_id == user_id)
    if action:
        query = query.where(models.AuditLog.action == action)
    if entity_type:
        query = query.where(models.AuditLog.entity_type == entity_type)
    if correlation_id:
        query = query.where(models.AuditLog.correlation_id == correlation_id)
        
    query = query.order_by(models.AuditLog.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@app.get("/api/patients/{id}/timeline", response_model=List[schemas.ClinicalEventResponse])
async def get_patient_timeline(id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve the immutable clinical event timeline for a patient."""
    from sqlalchemy import select
    import models
    query = (
        select(models.ClinicalEvent)
        .where(models.ClinicalEvent.patient_id == id)
        .order_by(models.ClinicalEvent.timestamp.desc())
    )
    result = await db.execute(query)
    return result.scalars().all()


@app.get("/api/health/metrics")
async def get_health_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(check_roles([models.UserRole.ADMIN]))
):
    """Expose internal platform health metrics to administrators."""
    import crud
    from database import engine
    
    pool = engine.pool
    metrics = {
        "db_pool_size": pool.size() if hasattr(pool, "size") else 5,
        "db_checked_out": pool.checkedout() if hasattr(pool, "checkedout") else 0,
        "db_overflow": pool.overflow() if hasattr(pool, "overflow") else 0,
        "active_websocket_clients": len(manager.active_connections),
        "recent_transaction_retries": getattr(crud, "RETRY_COUNT", 0)
    }
    return metrics


@app.post("/api/patients/{id}/feedback", response_model=schemas.DoctorFeedbackResponse)
async def submit_doctor_feedback(
    id: int,
    payload: schemas.DoctorFeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(check_roles([models.UserRole.DOCTOR, models.UserRole.ADMIN]))
):
    """Submit clinical feedback on a patient's score or recommendation."""
    from sqlalchemy import select
    # Verify patient exists
    patient_res = await db.execute(select(models.Patient).where(models.Patient.id == id))
    patient = patient_res.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    feedback = await crud.create_doctor_feedback(db, id, payload, current_user.id)
    
    if payload.recommendation_id:
        from sqlalchemy.orm import selectinload
        rec_res = await db.execute(
            select(models.Recommendation).options(selectinload(models.Recommendation.patient)).where(models.Recommendation.id == payload.recommendation_id)
        )
        rec = rec_res.scalar_one_or_none()
        if rec and rec.is_shadow:
            rec.status = models.RecommendationStatus.REJECTED
            rec.actioned_by_user_id = current_user.id
            rec.override_reason = f"Shadow Validation Complete: {payload.feedback_type}"
            await db.commit()
            await manager.broadcast({
                "type": "RECOMMENDATION_ACTIONED",
                "data": {
                    "recommendation_id": rec.id,
                    "action": "REJECT",
                    "patient_id": rec.patient_id,
                    "patient_name": patient.name,
                    "status": "REJECTED"
                }
            })

    return feedback


@app.post("/api/patients/{id}/baselines", response_model=schemas.PatientBaselineResponse)
async def update_patient_baseline(
    id: int,
    payload: schemas.PatientBaselineCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(check_roles([models.UserRole.DOCTOR, models.UserRole.ADMIN]))
):
    """Set or update physiological baselines for a patient (e.g. COPD baseline)."""
    from sqlalchemy import select
    # Verify patient exists
    patient_res = await db.execute(select(models.Patient).where(models.Patient.id == id))
    if not patient_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Patient not found")
        
    baseline = await crud.create_patient_baseline(db, id, payload, current_user.id)
    return baseline


async def send_delta_rehydration(websocket: WebSocket, db: AsyncSession, last_received: datetime):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    import models
    
    # naive UTC conversion
    if last_received.tzinfo is not None:
        last_received = last_received.astimezone(timezone.utc).replace(tzinfo=None)
        
    logger.info(f"Checking delta rehydration since: {last_received.isoformat()}")
    
    # 1. Query alerts
    alerts_res = await db.execute(
        select(models.Alert)
        .options(selectinload(models.Alert.patient))
        .where(models.Alert.created_at > last_received)
        .order_by(models.Alert.created_at.asc())
    )
    alerts = alerts_res.scalars().all()
    
    # 2. Query recommendations
    recs_res = await db.execute(
        select(models.Recommendation)
        .options(selectinload(models.Recommendation.patient))
        .where(models.Recommendation.created_at > last_received)
        .order_by(models.Recommendation.created_at.asc())
    )
    recs = recs_res.scalars().all()
    
    # 3. Query transfer requests
    trans_res = await db.execute(
        select(models.TransferRequest)
        .options(selectinload(models.TransferRequest.patient), selectinload(models.TransferRequest.partner_hospital))
        .where(models.TransferRequest.created_at > last_received)
        .order_by(models.TransferRequest.created_at.asc())
    )
    trans = trans_res.scalars().all()
    
    if alerts or recs or trans:
        alerts_data = []
        for alert in alerts:
            alerts_data.append({
                "id": alert.id,
                "patient_id": alert.patient_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "is_acknowledged": alert.is_acknowledged,
                "created_at": alert.created_at.isoformat(),
                "patient": {
                    "id": alert.patient.id,
                    "name": alert.patient.name,
                    "age": alert.patient.age,
                    "gender": alert.patient.gender,
                    "status": alert.patient.status,
                    "criticality_score": alert.patient.criticality_score,
                } if alert.patient else None
            })
            
        recs_data = []
        for rec in recs:
            recs_data.append({
                "id": rec.id,
                "patient_id": rec.patient_id,
                "patient_name": rec.patient.name if rec.patient else "Unknown",
                "source_bed_id": rec.source_bed_id,
                "target_bed_id": rec.target_bed_id,
                "partner_hospital_id": rec.partner_hospital_id,
                "status": rec.status,
                "criticality_score": rec.criticality_score,
                "reasoning": rec.reasoning,
                "created_at": rec.created_at.isoformat()
            })
            
        trans_data = []
        for tr in trans:
            trans_data.append({
                "id": tr.id,
                "patient_id": tr.patient_id,
                "patient_name": tr.patient.name if tr.patient else "Unknown",
                "partner_hospital_name": tr.partner_hospital.name if tr.partner_hospital else "Unknown",
                "reason": tr.reason,
                "status": tr.status,
                "created_at": tr.created_at.isoformat()
            })
            
        delta_payload = {
            "type": "DELTA_REHYDRATION",
            "data": {
                "alerts": alerts_data,
                "recommendations": recs_data,
                "transfer_requests": trans_data
            }
        }
        await websocket.send_json(delta_payload)


@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    # Secure WebSocket handshake upgrade using HttpOnly token cookie
    token = websocket.cookies.get("auth_token")
    if not token:
        logger.warning("WebSocket connection rejected: Missing auth_token cookie.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    from services.auth import decode_access_token
    payload = decode_access_token(token)
    if not payload:
        logger.warning("WebSocket connection rejected: Invalid or expired token.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    username = payload.get("sub")
    if not username:
        logger.warning("WebSocket connection rejected: Token subject missing.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    from sqlalchemy import select
    import models
    res = await db.execute(select(models.User).where(models.User.username == username))
    user = res.scalar_one_or_none()
    if not user or not user.is_active:
        logger.warning(f"WebSocket connection rejected: User '{username}' is inactive or not found.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    try:
        initial_payload = {
            "type": "INITIAL_STATE",
            "data": {
                "icu_rate": 84.5,
                "general_rate": 61.2,
                "emergency_rate": 70.0,
                "total_beds_occupied": 130,
                "total_beds_available": 50,
                "pending_approvals": 4
            }
        }
        await websocket.send_json(initial_payload)

        # Check if client passed last_received_timestamp to fetch delta state
        from datetime import timezone
        last_received_str = websocket.query_params.get("last_received_timestamp")
        if last_received_str:
            try:
                clean_ts = last_received_str.replace("Z", "+00:00")
                last_received_dt = datetime.fromisoformat(clean_ts)
                await send_delta_rehydration(websocket, db, last_received_dt)
            except Exception as ex:
                logger.warning(f"Failed to parse last_received_timestamp '{last_received_str}': {ex}")
        
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received message from client: {data}")
            try:
                msg = json.loads(data)
                if msg.get("command") == "PING":
                    await websocket.send_json({"type": "PONG"})
                elif msg.get("command") == "PONG":
                    # Keepalive acknowledgment received
                    pass
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON format"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        manager.disconnect(websocket)
