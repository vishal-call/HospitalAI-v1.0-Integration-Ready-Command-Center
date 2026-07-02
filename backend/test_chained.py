import sys
import requests
import json

def test_chained_pipeline():
    print("Testing Chained Transfer pipeline...")
    session = requests.Session()
    
    # 1. Log in as admin to trigger scenario
    login_payload = {
        "email": "admin@hospitalai.com",
        "password": "password123"
    }
    login_resp = session.post("http://localhost:8000/api/auth/login", json=login_payload, timeout=5)
    assert login_resp.status_code == 200
    
    # 2. Trigger the scenario trigger_chained_chain
    trigger_resp = session.post("http://localhost:8000/api/scenarios/trigger", json={"scenario": "trigger_chained_chain"}, timeout=10)
    if trigger_resp.status_code != 200:
        print("Trigger Failed:", trigger_resp.text)
    assert trigger_resp.status_code == 200
    print("Scenario trigger_chained_chain triggered successfully!")
    
    # 3. Fetch pending recommendations as doctor
    session = requests.Session()
    login_payload = {
        "email": "doctor@hospitalai.com",
        "password": "password123"
    }
    login_resp = session.post("http://localhost:8000/api/auth/login", json=login_payload, timeout=5)
    assert login_resp.status_code == 200
    
    recs_resp = session.get("http://localhost:8000/api/recommendations/pending", timeout=5)
    assert recs_resp.status_code == 200
    recs = recs_resp.json()
    assert len(recs) > 0
    
    # Find CHAINED_TRANSFER recommendation
    chained_rec = next((r for r in recs if r.get("recommendation_type") == "CHAINED_TRANSFER"), None)
    assert chained_rec is not None, "CHAINED_TRANSFER recommendation not found!"
    print(f"Found chained recommendation reasoning: {chained_rec['reasoning']}")
    assert chained_rec["status"] == "PENDING"
    assert chained_rec["chained_patient_id"] is not None
    assert chained_rec["chained_target_bed_id"] is not None
    
    bed_id = chained_rec["chained_target_bed_id"]
    
    # 4. Try to approve the chained transfer while General Ward bed is manually updated to OCCUPIED.
    update_bed_resp = session.post(f"http://localhost:8000/api/beds/{bed_id}/status", json={"status": "OCCUPIED"}, timeout=5)
    assert update_bed_resp.status_code == 200
    
    # Attempt approval as doctor - should fail with 409 Conflict
    action_payload = {
        "action": "APPROVE",
        "user_id": 3
    }
    approve_fail_resp = session.post(f"http://localhost:8000/api/recommendations/{chained_rec['id']}/action", json=action_payload, timeout=5)
    assert approve_fail_resp.status_code == 409
    print("Atomic rollback test PASSED! (Approve blocked due to occupied bed)")
    
    # 5. Restore bed status to AVAILABLE and check successful execution
    restore_bed_resp = session.post(f"http://localhost:8000/api/beds/{bed_id}/status", json={"status": "AVAILABLE"}, timeout=5)
    assert restore_bed_resp.status_code == 200
    
    # Approve recommendation - should succeed
    approve_success_resp = session.post(f"http://localhost:8000/api/recommendations/{chained_rec['id']}/action", json=action_payload, timeout=5)
    assert approve_success_resp.status_code == 200
    print("Chained transfer approval succeeded!")
    
    # Verify state:
    # Stable patient should now be in General Ward target bed
    # Critical patient should now be in the ICU target bed
    patients_resp = session.get("http://localhost:8000/api/patients", timeout=5)
    assert patients_resp.status_code == 200
    patients = patients_resp.json()
    
    stable_patient = next(p for p in patients if p["id"] == chained_rec["chained_patient_id"])
    critical_patient = next(p for p in patients if p["id"] == chained_rec["patient_id"])
    
    assert stable_patient["current_bed_id"] == chained_rec["chained_target_bed_id"]
    assert critical_patient["current_bed_id"] == chained_rec["target_bed_id"]
    
    print("Chained relocations state validation PASSED!")

if __name__ == "__main__":
    test_chained_pipeline()
