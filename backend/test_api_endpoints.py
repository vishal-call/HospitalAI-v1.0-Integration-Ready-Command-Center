import sys
import time
import subprocess
import requests
import json

def test_rest_endpoints():
    print("Testing REST API endpoints...")
    try:
        # 1. Test GET /api/wards
        wards_resp = requests.get("http://localhost:8000/api/wards", timeout=5)
        print(f"GET /api/wards status: {wards_resp.status_code}")
        assert wards_resp.status_code == 200
        wards = wards_resp.json()
        print(f"Retrieved {len(wards)} wards.")
        assert len(wards) == 3
        # Check ICU, Emergency, General Ward capacities
        ward_names = [w["name"] for w in wards]
        print(f"Ward names: {ward_names}")
        assert any("ICU" in name or "Intensive Care" in name for name in ward_names)
        
        # 2. Test GET /api/patients
        patients_resp = requests.get("http://localhost:8000/api/patients", timeout=5)
        print(f"GET /api/patients status: {patients_resp.status_code}")
        assert patients_resp.status_code == 200
        patients = patients_resp.json()
        print(f"Retrieved {len(patients)} active patients.")
        assert len(patients) >= 20

        # Verify boundary conditions:
        scores = [p["criticality_score"] for p in patients]
        names = [p["name"] for p in patients]
        print("Verifying patient boundary scores:")
        for name, score in zip(names, scores):
            if "Stable-Edge" in name:
                print(f"  Stable Edge case: {name} = {score} (Expected: 3.9)")
                assert score == 3.9
            elif "Serious-Lower" in name:
                print(f"  Serious Lower: {name} = {score} (Expected: 4.0)")
                assert score == 4.0
            elif "Serious-Upper" in name:
                print(f"  Serious Upper: {name} = {score} (Expected: 7.9)")
                assert score == 7.9
            elif "Critical-Lower" in name:
                print(f"  Critical Lower: {name} = {score} (Expected: 8.0)")
                assert score == 8.0
            elif "Critical-Upper" in name:
                print(f"  Critical Upper: {name} = {score} (Expected: 10.0)")
                assert score == 10.0

        # 3. Test GET /api/beds
        beds_resp = requests.get("http://localhost:8000/api/beds", timeout=5)
        print(f"GET /api/beds status: {beds_resp.status_code}")
        assert beds_resp.status_code == 200
        beds = beds_resp.json()
        print(f"Retrieved {len(beds)} beds total.")
        assert len(beds) == 56
        
        # 4. Test POST /api/patients/admit (atomic transaction)
        # Find ward ID for General Ward
        general_ward = next(w for w in wards if "General" in w["name"])
        target_ward_id = general_ward["id"]
        
        payload = {
            "name": "New Test Patient",
            "age": 44,
            "gender": "Female",
            "admission_reason": "Testing atomic admission transaction",
            "status": "STABLE",
            "target_ward_id": target_ward_id
        }
        
        print(f"Posting admission to ward {target_ward_id}...")
        admit_resp = requests.post("http://localhost:8000/api/patients/admit", json=payload, timeout=5)
        print(f"POST /api/patients/admit status: {admit_resp.status_code}")
        assert admit_resp.status_code == 200
        admitted = admit_resp.json()
        print(f"Admitted patient response: {admitted}")
        assert admitted["name"] == "New Test Patient"
        assert admitted["current_bed_id"] is not None
        
        # Verify bed is occupied and maps to patient id
        new_bed_id = admitted["current_bed_id"]
        beds_updated_resp = requests.get("http://localhost:8000/api/beds", timeout=5)
        updated_beds = beds_updated_resp.json()
        target_bed = next(b for b in updated_beds if b["id"] == new_bed_id)
        print(f"Bed status after admission: {target_bed}")
        assert target_bed["status"] == "OCCUPIED"
        assert target_bed["patient_id"] == admitted["id"]
        
        print("REST API and transaction tests PASSED!\n")
        return True
    except Exception as e:
        print(f"REST API tests FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Starting FastAPI Uvicorn server in subprocess...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--port", "8000"],
        text=True
    )
    
    time.sleep(3)
    
    success = False
    try:
        success = test_rest_endpoints()
    finally:
        print("Terminating FastAPI server...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
            print("Server terminated successfully.")
        except subprocess.TimeoutExpired:
            proc.kill()
            print("Server force killed.")
            
    if success:
        print("REST ENDPOINTS AND TRANSACTION VERIFICATION SUCCEEDED!")
        sys.exit(0)
    else:
        print("VERIFICATION FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()
