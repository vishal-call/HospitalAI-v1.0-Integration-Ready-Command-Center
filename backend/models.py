import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Enum as SqlEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from database import Base

# Enums for Database Integrity
class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    DOCTOR = "DOCTOR"
    NURSE = "NURSE"
    COORDINATOR = "COORDINATOR"

class PatientStatus(str, enum.Enum):
    STABLE = "STABLE"
    SERIOUS = "SERIOUS"
    CRITICAL = "CRITICAL"

class WardType(str, enum.Enum):
    ICU = "ICU"
    GENERAL = "GENERAL"
    EMERGENCY = "EMERGENCY"

class BedStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    CLEANING = "CLEANING"
    RESERVED = "RESERVED"
    MAINTENANCE = "MAINTENANCE"

class RecommendationStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

class RecommendationType(str, enum.Enum):
    LOCAL_ICU_TRANSFER = "LOCAL_ICU_TRANSFER"
    INTER_HOSPITAL_TRANSFER = "INTER_HOSPITAL_TRANSFER"
    CHAINED_TRANSFER = "CHAINED_TRANSFER"

class TransferRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class AlertType(str, enum.Enum):
    SCORE_SPIKE = "SCORE_SPIKE"
    LOW_OXYGEN = "LOW_OXYGEN"
    ICU_AT_CAPACITY = "ICU_AT_CAPACITY"

class AlertSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AlertStatus(str, enum.Enum):
    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    EXPIRED = "EXPIRED"
    DISMISSED = "DISMISSED"
    FALSE_ALARM = "FALSE_ALARM"

class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    OVERDUE = "OVERDUE"


class ClinicalEventType(str, enum.Enum):
    ADMISSION = "ADMISSION"
    VITALS_RECORDED = "VITALS_RECORDED"
    ALERT_TRIGGERED = "ALERT_TRIGGERED"
    RECOMMENDATION_GENERATED = "RECOMMENDATION_GENERATED"
    SHADOW_RECOMMENDATION_GENERATED = "SHADOW_RECOMMENDATION_GENERATED"
    RECOMMENDATION_APPROVED = "RECOMMENDATION_APPROVED"
    RECOMMENDATION_REJECTED = "RECOMMENDATION_REJECTED"
    TRANSFER_COMPLETED = "TRANSFER_COMPLETED"


class FeedbackType(str, enum.Enum):
    USEFUL = "USEFUL"
    TOO_SENSITIVE = "TOO_SENSITIVE"
    TOO_LATE = "TOO_LATE"
    INCORRECT_BASELINE = "INCORRECT_BASELINE"
    ALREADY_REVIEWED = "ALREADY_REVIEWED"
    NEEDS_ESCALATION = "NEEDS_ESCALATION"


class ConsciousnessLevel(str, enum.Enum):
    ALERT = "ALERT"
    CVPU = "CVPU" # Confusion, Voice, Pain, Unresponsive

class IntegrationType(str, enum.Enum):
    MANUAL = "MANUAL"
    CSV = "CSV"
    API = "API"

class IntegrationMode(str, enum.Enum):
    MANUAL = "MANUAL"
    CSV_IMPORT = "CSV_IMPORT"
    API_READ_ONLY = "API_READ_ONLY"

class IntegrationStatus(str, enum.Enum):
    CONNECTED = "CONNECTED"
    DISABLED = "DISABLED"
    MANUAL = "MANUAL"
    CSV_READY = "CSV_READY"
    SYNCING = "SYNCING"
    FAILED = "FAILED"
    READ_ONLY = "READ_ONLY"

class LogDirection(str, enum.Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"

class LogStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"

class IssueSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class IssueStatus(str, enum.Enum):
    OPEN = "OPEN"
    REVIEWED = "REVIEWED"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"


class RiskBand(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole), nullable=False, default=UserRole.COORDINATOR)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    approved_recommendations: Mapped[List["Recommendation"]] = relationship(
        "Recommendation", back_populates="approved_by", foreign_keys="Recommendation.approved_by_user_id"
    )

    def __repr__(self) -> str:
        return f"<User {self.username} (Role: {self.role})>"


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    admission_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[PatientStatus] = mapped_column(SqlEnum(PatientStatus), nullable=False, default=PatientStatus.STABLE)
    criticality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    admitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    discharged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Track current occupied bed to satisfy user mandate. Circular constraint resolved via use_alter.
    current_bed_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey("beds.id", ondelete="SET NULL", use_alter=True, name="fk_patient_current_bed"), 
        nullable=True
    )

    # Relationships
    current_bed: Mapped[Optional["Bed"]] = relationship(
        "Bed", foreign_keys=[current_bed_id], post_update=True
    )
    recommendations: Mapped[List["Recommendation"]] = relationship(
        "Recommendation", back_populates="patient", foreign_keys="Recommendation.patient_id"
    )

    def __repr__(self) -> str:
        return f"<Patient {self.name} (Status: {self.status}, Score: {self.criticality_score:.2f})>"


class Ward(Base):
    __tablename__ = "wards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    type: Mapped[WardType] = mapped_column(SqlEnum(WardType), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    beds: Mapped[List["Bed"]] = relationship("Bed", back_populates="ward", cascade="all, delete-orphan", foreign_keys="Bed.ward_id")

    def __repr__(self) -> str:
        return f"<Ward {self.name} (Type: {self.type}, Capacity: {self.capacity})>"


class Bed(Base):
    __tablename__ = "beds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ward_id: Mapped[int] = mapped_column(Integer, ForeignKey("wards.id", ondelete="CASCADE"), nullable=False)
    bed_number: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[BedStatus] = mapped_column(SqlEnum(BedStatus), nullable=False, default=BedStatus.AVAILABLE)
    
    # Store patient occupying the bed
    patient_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="SET NULL", use_alter=True, name="fk_bed_patient"), nullable=True
    )

    # Relationships
    ward: Mapped["Ward"] = relationship("Ward", back_populates="beds", foreign_keys=[ward_id])
    patient: Mapped[Optional["Patient"]] = relationship("Patient", foreign_keys=[patient_id], post_update=True)

    def __repr__(self) -> str:
        return f"<Bed {self.bed_number} (Ward ID: {self.ward_id}, Status: {self.status})>"


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    source_bed_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("beds.id", ondelete="SET NULL"), nullable=True)
    target_bed_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("beds.id", ondelete="CASCADE"), nullable=True)
    partner_hospital_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("partner_hospitals.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[RecommendationStatus] = mapped_column(
        SqlEnum(RecommendationStatus), nullable=False, default=RecommendationStatus.PENDING
    )
    recommendation_type: Mapped[RecommendationType] = mapped_column(
        SqlEnum(RecommendationType), nullable=False, default=RecommendationType.LOCAL_ICU_TRANSFER
    )
    chained_patient_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="SET NULL"), nullable=True
    )
    chained_target_bed_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("beds.id", ondelete="SET NULL"), nullable=True
    )
    criticality_score: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_shadow: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actioned_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    override_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="recommendations", foreign_keys=[patient_id])
    approved_by: Mapped[Optional["User"]] = relationship("User", back_populates="approved_recommendations", foreign_keys=[approved_by_user_id])
    actioned_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[actioned_by_user_id])
    partner_hospital: Mapped[Optional["PartnerHospital"]] = relationship("PartnerHospital", foreign_keys=[partner_hospital_id])
    chained_patient: Mapped[Optional["Patient"]] = relationship("Patient", foreign_keys=[chained_patient_id])
    chained_target_bed: Mapped[Optional["Bed"]] = relationship("Bed", foreign_keys=[chained_target_bed_id])

    def __repr__(self) -> str:
        return f"<Recommendation Patient ID: {self.patient_id} -> Target Bed: {self.target_bed_id} / Partner: {self.partner_hospital_id} (Status: {self.status})>"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=True)
    alert_type: Mapped[AlertType] = mapped_column(SqlEnum(AlertType), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(SqlEnum(AlertSeverity), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(SqlEnum(AlertStatus), nullable=False, default=AlertStatus.CREATED)
    
    assigned_to_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_to_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    acknowledged_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    resolved_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolution_note: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    sla_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False) # Legacy flag, keep for now but prefer status
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    patient: Mapped[Optional["Patient"]] = relationship("Patient", foreign_keys=[patient_id])
    assigned_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_user_id])
    acknowledged_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[acknowledged_by])
    resolved_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[resolved_by])

    def __repr__(self) -> str:
        return f"<Alert ID: {self.id}, Patient ID: {self.patient_id}, Type: {self.alert_type}, Status: {self.status}>"


class PartnerHospital(Base):
    __tablename__ = "partner_hospitals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(150), nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    icu_beds_available: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    general_beds_available: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<PartnerHospital Name: {self.name}, Distance: {self.distance_km} km>"


class TransferRequest(Base):
    __tablename__ = "transfer_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    partner_hospital_id: Mapped[int] = mapped_column(Integer, ForeignKey("partner_hospitals.id", ondelete="CASCADE"), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[TransferRequestStatus] = mapped_column(
        SqlEnum(TransferRequestStatus), nullable=False, default=TransferRequestStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", foreign_keys=[patient_id])
    partner_hospital: Mapped["PartnerHospital"] = relationship("PartnerHospital", foreign_keys=[partner_hospital_id])

    def __repr__(self) -> str:
        return f"<TransferRequest Patient ID: {self.patient_id} -> Partner: {self.partner_hospital_id} ({self.status})>"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    before_data: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    after_data: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<AuditLog User: {self.user_id}, Action: {self.action}, Entity: {self.entity_type}/{self.entity_id}>"


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    request_body_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_body: Mapped[dict] = mapped_column(JSON, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        return f"<IdempotencyKey ID: {self.id}, Endpoint: {self.endpoint}, Expires: {self.expires_at}>"


class ClinicalEvent(Base):
    __tablename__ = "clinical_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[ClinicalEventType] = mapped_column(SqlEnum(ClinicalEventType), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    event_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    actor_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", foreign_keys=[patient_id])
    actor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[actor_id])

    def __repr__(self) -> str:
        return f"<ClinicalEvent ID: {self.id}, Type: {self.event_type}, Patient: {self.patient_id}>"


class PatientVitals(Base):
    __tablename__ = "patient_vitals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    heart_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    resp_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    spo2: Mapped[int] = mapped_column(Integer, nullable=False)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    systolic_bp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    consciousness_level: Mapped[ConsciousnessLevel] = mapped_column(SqlEnum(ConsciousnessLevel), nullable=False, default=ConsciousnessLevel.ALERT)
    oxygen_supplement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    spo2_scale: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    patient: Mapped["Patient"] = relationship("Patient", foreign_keys=[patient_id])


class ScoringPolicy(Base):
    __tablename__ = "scoring_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ScoreRecord(Base):
    __tablename__ = "score_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    policy_id: Mapped[int] = mapped_column(Integer, ForeignKey("scoring_policies.id", ondelete="RESTRICT"), nullable=False)
    clinical_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_band: Mapped[RiskBand] = mapped_column(SqlEnum(RiskBand), nullable=False)
    operational_priority: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    patient: Mapped["Patient"] = relationship("Patient", foreign_keys=[patient_id])
    policy: Mapped["ScoringPolicy"] = relationship("ScoringPolicy", foreign_keys=[policy_id])


class ScoreExplanation(Base):
    __tablename__ = "score_explanations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    score_record_id: Mapped[int] = mapped_column(Integer, ForeignKey("score_records.id", ondelete="CASCADE"), nullable=False)
    parameter_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False)
    red_flags: Mapped[list] = mapped_column(JSON, nullable=False)

    score_record: Mapped["ScoreRecord"] = relationship("ScoreRecord", foreign_keys=[score_record_id])


class DoctorFeedback(Base):
    __tablename__ = "doctor_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    score_record_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("score_records.id", ondelete="SET NULL"), nullable=True)
    recommendation_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("recommendations.id", ondelete="SET NULL"), nullable=True)
    feedback_type: Mapped[FeedbackType] = mapped_column(SqlEnum(FeedbackType), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    patient: Mapped["Patient"] = relationship("Patient", foreign_keys=[patient_id])
    score_record: Mapped[Optional["ScoreRecord"]] = relationship("ScoreRecord", foreign_keys=[score_record_id])
    recommendation: Mapped[Optional["Recommendation"]] = relationship("Recommendation", foreign_keys=[recommendation_id])
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])


class PatientBaseline(Base):
    __tablename__ = "patient_baselines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), unique=True, nullable=False)
    baseline_spo2: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    baseline_heart_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    baseline_systolic_bp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    baseline_respiratory_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    approved_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    patient: Mapped["Patient"] = relationship("Patient", foreign_keys=[patient_id])
    approver: Mapped["User"] = relationship("User", foreign_keys=[approved_by])


class ResponseSLAPolicy(Base):
    __tablename__ = "response_sla_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hospital_id: Mapped[Optional[int]] = mapped_column(Integer, default=1, nullable=True)
    risk_band: Mapped[str] = mapped_column(String(50), nullable=False)
    acknowledge_within_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    resolve_within_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    escalate_to_role: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<ResponseSLAPolicy Risk: {self.risk_band}, Active: {self.is_active}>"


class ClinicalTask(Base):
    __tablename__ = "clinical_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=True)
    alert_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=True)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(SqlEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    assigned_to_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    assigned_to_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completion_note: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    patient: Mapped[Optional["Patient"]] = relationship("Patient", foreign_keys=[patient_id])
    alert: Mapped[Optional["Alert"]] = relationship("Alert", foreign_keys=[alert_id])
    assigned_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_user_id])


class AlertEscalation(Base):
    __tablename__ = "alert_escalations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False)
    from_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    alert: Mapped["Alert"] = relationship("Alert", foreign_keys=[alert_id])


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipient_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    recipient_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    recipient_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[recipient_user_id])


# --- INTEGRATION PHASE 1 MODELS ---

class Integration(Base):
    __tablename__ = "integrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hospital_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[IntegrationType] = mapped_column(SqlEnum(IntegrationType, name="integration_type_enum"), nullable=False)
    mode: Mapped[IntegrationMode] = mapped_column(SqlEnum(IntegrationMode, name="integration_mode_enum"), nullable=False)
    status: Mapped[IntegrationStatus] = mapped_column(SqlEnum(IntegrationStatus, name="integration_status_enum"), nullable=False)
    config_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ExternalIdMapping(Base):
    __tablename__ = "external_id_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hospital_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    integration_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("integrations.id"), nullable=True)
    external_patient_code: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    internal_patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class IntegrationLog(Base):
    __tablename__ = "integration_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hospital_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    integration_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("integrations.id"), nullable=True)
    integration_name: Mapped[str] = mapped_column(String(200), nullable=False)
    integration_type: Mapped[IntegrationType] = mapped_column(SqlEnum(IntegrationType, name="integration_type_enum_log"), nullable=False)
    mode: Mapped[IntegrationMode] = mapped_column(SqlEnum(IntegrationMode, name="integration_mode_enum_log"), nullable=False)
    direction: Mapped[LogDirection] = mapped_column(SqlEnum(LogDirection, name="log_direction_enum"), nullable=False)
    status: Mapped[LogStatus] = mapped_column(SqlEnum(LogStatus, name="log_status_enum"), nullable=False)
    records_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_success: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class IntegrationApiKey(Base):
    __tablename__ = "integration_api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hospital_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    integration_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("integrations.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    scopes: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hospital_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    integration_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("integrations.id"), nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[LogStatus] = mapped_column(SqlEnum(LogStatus, name="import_batch_status_enum"), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ImportError(Base):
    __tablename__ = "import_errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("import_batches.id"), nullable=True)
    row_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    field_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_row_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ReconciliationIssue(Base):
    __tablename__ = "reconciliation_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hospital_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_system: Mapped[str] = mapped_column(String(100), nullable=False)
    external_reference: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    external_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    internal_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[IssueSeverity] = mapped_column(SqlEnum(IssueSeverity, name="issue_severity_enum"), nullable=False)
    status: Mapped[IssueStatus] = mapped_column(SqlEnum(IssueStatus, name="issue_status_enum"), nullable=False)
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hospital_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    issue_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[IssueSeverity] = mapped_column(SqlEnum(IssueSeverity, name="dq_issue_severity_enum"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[IssueStatus] = mapped_column(SqlEnum(IssueStatus, name="dq_issue_status_enum"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

