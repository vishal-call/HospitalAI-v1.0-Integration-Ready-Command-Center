import sys
import os
import time
import subprocess
import requests
import asyncio
import threading
from sqlalchemy import text

def keep_wsl_awake(stop_event):
    while not stop_event.is_set():
        try:
            # Query pg_isready to keep the VM network bridge active
            subprocess.run(
                ["wsl", "-d", "Ubuntu", "--", "pg_isready"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5.0
            )
        except Exception:
            pass
        time.sleep(2.0)

def test_inter_hospital_transfer_flow():
    print("Starting Inter-Hospital transfer flow test...")
    
    # 1. Hydrate database fresh using seed.py
    # (Already done in main block)
    
    # 2. Simulate 100% full ICU where ALL patients have EWS > 3.0 (to block internal step-downs)
    # The seeder populates patients Robert, Jane, Elizabeth, Charles, Patricia, Thomas, Barbara
    # who all have scores >= 8.0.
    # We will occupy the remaining 5 beds with dummy patient ID 4 (Emma Brown, score 3.2 -> let's make it 5.0 to block step-down!)
    async def force_full_icu_no_stepdown():
        from database import engine
        async with engine.begin() as conn:
            # Block step-down: Update Emma Brown's score to 5.0 (greater than 3.0 threshold)
            await conn.execute(text("UPDATE patients SET criticality_score=5.0 WHERE id=4"))
            
            # Occupy all 12 beds in ICU (ward_id=1)
            await conn.execute(text("UPDATE beds SET status='OCCUPIED', patient_id=4 WHERE ward_id=1"))
            
            # Set the actual critical patients seeded to occupy their beds (1-7)
            # Bed 1 (ICU-101) occupied by Robert (patient ID 8, score 8.0)
            await conn.execute(text("UPDATE beds SET patient_id=8 WHERE id=1"))
            await conn.execute(text("UPDATE patients SET current_bed_id=1 WHERE id=8"))
            
            # Bed 2 (ICU-102) occupied by Jane (patient ID 9, score 10.0)
            await conn.execute(text("UPDATE beds SET patient_id=9 WHERE id=2"))
            await conn.execute(text("UPDATE patients SET current_bed_id=2 WHERE id=9"))
            
            # Bed 3 (ICU-103) occupied by Elizabeth (patient ID 10, score 8.8)
            await conn.execute(text("UPDATE beds SET patient_id=10 WHERE id=3"))
            await conn.execute(text("UPDATE patients SET current_bed_id=3 WHERE id=10"))

            # Bed 4 (ICU-104) occupied by Charles (patient ID 11, score 9.2)
            await conn.execute(text("UPDATE beds SET patient_id=11 WHERE id=4"))
            await conn.execute(text("UPDATE patients SET current_bed_id=4 WHERE id=11"))

            # Bed 5 (ICU-105) occupied by Patricia (patient ID 12, score 8.5)
            await conn.execute(text("UPDATE beds SET patient_id=12 WHERE id=5"))
            await conn.execute(text("UPDATE patients SET current_bed_id=5 WHERE id=12"))

            # Bed 6 (ICU-106) occupied by Thomas (patient ID 13, score 9.6)
            await conn.execute(text("UPDATE beds SET patient_id=13 WHERE id=6"))
            await conn.execute(text("UPDATE patients SET current_bed_id=6 WHERE id=13"))

            # Bed 7 (ICU-107) occupied by Barbara (patient ID 14, score 9.0)
            await conn.execute(text("UPDATE beds SET patient_id=14 WHERE id=7"))
            await conn.execute(text("UPDATE patients SET current_bed_id=7 WHERE id=14"))
        await engine.dispose()

    asyncio.run(force_full_icu_no_stepdown())
    time.sleep(4)
    
    session = requests.Session()
    # Log in first to establish auth cookie
    login_payload = {
        "email": "coord@hospitalai.com",
        "password": "password123"
    }
    login_resp = session.post("http://localhost:8000/api/auth/login", json=login_payload, timeout=5)
    assert login_resp.status_code == 200

    # 3. Log critical vitals for a General Ward patient: John Stable-Edge (ID 1, currently in bed GW-301, ID 27)
    # Vitals will trigger critical EWS of 9.0.
    # Since he is critical and needs ICU, but ICU is 100% full, and all ICU patients have score >= 5.0 (> 3.0),
    # the Inter-Hospital Agent must be invoked.
    john_vitals = {
        "heart_rate": 135,
        "resp_rate": 32,
        "spo2": 90
    }
    
    time.sleep(4)
    vitals_resp = session.post("http://localhost:8000/api/patients/1/vitals", json=john_vitals, timeout=30)
    assert vitals_resp.status_code == 200
    
    # 4. Fetch pending recommendations and verify external transfer
    time.sleep(4)
    recs_resp = session.get("http://localhost:8000/api/recommendations/pending", timeout=30)
    assert recs_resp.status_code == 200
    recs = recs_resp.json()
    
    # Find the recommendation for John Stable-Edge (patient_id: 1)
    john_rec = next((r for r in recs if r["patient_id"] == 1), None)
    assert john_rec is not None
    assert john_rec["partner_hospital_id"] is not None
    assert john_rec["target_bed_id"] is None
    
    # It must target St. Jude Medical Center (Partner ID 1, distance 5.2 km)
    assert john_rec["partner_hospital"]["name"] == "St. Jude Medical Center"
    print(f"Inter-Hospital recommendation generated! ID: {john_rec['id']}, Target Partner: {john_rec['partner_hospital']['name']}, Distance: {john_rec['partner_hospital']['distance_km']} km")
    
    # 5. Fetch Partner Hospitals list and check initial capacity
    time.sleep(4)
    partners_resp = session.get("http://localhost:8000/api/partner-hospitals", timeout=30)
    assert partners_resp.status_code == 200
    partners = partners_resp.json()
    st_jude = next(p for p in partners if p["name"] == "St. Jude Medical Center")
    initial_icu_avail = st_jude["icu_beds_available"]
    
    # 6. Approve the external transfer recommendation in HITL Action Center
    action_payload = {"action": "APPROVE", "user_id": 2}
    time.sleep(4)
    action_resp = session.post(f"http://localhost:8000/api/recommendations/{john_rec['id']}/action", json=action_payload, timeout=30)
    if action_resp.status_code != 200:
        print("ACTION ERROR DETAIL:", action_resp.text)
    assert action_resp.status_code == 200
    print("Approved external transfer recommendation!")
    
    # 7. Verify local bed release (GW-301, ID 27 should be AVAILABLE)
    async def verify_db_states():
        from database import engine
        async with engine.begin() as conn:
            # Check bed 27 status
            bed_res = await conn.execute(text("SELECT status, patient_id FROM beds WHERE id=27"))
            bed = bed_res.fetchone()
            assert bed[0] == "AVAILABLE"
            assert bed[1] is None
            
            # Check patient 1 status (discharged_at is set, current_bed_id is null)
            patient_res = await conn.execute(text("SELECT current_bed_id, discharged_at FROM patients WHERE id=1"))
            patient = patient_res.fetchone()
            assert patient[0] is None
            assert patient[1] is not None
            
            # Check PartnerHospital ICU beds availability is decremented
            partner_res = await conn.execute(text("SELECT icu_beds_available FROM partner_hospitals WHERE id=1"))
            partner = partner_res.fetchone()
            assert partner[0] == initial_icu_avail - 1
            
            # Check TransferRequest status is APPROVED
            tr_res = await conn.execute(text("SELECT status FROM transfer_requests WHERE patient_id=1"))
            tr = tr_res.fetchone()
            assert tr[0] == "APPROVED"
        await engine.dispose()

    asyncio.run(verify_db_states())
    print("Database verification completed! Bed released, patient discharged, partner capacity decremented, and transfer request approved successfully.")
    return True

def main():
    import os
    
    wsl_ip = "localhost"
    try:
        print("Waking up WSL and resolving WSL IP...")
        res = subprocess.run(["wsl", "hostname", "-I"], capture_output=True, text=True, timeout=12.0)
        if res.returncode == 0:
            ip_list = res.stdout.strip().split()
            if ip_list:
                wsl_ip = ip_list[0]
                print(f"Resolved WSL IP: {wsl_ip}")
    except Exception as e:
        print(f"Failed to resolve WSL IP: {e}")
        
    os.environ["WSL_IP"] = wsl_ip
    env = os.environ.copy()
    
    # Start background keepalive thread to maintain virtual network switch activity
    print("Starting background WSL keep-alive thread...")
    stop_keepalive = threading.Event()
    keepalive_thread = threading.Thread(target=keep_wsl_awake, args=(stop_keepalive,), daemon=True)
    keepalive_thread.start()
    
    # 2. Reset database state by running seed.py
    print("Hydrating database with fresh seed data...")
    subprocess.run([sys.executable, "seed.py"], env=env, check=True)
    
    # 3. Start FastAPI Uvicorn server in subprocess
    print("Starting FastAPI Uvicorn server...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--port", "8000"],
        env=env,
        text=True
    )
    
    time.sleep(10)
    
    success = False
    try:
        success = test_inter_hospital_transfer_flow()
    finally:
        print("Terminating FastAPI server...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            
        print("Stopping background WSL keep-alive thread...")
        stop_keepalive.set()
        keepalive_thread.join(timeout=2.0)
            
    if success:
        print("ALL INTER-HOSPITAL TRANSFER AGENT TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("INTER-HOSPITAL TRANSFER AGENT TESTS FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()
