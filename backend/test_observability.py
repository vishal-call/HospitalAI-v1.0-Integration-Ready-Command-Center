import sys
import os
import time
import subprocess
import requests
import threading

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

def test_observability_pipeline():
    print("Starting Observability, Audit Logs, and Scenario Trigger test...")
    
    # 1. Login with Nurse (non-Admin) credentials
    print("\n--- TEST 1: Verify RBAC Denials for Nurse ---")
    nurse_payload = {
        "email": "nurse@hospitalai.com",
        "password": "password123"
    }
    nurse_session = requests.Session()
    login_resp = nurse_session.post("http://localhost:8000/api/auth/login", json=nurse_payload)
    assert login_resp.status_code == 200
    print("Nurse login successful.")

    # 1a. Attempt to get audit logs
    audit_resp = nurse_session.get("http://localhost:8000/api/audit-logs")
    print(f"Nurse audit log request status: {audit_resp.status_code}")
    assert audit_resp.status_code == 403
    print("PASSED: Nurse forbidden from retrieving audit logs.")

    # 1b. Attempt to get health metrics
    metrics_resp = nurse_session.get("http://localhost:8000/api/health/metrics")
    print(f"Nurse health metrics request status: {metrics_resp.status_code}")
    assert metrics_resp.status_code == 403
    print("PASSED: Nurse forbidden from retrieving health metrics.")

    # 1c. Attempt to trigger a scenario
    trigger_resp = nurse_session.post(
        "http://localhost:8000/api/scenarios/trigger",
        json={"scenario": "spawn_critical_emergency"}
    )
    print(f"Nurse scenario trigger request status: {trigger_resp.status_code}")
    assert trigger_resp.status_code == 403
    print("PASSED: Nurse forbidden from triggering scenarios.")

    # 2. Login with Admin credentials
    print("\n--- TEST 2: Verify Administrative Access ---")
    admin_payload = {
        "email": "admin@hospitalai.com",
        "password": "password123"
    }
    admin_session = requests.Session()
    login_resp = admin_session.post("http://localhost:8000/api/auth/login", json=admin_payload)
    assert login_resp.status_code == 200
    print("Admin login successful.")

    # 2a. Query Health Metrics
    metrics_resp = admin_session.get("http://localhost:8000/api/health/metrics")
    print(f"Admin health metrics request status: {metrics_resp.status_code}")
    assert metrics_resp.status_code == 200
    metrics_data = metrics_resp.json()
    print(f"Metrics response data: {metrics_data}")
    assert "active_websocket_clients" in metrics_data
    assert "recent_transaction_retries" in metrics_data
    assert "db_pool_size" in metrics_data
    print("PASSED: Admin successfully fetched platform health metrics.")

    # 2b. Query Audit Logs
    audit_resp = admin_session.get("http://localhost:8000/api/audit-logs")
    print(f"Admin audit logs request status: {audit_resp.status_code}")
    assert audit_resp.status_code == 200
    initial_logs = audit_resp.json()
    print(f"Initial audit logs count: {len(initial_logs)}")
    print("PASSED: Admin successfully fetched audit logs.")

    # 3. Trigger Critical Emergency Scenario with a custom correlation trace ID
    print("\n--- TEST 3: Trigger Scenario and Verify Trace correlation ---")
    custom_trace_id = "12345678-1234-5678-1234-567812345678"
    headers = {"X-Correlation-ID": custom_trace_id}
    
    scenario_resp = admin_session.post(
        "http://localhost:8000/api/scenarios/trigger",
        json={"scenario": "spawn_critical_emergency"},
        headers=headers
    )
    print(f"Scenario trigger response status: {scenario_resp.status_code}")
    assert scenario_resp.status_code == 200
    trigger_data = scenario_resp.json()
    print(f"Trigger response message: {trigger_data['message']}")
    assert "Spawned critical emergency patient" in trigger_data["message"]

    # 4. Verify that a corresponding ADMIT audit log exists with the custom correlation ID
    print("\n--- TEST 4: Query Audit log for trace matching ---")
    audit_resp = admin_session.get("http://localhost:8000/api/audit-logs", params={"correlation_id": custom_trace_id})
    assert audit_resp.status_code == 200
    filtered_logs = audit_resp.json()
    print(f"Logs matching correlation ID '{custom_trace_id}': {len(filtered_logs)}")
    
    # Assert we have logged the admission audit trail correctly
    assert len(filtered_logs) > 0
    admit_log = next(log for log in filtered_logs if log["action"] == "ADMIT")
    assert admit_log["entity_type"] == "patient"
    assert admit_log["user_id"] == "admin"
    assert admit_log["correlation_id"] == custom_trace_id
    assert admit_log["after_data"] is not None
    print(f"Verified Audit Log Record: {admit_log}")
    print("PASSED: Audit log record verified with custom correlation trace ID, entity type, and user context.")
    
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
    
    # Reset database state by running seed.py
    print("Hydrating database with fresh seed data...")
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
        success = test_observability_pipeline()
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
        print("\nALL OBSERVABILITY AND AUDIT VERIFICATION TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("\nOBSERVABILITY VERIFICATION TESTS FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()
