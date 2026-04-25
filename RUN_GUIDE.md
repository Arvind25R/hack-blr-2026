# DevOps Platform — Complete Run Guide

## Prerequisites

| Tool | Required Version | Install | Verify |
|------|-----------------|---------|--------|
| Python | 3.11+ | https://python.org | `python --version` |
| Docker | 20.10+ | https://docs.docker.com/get-docker/ | `docker --version` |
| docker-compose | 1.29+ | Bundled with Docker Desktop | `docker-compose --version` |
| Node.js | 22.x | https://nodejs.org | `node --version` |
| npm | 10.x | Bundled with Node.js | `npm --version` |
| ngrok | latest (optional) | https://ngrok.com/download | `ngrok version` |

> **Docker Desktop must be running** before starting services.

---

## Project Structure

```
HackBLR/
├── services/
│   ├── service-a/       (port 8001)
│   ├── service-b/       (port 8002)
│   ├── service-c/       (port 8003)
│   └── admin-service/   (port 8000)
├── frontend/            (port 5173)
├── infra/
├── seed_qdrant.py       (Qdrant runbook seeder)
├── seed_requirements.txt
├── docker-compose.yml
└── .env
```

---

## Step 0: Initial Setup (One-Time Only)

### 0a. Create virtual environments and install dependencies

```powershell
# Admin Service
cd C:\HackBLR\services\admin-service
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
deactivate

# Service A
cd C:\HackBLR\services\service-a
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
deactivate

# Service B
cd C:\HackBLR\services\service-b
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
deactivate

# Service C
cd C:\HackBLR\services\service-c
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
deactivate
```

### 0b. Install frontend dependencies

```powershell
cd C:\HackBLR\frontend
npm install
```

### 0c. Create `.env` file at project root

Create `C:\HackBLR\.env` with:

```env
SERVICE_A_URL=http://localhost:8001
SERVICE_B_URL=http://localhost:8002
SERVICE_C_URL=http://localhost:8003
ADMIN_SERVICE_URL=http://localhost:8000
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_URL=
QDRANT_API_KEY=
VAPI_API_KEY=
VAPI_PHONE_NUMBER=
NGROK_URL=
```

> See the `.env` file for detailed comments on each variable.

### 0d. Set up Qdrant (choose one)

#### Option 1: Local Docker (default)

```powershell
cd C:\HackBLR
docker-compose up qdrant -d
```

Verify:
```powershell
curl http://localhost:6333/healthz
```

Leave `QDRANT_URL` and `QDRANT_API_KEY` empty in `.env` — it will use `QDRANT_HOST:QDRANT_PORT` automatically.

#### Option 2: Qdrant Cloud

No local Docker needed for Qdrant. Get your credentials from [cloud.qdrant.io](https://cloud.qdrant.io):

1. Go to your cluster → **API Keys**
2. Copy the **Cluster URL** (e.g., `https://abc-123.cloud.qdrant.io`) and **API Key**
3. Set both in `.env`:

```env
QDRANT_URL=https://your-cluster-id.cloud.qdrant.io
QDRANT_API_KEY=your-api-key-here
```

When both are set, `QDRANT_HOST` and `QDRANT_PORT` are ignored.

### 0e. Seed Qdrant with runbooks (Optional but recommended)

This populates the vector database with 15 runbook entries for root cause analysis.
Works with **both** local Docker and Qdrant Cloud — it reads the same env vars.

```powershell
cd C:\HackBLR
pip install -r seed_requirements.txt
python seed_qdrant.py
```

> **Note:** First run downloads the `all-MiniLM-L6-v2` model (~80MB). Without seeding, Qdrant queries return no results and incidents get `action_type: none`.

---

## Option A: Run Locally (Without Docker for services)

### 1. Start All Backend Services (4 separate terminals)

```powershell
# Terminal 1 — Admin Service
cd C:\HackBLR\services\admin-service
.\venv\Scripts\activate
uvicorn app.main:app --port 8000 --reload
```

```powershell
# Terminal 2 — Service A
cd C:\HackBLR\services\service-a
.\venv\Scripts\activate
uvicorn app.main:app --port 8001 --reload
```

```powershell
# Terminal 3 — Service B
cd C:\HackBLR\services\service-b
.\venv\Scripts\activate
uvicorn app.main:app --port 8002 --reload
```

```powershell
# Terminal 4 — Service C
cd C:\HackBLR\services\service-c
.\venv\Scripts\activate
uvicorn app.main:app --port 8003 --reload
```

### 2. Start Frontend (Terminal 5)

```powershell
cd C:\HackBLR\frontend
npm run dev
```

### 3. Verify Everything

```powershell
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

Each should return:
```json
{"status": "healthy", "service": "<service-name>"}
```

Open **http://localhost:5173** in your browser.

> **Note:** When running locally (not via docker-compose), `infra/restart` and `infra/scale` will return `success: false` with "Container not found" since services aren't Docker containers. The approval flow still works — it just skips the infra action.

---

## Option B: Run Everything With Docker

```powershell
cd C:\HackBLR
docker-compose up --build
```

Then start the frontend separately:
```powershell
cd C:\HackBLR\frontend
npm run dev
```

Verify:
```powershell
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

Stop everything:
```powershell
docker-compose down
```

---

### 2. Start Frontend (Terminal 5)

```powershell
cd C:\HackBLR\frontend
npm run dev
```

### 3. Verify Everything

```powershell
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

Each should return:
```json
{"status": "healthy", "service": "<service-name>"}
```

Open **http://localhost:5173** in your browser.

> **Note:** When running locally (not via docker-compose), `infra/restart` and `infra/scale` will return `success: false` with "Container not found" since services aren't Docker containers. The approval flow still works — it just skips the infra action.

---

## Option B: Run Everything With Docker

```powershell
cd C:\HackBLR
docker-compose up --build
```

Then start the frontend separately:
```powershell
cd C:\HackBLR\frontend
npm run dev
```

Verify:
```powershell
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

Stop everything:
```powershell
docker-compose down
```

---
## API Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (all services) |
| `/process` | GET | Process request (service-a entry point) |
| `/logs/` | GET | Query logs (params: `service`, `trace_id`, `status`, `limit`) |
| `/incidents/` | GET | List incidents (params: `service`, `status`) |
| `/incidents/{id}` | GET | Get single incident |
| `/incidents/{id}/status` | PATCH | Update incident state |
| `/approval/approve/{id}` | POST | Approve + auto-remediate |
| `/approval/reject/{id}` | POST | Reject incident |
| `/approval/notify/{id}` | POST | Trigger Vapi voice call |
| `/infra/restart/{service}` | POST | Restart container |
| `/infra/scale/{service}` | POST | Scale replicas (param: `replicas`) |
| `/infra/status` | GET | All service statuses |
| `/qdrant/search` | GET | Search runbooks (param: `q`) |
| `/audit/` | GET | Audit trail (param: `incident_id`) |

---

## Demo Scenarios

### Scenario 1: Downstream Service Failure → Auto-Recovery

**What happens:** Service C fails → errors cascade through B and A → watchdog detects → Qdrant suggests restart → you approve → service recovers.

```powershell
# Step 1: Send 4 errors targeting service-c
1..4 | ForEach-Object { curl "http://localhost:8001/process?fail=error&fail_at=service-c" 2>$null }

# Step 2: Wait for watchdog to detect (polls every 10s)
Write-Host "Waiting 12s for watchdog detection..."
Start-Sleep 12

# Step 3: Check that an incident was created
curl http://localhost:8000/incidents/
# Look for: status=DETECTED or ANALYZED, service_name=service-c

# Step 4: Note the incident ID from the response, then approve it
# Replace <ID> with the actual incident ID number
curl -X POST http://localhost:8000/approval/approve/<ID>
# Response shows: status=RESOLVED, action_taken, action_result

# Step 5: Verify the full audit trail
curl "http://localhost:8000/audit/?incident_id=<ID>"
# Shows: approved → action:restart/none → resolved

# Step 6: Confirm service is working again
curl http://localhost:8001/process
# Should succeed normally
```

**Expected audit trail:**
1. `approved` by `fallback_api`
2. `action:restart` (if Docker) or `action:none` (if local)
3. `resolved` — incident closed

---
### Scenario 2: Latency Spike → Scaling

**What happens:** Service C responds slowly → watchdog detects latency spike → Qdrant suggests scaling → you approve.

```powershell
# Step 1: Send 4 high-latency requests targeting service-c
1..4 | ForEach-Object { curl "http://localhost:8001/process?fail=high_latency&fail_at=service-c" 2>$null }

# Step 2: Wait for watchdog
Write-Host "Waiting 12s for watchdog detection..."
Start-Sleep 12

# Step 3: Check for latency incident
curl "http://localhost:8000/incidents/?status=DETECTED"

# Step 4: Approve the incident (replace <ID>)
curl -X POST http://localhost:8000/approval/approve/<ID>

# Step 5: Check audit trail
curl "http://localhost:8000/audit/?incident_id=<ID>"
```

**Expected:** Incident with "latency spike" → Qdrant suggests "scale" → approve → scale action executed.

---

### Scenario 3: Non-Infra Error → No Auto-Fix

**What happens:** Service A itself fails (not a downstream/infra issue) → watchdog detects → Qdrant suggests "contact dev team" → no infra action taken.

```powershell
# Step 1: Send 4 errors at service-a (no fail_at, so A fails directly)
1..4 | ForEach-Object { curl "http://localhost:8001/process?fail=error" 2>$null }

# Step 2: Wait for watchdog
Write-Host "Waiting 12s for watchdog detection..."
Start-Sleep 12

# Step 3: Check incident
curl http://localhost:8000/incidents/

# Step 4: Approve — action will be "none"
curl -X POST http://localhost:8000/approval/approve/<ID>
# Response: action_taken=none, no restart/scale performed

# Step 5: Verify audit
curl "http://localhost:8000/audit/?incident_id=<ID>"
```

**Expected:** Incident resolved with `action_type: none` — system correctly identifies this isn't an infra problem.

---

### Scenario 4: Reject an Incident

```powershell
# After an incident is created (from any scenario above):
curl -X POST "http://localhost:8000/approval/reject/<ID>?reason=False+positive"

# Check incident status
curl http://localhost:8000/incidents/<ID>
# status should be REJECTED
```

---

## UI Demo Walkthrough

1. Open **http://localhost:5173**
2. Observe 3 service cards showing live status (green = healthy)
3. Click **"💥 Burst 4 Errors (C)"** in the Action Panel
4. Watch the **Logs table** update with error entries (polls every 4s)
5. Wait ~12 seconds — a new incident appears in the **Incidents** section
6. Click **"✅ Approve"** on the incident
7. Watch the incident transition: APPROVED → ACTION_TAKEN → RESOLVED
8. Click **"🚀 Send Normal Request"** to verify the system still works
9. Check the **Audit Trail** section for the full action history

---

## Additional API Examples

### Logs

```powershell
# All logs
curl http://localhost:8000/logs/

# Filter by service
curl "http://localhost:8000/logs/?service=service-c"

# Filter by status
curl "http://localhost:8000/logs/?status=ERROR"

# Filter by trace ID
curl "http://localhost:8000/logs/?trace_id=<TRACE_ID>"

# Limit results
curl "http://localhost:8000/logs/?limit=10"
```
### Infra Control

```powershell
# Restart a service (Docker only)
curl -X POST http://localhost:8000/infra/restart/service-c

# Scale a service to 3 replicas (Docker only)
curl -X POST "http://localhost:8000/infra/scale/service-c?replicas=3"

# Check all service statuses
curl http://localhost:8000/infra/status

# Check single service
curl http://localhost:8000/infra/status/service-c
```

### Qdrant Search

```powershell
# Search runbooks
curl "http://localhost:8000/qdrant/search?q=service+c+is+down"

# Query with POST
curl -X POST http://localhost:8000/qdrant/query -H "Content-Type: application/json" -d "{\"query\": \"high latency on service c\"}"
```

### Manual Incident State Transition

```powershell
curl -X PATCH http://localhost:8000/incidents/1/status -H "Content-Type: application/json" -d "{\"status\":\"ANALYZED\"}"
```

---

## Exposing via ngrok (for Vapi Voice Integration)

```powershell
# 1. Start ngrok tunnel to admin service
ngrok http 8000

# 2. Copy the HTTPS URL from ngrok output (e.g., https://abc123.ngrok.io)

# 3. Update .env:
#    NGROK_URL=https://abc123.ngrok.io
#    VAPI_API_KEY=your-vapi-api-key
#    VAPI_PHONE_NUMBER=+1234567890

# 4. Restart admin service to pick up new env vars

# 5. Test external access
curl https://abc123.ngrok.io/health
```

Vapi will use `POST https://<ngrok-url>/approval/vapi-webhook` for callbacks.

---

## Shutting Down

### If running locally (Option A)

Press `Ctrl+C` in each of the 5 terminal windows (admin, service-a, service-b, service-c, frontend). That's safe — uvicorn and Vite handle `Ctrl+C` gracefully.

If any process doesn't stop, force-kill all at once:

```powershell
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Stop-Process -Name node -Force -ErrorAction SilentlyContinue
```

### If running via Docker (Option B)

```powershell
cd C:\HackBLR
docker-compose down
```

This stops and removes all containers and the network. Add `-v` to also delete volumes (Qdrant data, admin DB):

```powershell
docker-compose down -v
```

If the frontend is running separately, press `Ctrl+C` in its terminal or:

```powershell
Stop-Process -Name node -Force -ErrorAction SilentlyContinue
```

### Verify everything is stopped

```powershell
# Check no Python/Node processes remain
Get-Process -Name python, node -ErrorAction SilentlyContinue

# Check no Docker containers remain
docker ps --filter "name=service-" --filter "name=admin-" --filter "name=qdrant"
```

Both commands should return empty output.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Port already in use | `Stop-Process -Name python -ErrorAction SilentlyContinue` or change port |
| Docker not running | Start Docker Desktop first |
| venv not found | `cd <service-dir>; python -m venv venv` |
| Dependencies missing | `.\venv\Scripts\activate; pip install -r requirements.txt` |
| Qdrant not responding | Local: `docker-compose up qdrant -d`. Cloud: check `QDRANT_URL` and `QDRANT_API_KEY` in `.env` |
| Qdrant not seeded | `cd C:\HackBLR; python seed_qdrant.py` (incidents will show action_type: none without this) |
| Frontend can't reach API | Ensure admin service is running on port 8000 (Vite proxies to it) |
| Infra restart fails | Expected when running locally — services must be Docker containers |
| Watchdog not detecting | Check logs exist: `curl http://localhost:8000/logs/` — need ≥4 errors in 30s window |
| curl returns HTML | Use `curl.exe` instead of `curl` (PowerShell alias conflict) |
