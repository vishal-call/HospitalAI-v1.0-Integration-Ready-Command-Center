# HospitalAI - Human-in-the-Loop (HITL) Concurrency & State Machine

This document details the backend architectural safeguards preventing concurrency conflicts, race conditions, and transaction deadlocks during clinical transfer approvals.

---

## 1. Concurrency Controls: Pessimistic Row Locking
In high-throughput environments, multiple clinical coordinators might attempt to approve transfers or occupy beds simultaneously.
To prevent double-allocations, HospitalAI uses **pessimistic row-level locking**:
* **Mechanism**:
  - The database transaction executes a `SELECT ... FOR UPDATE` query (using SQLAlchemy `.with_for_update()`) on critical entities:
    - Bed records (`models.Bed`) during patient admission and transfer execution.
    - Recommendation records (`models.Recommendation`) before status updates.
    - Partner hospital records (`models.PartnerHospital`) during external allocations.
  - This holds a transaction-level lock on the row, forcing other concurrent update requests to block until the active transaction completes (commits or rolls back).

---

## 2. Deadlock Resolution: Tenacity Exponential Backoff
When multiple transactions acquire pessimistic locks on different tables in conflicting orders, PostgreSQL might throw a serialization conflict or deadlock error.
* **Resolution**:
  - Critical CRUD functions (`action_recommendation`) are wrapped with a `@retry` decorator using the **Tenacity** retry library.
  - **Configuration**:
    - **Trigger**: Retries on database operational or lock errors (`OperationalError`, `DBAPIError`).
    - **Strategy**: 3 maximum attempts with exponential backoff (`multiplier=1`, `min=1s`, `max=4s`).
    - **Telemetry**: Increments a global observability counter `RETRY_COUNT` on retry attempts to expose database health to administrators.

---

## 3. Strict Recommendation State Machine
Recommendations are bound to a state machine transition schema to protect database records from invalid action overrides.

```mermaid
stateDiagram-Model
    [*] --> PENDING
    PENDING --> APPROVED : Coordinator/Doctor APPROVE
    PENDING --> REJECTED : Coordinator/Doctor REJECT
    APPROVED --> [*]
    REJECTED --> [*]
```

* **Constraints**:
  - A recommendation can only transition from `PENDING` to `APPROVED` or `REJECTED`.
  - If a user attempts to execute actions on a recommendation that is already actioned, the transaction immediately raises an `HTTP 409 Conflict` error and aborts, preventing double-actions.
