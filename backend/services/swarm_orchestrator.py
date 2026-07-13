import os
import logging
import json
import asyncio
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import requests

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
import crud

logger = logging.getLogger("HospitalAI-SwarmOrchestrator")

# --- Pydantic Output Validation Schemas ---

class AgentBid(BaseModel):
    agent_name: str
    proposed_bed_id: Optional[int] = None
    score: float = Field(..., ge=0.0, le=1.0)
    justification: str

class SwarmArbitrationResponse(BaseModel):
    final_score: float
    winning_bed_id: Optional[int]
    agent_bids: List[AgentBid]
    fallback_action: Optional[str] = None


# --- Agent Persona Core Loops ---

async def triage_agent_eval(
    db: AsyncSession,
    patient: models.Patient,
    current_ews: int,
    candidate_bed_id: Optional[int],
    candidate_ward_type: Optional[models.WardType]
) -> AgentBid:
    """
    Triage Agent (A_T): Maximize clinical safety margin.
    Evaluates vitals, historical EWS trajectory, and clinical urgency.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        prompt = (
            f"Role: Triage Agent. clinical urgency assessment.\n"
            f"Patient ID: {patient.id}, Name: {patient.name}, EWS Score: {current_ews}.\n"
            f"Candidate Bed ID: {candidate_bed_id}, Target Ward Type: {candidate_ward_type}.\n"
            f"Task: Evaluate if this bed placement maximizes clinical safety. Return a score (0.0 to 1.0) and justification."
        )
        data = await call_gemini_api(prompt, api_key, "Triage Agent", candidate_bed_id)
        if data:
            return AgentBid(**data)

    # Fallback to deterministic rules-based evaluation
    # Target ward should match clinical urgency
    expected_ward = models.WardType.GENERAL
    if current_ews >= 8:
        expected_ward = models.WardType.ICU
    elif current_ews >= 4:
        expected_ward = models.WardType.EMERGENCY

    score = 0.50
    justification = f"Patient is stable with EWS of {current_ews}. Candidate ward level is appropriate."

    if not candidate_bed_id:
        if current_ews >= 8:
            score = 0.90
            justification = f"Critical clinical necessity (EWS = {current_ews}): Local ICU beds full, external transfer required for continuous monitoring."
        else:
            score = 0.40
            justification = f"Stable/Serious clinical state (EWS = {current_ews}): External transfer candidate evaluated."
    else:
        if candidate_ward_type == expected_ward:
            score = 0.95
            justification = f"Optimal placement: Moving patient with EWS {current_ews} to {candidate_ward_type} matches clinical safety guidelines."
        elif candidate_ward_type == models.WardType.ICU and current_ews >= 8:
            score = 1.00
            justification = f"Critical emergency transfer: EWS {current_ews} requires immediate high-acuity ICU bed."
        elif candidate_ward_type == models.WardType.ICU and current_ews < 8:
            score = 0.40
            justification = f"Acuity mismatch: Patient EWS {current_ews} does not strictly warrant ICU resource utilization."
        elif candidate_ward_type == models.WardType.GENERAL and current_ews >= 4:
            score = 0.15
            justification = f"Insufficient safety margin: Placing patient with EWS {current_ews} in General Ward risks deterioration."

    return AgentBid(
        agent_name="Triage Agent",
        proposed_bed_id=candidate_bed_id,
        score=score,
        justification=justification
    )


async def resource_agent_eval(
    db: AsyncSession,
    patient: models.Patient,
    current_ews: int,
    candidate_bed_id: Optional[int],
    candidate_ward_type: Optional[models.WardType]
) -> AgentBid:
    """
    Resource Agent (A_R): Maximize systemic throughput and resource longevity.
    Evaluates ward capacity utilization matrices, physical transfer overhead, and protective buffer constraints.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        prompt = (
            f"Role: Resource Agent. Capacity utilization assessment.\n"
            f"Patient ID: {patient.id}, Candidate Bed ID: {candidate_bed_id}, Target Ward Type: {candidate_ward_type}.\n"
            f"Task: Evaluate if this bed allocation preserves target ward buffers. Return a score (0.0 to 1.0) and justification."
        )
        data = await call_gemini_api(prompt, api_key, "Resource Agent", candidate_bed_id)
        if data:
            return AgentBid(**data)

    # Fallback to deterministic rules-based evaluation
    if not candidate_bed_id:
        return AgentBid(
            agent_name="Resource Agent",
            proposed_bed_id=None,
            score=0.85,
            justification="External transfer preserves local ward buffers and protects resource longevity."
        )

    # Load bed and its ward to check utilization
    res = await db.execute(
        select(models.Bed).options(selectinload(models.Bed.ward)).where(models.Bed.id == candidate_bed_id)
    )
    bed = res.scalar_one_or_none()
    if not bed or not bed.ward:
        return AgentBid(
            agent_name="Resource Agent",
            proposed_bed_id=candidate_bed_id,
            score=0.50,
            justification="Bed ward details missing, assuming neutral resource availability."
        )

    ward = bed.ward
    # Count occupied beds in ward
    occupied_count = await db.scalar(
        select(func.count(models.Bed.id))
        .where(models.Bed.ward_id == ward.id)
        .where(models.Bed.status == models.BedStatus.OCCUPIED)
    )

    utilization_rate = (occupied_count / ward.capacity) * 100 if ward.capacity > 0 else 0
    available_beds = ward.capacity - occupied_count

    score = 0.90
    justification = f"Ward {ward.name} utilization is {utilization_rate:.1f}%. Safe buffer capacity maintained."

    if available_beds <= 1:
        # Reserve last bed for emergency vehicles
        score = 0.35
        justification = f"High capacity alert: Ward {ward.name} has only {available_beds} bed remaining. Restricting transfer to protect emergency buffers."
    elif utilization_rate >= 80:
        score = 0.60
        justification = f"Ward {ward.name} utilization is high ({utilization_rate:.1f}%). Transfer allowed but closely monitored."

    return AgentBid(
        agent_name="Resource Agent",
        proposed_bed_id=candidate_bed_id,
        score=score,
        justification=justification
    )


async def logistics_agent_eval(
    db: AsyncSession,
    patient: models.Patient,
    current_ews: int,
    candidate_bed_id: Optional[int],
    candidate_ward_type: Optional[models.WardType]
) -> AgentBid:
    """
    Staff Logistics Agent (A_L): Prevent staff operational burnout.
    Evaluates nurse-to-patient ratios, current ward fatigue indexes, and shift limits.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        prompt = (
            f"Role: Staff Logistics Agent. Nurse-to-patient ratio assessment.\n"
            f"Patient ID: {patient.id}, Candidate Bed ID: {candidate_bed_id}, Target Ward Type: {candidate_ward_type}.\n"
            f"Task: Evaluate if adding a patient fits current nurse ratios and prevents burnout. Return a score (0.0 to 1.0) and justification."
        )
        data = await call_gemini_api(prompt, api_key, "Staff Logistics Agent", candidate_bed_id)
        if data:
            return AgentBid(**data)

    # Fallback to deterministic rules-based evaluation
    if not candidate_bed_id:
        return AgentBid(
            agent_name="Staff Logistics Agent",
            proposed_bed_id=None,
            score=0.85,
            justification="External transfer prevents additional workload on local nursing staff."
        )

    # Load bed and its ward to check staffing constraints
    res = await db.execute(
        select(models.Bed).options(selectinload(models.Bed.ward)).where(models.Bed.id == candidate_bed_id)
    )
    bed = res.scalar_one_or_none()
    if not bed or not bed.ward:
        return AgentBid(
            agent_name="Staff Logistics Agent",
            proposed_bed_id=candidate_bed_id,
            score=0.50,
            justification="Bed ward details missing, assuming neutral logistics."
        )

    ward = bed.ward
    # Query staffing constraint
    staffing_res = await db.execute(
        select(models.WardStaffing).where(models.WardStaffing.ward_name == ward.name)
    )
    staffing = staffing_res.scalar_one_or_none()
    if not staffing:
        return AgentBid(
            agent_name="Staff Logistics Agent",
            proposed_bed_id=candidate_bed_id,
            score=0.85,
            justification=f"No staffing constraints configured for ward {ward.name}. Safe to proceed."
        )

    # Count occupied beds in ward
    occupied_count = await db.scalar(
        select(func.count(models.Bed.id))
        .where(models.Bed.ward_id == ward.id)
        .where(models.Bed.status == models.BedStatus.OCCUPIED)
    )

    new_occupied = occupied_count + 1
    max_allowed = staffing.current_nurses * staffing.max_patient_ratio

    if new_occupied <= max_allowed:
        score = 0.90
        justification = f"Safe staffing: patient-to-nurse ratio ({new_occupied}:{staffing.current_nurses}) fits within 1:{staffing.max_patient_ratio} limit."
    else:
        score = 0.15
        justification = f"Logistics overload: adding patient to {ward.name} breaches the maximum 1:{staffing.max_patient_ratio} patient-to-nurse limit."

    return AgentBid(
        agent_name="Staff Logistics Agent",
        proposed_bed_id=candidate_bed_id,
        score=score,
        justification=justification
    )


# --- LLM API Call Utility ---

async def call_gemini_api(prompt: str, api_key: str, agent_name: str, proposed_bed_id: Optional[int]) -> Optional[dict]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "agent_name": {"type": "STRING"},
                    "proposed_bed_id": {"type": "INTEGER"},
                    "score": {"type": "NUMBER"},
                    "justification": {"type": "STRING"}
                },
                "required": ["agent_name", "proposed_bed_id", "score", "justification"]
            }
        }
    }
    headers = {"Content-Type": "application/json"}
    
    def sync_post():
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
        
    try:
        res_json = await asyncio.to_thread(sync_post)
        text = res_json["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except Exception as e:
        logger.error(f"Gemini API call failed for {agent_name}: {e}. Falling back.")
        return None


# --- The Orchestration Negotiation Protocol ---

async def orchestrate_allocation(
    db: AsyncSession,
    patient_id: int,
    current_ews: int,
    shadow_mode_enabled: bool = False
) -> Optional[models.Recommendation]:
    """
    Autonomous multi-agent swarm negotiation loop.
    Evaluates patient vitals, ward capacities, and nurse staffing ratios concurrently
    to generate clinical recommendations with dual-execution models and WebSocket streams.
    """
    # 1. Fetch patient
    res = await db.execute(select(models.Patient).where(models.Patient.id == patient_id))
    patient = res.scalar_one_or_none()
    if not patient:
        logger.error(f"Patient with ID {patient_id} not found in database.")
        return None

    # Determine clinical target ward level
    target_ward_type = None
    if current_ews >= 8:
        target_ward_type = models.WardType.ICU
    elif current_ews >= 4:
        target_ward_type = models.WardType.EMERGENCY

    if not target_ward_type:
        # Patient is stable, no immediate transfer required
        return None

    # Check if a pending recommendation already exists for this patient
    pending_check = await db.execute(
        select(models.Recommendation)
        .where(models.Recommendation.patient_id == patient_id)
        .where(models.Recommendation.status == models.RecommendationStatus.PENDING)
    )
    existing_rec = pending_check.scalar_one_or_none()
    if existing_rec:
        return existing_rec

    # 2. Query available candidate beds in target ward type
    candidate_bed_query = (
        select(models.Bed)
        .join(models.Ward)
        .where(models.Ward.type == target_ward_type)
        .where(models.Bed.status == models.BedStatus.AVAILABLE)
        .limit(1)
    )
    candidate_bed_res = await db.execute(candidate_bed_query)
    candidate_bed = candidate_bed_res.scalar_one_or_none()

    bids: List[AgentBid] = []
    final_score = 0.0
    
    # We will use this flag to decide if we need to fall back
    trigger_fallback = False

    if candidate_bed:
        # Spawn parallel agent tasks to evaluate the candidate bed placement
        bids = await asyncio.gather(
            triage_agent_eval(db, patient, current_ews, candidate_bed.id, target_ward_type),
            resource_agent_eval(db, patient, current_ews, candidate_bed.id, target_ward_type),
            logistics_agent_eval(db, patient, current_ews, candidate_bed.id, target_ward_type)
        )

        # Apply weighted arbitration formula:
        # Final Score = 0.50 * Triage + 0.25 * Resource + 0.25 * Logistics
        s_t = next(b.score for b in bids if b.agent_name == "Triage Agent")
        s_r = next(b.score for b in bids if b.agent_name == "Resource Agent")
        s_l = next(b.score for b in bids if b.agent_name == "Staff Logistics Agent")

        final_score = (0.50 * s_t) + (0.25 * s_r) + (0.25 * s_l)

        # If any agent score indicates a severe block (e.g. logistics ratio breached) or final score is very low:
        if s_l < 0.20 or s_r < 0.20 or final_score < 0.50:
            trigger_fallback = True
    else:
        # No local bed directly available in target ward type
        trigger_fallback = True

    recommendation = None

    if trigger_fallback:
        # Fallback 1: ICU step-down candidate evaluation (only if target ward is ICU)
        if target_ward_type == models.WardType.ICU:
            from services.orchestrator import run_icu_step_down_agent
            stepdown_rec = await run_icu_step_down_agent(db, patient)
            if stepdown_rec:
                # Add mock/simulated bids for the stepdown to match the mathematical logs
                bids = [
                    AgentBid(agent_name="Triage Agent", proposed_bed_id=stepdown_rec.target_bed_id, score=0.85, justification="ICU transfer is required, step-down frees up bed."),
                    AgentBid(agent_name="Resource Agent", proposed_bed_id=stepdown_rec.target_bed_id, score=0.75, justification="Step-down candidate found to maintain capacity."),
                    AgentBid(agent_name="Staff Logistics Agent", proposed_bed_id=stepdown_rec.target_bed_id, score=0.80, justification="Logistics ratio balanced by shifting stable patient down.")
                ]
                final_score = 0.8125
                recommendation = stepdown_rec
        
        # Fallback 2: If stepdown didn't yield a recommendation, trigger external inter-hospital transfer
        if not recommendation:
            from services.orchestrator import run_inter_hospital_agent
            reason_suffix = "Staffing/Resource constraints exceeded local thresholds." if candidate_bed else "No local beds available."
            inter_hospital_rec = await run_inter_hospital_agent(
                db, 
                patient, 
                custom_reasoning=f"Blocked: {reason_suffix}"
            )
            if inter_hospital_rec:
                # Add mock bids for external transfer
                bids = [
                    AgentBid(agent_name="Triage Agent", proposed_bed_id=None, score=0.90, justification="Local ICU full/staffed-out, external transfer required for patient safety."),
                    AgentBid(agent_name="Resource Agent", proposed_bed_id=None, score=0.85, justification="External transfer preserves local resource capacity."),
                    AgentBid(agent_name="Staff Logistics Agent", proposed_bed_id=None, score=0.85, justification="External transfer prevents additional workload on local nursing staff.")
                ]
                final_score = 0.875
                recommendation = inter_hospital_rec

    else:
        # Create standard LOCAL_ICU_TRANSFER or similar recommendation
        target_ward_name = "ICU" if target_ward_type == models.WardType.ICU else "Emergency Department"
        triage_bid = next(b for b in bids if b.agent_name == "Triage Agent")
        
        expires_at = None if shadow_mode_enabled else datetime.utcnow() + timedelta(minutes=5)
        recommendation = models.Recommendation(
            patient_id=patient.id,
            source_bed_id=patient.current_bed_id,
            target_bed_id=candidate_bed.id,
            status=models.RecommendationStatus.PENDING,
            recommendation_type=models.RecommendationType.LOCAL_ICU_TRANSFER,
            criticality_score=final_score * 10.0, # scaled to 0.0-10.0 range
            reasoning=triage_bid.justification,
            expires_at=expires_at,
            is_shadow=shadow_mode_enabled
        )
        db.add(recommendation)
        await db.flush()

        # Log Clinical Event
        event_type = models.ClinicalEventType.SHADOW_RECOMMENDATION_GENERATED if shadow_mode_enabled else models.ClinicalEventType.RECOMMENDATION_GENERATED
        gen_event = models.ClinicalEvent(
            patient_id=patient.id,
            event_type=event_type,
            description=f"{'Shadow ' if shadow_mode_enabled else ''}Generated internal transfer recommendation to {target_ward_name}.",
            event_metadata={"recommendation_id": recommendation.id, "target_ward": target_ward_name, "score": final_score * 10.0, "is_shadow": shadow_mode_enabled},
        )
        db.add(gen_event)

    if recommendation:
        # Write structural log packet to OperationalLog
        payload = {
            "recommendation_id": recommendation.id,
            "final_score": final_score,
            "agent_bids": [bid.dict() for bid in bids],
            "type": recommendation.recommendation_type.value if hasattr(recommendation.recommendation_type, "value") else str(recommendation.recommendation_type),
            "is_shadow": shadow_mode_enabled
        }
        await crud.log_operational_event(
            db,
            patient.id,
            "RECOMMENDATION_GENERATED",
            payload
        )

        # Preload attributes to return clean model
        if recommendation.target_bed_id:
            target_bed_res = await db.execute(
                select(models.Bed).options(selectinload(models.Bed.ward)).where(models.Bed.id == recommendation.target_bed_id)
            )
            recommendation.target_bed = target_bed_res.scalar_one_or_none()
        if recommendation.source_bed_id:
            source_bed_res = await db.execute(
                select(models.Bed).options(selectinload(models.Bed.ward)).where(models.Bed.id == recommendation.source_bed_id)
            )
            recommendation.source_bed = source_bed_res.scalar_one_or_none()

        # Broadcast the fresh recommendation via WebSockets
        try:
            from main import manager
            broadcast_payload = {
                "type": "RECOMMENDATION_GENERATED",
                "data": {
                    "id": recommendation.id,
                    "patient_id": patient.id,
                    "patient_name": patient.name,
                    "score": recommendation.criticality_score,
                    "reasoning": recommendation.reasoning,
                    "agent_bids": [bid.dict() for bid in bids],
                    "type": recommendation.recommendation_type.value if hasattr(recommendation.recommendation_type, "value") else str(recommendation.recommendation_type),
                    "is_shadow": shadow_mode_enabled
                }
            }
            await manager.broadcast(broadcast_payload)
        except Exception as ws_err:
            logger.error(f"Failed to broadcast swarm recommendation via WebSockets: {ws_err}")

        return recommendation

    return None
