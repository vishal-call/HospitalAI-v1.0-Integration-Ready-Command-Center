import sys
import time
import subprocess
import requests
import asyncio
import websockets
import json

def test_health():
    print("Testing /api/health endpoint...")
    try:
        response = requests.get("http://127.0.0.1:8000/api/health", timeout=5)
        print(f"Health response status: {response.status_code}")
        print(f"Health response JSON: {response.json()}")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        print("Health check PASSED!\n")
        return True
    except Exception as e:
        print(f"Health check FAILED: {e}\n")
        return False

async def test_websocket():
    print("Testing WebSocket /ws/dashboard...")
    uri = "ws://127.0.0.1:8000/ws/dashboard"
    try:
        # Log in first to get the auth_token cookie
        login_payload = {
            "email": "coord@hospitalai.com",
            "password": "password123"
        }
        res = requests.post("http://127.0.0.1:8000/api/auth/login", json=login_payload)
        auth_token = res.cookies.get("auth_token")
        
        headers = {}
        if auth_token:
            headers["Cookie"] = f"auth_token={auth_token}"
            
        async with websockets.connect(uri, additional_headers=headers) as websocket:
            # 1. Read initial state
            response = await websocket.recv()
            data = json.loads(response)
            print(f"Received initial state: {data}")
            assert data["type"] == "INITIAL_STATE"
            assert "icu_rate" in data["data"]
            
            # 2. Send ping command
            ping_msg = json.dumps({"command": "PING"})
            print(f"Sending: {ping_msg}")
            await websocket.send(ping_msg)
            
            # 3. Read pong response
            pong_response = await websocket.recv()
            pong_data = json.loads(pong_response)
            print(f"Received pong response: {pong_data}")
            assert pong_data["type"] == "PONG"
            
            # 4. Wait for a live occupancy broadcast
            print("Waiting for occupancy broadcast...")
            broadcast_resp = await websocket.recv()
            broadcast_data = json.loads(broadcast_resp)
            print(f"Received broadcast: {broadcast_data}")
            assert broadcast_data["type"] == "OCCUPANCY_METRICS"
            
            print("WebSocket test PASSED!\n")
            return True
    except Exception as e:
        print(f"WebSocket test FAILED: {e}\n")
        return False

def main():
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

    # Hydrate database with fresh seed data
    print("Hydrating database with fresh seed data...")
    subprocess.run([sys.executable, "seed.py"], env=env, check=True)

    print("Starting FastAPI Uvicorn server in subprocess...")
    # Start uvicorn without pipe redirection to prevent deadlock and with env passed
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        env=env,
        text=True
    )
    
    # Wait for server to bind and start
    time.sleep(6)
    
    success = False
    try:
        health_ok = test_health()
        if health_ok:
            ws_ok = asyncio.run(test_websocket())
            success = health_ok and ws_ok
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
        print("ALL TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()
