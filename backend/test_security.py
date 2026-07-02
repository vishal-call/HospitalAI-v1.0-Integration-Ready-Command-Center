import sys
import os
import time
import subprocess
import requests
import asyncio
import threading
import websockets
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

def test_security_and_rbac_flow():
    print("Starting Security and Role-Based Access Control (RBAC) test...")
    
    # 1. Test Login with invalid credentials
    print("\n--- TEST 1: Login with invalid credentials ---")
    login_payload = {
        "email": "coord@hospitalai.com",
        "password": "wrong_password"
    }
    login_resp = requests.post("http://localhost:8000/api/auth/login", json=login_payload)
    print(f"Invalid Login Status: {login_resp.status_code}")
    assert login_resp.status_code == 401
    assert "Incorrect email or password" in login_resp.text
    print("PASSED: Invalid login rejected with 401.")

    # 2. Test Login with Coordinator credentials
    print("\n--- TEST 2: Login with Coordinator credentials ---")
    login_payload = {
        "email": "coord@hospitalai.com",
        "password": "password123"
    }
    coord_session = requests.Session()
    login_resp = coord_session.post("http://localhost:8000/api/auth/login", json=login_payload)
    print(f"Coordinator Login Status: {login_resp.status_code}")
    assert login_resp.status_code == 200
    coord_data = login_resp.json()
    assert coord_data["username"] == "coordinator"
    assert coord_data["role"] == "COORDINATOR"
    
    # Verify HttpOnly Cookie is set
    cookies = coord_session.cookies.get_dict()
    assert "auth_token" in cookies
    coord_token = cookies["auth_token"]
    print("PASSED: Coordinator logged in successfully and auth_token cookie was set.")

    # 3. Test Profile Retrieval (GET /api/auth/me) for Coordinator
    print("\n--- TEST 3: Retrieve profile (/api/auth/me) with cookie ---")
    me_resp = coord_session.get("http://localhost:8000/api/auth/me")
    print(f"Profile Retrieval Status: {me_resp.status_code}")
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["username"] == "coordinator"
    assert me_data["role"] == "COORDINATOR"
    print("PASSED: Profile retrieved successfully using HttpOnly cookie.")

    # 4. Test Login with Nurse credentials
    print("\n--- TEST 4: Login with Nurse credentials ---")
    nurse_payload = {
        "email": "nurse@hospitalai.com",
        "password": "password123"
    }
    nurse_session = requests.Session()
    login_resp = nurse_session.post("http://localhost:8000/api/auth/login", json=nurse_payload)
    print(f"Nurse Login Status: {login_resp.status_code}")
    assert login_resp.status_code == 200
    nurse_data = login_resp.json()
    assert nurse_data["username"] == "nurse"
    assert nurse_data["role"] == "NURSE"
    nurse_token = nurse_session.cookies.get_dict()["auth_token"]
    print("PASSED: Nurse logged in successfully.")

    # 5. Test protected Action Center overrides (RBAC checks)
    print("\n--- TEST 5: Verify RBAC constraints on action recommendation ---")
    
    # 5a. Unauthenticated access (expect 401)
    unauth_resp = requests.post("http://localhost:8000/api/recommendations/1/action", json={"action": "APPROVE"})
    print(f"Unauthenticated Overrides Status: {unauth_resp.status_code}")
    assert unauth_resp.status_code == 401
    print("PASSED: Unauthenticated access rejected with 401.")

    # 5b. Nurse access (expect 403 Forbidden - MANDATE TEST)
    nurse_action_resp = nurse_session.post("http://localhost:8000/api/recommendations/1/action", json={"action": "APPROVE"})
    print(f"Nurse (Unauthorized) Overrides Status: {nurse_action_resp.status_code}")
    assert nurse_action_resp.status_code == 403
    assert "Insufficient permissions" in nurse_action_resp.text
    print("PASSED: Nurse role was successfully forbidden (403) from approving recommendations.")

    # 5c. Coordinator access (expect 200 OK)
    # First, let's trigger a recommendation by logging vitals
    print("Simulating patient vitals trigger for recommendation...")
    vitals_payload = {
        "heart_rate": 135,
        "resp_rate": 32,
        "spo2": 90
    }
    vitals_resp = coord_session.post("http://localhost:8000/api/patients/1/vitals", json=vitals_payload)
    assert vitals_resp.status_code == 200
    
    recs_resp = coord_session.get("http://localhost:8000/api/recommendations/pending")
    assert recs_resp.status_code == 200
    pending_recs = recs_resp.json()
    rec_to_action = next((r for r in pending_recs if r["patient_id"] == 1), None)
    assert rec_to_action is not None
    
    coord_action_resp = coord_session.post(
        f"http://localhost:8000/api/recommendations/{rec_to_action['id']}/action",
        json={"action": "APPROVE"}
    )
    print(f"Coordinator (Authorized) Overrides Status: {coord_action_resp.status_code}")
    assert coord_action_resp.status_code == 200
    print("PASSED: Coordinator successfully approved recommendation.")

    # 6. Test WebSocket Handshake upgrade security
    print("\n--- TEST 6: Verify WebSocket handshake security ---")
    
    async def test_ws_unauth():
        try:
            async with websockets.connect("ws://localhost:8000/ws/dashboard") as ws:
                # Should close immediately
                await ws.recv()
                assert False, "Should have been closed."
        except Exception as e:
            # Rejections in newer websockets raise InvalidStatus
            status_code = getattr(e, "status_code", None)
            if status_code is None and hasattr(e, "response"):
                status_code = getattr(e.response, "status_code", None)
            print(f"Unauthenticated WebSocket connection upgrade rejected: {e} (Status: {status_code})")
            assert status_code in [401, 403] or "rejected" in str(e).lower()
            
    async def test_ws_auth(token):
        headers = {"Cookie": f"auth_token={token}"}
        async with websockets.connect("ws://localhost:8000/ws/dashboard", additional_headers=headers) as ws:
            # Should receive initial state
            msg = await ws.recv()
            print("Authenticated WebSocket received initial state!")
            assert "INITIAL_STATE" in msg
            
    print("Testing unauthenticated WebSocket connection...")
    asyncio.run(test_ws_unauth())
    print("Testing authenticated WebSocket connection...")
    asyncio.run(test_ws_auth(coord_token))
    print("PASSED: WebSocket upgrade handshake successfully authenticated.")
    
    # 7. Test Logout
    print("\n--- TEST 7: Logout staff session ---")
    logout_resp = coord_session.post("http://localhost:8000/api/auth/logout")
    print(f"Logout Status: {logout_resp.status_code}")
    assert logout_resp.status_code == 200
    
    # Verify cookie is cleared (max-age=0/expires/deleted)
    me_resp_after = coord_session.get("http://localhost:8000/api/auth/me")
    print(f"Profile Retrieval Status After Logout: {me_resp_after.status_code}")
    assert me_resp_after.status_code == 401
    print("PASSED: Cookie successfully cleared and profile access blocked.")

    return True

def main():
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
    
    # Reset database state by running seed.py (hashes passwords)
    print("Hydrating database with fresh secure seed data...")
    subprocess.run([sys.executable, "seed.py"], env=env, check=True)
    
    # Start FastAPI Uvicorn server in subprocess
    print("Starting FastAPI Uvicorn server...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--port", "8000"],
        env=env,
        text=True
    )
    
    # Wait for Uvicorn to bind
    time.sleep(10)
    
    success = False
    try:
        success = test_security_and_rbac_flow()
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
        print("\nALL SECURITY AND RBAC VERIFICATION TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("\nSECURITY AND RBAC VERIFICATION TESTS FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()
