@echo off
echo ===================================================
echo       Starting HospitalAI Command Center
echo ===================================================

echo.
echo [1/4] Starting PostgreSQL database in WSL...
wsl -u root service postgresql start

echo.
echo [2/4] Starting Database Proxy...
start "HospitalAI DB Proxy" cmd /k "cd backend && .\venv\Scripts\python.exe proxy.py"

echo.
echo [3/4] Starting Backend (FastAPI)...
start "HospitalAI Backend" cmd /k "cd backend && .\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000"

echo.
echo [4/4] Starting Frontend (Next.js)...
start "HospitalAI Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ===================================================
echo All services have been started in separate windows!
echo Once the frontend finishes compiling, open your browser:
echo http://localhost:3000
echo ===================================================
echo.
pause
