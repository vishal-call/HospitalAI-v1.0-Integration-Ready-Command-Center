import os
import sys
import time
import subprocess
import requests
import json

def test_interop_security():
    print("Testing interop security...")
    # Send empty request with no API Key
    url = "http://127.0.0.1:8000/api/interop/hl7/observation"
    res = requests.post(url, data="some payload")
    print(f"Empty auth status: {res.status_code}")
    assert res.status_code == 401

    # Send request with invalid API Key
    headers = {"X-API-Key": "INVALID_KEY_123"}
    res = requests.post(url, headers=headers, data="some payload")
    print(f"Invalid auth status: {res.status_code}")
    assert res.status_code == 401
    print("Interop security test PASSED!\n")

def test_hl7_ingestion():
    print("Testing HL7 ORU^R01 ingestion...")
    url = "http://127.0.0.1:8000/api/interop/hl7/observation"
    headers = {
        "X-API-Key": "TEST_SECRET_HL7",
        "Content-Type": "text/plain"
    }
    # Standard HL7 ORU^R01 message for Patient ID 1
    hl7_msg = (
        "MSH|^~\\&|SENDING_APP|SENDING_FACILITY|REC_APP|REC_FACILITY|20260711120000||ORU^R01|MSGID001|P|2.3|\n"
        "PID|1||1||Smith^John||19800101|M||\n"
        "OBR|1||||||||||||||||||||||||F\n"
        "OBX|1|NM|8867-4^Heart Rate^LN||125|bpm|||||F\n"
        "OBX|2|NM|2708-6^Oxygen Saturation^LN||91|%|||||F\n"
        "OBX|3|NM|8480-6^Systolic Blood Pressure^LN||145|mmHg|||||F\n"
        "OBX|4|NM|9279-1^Respiratory Rate^LN||26|bpm|||||F\n"
    )

    res = requests.post(url, headers=headers, data=hl7_msg)
    print(f"HL7 Ingestion status: {res.status_code}")
    assert res.status_code == 200
    data = res.json()
    print(f"Ingestion result payload: {data}")
    # Verify patient details and score recalculation
    assert data["id"] == 1
    assert data["status"] in ["SERIOUS", "CRITICAL"] # Recalculated due to high heart rate / resp rate / low SpO2
    assert data["criticality_score"] > 0
    print("HL7 ingestion test PASSED!\n")

def test_fhir_ingestion():
    print("Testing FHIR Observation JSON ingestion...")
    url = "http://127.0.0.1:8000/api/interop/hl7/observation"
    headers = {
        "Authorization": "Bearer TEST_SECRET_HL7",
        "Content-Type": "application/json"
    }
    # FHIR Observation payload for Patient ID 1
    fhir_payload = {
        "resourceType": "Observation",
        "status": "final",
        "subject": {
            "reference": "Patient/1"
        },
        "component": [
            {
                "code": {
                    "coding": [{"code": "8867-4", "display": "Heart Rate"}]
                },
                "valueQuantity": {"value": 82, "unit": "bpm"}
            },
            {
                "code": {
                    "coding": [{"code": "2708-6", "display": "SpO2"}]
                },
                "valueQuantity": {"value": 98, "unit": "%"}
            }
        ]
    }

    res = requests.post(url, headers=headers, json=fhir_payload)
    print(f"FHIR Ingestion status: {res.status_code}")
    assert res.status_code == 200
    data = res.json()
    print(f"FHIR Ingestion result payload: {data}")
    assert data["id"] == 1
    print("FHIR ingestion test PASSED!\n")

def test_sso_authentication():
    print("Testing OIDC SSO login flow and auto-provisioning...")
    # 1. Initiate login
    login_url = "http://127.0.0.1:8000/api/auth/sso/login"
    res = requests.get(login_url, allow_redirects=False)
    print(f"SSO Login Redirect status: {res.status_code}")
    assert res.status_code in [302, 307]
    redirect_location = res.headers.get("Location")
    print(f"Redirect location: {redirect_location}")
    assert "/api/auth/sso/callback" in redirect_location

    # 2. Trigger mock callback
    callback_url = "http://127.0.0.1:8000" + redirect_location
    session = requests.Session()
    callback_res = session.get(callback_url, allow_redirects=False)
    print(f"SSO Callback response status: {callback_res.status_code}")
    assert callback_res.status_code in [302, 307]
    
    # Check that auth token cookie is set
    assert "auth_token" in session.cookies.get_dict()
    
    # Validate target redirect is to frontend /login with token query param
    target_redirect = callback_res.headers.get("Location")
    print(f"Target frontend redirect: {target_redirect}")
    assert "/login?token=" in target_redirect
    
    # Extract token
    token = target_redirect.split("token=")[1]
    
    # 3. Retrieve profile using the created session cookie to verify user
    me_res = session.get("http://127.0.0.1:8000/api/auth/me")
    print(f"Profile status: {me_res.status_code}")
    assert me_res.status_code == 200
    profile_data = me_res.json()
    print(f"Provisioned user profile data: {profile_data}")
    assert profile_data["username"] == "sso_clinician"
    assert profile_data["email"] == "sso_clinician@hospitalai.com"
    assert profile_data["role"] == "DOCTOR"
    print("SSO authentication and auto-provisioning test PASSED!\n")

def main():
    # Setup test environment variables
    os.environ["SSO_MOCK"] = "true"
    os.environ["FRONTEND_URL"] = "http://localhost:3000"
    
    # Hydrate database
    print("Seeding test database...")
    subprocess.run([sys.executable, "seed.py"], check=True)

    print("Spawning FastAPI Uvicorn server...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"]
    )
    
    # Wait for server to bind using socket connection check
    import socket
    server_ready = False
    for _ in range(30):  # try for 15 seconds
        try:
            with socket.create_connection(("127.0.0.1", 8000), timeout=0.5):
                server_ready = True
                break
        except (ConnectionRefusedError, socket.timeout, OSError):
            time.sleep(0.5)
            
    if not server_ready:
        print("FastAPI server failed to start within timeout.")
        proc.kill()
        sys.exit(1)

    success = False
    try:
        test_interop_security()
        test_hl7_ingestion()
        test_fhir_ingestion()
        test_sso_authentication()
        success = True
        print("ALL INTEROP INTEGRATION TESTS PASSED successfully!")
    except Exception as e:
        print(f"INTEROP INTEGRATION TESTS FAILED: {e}")
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
