# HospitalAI: Enterprise Security & Data Governance Architecture

## 1. Executive Summary
HospitalAI is architected with a "Security-First, Zero-Trust" methodology, designed to meet the rigorous compliance standards of modern healthcare networks (HIPAA, HITECH, GDPR). The platform ensures strict data isolation, immutable auditability, and encrypted telemetry pipelines.

## 2. Data Protection (In-Transit and At-Rest)
* **Data in Transit:** All client-to-server and server-to-database communication is strictly enforced over **TLS 1.3**. WebSockets (`wss://`) utilize secure handshake protocols to prevent man-in-the-middle (MITM) interception of live telemetry.
* **Data at Rest:** The PostgreSQL database utilizes transparent **AES-256 encryption** for all stored volumes and automated backups. 
* **Secret Management:** No API keys, database credentials, or cryptographic salts are stored in the codebase. All secrets are injected dynamically via secure PaaS Environment Variables.

## 3. Identity & Access Management (IAM)
* **Enterprise Single Sign-On (SSO):** HospitalAI supports OpenID Connect (OIDC) and OAuth2, allowing integration with hospital identity providers (Microsoft Entra ID, Okta, PingIdentity).
* **Strict Role-Based Access Control (RBAC):** The system enforces a rigid hierarchy of permissions at the API router level:
  * `ADMIN`: System configuration, Ward/Bed logistics, and Analytics.
  * `COORDINATOR`: Authorization of AI-recommended patient transfers.
  * `CLINICIAN (Doctor/Nurse)`: Read-only access to clinical recommendations and telemetry.
* **Token Security:** Authentication relies on short-lived, cryptographically signed JWTs (JSON Web Tokens) delivered via `HttpOnly`, `Secure`, and `SameSite=None` cookies, neutralizing XSS (Cross-Site Scripting) token theft.

## 4. Immutable Auditability & Telemetry
* **Clinical Audit Trail:** Every administrative action (staff role changes, ward capacity adjustments) and clinical mutation generates a permanent record in the database.
* **AI Explainability Ledger:** The system utilizes an `OperationalLog` architecture to track exactly when an AI recommendation was generated, what the EWS score was at that millisecond, and which specific human Coordinator approved or rejected the transfer. This guarantees full forensic reconstructability of clinical decisions.

## 5. Infrastructure Resilience
* **Stateless Compute:** The Python/FastAPI backend is entirely stateless, allowing horizontal scaling without session loss or data corruption.
* **Relational Safety:** The system utilizes pessimistic database locking (e.g., `SELECT ... FOR UPDATE`) during concurrent bed assignments to prevent race conditions (double-booking a critical ICU bed). Strict foreign-key constraints prevent the accidental deletion of occupied clinical spaces.
