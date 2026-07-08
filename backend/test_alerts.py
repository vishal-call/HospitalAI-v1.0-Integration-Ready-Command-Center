import sys
import os
import time
import subprocess
import requests
import asyncio
from sqlalchemy import text
from database import engine

def test_score_math():
    print("Testing scoring math...")
    from services.scoring import calculate_criticality_score
    
    # Normal signs -> 0
    assert calculate_criticality_score(75, 16, 98) == 0.0
    # Hypoxic SpO2 -> 3 + HR & RR deviations -> 10.0
    assert calculate_criticality_score(135, 32, 85) == 10.0
    # Spike HR and RR -> 2 + 2 = 4 -> 4.4
    score_mod = calculate_criticality_score(120, 26, 98)
    assert 4.0 <= score_mod <= 5.0
    print("Scoring math tests PASSED!")

def test_alerts_and_stepdown_pipeline():
    print("Testing alerts and step-down endpoints...")
    session = requests.Session()
    # Log in first to establish auth cookie
    login_payload = {
        "email": "coord@hospitalai.com",
        "password": "password123"
    }
    login_resp = session.post("http://localhost:8000/api/auth/login", json=login_payload, timeout=5)
    assert login_resp.status_code == 200
    
    # 1. Admit Connie Critical to General Ward (vitals will trigger scoring & transfer rec)
    admit_payload = {
      "name": "Connie Critical",
      "age": 44,
      "gender": "Female",
      "admission_reason": "Severe pneumonia watch",
      "status": "CRITICAL",
      "target_ward_id": 3, # General Ward
      "heart_rate": 135,
      "resp_rate": 32,
      "spo2": 85
    }
    
    admit_resp = session.post("http://localhost:8000/api/patients/admit", json=admit_payload, timeout=5)
    assert admit_resp.status_code == 200
    patient = admit_resp.json()
    print(f"Patient admitted: {patient['name']}, Bed: {patient['current_bed_id']}, Score: {patient['criticality_score']}")
    
    # 2. Fetch pending recommendations. Since Connie is Critical in General Ward, she should have a transfer recommendation.
    recs_resp = session.get("http://localhost:8000/api/recommendations/pending", timeout=5)
    assert recs_resp.status_code == 200
    recs = recs_resp.json()
    print(f"Pending recommendations count: {len(recs)}")
    
    connie_rec = next((r for r in recs if r["patient_id"] == patient["id"]), None)
    assert connie_rec is not None
    print(f"Found Connie transfer recommendation ID: {connie_rec['id']}, Target ICU Bed ID: {connie_rec['target_bed_id']}")
    
    # Approve Connie's transfer to ICU to free up capacity / test transfer
    action_payload = {"action": "APPROVE", "user_id": 2}
    action_resp = session.post(f"http://localhost:8000/api/recommendations/{connie_rec['id']}/action", json=action_payload, timeout=5)
    assert action_resp.status_code == 200
    
    # 3. Test Alerts Triggering: log hypoxic vitals for a stable patient
    # Find John Stable-Edge (should be patient ID 1 in fresh seed)
    john_vitals = {
        "heart_rate": 135,
        "resp_rate": 32,
        "spo2": 90 # Hypoxic (<92%) and Spike (previous: 3.9 -> current: 10.0)
    }
    vitals_resp = session.post("http://localhost:8000/api/patients/1/vitals", json=john_vitals, timeout=5)
    assert vitals_resp.status_code == 200
    
    # Fetch active alerts
    alerts_resp = session.get("http://localhost:8000/api/alerts", timeout=5)
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()
    print(f"Active alerts count: {len(alerts)}")
    
    # Verify LOW_OXYGEN and SCORE_SPIKE are generated for John Stable-Edge (patient_id: 1)
    john_alerts = [a for a in alerts if a["patient_id"] == 1]
    alert_types = [a["alert_type"] for a in john_alerts]
    assert "LOW_OXYGEN" in alert_types
    assert "SCORE_SPIKE" in alert_types
    print("Hypoxia and Score Spike alerts verified successfully!")
    
    # Acknowledge one alert
    target_alert = john_alerts[0]
    ack_resp = session.post(f"http://localhost:8000/api/alerts/{target_alert['id']}/acknowledge", json={}, timeout=5)
    assert ack_resp.status_code == 200
    assert ack_resp.json()["is_acknowledged"] is True
    print(f"Acknowledged alert ID: {target_alert['id']}")
    
    # 4. Test ICU Step-Down Agent
    # We will reset database seed data first to ensure clean state
    # Then we will execute db calls to force ICU to 100% capacity and place a stable patient inside it.
    print("Simulating ICU full capacity (100%) and stable patient relocation evaluation...")
    
    async def force_icu_state():
        async with engine.begin() as conn:
            # First, fetch ICU beds (ward_id=1)
            # Mark all 12 beds as OCCUPIED
            await conn.execute(text("UPDATE beds SET status='OCCUPIED', patient_id=4 WHERE ward_id=1"))
            
            # Make bed 1 (ICU-101) occupied by Alice Smith (ID 2, who has a stable score of 1.5)
            await conn.execute(text("UPDATE beds SET patient_id=2 WHERE id=1"))
            await conn.execute(text("UPDATE patients SET current_bed_id=1, criticality_score=1.5, status='STABLE' WHERE id=2"))
            
    asyncio.run(force_icu_state())
    
    # Log vitals to trigger critical status for David Jones (ID 3), who is in General Ward.
    # Since he is critical and needs ICU, but ICU is 100% full, the ICU Agent should recommend stepping Alice Smith (ID 2) down to a GENERAL bed.
    vitals_resp = session.post("http://localhost:8000/api/patients/3/vitals", json=john_vitals, timeout=5)
    assert vitals_resp.status_code == 200
    
    # Fetch pending recommendations
    recs_resp = session.get("http://localhost:8000/api/recommendations/pending", timeout=5)
    assert recs_resp.status_code == 200
    recs = recs_resp.json()
    
    # We expect a pending step-down recommendation for Alice Smith (patient_id: 2 or chained_patient_id: 2) targeting a General Ward bed.
    alice_rec = next((r for r in recs if r["patient_id"] == 2 or r.get("chained_patient_id") == 2), None)
    assert alice_rec is not None
    print(f"ICU Step-down recommendation triggered successfully! ID: {alice_rec['id']}, Reasoning: {alice_rec['reasoning']}")
    
    # Fetch active alerts
    alerts_resp = session.get("http://localhost:8000/api/alerts", timeout=5)
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()
    
    # We expect a system alert ICU_AT_CAPACITY
    capacity_alert = next((a for a in alerts if a["alert_type"] == "ICU_AT_CAPACITY"), None)
    assert capacity_alert is not None
    print(f"ICU Capacity alert verified! Alert: {capacity_alert['message']}")
    
    return True

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
        success = test_alerts_and_stepdown_pipeline()
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
        print("ALL ALERT ENGINE AND ICU AGENT TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("ALERT ENGINE AND ICU AGENT TESTS FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()
