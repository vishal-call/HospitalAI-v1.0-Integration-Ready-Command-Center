import sys
import time
import subprocess
import requests
import asyncio
import websockets
import json

def test_health():
    print("Testing /health endpoint...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"Health response status: {response.status_code}")
        print(f"Health response JSON: {response.json()}")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        print("Health check PASSED!\n")
        return True
    except Exception as e:
        print(f"Health check FAILED: {e}\n")
        return False

async def test_websocket():
    print("Testing WebSocket /ws/dashboard...")
    uri = "ws://localhost:8000/ws/dashboard"
    try:
        async with websockets.connect(uri) as websocket:
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
    print("Starting FastAPI Uvicorn server in subprocess...")
    # Start uvicorn
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to bind and start
    time.sleep(3)
    
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
