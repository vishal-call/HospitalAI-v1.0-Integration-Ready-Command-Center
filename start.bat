@echo off
echo ===================================================
echo       Starting HospitalAI Command Center
echo ===================================================

echo.
echo [1/3] Starting PostgreSQL database in WSL...
wsl -u root service postgresql start

echo.
echo [2/3] Starting Backend (FastAPI)...
cd backend
start "HospitalAI Backend" cmd /c ".\venv\Scripts\activate.bat && python -m uvicorn main:app --reload"
cd ..

echo.
echo [3/3] Starting Frontend (Next.js)...
cd frontend
start "HospitalAI Frontend" cmd /c "npm run dev"
cd ..

echo.
echo ===================================================
echo All services have been started in separate windows!
echo Once the frontend finishes compiling, open your browser:
echo http://localhost:3000
echo ===================================================
echo.
pause
