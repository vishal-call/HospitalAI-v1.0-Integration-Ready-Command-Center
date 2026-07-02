# HospitalAI - Product Demonstration Script

This script guide outlines how to present the HospitalAI Command Center platform to clinical directors and system administrators.

---

## Scenario A: The Default Baseline
1. **Initial Log In**:
   - Access the platform login screen at `http://localhost:3000/login`.
   - Log in using the **Coordinator** or **Doctor** credentials (`doctor@hospitalai.com` / `password123`).
2. **Dashboard Overview**:
   - Point out the **Operations Command** dashboard featuring glassmorphic KPI statistics (Vacant Beds, Active Alert Feeds, ICU Utilization rate).
   - Display the **Interactive Bed Grid Matrix**, highlighting color-coded ward statuses (Green: Available, Red: Occupied, Yellow: Cleaning, Blue: Reserved, Gray: Maintenance).

---

## Scenario B: Triggering ICU Saturation & Deterioration
1. **Trigger ICU Capacity Strain**:
   - Navigate to `/scenarios` (Only accessible as `admin` or using the Admin navigation badge).
   - Click **Trigger: ICU saturation**. This will populate all vacant ICU beds with dummy serious cases.
   - Return to `/`. Notice that the **ICU Utilization rate** spikes to 100%, and an **ICU at Capacity** system alarm triggers on the alert feed.
2. **Log Vitals for Deteriorating Patient**:
   - Search for patient **"John Stable-Edge"** in the general patient registry.
   - Click **Log Vitals** and enter deteriorating metrics:
     - **Heart Rate**: `140` BPM
     - **Respiratory Rate**: `32` Breaths/Min
     - **SpO2**: `85` %
   - Click **Save Vitals**.
3. **Behold Live WebSocket Propagation**:
   - The SpO2 warning card pops up in the Alert Feed immediately.
   - The criticality score calculation triggers, flagging John as `CRITICAL` (EWS 10.0).
   - A **Critical Escalation** recommendation card populates in the **HITL Action Center**.

---

## Scenario C: Human-in-the-Loop Orchestration
1. **Nurse Lockout (RBAC Check)**:
   - Log out and log back in as a Nurse (`nurse@hospitalai.com` / `password123`).
   - Locate the pending recommendation card for John Stable-Edge in the **HITL Action Center**.
   - Show that the **Approve** and **Reject** buttons are disabled. A warning banner states: *"Requires DOCTOR Clearance to approve"*.
2. **Doctor Authorization & Transfer**:
   - Log out and log back in as a Doctor (`doctor@hospitalai.com`).
   - Click **Approve** on John's recommendation card.
   - Point out:
     - Since local ICU is at 100% capacity, the Orchestrator has recommended an **Inter-Hospital Transfer** to *St. Jude Medical Center*.
     - Upon approval, the local bed is released, the patient is discharged, and the external hospital's available ICU beds count decrements atomically.
