export type UserRole = "ADMIN" | "DOCTOR" | "NURSE" | "COORDINATOR";
export type PatientStatus = "STABLE" | "SERIOUS" | "CRITICAL";
export type WardType = "ICU" | "GENERAL" | "EMERGENCY";
export type BedStatus = "AVAILABLE" | "OCCUPIED" | "CLEANING" | "RESERVED" | "MAINTENANCE";
export type RecommendationStatus = "PENDING" | "APPROVED" | "REJECTED";

export interface Patient {
  id: number;
  name: string;
  age: number;
  gender: string;
  admission_reason: string;
  status: PatientStatus;
  criticality_score: number;
  current_bed_id: number | null;
  admitted_at: string;
  discharged_at: string | null;
}

export interface Bed {
  id: number;
  ward_id: number;
  bed_number: string;
  status: BedStatus;
  patient_id: number | null;
  patient?: Patient | null;
}

export interface Ward {
  id: number;
  name: string;
  type: WardType;
  capacity: number;
  beds?: Bed[];
  occupied_beds_count: number;
  utilization_rate: number;
  current_nurses?: number;
  max_patient_ratio?: number;
}

export interface Recommendation {
  id: number;
  patient_id: number;
  source_bed_id: number | null;
  target_bed_id: number | null;
  partner_hospital_id: number | null;
  status: RecommendationStatus;
  criticality_score: number;
  reasoning: string;
  created_at: string;
  expires_at: string | null;
  approved_at: string | null;
  approved_by_user_id: number | null;
  actioned_by_user_id?: number | null;
  override_reason?: string | null;
  recommendation_type?: string | null;
  chained_patient_id?: number | null;
  chained_target_bed_id?: number | null;
  is_shadow?: boolean;
}

export interface PatientAdmitPayload {
  name: string;
  age: number;
  gender: string;
  admission_reason: string;
  status: PatientStatus;
  target_ward_id: number;
}

export interface BedSimple {
  id: number;
  ward_id: number;
  bed_number: string;
  status: BedStatus;
  patient_id: number | null;
}

export interface RecommendationDetail extends Recommendation {
  patient?: Patient | null;
  target_bed?: BedSimple | null;
  source_bed?: BedSimple | null;
  partner_hospital?: PartnerHospital | null;
  chained_patient?: Patient | null;
  chained_target_bed?: BedSimple | null;
}

export interface PartnerHospital {
  id: number;
  name: string;
  location: string;
  distance_km: number;
  icu_beds_available: number;
  general_beds_available: number;
}

export type AlertStatus = "CREATED" | "ASSIGNED" | "ACKNOWLEDGED" | "IN_PROGRESS" | "RESOLVED" | "ESCALATED" | "EXPIRED" | "DISMISSED" | "FALSE_ALARM";

export interface Alert {
  id: number;
  patient_id: number | null;
  alert_type: "SCORE_SPIKE" | "LOW_OXYGEN" | "ICU_AT_CAPACITY";
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  message: string;
  status: AlertStatus;
  assigned_to_user_id?: number | null;
  assigned_to_role?: string | null;
  acknowledged_by?: number | null;
  acknowledged_at?: string | null;
  resolved_by?: number | null;
  resolved_at?: string | null;
  resolution_note?: string | null;
  sla_due_at?: string | null;
  created_at: string;
  patient?: Patient | null;
}

export type AlertResponse = Alert;

export type AlertAcknowledgePayload = Record<string, never>;

export interface AlertResolvePayload {
  resolution_note: string;
}

export interface NotificationResponse {
  id: number;
  recipient_user_id?: number | null;
  recipient_role?: string | null;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface ClinicalEvent {
  id: number;
  patient_id: number;
  event_type: "ADMISSION" | "VITALS_RECORDED" | "ALERT_TRIGGERED" | "RECOMMENDATION_GENERATED" | "SHADOW_RECOMMENDATION_GENERATED" | "RECOMMENDATION_APPROVED" | "RECOMMENDATION_REJECTED" | "TRANSFER_COMPLETED";
  description: string;
  event_metadata?: Record<string, unknown> | null;
  timestamp: string;
  actor_id?: number | null;
}

let rawBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
if (rawBaseUrl.endsWith("/")) {
  rawBaseUrl = rawBaseUrl.slice(0, -1);
}
export const API_BASE_URL = rawBaseUrl;

async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  options.credentials = "include";

  if (typeof window !== "undefined") {
    const token = localStorage.getItem("auth_token");
    if (token) {
      const headers = (options.headers || {}) as Record<string, string>;
      headers["Authorization"] = `Bearer ${token}`;
      options.headers = headers;
    }
  }

  const method = (options.method || "GET").toUpperCase();
  const isRetryable = method === "GET";

  if (!isRetryable) {
    return fetch(url, options);
  }

  const maxRetries = 3;
  let delay = 1000; // start with 1 second

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const res = await fetch(url, options);
      // Retry on any 5xx server error, but return immediately for 2xx, 3xx, 4xx
      if (res.status < 500) {
        return res;
      }
      if (attempt < maxRetries) {
        console.warn(`Transient API error (status ${res.status}) on ${url}. Retrying attempt ${attempt + 1}/${maxRetries} in ${delay}ms...`);
      } else {
        return res;
      }
    } catch (err) {
      if (attempt === maxRetries) {
        throw err;
      }
      console.warn(`Transient API connection error on ${url}:`, err, `. Retrying attempt ${attempt + 1}/${maxRetries} in ${delay}ms...`);
    }

    await new Promise((resolve) => setTimeout(resolve, delay));
    delay *= 2; // exponential backoff
  }

  throw new Error("API fetch retry loop ended unexpectedly without returning or throwing.");
}

export interface User {
  id: number;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  token?: string;
}

export async function login(email: string, password: string): Promise<User> {
  const res = await authFetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Incorrect email or password.");
  }
  return res.json();
}

export async function logout(): Promise<{ message: string }> {
  const res = await authFetch(`${API_BASE_URL}/api/auth/logout`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to log out");
  return res.json();
}

export async function fetchCurrentUser(): Promise<User> {
  const res = await authFetch(`${API_BASE_URL}/api/auth/me`, { cache: 'no-store' });
  if (!res.ok) throw new Error("Not authenticated");
  return res.json();
}

export async function fetchWards(): Promise<Ward[]> {
  const res = await authFetch(`${API_BASE_URL}/api/wards`, { cache: 'no-store' });
  if (!res.ok) throw new Error("Failed to fetch wards");
  return res.json();
}

export async function fetchBeds(wardId?: number): Promise<Bed[]> {
  const url = wardId 
    ? `${API_BASE_URL}/api/beds?ward_id=${wardId}`
    : `${API_BASE_URL}/api/beds`;
  const res = await authFetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error("Failed to fetch beds");
  return res.json();
}

export interface VitalsPayload {
  heart_rate: number;
  resp_rate: number;
  spo2: number;
  temperature?: number;
  systolic_bp?: number;
  consciousness_level: "ALERT" | "CVPU";
  oxygen_supplement: boolean;
  spo2_scale: number;
}

export interface ScoreExplanation {
  id: number;
  score_record_id: number;
  parameter_breakdown: Record<string, unknown>;
  red_flags: string[];
}

export interface ScoreRecord {
  id: number;
  patient_id: number;
  policy_id: number;
  clinical_score: number;
  risk_band: "LOW" | "MEDIUM" | "HIGH";
  operational_priority: number;
  created_at: string;
  explanation?: ScoreExplanation | null;
}

export interface PatientVitals {
  id: number;
  patient_id: number;
  heart_rate: number;
  resp_rate: number;
  spo2: number;
  temperature?: number | null;
  systolic_bp?: number | null;
  consciousness_level: "ALERT" | "CVPU";
  oxygen_supplement: boolean;
  spo2_scale: number;
  recorded_at: string;
}

export async function fetchPatients(): Promise<Patient[]> {
  const res = await authFetch(`${API_BASE_URL}/api/patients`, { cache: 'no-store' });
  if (!res.ok) throw new Error("Failed to fetch patients");
  return res.json();
}

export async function fetchPatient(id: number): Promise<Patient & { score_record?: ScoreRecord }> {
  const res = await authFetch(`${API_BASE_URL}/api/patients/${id}`, { cache: 'no-store' });
  if (!res.ok) throw new Error("Failed to fetch patient");
  return res.json();
}

export async function admitPatient(payload: PatientAdmitPayload, idempotencyKey?: string): Promise<Patient> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (idempotencyKey) {
    headers["X-Idempotency-Key"] = idempotencyKey;
  }
  const res = await authFetch(`${API_BASE_URL}/api/patients/admit`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Failed to admit patient");
  }
  return res.json();
}

export async function fetchPendingRecommendations(): Promise<RecommendationDetail[]> {
  const res = await authFetch(`${API_BASE_URL}/api/recommendations/pending`, { cache: 'no-store' });
  if (!res.ok) throw new Error("Failed to fetch pending recommendations");
  return res.json();
}

export async function actionRecommendation(
  id: number,
  action: "APPROVE" | "REJECT",
  userId: number
): Promise<RecommendationDetail> {
  const res = await authFetch(`${API_BASE_URL}/api/recommendations/${id}/action`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ action, user_id: userId }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Failed to ${action.toLowerCase()} recommendation`);
  }
  return res.json();
}

export async function rejectRecommendation(
  id: number,
  reason: string,
  userId: number
): Promise<RecommendationDetail> {
  const res = await authFetch(`${API_BASE_URL}/api/recommendations/${id}/reject`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ reason, user_id: userId }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Failed to reject recommendation`);
  }
  return res.json();
}



export async function logPatientVitals(
  id: number,
  payload: VitalsPayload,
  idempotencyKey?: string
): Promise<Patient> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (idempotencyKey) {
    headers["X-Idempotency-Key"] = idempotencyKey;
  }
  const res = await authFetch(`${API_BASE_URL}/api/patients/${id}/vitals`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Failed to log patient vitals");
  }
  return res.json();
}

export async function fetchPartnerHospitals(): Promise<PartnerHospital[]> {
  const res = await authFetch(`${API_BASE_URL}/api/partner-hospitals`, { cache: 'no-store' });
  if (!res.ok) throw new Error("Failed to fetch partner hospitals");
  return res.json();
}

export async function updateBedStatus(id: number, status: BedStatus): Promise<Bed> {
  const res = await authFetch(`${API_BASE_URL}/api/beds/${id}/status`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ status }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Failed to update bed status");
  }
  return res.json();
}

export interface AuditLog {
  id: number;
  user_id?: string;
  action: string;
  entity_type: string;
  entity_id?: number;
  before_data?: string;
  after_data?: string;
  correlation_id?: string;
  created_at: string;
}

export interface HealthMetrics {
  db_pool_size: number;
  db_checked_out: number;
  db_overflow: number;
  active_websocket_clients: number;
  recent_transaction_retries: number;
}

export async function fetchAuditLogs(filters?: {
  user_id?: string;
  action?: string;
  entity_type?: string;
  correlation_id?: string;
}): Promise<AuditLog[]> {
  const params = new URLSearchParams();
  if (filters) {
    if (filters.user_id) params.append("user_id", filters.user_id);
    if (filters.action) params.append("action", filters.action);
    if (filters.entity_type) params.append("entity_type", filters.entity_type);
    if (filters.correlation_id) params.append("correlation_id", filters.correlation_id);
  }
  const query = params.toString() ? `?${params.toString()}` : "";
  const res = await authFetch(`${API_BASE_URL}/api/audit-logs${query}`, { cache: "no-store" });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Failed to fetch audit logs");
  }
  return res.json();
}

export async function fetchHealthMetrics(): Promise<HealthMetrics> {
  const res = await authFetch(`${API_BASE_URL}/api/health/metrics`, { cache: "no-store" });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Failed to fetch health metrics");
  }
  return res.json();
}

export async function triggerScenario(scenario: string): Promise<unknown> {
  const res = await authFetch(`${API_BASE_URL}/api/scenarios/trigger`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ scenario }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Failed to trigger scenario");
  }
  return res.json();
}

export async function getPatientTimeline(patientId: number): Promise<ClinicalEvent[]> {
  const res = await authFetch(`${API_BASE_URL}/api/patients/${patientId}/timeline`, { cache: 'no-store' });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Failed to fetch patient timeline");
  }
  return res.json();
}

export type FeedbackType = "USEFUL" | "TOO_SENSITIVE" | "TOO_LATE" | "INCORRECT_BASELINE" | "ALREADY_REVIEWED" | "NEEDS_ESCALATION";

export interface DoctorFeedbackCreate {
  score_record_id?: number | null;
  recommendation_id?: number | null;
  feedback_type: FeedbackType;
  comment?: string | null;
}

export interface PatientBaselineCreate {
  baseline_spo2?: number | null;
  baseline_heart_rate?: number | null;
  baseline_systolic_bp?: number | null;
  baseline_respiratory_rate?: number | null;
  notes?: string | null;
}

export interface PatientBaselineResponse extends PatientBaselineCreate {
  id: number;
  patient_id: number;
  approved_by: number;
  last_updated: string;
}

export async function submitDoctorFeedback(patientId: number, payload: DoctorFeedbackCreate): Promise<unknown> {
  const res = await authFetch(`${API_BASE_URL}/api/patients/${patientId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Failed to submit clinical feedback");
  }
  return res.json();
}

export async function upsertPatientBaseline(patientId: number, payload: PatientBaselineCreate): Promise<PatientBaselineResponse> {
  const res = await authFetch(`${API_BASE_URL}/api/patients/${patientId}/baselines`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Failed to upsert patient baseline");
  }
  return res.json();
}

export async function fetchPatientBaseline(patientId: number): Promise<PatientBaselineResponse | null> {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/patients/${patientId}/baselines`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function fetchActiveAlerts(): Promise<AlertResponse[]> {
  const res = await authFetch(`${API_BASE_URL}/api/alerts`, { cache: 'no-store' });
  if (!res.ok) throw new Error("Failed to fetch alerts");
  return res.json();
}

export async function acknowledgeAlert(id: number): Promise<AlertResponse> {
  const res = await authFetch(`${API_BASE_URL}/api/alerts/${id}/acknowledge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error("Failed to acknowledge alert");
  return res.json();
}

export async function resolveAlert(id: number, payload: AlertResolvePayload): Promise<AlertResponse> {
  const res = await authFetch(`${API_BASE_URL}/api/alerts/${id}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to resolve alert");
  return res.json();
}

export async function fetchUnreadNotifications(): Promise<NotificationResponse[]> {
  const res = await authFetch(`${API_BASE_URL}/api/notifications`, { cache: 'no-store' });
  if (!res.ok) {
    if (res.status === 404) return [];
    throw new Error("Failed to fetch notifications");
  }
  return res.json();
}

export interface CsvPreviewResponse {
  total_rows: number;
  valid_count: number;
  invalid_count: number;
  rows: Array<{
    row_number: number;
    raw_data: Record<string, string>;
    is_valid: boolean;
    errors: string[];
    normalized_data: Record<string, unknown>;
  }>;
  error?: string;
}

export async function previewCsvImport(file: File, entityType: string): Promise<CsvPreviewResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("entity_type", entityType);

  const res = await authFetch(`${API_BASE_URL}/api/integrations/csv-import/preview`, {
    method: "POST",
    body: formData,
    // Do NOT set Content-Type header. Let the browser set it to multipart/form-data with the correct boundary
  });
  
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Failed to preview CSV");
  }
  
  return res.json();
}

export interface CsvCommitResponse {
  import_batch_id: number;
  integration_log_id: number;
  total_rows: number;
  valid_count: number;
  invalid_count: number;
}

export async function commitCsvImport(file: File, entityType: string, integrationId: number = 1): Promise<CsvCommitResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("entity_type", entityType);

  const res = await authFetch(`${API_BASE_URL}/api/integrations/csv-import/commit`, {
    method: "POST",
    body: formData,
  });
  
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Failed to commit CSV");
  }
  
  return res.json();
}

export interface DataQualityMetrics {
  data_quality_score: number;
  missing_vitals: number;
  failed_imports: number;
  active_issues: number;
}

export async function getDataQualityMetrics(): Promise<DataQualityMetrics> {
  const res = await authFetch(`${API_BASE_URL}/api/integrations/data-quality`);
  if (!res.ok) throw new Error("Failed to fetch data quality metrics");
  return res.json();
}

export interface ReconciliationIssue {
  id: number;
  entity_type: string;
  entity_id: string;
  source_system: string;
  field_name: string;
  external_value: string;
  internal_value: string;
  severity: string;
  status: string;
  created_at: string;
}

export async function getReconciliationIssues(): Promise<ReconciliationIssue[]> {
  const res = await authFetch(`${API_BASE_URL}/api/integrations/reconciliation-issues`);
  if (!res.ok) throw new Error("Failed to fetch reconciliation issues");
  return res.json();
}

export async function resolveReconciliationIssue(id: number, action: string, note: string): Promise<any> {
  const res = await authFetch(`${API_BASE_URL}/api/integrations/reconciliation-issues/${id}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, note })
  });
  if (!res.ok) throw new Error("Failed to resolve issue");
  return res.json();
}

export interface ApiKey {
  id: number;
  name: string;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
}

export async function getApiKeys(): Promise<ApiKey[]> {
  const res = await authFetch(`${API_BASE_URL}/api/integrations/api-keys`);
  if (!res.ok) throw new Error("Failed to fetch API keys");
  return res.json();
}

export async function createApiKey(name: string, scopes: string[]): Promise<{ raw_key: string, prefix: string }> {
  const res = await authFetch(`${API_BASE_URL}/api/integrations/api-keys`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, scopes })
  });
  if (!res.ok) throw new Error("Failed to create API key");
  return res.json();
}

export async function revokeApiKey(id: number): Promise<void> {
  const res = await authFetch(`${API_BASE_URL}/api/integrations/api-keys/${id}/revoke`, {
    method: "POST"
  });
  if (!res.ok) throw new Error("Failed to revoke API key");
}
