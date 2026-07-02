# HospitalAI - Security & RBAC Model

This document outlines the authentication protocol, session token strategy, and Role-Based Access Control (RBAC) rules built into HospitalAI.

---

## 1. Authentication & Token Management
* **JWT Cookie Architecture**:
  - Authenticated sessions are managed via JSON Web Tokens (JWT).
  - The JWT is signed on the FastAPI backend using `HS256` and a secure environment secret key.
  - The token is transmitted to the client inside an `HttpOnly` cookie named `auth_token`.
  - **Security Properties**:
    - `HttpOnly`: Prevents client-side scripts (e.g. Cross-Site Scripting, XSS) from reading the session token.
    - `Secure`: Ensures the cookie is only transmitted over HTTPS connections (in production).
    - `SameSite=Lax`: Protects against Cross-Site Request Forgery (CSRF).

---

## 2. WebSocket Security Handshake
* **Authentication on Upgrade**:
  - Standard WebSocket protocols do not natively support custom headers.
  - During the handshake upgrade phase, FastAPI extracts the `auth_token` HttpOnly cookie directly from the connection headers.
  - The server decodes and validates the token. If the signature is invalid, expired, or missing, the connection is instantly rejected with `HTTP 403 Forbidden` / `WS 1008 Policy Violation`.

---

## 3. RBAC Permissions Matrix

The platform classifies actions into four roles: `ADMIN`, `COORDINATOR`, `DOCTOR`, and `NURSE`.

| Endpoint Path | Required Role(s) | Nurse | Doctor | Coordinator | Admin |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `POST /api/patients/admit` | Anyone (Unprotected) | ✓ | ✓ | ✓ | ✓ |
| `POST /api/patients/{id}/vitals` | Anyone (Unprotected) | ✓ | ✓ | ✓ | ✓ |
| `POST /api/alerts/{id}/acknowledge`| Anyone (Unprotected) | ✓ | ✓ | ✓ | ✓ |
| `POST /api/beds/{id}/status` | Doctor, Coordinator, Nurse | ✓ | ✓ | ✓ | ✓ |
| `POST /api/recommendations/{id}/action` | Doctor, Coordinator | ❌ | ✓ | ✓ | ❌ |
| `GET /api/audit-logs` | Admin Only | ❌ | ❌ | ❌ | ✓ |
| `GET /api/health/metrics` | Admin Only | ❌ | ❌ | ❌ | ✓ |
| `POST /api/scenarios/trigger` | Admin Only | ❌ | ❌ | ❌ | ✓ |

---

## 4. Distributed Tracing Observability
* **Correlation-ID Tracing**:
  - The backend integrates `asgi-correlation-id` middleware.
  - Incoming requests are assigned a unique, validated UUID `X-Correlation-ID` header.
  - This trace ID is bound to the logging context and written into the `AuditLog` database entry, allowing administrators to trace an entire clinical pipeline.
