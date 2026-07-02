import sys
import time
import subprocess
import requests
import json

from services.scoring import calculate_criticality_score

def test_score_math():
    print("Testing scoring math...")
    # Stable (Expected: 0.0)
    assert calculate_criticality_score(75, 16, 98) == 0.0
    # Serious boundary-value (Expected: 4.0)
    assert calculate_criticality_score(115, 23, 93) == 4.0
    # Critical boundary-value (Expected: 10.0)
    assert calculate_criticality_score(135, 32, 85) == 10.0
    print("Scoring math tests PASSED!\n")

def test_hitl_pipeline():
    print("Testing HITL pipeline endpoints...")
    try:
        session = requests.Session()
        # Log in first to establish auth cookie
        login_payload = {
            "email": "coord@hospitalai.com",
            "password": "password123"
        }
        login_resp = session.post("http://localhost:8000/api/auth/login", json=login_payload, timeout=5)
        assert login_resp.status_code == 200

        # 1. Fetch wards to get General Ward (id: 3) and ICU (id: 1)
        wards_resp = session.get("http://localhost:8000/api/wards", timeout=5)
        wards = wards_resp.json()
        general_ward = next(w for w in wards if "General" in w["name"])
        icu_ward = next(w for w in wards if "ICU" in w["name"])
        
        # 2. Admit a critical patient to the General Ward
        payload = {
            "name": "Connie Critical",
            "age": 68,
            "gender": "Female",
            "admission_reason": "Acute dyspnea and hypoxemia",
            "status": "CRITICAL",
            "target_ward_id": general_ward["id"],
            "heart_rate": 135,
            "resp_rate": 32,
            "spo2": 85
        }
        print("Admitting critical patient to General Ward...")
        admit_resp = session.post("http://localhost:8000/api/patients/admit", json=payload, timeout=5)
        assert admit_resp.status_code == 200
        patient = admit_resp.json()
        print(f"Patient admitted: {patient['name']}, Bed: {patient['current_bed_id']}, Score: {patient['criticality_score']}")
        
        # 3. Check if recommendation was created dynamically in the pending queue
        print("Fetching pending recommendations...")
        recs_resp = session.get("http://localhost:8000/api/recommendations/pending", timeout=5)
        assert recs_resp.status_code == 200
        recs = recs_resp.json()
        print(f"Pending recommendations count: {len(recs)}")
        
        # Find recommendation for Connie Critical
        my_rec = next(r for r in recs if r["patient_id"] == patient["id"])
        print(f"Found pending recommendation: ID {my_rec['id']}, Reasoning: {my_rec['reasoning']}")
        assert my_rec["status"] == "PENDING"
        assert my_rec["criticality_score"] == 10.0
        
        # 4. Action recommendation: APPROVE transfer
        action_payload = {
            "action": "APPROVE",
            "user_id": 2 # Coordinator user ID
        }
        print(f"Approving transfer for recommendation ID {my_rec['id']}...")
        action_resp = session.post(f"http://localhost:8000/api/recommendations/{my_rec['id']}/action", json=action_payload, timeout=5)
        assert action_resp.status_code == 200
        actioned_rec = action_resp.json()
        print(f"Actioned recommendation: Status = {actioned_rec['status']}")
        assert actioned_rec["status"] == "APPROVED"
        
        # Verify database update: Patient current bed should match the target bed
        patients_resp = session.get("http://localhost:8000/api/patients", timeout=5)
        patients_list = patients_resp.json()
        updated_patient = next(p for p in patients_list if p["id"] == patient["id"])
        print(f"Patient bed after transfer approval: {updated_patient['current_bed_id']} (Expected target bed: {my_rec['target_bed_id']})")
        assert updated_patient["current_bed_id"] == my_rec["target_bed_id"]
        
        # 5. Test CONCURRENCY conflict and ROLLBACK scenario
        # Admit another critical patient to the General Ward to trigger another recommendation
        payload_2 = {
            "name": "Clara Conflict",
            "age": 70,
            "gender": "Female",
            "admission_reason": "Desaturation under observation",
            "status": "CRITICAL",
            "target_ward_id": general_ward["id"],
            "heart_rate": 135,
            "resp_rate": 32,
            "spo2": 85
        }
        print("Admitting second critical patient Clara Conflict...")
        admit_resp_2 = session.post("http://localhost:8000/api/patients/admit", json=payload_2, timeout=5)
        patient_2 = admit_resp_2.json()
        
        # Fetch pending recommendations again
        recs_resp = session.get("http://localhost:8000/api/recommendations/pending", timeout=5)
        recs = recs_resp.json()
        my_rec_2 = next(r for r in recs if r["patient_id"] == patient_2["id"])
        print(f"Found second pending recommendation: ID {my_rec_2['id']} pointing to target bed ID {my_rec_2['target_bed_id']}")
        
        # Simulating a concurrency snag: target bed is occupied or state is altered right before approval
        print(f"Simulating concurrency snag: Marking target bed {my_rec_2['target_bed_id']} as occupied in database...")
        from database import engine
        from sqlalchemy import text
        import asyncio
        
        async def mark_bed_occupied(bed_id):
            async with engine.begin() as conn:
                await conn.execute(text(f"UPDATE beds SET status='OCCUPIED', patient_id=20 WHERE id={bed_id}"))
                
        asyncio.run(mark_bed_occupied(my_rec_2['target_bed_id']))
        
        # Attempt to approve recommendation now, should return 409 Conflict
        print("Attempting to approve recommendation with occupied target bed...")
        action_resp_2 = session.post(f"http://localhost:8000/api/recommendations/{my_rec_2['id']}/action", json=action_payload, timeout=5)
        print(f"Action response for conflict: {action_resp_2.status_code}")
        print(f"Conflict response JSON: {action_resp_2.json()}")
        assert action_resp_2.status_code == 409
        assert "Concurrency Conflict" in action_resp_2.json()["detail"]
        
        # Check that recommendation remains PENDING and patient bed remains unchanged (correct transaction rollback!)
        recs_check_resp = session.get("http://localhost:8000/api/recommendations/pending", timeout=5)
        recs_check = recs_check_resp.json()
        unchecked_rec = next(r for r in recs_check if r["id"] == my_rec_2["id"])
        print(f"Verified recommendation {my_rec_2['id']} state remains: {unchecked_rec['status']} (Expected: PENDING)")
        assert unchecked_rec["status"] == "PENDING"
        
        print("HITL pipeline and transaction rollback tests PASSED!\n")
        return True
    except Exception as e:
        print(f"HITL tests FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False

def main():
    # 1. Resolve WSL IP once in parent and inject into environment
    import os
    wsl_ip = "localhost"
    try:
        res = subprocess.run(["wsl", "hostname", "-I"], capture_output=True, text=True, timeout=3)
        if res.returncode == 0:
            ip_list = res.stdout.strip().split()
            if ip_list:
                wsl_ip = ip_list[0]
                print(f"Parent resolved WSL IP: {wsl_ip}")
    except Exception as e:
        print(f"Parent failed to resolve WSL IP: {e}")
        
    os.environ["WSL_IP"] = wsl_ip
    env = os.environ.copy()
    
    test_score_math()
    
    # 2. Reset database state by running seed.py
    print("Hydrating database with fresh seed data...")
    subprocess.run([sys.executable, "seed.py"], env=env, check=True)
    
    # 3. Start a background process inside WSL to prevent VM auto-shutdown
    print("Starting WSL keep-alive process...")
    wsl_keep_alive = subprocess.Popen(
        ["wsl", "-d", "Ubuntu", "--", "sleep", "120"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    print("Starting FastAPI Uvicorn server in subprocess...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--port", "8000"],
        env=env,
        text=True
    )
    
    time.sleep(6)
    
    success = False
    try:
        success = test_hitl_pipeline()
    finally:
        print("Terminating FastAPI server...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
            print("Server terminated successfully.")
        except subprocess.TimeoutExpired:
            proc.kill()
            print("Server force killed.")
            
        print("Terminating WSL keep-alive process...")
        wsl_keep_alive.terminate()
        wsl_keep_alive.wait()
            
    if success:
        print("ALL INTELLIGENCE AND HITL TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("VERIFICATION FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()
