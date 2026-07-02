from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from models import UserRole, PatientStatus, WardType, BedStatus, RecommendationStatus, RecommendationType, AlertType, AlertSeverity, AlertStatus, TaskStatus, TransferRequestStatus, ClinicalEventType, ConsciousnessLevel, RiskBand, FeedbackType, IntegrationType, IntegrationMode, IntegrationStatus

# --- User Schemas ---
class UserBase(BaseModel):
    username: str = Field(..., max_length=50)
    email: EmailStr
    role: UserRole

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserResponse(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class LoginPayload(BaseModel):
    email: EmailStr
    password: str

# --- Patient Schemas ---
class PatientBase(BaseModel):
    name: str = Field(..., max_length=100)
    age: int = Field(..., ge=0, le=120)
    gender: str = Field(..., max_length=20)
    admission_reason: str = Field(..., max_length=255)
    status: PatientStatus

class PatientCreate(PatientBase):
    criticality_score: float = Field(0.0, ge=0.0, le=10.0)

class PatientResponse(PatientBase):
    id: int
    criticality_score: float
    current_bed_id: Optional[int] = None
    admitted_at: datetime
    discharged_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Bed Schemas ---
class BedBase(BaseModel):
    bed_number: str = Field(..., max_length=20)
    status: BedStatus

class BedCreate(BedBase):
    ward_id: int

class BedResponse(BedBase):
    id: int
    ward_id: int
    patient_id: Optional[int] = None
    patient: Optional[PatientResponse] = None

    class Config:
        from_attributes = True

# --- Ward Schemas ---
class WardBase(BaseModel):
    name: str = Field(..., max_length=100)
    type: WardType
    capacity: int = Field(..., gt=0)

class WardCreate(WardBase):
    pass

class WardResponse(WardBase):
    id: int
    beds: List[BedResponse] = []
    occupied_beds_count: int = 0
    utilization_rate: float = 0.0

    class Config:
        from_attributes = True

# --- Recommendation Schemas ---
class RecommendationBase(BaseModel):
    patient_id: int
    source_bed_id: Optional[int] = None
    target_bed_id: Optional[int] = None
    partner_hospital_id: Optional[int] = None
    status: RecommendationStatus
    recommendation_type: Optional[RecommendationType] = None
    chained_patient_id: Optional[int] = None
    chained_target_bed_id: Optional[int] = None
    criticality_score: float
    reasoning: str

class RecommendationResponse(RecommendationBase):
    id: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_shadow: bool
    approved_at: Optional[datetime] = None
    approved_by_user_id: Optional[int] = None
    actioned_by_user_id: Optional[int] = None
    override_reason: Optional[str] = None

    class Config:
        from_attributes = True

# --- Admission Payload ---
class PatientAdmitPayload(BaseModel):
    name: str = Field(..., max_length=100)
    age: int = Field(..., ge=0, le=120)
    gender: str = Field(..., max_length=20)
    admission_reason: str = Field(..., max_length=255)
    status: PatientStatus
    target_ward_id: int
    heart_rate: Optional[int] = Field(None, ge=0, le=300)
    resp_rate: Optional[int] = Field(None, ge=0, le=100)
    spo2: Optional[int] = Field(None, ge=0, le=100)

class RecommendationActionPayload(BaseModel):
    action: str = Field(..., pattern="^(APPROVE|REJECT)$")
    user_id: Optional[int] = None

class RecommendationRejectPayload(BaseModel):
    reason: str = Field(..., min_length=10, max_length=500)
    user_id: Optional[int] = None

class BedSimpleResponse(BaseModel):
    id: int
    ward_id: int
    bed_number: str
    status: BedStatus
    patient_id: Optional[int] = None

    class Config:
        from_attributes = True

class PartnerHospitalResponse(BaseModel):
    id: int
    name: str
    location: str
    distance_km: float
    icu_beds_available: int
    general_beds_available: int

    class Config:
        from_attributes = True


class TransferRequestResponse(BaseModel):
    id: int
    patient_id: int
    partner_hospital_id: int
    reason: str
    status: TransferRequestStatus
    created_at: datetime

    class Config:
        from_attributes = True


class RecommendationDetailResponse(RecommendationResponse):
    patient: Optional[PatientResponse] = None
    target_bed: Optional[BedSimpleResponse] = None
    source_bed: Optional[BedSimpleResponse] = None
    partner_hospital: Optional[PartnerHospitalResponse] = None
    chained_patient: Optional[PatientResponse] = None
    chained_target_bed: Optional[BedSimpleResponse] = None


class VitalsPayload(BaseModel):
    heart_rate: int = Field(..., ge=0, le=300)
    resp_rate: int = Field(..., ge=0, le=100)
    spo2: int = Field(..., ge=0, le=100)
    temperature: Optional[float] = Field(None, ge=20.0, le=45.0)
    systolic_bp: Optional[int] = Field(None, ge=0, le=300)
    consciousness_level: ConsciousnessLevel = Field(default=ConsciousnessLevel.ALERT)
    oxygen_supplement: bool = Field(default=False)
    spo2_scale: int = Field(default=1, ge=1, le=2)


class ScoringPolicyResponse(BaseModel):
    id: int
    name: str
    version: str
    config_json: dict
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ScoreExplanationResponse(BaseModel):
    id: int
    score_record_id: int
    parameter_breakdown: dict
    red_flags: list

    class Config:
        from_attributes = True


class ScoreRecordResponse(BaseModel):
    id: int
    patient_id: int
    policy_id: int
    clinical_score: int
    risk_band: RiskBand
    operational_priority: float
    created_at: datetime
    explanation: Optional[ScoreExplanationResponse] = None

    class Config:
        from_attributes = True


class PatientVitalsResponse(BaseModel):
    id: int
    patient_id: int
    heart_rate: int
    resp_rate: int
    spo2: int
    temperature: Optional[float] = None
    systolic_bp: Optional[int] = None
    consciousness_level: ConsciousnessLevel
    oxygen_supplement: bool
    spo2_scale: int
    recorded_at: datetime

    class Config:
        from_attributes = True


class AlertAcknowledgePayload(BaseModel):
    user_id: Optional[int] = None


class AlertResolvePayload(BaseModel):
    resolution_note: str = Field(..., min_length=5, max_length=1000)
    user_id: Optional[int] = None


class AlertResponse(BaseModel):
    id: int
    patient_id: Optional[int] = None
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    status: AlertStatus
    assigned_to_user_id: Optional[int] = None
    assigned_to_role: Optional[str] = None
    acknowledged_by: Optional[int] = None
    acknowledged_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
    sla_due_at: Optional[datetime] = None
    is_acknowledged: bool
    created_at: datetime
    patient: Optional[PatientResponse] = None

    class Config:
        from_attributes = True

class NotificationResponse(BaseModel):
    id: int
    recipient_user_id: Optional[int] = None
    recipient_role: Optional[str] = None
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ClinicalTaskResponse(BaseModel):
    id: int
    patient_id: Optional[int] = None
    alert_id: Optional[int] = None
    task_type: str
    status: TaskStatus
    assigned_to_role: Optional[str] = None
    assigned_to_user_id: Optional[int] = None
    due_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    completion_note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BedStatusUpdatePayload(BaseModel):
    status: BedStatus


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    before_data: Optional[str] = None
    after_data: Optional[str] = None
    correlation_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ClinicalEventResponse(BaseModel):
    id: int
    patient_id: int
    event_type: ClinicalEventType
    description: str
    event_metadata: Optional[dict] = None
    timestamp: datetime
    actor_id: Optional[int] = None

    class Config:
        from_attributes = True

# --- Feedback Schemas ---
class DoctorFeedbackCreate(BaseModel):
    score_record_id: Optional[int] = None
    recommendation_id: Optional[int] = None
    feedback_type: FeedbackType
    comment: Optional[str] = Field(None, max_length=500)

class DoctorFeedbackResponse(BaseModel):
    id: int
    patient_id: int
    score_record_id: Optional[int] = None
    recommendation_id: Optional[int] = None
    feedback_type: FeedbackType
    comment: Optional[str] = None
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Baseline Schemas ---
class PatientBaselineCreate(BaseModel):
    baseline_spo2: Optional[int] = Field(None, ge=0, le=100)
    baseline_heart_rate: Optional[int] = Field(None, ge=0, le=300)
    baseline_systolic_bp: Optional[int] = Field(None, ge=0, le=300)
    baseline_respiratory_rate: Optional[int] = Field(None, ge=0, le=100)
    notes: Optional[str] = Field(None, max_length=500)

class PatientBaselineResponse(BaseModel):
    id: int
    patient_id: int
    baseline_spo2: Optional[int] = None
    baseline_heart_rate: Optional[int] = None
    baseline_systolic_bp: Optional[int] = None
    baseline_respiratory_rate: Optional[int] = None
    notes: Optional[str] = None
    approved_by: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Integration Schemas ---
class IntegrationBase(BaseModel):
    name: str = Field(..., max_length=200)
    type: IntegrationType
    mode: IntegrationMode
    status: IntegrationStatus
    config_json: Optional[dict] = None

class IntegrationCreate(IntegrationBase):
    pass

class IntegrationUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    type: Optional[IntegrationType] = None
    mode: Optional[IntegrationMode] = None
    status: Optional[IntegrationStatus] = None
    config_json: Optional[dict] = None

class IntegrationResponse(IntegrationBase):
    id: int
    hospital_id: int
    last_sync_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
