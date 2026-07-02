# HospitalAI - Production Deployment Guide

This guide details how to build, seed, and run the HospitalAI platform in production.

---

## 1. Prerequisites
Ensure the target server has the following tools installed:
* **Docker** (v24.0.0 or later)
* **Docker Compose** (v2.20.0 or later)

---

## 2. Running the Containerized Production Stack
The unified Docker Compose configuration builds multi-stage production images and manages database persistence.

1. **Spin Up Services**:
   From the project root directory, execute:
   ```bash
   docker compose -f docker-compose.prod.yml up --build -d
   ```
   *This command compiles the Next.js standalone frontend, packages the FastAPI backend using a Python slim image, and mounts a persistent volume for the PostgreSQL container.*

2. **Verify Services**:
   Check that all services are online:
   ```bash
   docker compose -f docker-compose.prod.yml ps
   ```

---

## 3. Database Hydration & Seeding
If you are running the project in a development/WSL environment or initializing database schemas:

1. **Activate Virtual Environment**:
   ```bash
   cd backend
   python -m venv venv
   .\venv\Scripts\activate   # Windows
   source venv/bin/activate  # Linux/WSL
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Execute Database Seeder**:
   Run the seeding script to drop existing tables, construct schemas dynamically, and insert default user credentials:
   ```bash
   python seed.py
   ```

---

## 4. Run Verification Integration Tests
The backend contains automated integration verification tests:
* Run security checks: `python test_security.py`
* Run alerts checks: `python test_alerts.py`
* Run human-in-the-loop checks: `python test_hitl.py`
* Run observability checks: `python test_observability.py`
* Run inter-hospital transfer checks: `python test_inter_hospital.py`
