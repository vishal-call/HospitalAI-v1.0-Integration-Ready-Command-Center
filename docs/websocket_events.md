# HospitalAI - WebSocket Real-Time Event Mappings

This document defines the JSON payload specifications broadcast over the `ws://localhost:8000/ws/dashboard` live channel.

---

## 1. Initial State Handshake
Sent immediately upon successful client connection and verification.
* **Payload**:
  ```json
  {
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
  ```

---

## 2. Patient Admitted Event
Broadcast when a new patient is successfully admitted.
* **Payload**:
  ```json
  {
    "type": "PATIENT_ADMITTED",
    "data": {
      "patient_id": 21,
      "name": "Emergency Telemetry Spawn",
      "status": "CRITICAL",
      "criticality_score": 10.0,
      "bed_id": 20
    }
  }
  ```

---

## 3. Patient Vitals Updated Event
Broadcast when raw vitals are saved and EWS scores are recalculated.
* **Payload**:
  ```json
  {
    "type": "PATIENT_UPDATED",
    "data": {
      "patient_id": 1,
      "name": "John Stable-Edge",
      "status": "CRITICAL",
      "criticality_score": 10.0,
      "bed_id": 27
    },
    "recommendation": {
      "id": 1,
      "patient_name": "John Stable-Edge",
      "score": 10.0,
      "reasoning": "Recommend immediate transfer..."
    }
  }
  ```

---

## 4. Alert Triggered Event
Broadcast when clinical threshold violations are identified.
* **Payload**:
  ```json
  {
    "type": "ALERT_TRIGGERED",
    "data": [
      {
        "id": 4,
        "patient_id": 21,
        "alert_type": "LOW_OXYGEN",
        "severity": "CRITICAL",
        "message": "Patient John displays severe hypoxaemia (SpO2: 85%).",
        "is_acknowledged": false,
        "created_at": "2026-07-01T04:10:18.149859"
      }
    ]
  }
  ```

---

## 5. Bed Updated Event
Broadcast when a bed status changes manually or via transfer.
* **Payload**:
  ```json
  {
    "type": "BED_UPDATED",
    "data": {
      "bed_id": 8,
      "ward_id": 1,
      "bed_number": "ICU-108",
      "status": "CLEANING",
      "patient_id": null,
      "patient": null
    }
  }
  ```

---

## 6. Delta Rehydration Event
Broadcast to rehydrate client states following disconnect/reconnect phases.
* **Payload**:
  ```json
  {
    "type": "DELTA_REHYDRATION",
    "data": {
      "alerts": [],
      "recommendations": [],
      "transfer_requests": []
    }
  }
  ```
