# HospitalAI Operations Command Center

This is a Human-in-the-Loop Operational Resource Management Platform designed for hospital capacity management, patient triage, and inter-hospital transfers.

## Architecture
- **Database:** PostgreSQL (Running inside WSL/Ubuntu)
- **Backend:** Python / FastAPI (Running on Windows Host via Python venv)
- **Frontend:** Next.js / React (Running on Windows Host via Node.js)

## How to Start the Project Locally

Because the database is hosted inside WSL (Windows Subsystem for Linux), you need to start the database service first to prevent connectivity issues.

### Step 1: Start the Database (WSL)
Open a terminal (PowerShell) and start the PostgreSQL service. To ensure the WSL virtual machine does not suspend itself due to inactivity, we run a sleep command to keep it alive:
```powershell
wsl -u root service postgresql start; wsl sleep infinity
```
*(Leave this terminal window open in the background)*

### Step 2: Start the Backend (FastAPI)
Open a new terminal (PowerShell), navigate to the `backend` directory, activate the Python virtual environment, and start the Uvicorn server:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload
```
*(Leave this terminal window open in the background. The backend will run on `http://127.0.0.1:8000`)*

### Step 3: Start the Frontend (Next.js)
Open a new terminal (PowerShell), navigate to the `frontend` directory, and start the development server:
```powershell
cd frontend
npm run dev
```
*(Leave this terminal window open. The frontend will run on `http://localhost:3000`)*

## Accessing the Application
Once all three steps are running, open your browser and navigate to:
**http://localhost:3000**

You can log in using the seed accounts:
- **Coordinator:** `coord@hospitalai.com` / `password123`
- **Doctor:** `doctor@hospitalai.com` / `password123`
- **Nurse:** `nurse@hospitalai.com` / `password123`
- **Admin:** `admin@hospitalai.com` / `password123`
## Troubleshooting
- **Database Connection Refused:** Ensure Step 1 is running. If WSL shuts down, the Windows backend cannot connect to `127.0.0.1:5432`.
- **WebSocket Errors:** The frontend dynamically targets your IP to connect to the backend's WebSocket. Ensure the backend is running without errors.
