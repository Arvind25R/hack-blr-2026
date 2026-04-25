# DevOps Incident Detection & Auto-Remediation Platform — Plan & Checklist

## Overview

Build a multi-service platform with 3 microservices (A→B→C), an admin service (watchdog, incidents, infra control), Qdrant for runbook lookup, Vapi for voice approval, and a React dashboard — all orchestrated via Docker.

---

## Pre-requisites — ✅ DONE

| Requirement | Version | Status |
|-------------|---------|--------|
| Python | 3.11.0 | ✅ |
| Docker | 20.10.17 | ✅ Running |
| docker-compose | 1.29.2 | ✅ |
| Node.js | 22.18.0 | ✅ |
| npm | 10.9.3 | ✅ |
| Git | 2.37.3 | ✅ |

---

## Project Setup — ✅ DONE

- [x] Monorepo folder structure created (`services/service-a`, `service-b`, `service-c`, `admin-service`, `frontend/`, `infra/`)
- [x] Each Python service has `app/` with `routers/`, `models/`, `services/`, `utils/` + `__init__.py` files
- [x] Per-service virtual environments created and dependencies installed
- [x] `requirements.txt` per service (service-a/b/c: fastapi, uvicorn, httpx, python-dotenv; admin: + sqlalchemy, aiosqlite, qdrant-client, docker)
- [x] `.env` at root with service URLs, Qdrant, Vapi, ngrok config
- [x] `.gitignore` at root

---

## Requirements Checklist

### Step 1 — Scaffold & Base Apps ✅ DONE
- [x] Base `app/main.py` for service-a (port 8001)
- [x] Base `app/main.py` for service-b (port 8002)
- [x] Base `app/main.py` for service-c (port 8003)
- [x] Base `app/main.py` for admin-service (port 8000)
- [x] Health check `/health` endpoint on each
- [x] `Dockerfile` per service
- [x] `docker-compose.yml` at root with all services + Qdrant
- [x] Verified all 4 services start and respond locally

### Step 2 — Service Communication & Failure Simulation ✅ DONE
- [x] `/process` endpoint on each service
- [x] A calls B, B calls C via httpx
- [x] `traceId` generated at entry (Service A), propagated via `X-Trace-Id` header
- [x] `fail=timeout|error|high_latency` query param + `fail_at=service-a|b|c` targeting
- [x] Failures propagate upstream correctly with cascading error messages

### Step 3 — Logging & DB Schema ✅ DONE
- [x] Structured JSON logging in all services (traceId, service name, timestamp, status, error type)
- [x] Admin service SQLite schema: `logs`, `incidents`, `audit_logs`, `service_user_mapping`, `service_state`
- [x] Admin API: `POST /logs/` to ingest logs, `GET /logs/` to fetch (with filters: service, trace_id, status, limit)
- [x] All services send logs to admin service on each request (success, error, latency)

### Step 4 — Watchdog & Incident Detection ✅ DONE
- [x] Watchdog background task polling logs DB every 10s
- [x] Sliding window detection (last 30s)
- [x] Detect: high error rate (≥50%), service down (all errors + connection/timeout), latency spikes (≥4000ms avg or ≥2 LATENCY logs)
- [x] Create incident record on detection (skips if active incident exists for service)
- [x] Incident lifecycle states: DETECTED → ANALYZED → USER_NOTIFIED → APPROVED → ACTION_TAKEN → RESOLVED / REJECTED
- [x] State transitions via PATCH /incidents/{id}/status with timestamps
- [x] Incidents API: GET /incidents/, GET /incidents/{id}, PATCH /incidents/{id}/status

### Step 5 — Qdrant Integration ✅ DONE
- [x] Qdrant container in docker-compose (port 6333)
- [x] Standalone `seed_qdrant.py` with 15 runbook entries (sentence-transformers, all-MiniLM-L6-v2)
- [x] `seed_requirements.txt` for seed script deps
- [x] Admin `qdrant_service.py` — query with same embedding model
- [x] Admin router: `POST /qdrant/query`, `GET /qdrant/search?q=...`
- [x] Watchdog auto-queries Qdrant on incident → attaches solution → transitions to ANALYZED


### Step 6 — Infra Controller ✅ DONE
- [x] `InfraController` abstract interface (`restart_service`, `scale_service`, `get_status`, `get_all_statuses`)
- [x] `DockerController` implementation using Docker SDK
- [x] `KubernetesController` placeholder (interface only, raises NotImplementedError)
- [x] No Docker commands outside this abstraction layer
- [x] Admin API: `POST /infra/restart/{service}`, `POST /infra/scale/{service}?replicas=N`, `GET /infra/status/{service}`, `GET /infra/status`
- [x] Actions update `service_state` table
- [x] Audit logs generated for every action (restart/scale) with success/failure details

### Step 7 — Vapi Integration ✅ DONE
- [x] Vapi service: triggers voice call with incident details (service, error, solution)
- [x] Graceful fallback when Vapi not configured (VAPI_API_KEY missing)
- [x] Fallback `POST /approval/approve/{incident_id}` — approves + executes remediation
- [x] Fallback `POST /approval/reject/{incident_id}` — rejects incident
- [x] `POST /approval/notify/{incident_id}` — triggers Vapi call, transitions to USER_NOTIFIED
- [x] `POST /approval/vapi-webhook` — webhook endpoint for Vapi callbacks
- [x] On approval: extracts action_type from solution → calls InfraController → audit logged
- [x] Full lifecycle verified: DETECTED → APPROVED → ACTION_TAKEN → RESOLVED / REJECTED

### Step 8 — React Frontend ✅ DONE
- [x] Vite + Tailwind CSS project in `frontend/` (port 5173)
- [x] 3 service status boxes (green/red based on live infra status polling)
- [x] Traffic metrics display (total, success, errors, latency, avg duration, error rate)
- [x] Incident timeline view with approve/reject buttons
- [x] Logs viewer table (time, service, status, error, duration, traceId)
- [x] Action panel: send normal request, burst errors, burst latency, restart/scale per service
- [x] ServiceCard: simulate error/timeout/high_latency per service
- [x] All data from real API polling (5s intervals, no fake data)
- [x] Vite proxy: `/api` → admin:8000, `/service-a` → service-a:8001

### Step 9 — Final Integration & Testing ✅ DONE
- [x] Audit logs API: `GET /audit/` with optional `incident_id` filter
- [x] End-to-end scenario 1: C fails → cascade → watchdog → Qdrant → approve → restart → recover
- [x] End-to-end scenario 2: Latency spike → detect → suggest scaling → scale → stabilize
- [x] End-to-end scenario 3: Logic error → no infra action → suggest dev contact → unresolved
- [x] Audit trail complete for all actions
- [x] curl commands and demo instructions in RUN_GUIDE.md

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy, httpx |
| Database | SQLite (admin service) |
| Vector DB | Qdrant (Docker container) |
| Frontend | React (Vite), Tailwind CSS, Node.js 22.18.0 |
| Infra | Docker, docker-compose |
| External | ngrok, Vapi |

---

## ngrok Compatibility

All admin service APIs are fully ngrok-compatible:

```powershell
# Expose admin service
ngrok http 8000

# Then set in .env:
# NGROK_URL=https://your-subdomain.ngrok.io
```

Key endpoint for Vapi callbacks:
```
POST https://<ngrok-url>/approval/vapi-webhook
```

- ✅ CORS open (`allow_origins=["*"]`)
- ✅ No auth middleware blocking external calls
- ✅ All endpoints are standard HTTP REST (no WebSocket required)
- ✅ `NGROK_URL` env var wired into `vapi_service.py` as Vapi `serverUrl`
- ✅ JSON request/response on all endpoints

---

## Service Ports

| Service | Port |
|---------|------|
| admin-service | 8000 |
| service-a | 8001 |
| service-b | 8002 |
| service-c | 8003 |
| Qdrant | 6333 |
| Frontend | 5173 |

---

## Architecture

```
User / UI (React :5173)
    │
    ▼
Service A (:8001) ──► Service B (:8002) ──► Service C (:8003)
    │                       │                      │
    └───────────────────────┴──────────────────────┘
                            │
                    Logs → Admin Service (:8000)
                            │
                ┌───────────┼───────────┐
                ▼           ▼           ▼
           Watchdog    Qdrant(:6333)   Vapi
                │           │           │
                └───────────┴───────────┘
                            │
                    InfraController
                    (DockerController)
```