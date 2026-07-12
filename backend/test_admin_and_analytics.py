import os
import sys
import time
import subprocess
import requests
import json

# Setup test environment variables
os.environ["SSO_MOCK"] = "true"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/hospitalai"

API_BASE = "http://127.0.0.1:8000"

def get_admin_headers():
    # Login as admin
    url = f"{API_BASE}/api/auth/login"
    res = requests.post(url, json={
        "email": "admin@hospitalai.com",
        "password": "password123"
    })
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    token = res.json()["token"]
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def get_coordinator_headers():
    # Login as coordinator
    url = f"{API_BASE}/api/auth/login"
    res = requests.post(url, json={
        "email": "coord@hospitalai.com",
        "password": "password123"
    })
    assert res.status_code == 200, f"Coordinator login failed: {res.text}"
    token = res.json()["token"]
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def test_admin_rbac_restrictions():
    print("Testing admin RBAC restrictions...")
    # Coordinator tries to create a ward (should be blocked)
    coord_headers = get_coordinator_headers()
    url = f"{API_BASE}/api/admin/wards"
    res = requests.post(url, headers=coord_headers, json={
        "name": "Unauthorized ICU",
        "type": "ICU",
        "capacity": 5
    })
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"
    print("Admin RBAC restrictions test PASSED!\n")

def test_dynamic_ward_bed_crud():
    print("Testing dynamic Ward & Bed CRUD...")
    admin_headers = get_admin_headers()
    
    # 1. Create a ward
    url_ward = f"{API_BASE}/api/admin/wards"
    res = requests.post(url_ward, headers=admin_headers, json={
        "name": "Dynamic ICU Alpha",
        "type": "ICU",
        "capacity": 2
    })
    assert res.status_code == 200, f"Failed to create ward: {res.text}"
    ward = res.json()
    ward_id = ward["id"]
    print(f"Created ward: {ward}")
    
    # 2. Try to delete the ward (should succeed since it is empty)
    res_del = requests.delete(f"{url_ward}/{ward_id}", headers=admin_headers)
    assert res_del.status_code == 200, f"Failed to delete empty ward: {res_del.text}"
    print("Successfully deleted empty ward.")
    
    # Re-create ward for bed testing
    res = requests.post(url_ward, headers=admin_headers, json={
        "name": "Dynamic ICU Alpha",
        "type": "ICU",
        "capacity": 2
    })
    assert res.status_code == 200
    ward_id = res.json()["id"]

    # 3. Create a bed
    url_bed = f"{API_BASE}/api/admin/beds"
    res = requests.post(url_bed, headers=admin_headers, json={
        "ward_id": ward_id,
        "bed_number": "ICU-ALPHA-101",
        "status": "AVAILABLE"
    })
    assert res.status_code == 200, f"Failed to create bed: {res.text}"
    bed = res.json()
    bed_id = bed["id"]
    print(f"Created bed: {bed}")

    # 4. Try to delete ward with active beds (should fail)
    res_del_ward = requests.delete(f"{url_ward}/{ward_id}", headers=admin_headers)
    assert res_del_ward.status_code == 400 or res_del_ward.status_code == 409, f"Expected failure, got {res_del_ward.status_code}"
    print("Delete ward with active beds failed as expected.")

    # 5. Delete the bed
    res_del_bed = requests.delete(f"{url_bed}/{bed_id}", headers=admin_headers)
    assert res_del_bed.status_code == 200, f"Failed to delete empty bed: {res_del_bed.text}"
    print("Deleted empty bed successfully.")
    
    # 6. Delete the ward
    res_del_ward = requests.delete(f"{url_ward}/{ward_id}", headers=admin_headers)
    assert res_del_ward.status_code == 200, f"Failed to delete ward: {res_del_ward.text}"
    print("Deleted empty ward successfully.")
    
    print("Dynamic Ward & Bed CRUD test PASSED!\n")

def test_occupied_bed_deletion_restriction():
    print("Testing occupied Bed deletion restriction...")
    admin_headers = get_admin_headers()
    
    # Try to delete bed 1 (occupied by Patient 1 John Stable-Edge in General Ward in standard seed)
    url_bed = f"{API_BASE}/api/admin/beds/1"
    res = requests.delete(url_bed, headers=admin_headers)
    print(f"Delete occupied bed response: {res.status_code} - {res.text}")
    assert res.status_code == 400 or res.status_code == 409
    print("Occupied bed deletion prevented as expected.")
    print("Occupied Bed deletion restriction test PASSED!\n")

def test_staff_role_update():
    print("Testing dynamic staff role updates...")
    admin_headers = get_admin_headers()
    
    # Update coordinator role to nurse
    url = f"{API_BASE}/api/admin/staff/role"
    res = requests.patch(url, headers=admin_headers, json={
        "email": "coord@hospitalai.com",
        "role": "NURSE"
    })
    assert res.status_code == 200, f"Failed to update role: {res.text}"
    user = res.json()
    assert user["role"] == "NURSE"
    print("Role updated successfully to NURSE.")
    
    # Restore role to COORDINATOR
    res = requests.patch(url, headers=admin_headers, json={
        "email": "coord@hospitalai.com",
        "role": "COORDINATOR"
    })
    assert res.status_code == 200
    assert res.json()["role"] == "COORDINATOR"
    print("Role restored successfully to COORDINATOR.")
    print("Staff role update test PASSED!\n")

def test_telemetry_logging_and_summary():
    print("Testing operational telemetry logging & summary...")
    admin_headers = get_admin_headers()
    coord_headers = get_coordinator_headers()
    
    # 1. Ingest vitals that trigger alerts & recommendations
    # Send vitals for Patient 1 to trigger LOW_OXYGEN and SCORE_SPIKE
    url_vitals = f"{API_BASE}/api/patients/1/vitals"
    res = requests.post(url_vitals, headers=coord_headers, json={
        "heart_rate": 140,
        "resp_rate": 32,
        "spo2": 85,
        "temperature": 38.5,
        "systolic_bp": 110,
        "consciousness_level": "ALERT",
        "oxygen_supplement": True,
        "spo2_scale": 1
    })
    assert res.status_code == 200, f"Vitals log failed: {res.text}"
    print("Logged critical vitals.")
    
    # Wait for DB commits to flush
    time.sleep(1)
    
    # Check that recommendation was generated and summary logs recorded it
    res_summary = requests.get(f"{API_BASE}/api/admin/analytics/summary", headers=admin_headers)
    assert res_summary.status_code == 200
    summary = res_summary.json()
    print(f"Current operational analytics summary: {summary}")
    assert summary["alert_triggered_count"] >= 1
    assert summary["recommendation_generated_count"] >= 1
    
    # Fetch recommendations to find our new PENDING recommendation id
    res_recs = requests.get(f"{API_BASE}/api/recommendations/pending", headers=coord_headers)
    assert res_recs.status_code == 200
    recs = res_recs.json()
    new_rec = None
    for r in recs:
        if r["patient_id"] == 1 and r["status"] == "PENDING":
            new_rec = r
            break
            
    assert new_rec is not None, "Failed to find generated pending recommendation."
    rec_id = new_rec["id"]
    print(f"Found pending recommendation ID: {rec_id}")
    
    # 2. Action the recommendation (APPROVE)
    url_action = f"{API_BASE}/api/recommendations/{rec_id}/action"
    res_action = requests.post(url_action, headers=coord_headers, json={
        "action": "APPROVE"
    })
    assert res_action.status_code == 200, f"Recommendation action failed: {res_action.text}"
    print("Approved recommendation.")
    
    # 3. Check summary again.
    res_summary = requests.get(f"{API_BASE}/api/admin/analytics/summary", headers=admin_headers)
    assert res_summary.status_code == 200
    summary2 = res_summary.json()
    print(f"Updated operational analytics summary: {summary2}")
    
    assert summary2["approved_count"] >= 1
    assert summary2["ai_acceptance_rate"] > 0.0
    assert summary2["median_response_time_seconds"] >= 0.0
    
    print("Operational telemetry logging & summary test PASSED!\n")

def main():
    # Seeding database
    print("Re-seeding database...")
    subprocess.run([sys.executable, "seed.py"], check=True)

    print("Spawning FastAPI server...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"]
    )
    
    import socket
    server_ready = False
    for _ in range(30):
        try:
            with socket.create_connection(("127.0.0.1", 8000), timeout=0.5):
                server_ready = True
                break
        except (ConnectionRefusedError, socket.timeout, OSError):
            time.sleep(0.5)
            
    if not server_ready:
        print("Server failed to start.")
        proc.kill()
        sys.exit(1)
        
    success = False
    try:
        test_admin_rbac_restrictions()
        test_dynamic_ward_bed_crud()
        test_occupied_bed_deletion_restriction()
        test_staff_role_update()
        test_telemetry_logging_and_summary()
        success = True
        print("\nALL ADMIN AND TELEMETRY LOGGING TESTS PASSED SUCCESSFULLY!")
    except Exception as e:
        print(f"\nTESTS FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Terminating server...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
