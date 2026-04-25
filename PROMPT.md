# PROMPT.md — Complete Project Blueprint

> **Purpose:** This document contains every detail needed to understand, rebuild, or extend this project from scratch. It serves as both a comprehensive specification and an implementation guide with all code, architecture decisions, and configuration.

---

## 1. Project Vision

Build an **AI-powered DevOps incident detection and auto-remediation platform** that:

1. Runs 3 microservices in a chain (A → B → C) with realistic failure simulation
2. Automatically detects anomalies via a watchdog analyzing structured logs
3. Identifies root causes using RAG (Retrieval-Augmented Generation) via Qdrant vector DB
4. Notifies operators via Vapi voice calls (with REST fallback)
5. Executes approved infrastructure actions (restart/scale) via an abstracted controller
6. Provides a real-time React dashboard for monitoring and control
7. Maintains a complete audit trail of every action

---

## 2. Architecture

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

### Data Flow

1. **Request flow:** User → Service A → Service B → Service C → response bubbles back
2. **Log flow:** Each service sends structured JSON log to `POST /logs/` on admin service after every request
3. **Detection flow:** Watchdog (background task in admin) polls logs DB every 10s, applies sliding window detection rules
4. **Analysis flow:** On incident detection → query Qdrant with error description → get root cause + action type
5. **Approval flow:** Notify operator (Vapi voice call or dashboard) → operator approves → InfraController executes action
6. **Audit flow:** Every state transition, approval, and action is recorded in `audit_logs` table

---

## 3. Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Backend | Python | 3.11 | All 4 services |
| Framework | FastAPI | 0.104.1 | REST APIs with automatic OpenAPI docs |
| HTTP Client | httpx | 0.25.2 | Async service-to-service calls |
| ORM | SQLAlchemy | 2.0.23 | Database models and queries |
| Async DB | aiosqlite | 0.19.0 | SQLite async support |
| Database | SQLite | built-in | Admin service persistent storage |
| Vector DB | Qdrant | latest (Docker) | Runbook semantic search |
| Embeddings | sentence-transformers | ≥2.6.0 | all-MiniLM-L6-v2 model (384-dim) |
| Docker SDK | docker | 6.1.3 | Container management via Python |
| Frontend | React (Vite) | 19.x | Dashboard SPA |
| CSS | Tailwind CSS | 4.x | Utility-first styling (via @tailwindcss/vite) |
| Voice | Vapi | API | Voice-based incident approval |
| Tunnel | ngrok | latest | Expose local APIs for Vapi callbacks |
| Config | python-dotenv | 1.0.0 | Environment variable management |

---

## 4. Project Structure

```
root/
├── .env                              # Environment variables
├── .gitignore
├── docker-compose.yml                # All services + Qdrant orchestration
├── seed_qdrant.py                    # Standalone Qdrant seeder (15 runbooks)
├── seed_requirements.txt             # qdrant-client, sentence-transformers
├── PLAN.md / DETAILS.md / RUN_GUIDE.md / HIGH_LEVEL_IDEA.md / PROMPT.md
│
├── services/
│   ├── admin-service/                # Port 8000 — Central orchestrator
│   │   ├── Dockerfile
│   │   ├── requirements.txt          # fastapi, uvicorn, httpx, python-dotenv,
│   │   │                             # sqlalchemy, aiosqlite, qdrant-client,
│   │   │                             # sentence-transformers, docker
│   │   └── app/
│   │       ├── __init__.py
│   │       ├── main.py               # FastAPI app, CORS, router mounting, watchdog startup
│   │       ├── models/
│   │       │   ├── __init__.py
│   │       │   ├── database.py       # SQLAlchemy engine, session, Base, init_db()
│   │       │   ├── tables.py         # Log, Incident, AuditLog, ServiceUserMapping, ServiceState
│   │       │   └── schemas.py        # Pydantic models: LogCreate, LogResponse, IncidentResponse, etc.
│   │       ├── routers/
│   │       │   ├── __init__.py
│   │       │   ├── logs.py           # POST /logs/, GET /logs/ (with filters)
│   │       │   ├── incidents.py      # GET /incidents/, GET /incidents/{id}, PATCH /incidents/{id}/status
│   │       │   ├── approval.py       # POST approve/reject/notify/vapi-webhook
│   │       │   ├── infra.py          # POST restart/scale, GET status
│   │       │   ├── qdrant.py         # POST /qdrant/query, GET /qdrant/search
│   │       │   └── audit.py          # GET /audit/
│   │       ├── services/
│   │       │   ├── __init__.py
│   │       │   ├── watchdog.py       # Background detection loop
│   │       │   ├── qdrant_service.py # Qdrant client + embedding
│   │       │   ├── vapi_service.py   # Vapi voice call integration
│   │       │   ├── infra_controller.py       # Abstract InfraController interface
│   │       │   ├── docker_controller.py      # Docker SDK implementation
│   │       │   └── kubernetes_controller.py  # Placeholder (NotImplementedError)
│   │       └── utils/
│   │           └── __init__.py
│   │
│   ├── service-a/                    # Port 8001 — Entry point
│   │   ├── Dockerfile
│   │   ├── requirements.txt          # fastapi, uvicorn, httpx, python-dotenv
│   │   └── app/
│   │       ├── __init__.py
│   │       ├── main.py               # FastAPI app, CORS, /health
│   │       ├── routers/
│   │       │   ├── __init__.py
│   │       │   └── process.py        # GET /process — calls Service B
│   │       └── utils/
│   │           ├── __init__.py
│   │           ├── failure_simulator.py  # simulate_failure(fail, service_name)
│   │           └── log_sender.py         # send_log() → POST to admin /logs/
│   │
│   ├── service-b/                    # Port 8002 — Middle tier (same structure as A)
│   │   └── ...                       # process.py calls Service C
│   │
│   └── service-c/                    # Port 8003 — Leaf service (same structure)
│       └── ...                       # process.py has no downstream call
│
├── frontend/                         # Port 5173
│   ├── package.json
│   ├── vite.config.js                # Proxy: /api→:8000, /service-a→:8001
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── index.css                 # @import "tailwindcss"
│       ├── App.jsx                   # Main layout, polling hooks
│       ├── api/
│       │   └── client.js             # All API call functions
│       ├── components/
│       │   ├── ServiceCard.jsx       # Service status card with simulate buttons
│       │   ├── TrafficMetrics.jsx    # Computed metrics from logs
│       │   ├── IncidentTimeline.jsx  # Incident list with approve/reject
│       │   ├── LogsView.jsx          # Log table
│       │   └── ActionPanel.jsx       # Burst errors, latency, normal request, restart/scale
│       └── hooks/
│           └── usePolling.js         # Custom hook for interval-based API polling
│
└── infra/                            # Reserved for future infra configs
```

---

## 5. Environment Variables (.env)

```env
# Service URLs (use container names in Docker, localhost when running locally)
SERVICE_A_URL=http://localhost:8001
SERVICE_B_URL=http://localhost:8002
SERVICE_C_URL=http://localhost:8003
ADMIN_SERVICE_URL=http://localhost:8000

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Vapi (optional — leave empty for fallback mode)
VAPI_API_KEY=
VAPI_PHONE_NUMBER=
VAPI_ASSISTANT_ID=

# ngrok (optional — set when exposing for Vapi callbacks)
NGROK_URL=

# Database (admin service)
DATABASE_URL=sqlite:///./admin.db
```

**Docker note:** When running via docker-compose, service URLs should use container names:
```env
SERVICE_A_URL=http://service-a:8001
SERVICE_B_URL=http://service-b:8002
SERVICE_C_URL=http://service-c:8003
ADMIN_SERVICE_URL=http://admin-service:8000
QDRANT_HOST=qdrant
```

---

## 6. Database Schema (SQLite — Admin Service)

### 6a. `logs` table
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| trace_id | VARCHAR(64) | Indexed, NOT NULL — links related logs across services |
| service_name | VARCHAR(64) | Indexed, NOT NULL — which service generated this log |
| timestamp | DATETIME | Default: utcnow |
| status | VARCHAR(16) | NOT NULL — `SUCCESS`, `ERROR`, or `LATENCY` |
| error_type | VARCHAR(64) | Nullable — `internal_error`, `downstream_error`, `timeout`, `connection_error` |
| message | TEXT | Nullable — human-readable description |
| duration_ms | FLOAT | Nullable — request duration in milliseconds |

### 6b. `incidents` table
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| trace_id | VARCHAR(64) | Nullable — trace that triggered detection |
| service_name | VARCHAR(64) | NOT NULL |
| severity | VARCHAR(16) | `critical`, `high`, `medium` |
| status | VARCHAR(32) | Lifecycle state (see §7) |
| error_summary | TEXT | Watchdog-generated description |
| suggested_solution | TEXT | Qdrant-provided solution string |
| created_at | DATETIME | Auto-set |
| updated_at | DATETIME | Auto-updated on changes |

### 6c. `audit_logs` table
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| incident_id | INTEGER | Nullable — links to incident |
| action | VARCHAR(64) | e.g., `approved`, `rejected`, `action:restart`, `resolved` |
| approved_by | VARCHAR(128) | `fallback_api`, `vapi_voice_call`, `system` |
| details | TEXT | Context about the action |
| timestamp | DATETIME | Auto-set |

### 6d. `service_user_mapping` table
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| service_name | VARCHAR(64) | Unique |
| owner_name | VARCHAR(128) | |
| phone_number | VARCHAR(32) | For Vapi calls |
| email | VARCHAR(128) | |

### 6e. `service_state` table
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| service_name | VARCHAR(64) | Unique |
| status | VARCHAR(16) | `healthy`, `running`, `stopped`, `unknown` |
| replicas | INTEGER | Default: 1 |
| last_checked | DATETIME | |
| updated_at | DATETIME | Auto-updated |

---

## 7. Incident Lifecycle

```
DETECTED → ANALYZED → USER_NOTIFIED → APPROVED → ACTION_TAKEN → RESOLVED
                                         └──────→ REJECTED
```

| State | Triggered By | What Happens |
|-------|-------------|--------------|
| DETECTED | Watchdog | Anomaly found in logs (error rate, service down, latency) |
| ANALYZED | Watchdog (auto) | Qdrant queried, solution attached to `suggested_solution` field |
| USER_NOTIFIED | `POST /approval/notify/{id}` | Vapi voice call triggered (or skipped if not configured) |
| APPROVED | `POST /approval/approve/{id}` or Vapi webhook | Operator approves the suggested action |
| ACTION_TAKEN | System (auto after approval) | InfraController executes restart/scale/none |
| RESOLVED | System (auto after action) | Action succeeded or action_type was "none" |
| REJECTED | `POST /approval/reject/{id}` or Vapi webhook | Operator declines — no action taken |

---

## 8. Watchdog Detection Logic

The watchdog runs as an `asyncio` background task started on admin service startup via `@app.on_event("startup")`.

### Configuration Constants
```python
ERROR_RATE_THRESHOLD = 0.5       # 50% error rate triggers incident
MIN_LOGS_FOR_DETECTION = 3       # Minimum logs in window to evaluate
LATENCY_THRESHOLD_MS = 4000.0    # Avg latency above this triggers incident
WINDOW_SECONDS = 30              # Sliding window size
POLL_INTERVAL_SECONDS = 10       # How often watchdog checks
SERVICES = ["service-a", "service-b", "service-c"]
```

### Detection Rules (checked in priority order)

1. **Service Down** (severity: critical)
   - Condition: ALL logs are ERROR + at least `MIN_LOGS_FOR_DETECTION` logs + includes `connection_error` or `timeout` error types
   - Summary: "Service appears DOWN: all N requests failed in last 30s. Connection/timeout errors detected."

2. **High Error Rate** (severity: high if ≥80%, medium if ≥50%)
   - Condition: Error rate ≥ `ERROR_RATE_THRESHOLD` (50%) with ≥ `MIN_LOGS_FOR_DETECTION` logs
   - Summary: "High error rate detected: XX% (N/M requests failed in last 30s). Error types: ..."

3. **Latency Spike** (severity: medium)
   - Condition: Avg `duration_ms` ≥ `LATENCY_THRESHOLD_MS` (4000ms) OR ≥ 2 logs with status `LATENCY`
   - Summary: "Latency spike detected: avg response time NNNms (threshold: 4000ms). N high-latency requests in last 30s."

### Deduplication
- Before creating an incident, checks if an **active** incident (status in DETECTED, ANALYZED, USER_NOTIFIED, APPROVED, ACTION_TAKEN) already exists for that service
- If active incident exists, skips detection for that service

### Auto-Analysis
- Immediately after creating an incident, queries Qdrant with the `error_summary`
- If Qdrant returns a match (score > 0.3), attaches the solution and transitions to ANALYZED:
  ```
  suggested_solution = "[Action: restart] Root cause: ... Fix: ..."
  ```

---

## 9. Qdrant Integration

### Seed Data (15 runbook entries)

Each entry has:
- `error_pattern` — keywords/phrases for embedding
- `root_cause` — human explanation
- `recommended_fix` — action description
- `action_type` — `restart`, `scale`, or `none`
- `applicable_services` — comma-separated service names
- `severity` — `critical`, `high`, `medium`

Categories:
1. **Service Down / Connection Errors** (2 entries) → action: `restart`
2. **High Error Rate** (2 entries) → action: `restart` or `none` (code-level bugs)
3. **Timeout Errors** (1 entry) → action: `scale`
4. **Latency Spikes** (2 entries) → action: `scale`
5. **Cascading Failures** (1 entry) → action: `restart` (deepest service)
6. **Service-Specific** (3 entries, one per service) → action: `restart`
7. **Resource / Scaling** (2 entries) → action: `restart` or `scale`
8. **Non-Infra / Manual** (2 entries) → action: `none`

### Embedding
- Model: `all-MiniLM-L6-v2` (384 dimensions)
- Text embedded: `error_pattern + " " + root_cause` (combined for richer semantic matching)
- Distance: COSINE
- Collection name: `runbooks`

### Query Logic
```python
def get_best_solution(error_description: str) -> Optional[dict]:
    matches = query_runbook(error_description, top_k=1)
    if matches and matches[0]["score"] > 0.3:  # minimum relevance threshold
        return matches[0]
    return None
```

---

## 10. Infra Controller Abstraction

### Abstract Interface
```python
class InfraController(ABC):
    def restart_service(self, service_name: str) -> ActionResult
    def scale_service(self, service_name: str, replicas: int) -> ActionResult
    def get_status(self, service_name: str) -> ServiceStatus
    def get_all_statuses(self) -> list[ServiceStatus]
```

### Data Classes
```python
@dataclass
class ActionResult:
    success: bool
    service_name: str
    action: str          # "restart" or "scale"
    message: str
    details: Optional[str] = None

@dataclass
class ServiceStatus:
    service_name: str
    status: str          # "running", "stopped", "restarting", "unknown"
    replicas: int
    details: Optional[str] = None
```

### DockerController Implementation
- Uses `docker.from_env()` to connect to Docker daemon
- Maps logical service names to container names (1:1 mapping: `service-a` → `service-a`)
- `restart_service()`: calls `container.restart(timeout=10)`
- `scale_service()`: in plain Docker, simulates by restarting (true scaling needs Swarm/K8s)
- `get_status()`: calls `container.reload()` then reads `container.status`
- Graceful failure: if Docker daemon unavailable or container not found, returns `success=False`

### KubernetesController (Placeholder)
- All methods raise `NotImplementedError`
- Constructor itself raises `NotImplementedError` with guidance message
- Ready for future implementation with kubernetes Python client

---
## 11. Vapi Voice Integration

### Flow
1. `POST /approval/notify/{incident_id}` triggers voice call
2. Vapi calls the user's phone with incident details
3. Voice assistant asks for approval
4. User says "approve" or "reject"
5. Vapi calls `POST /approval/vapi-webhook` with the decision
6. Webhook processes approval/rejection same as fallback API

### Configuration
```python
VAPI_API_KEY = os.getenv("VAPI_API_KEY", "")
VAPI_PHONE_NUMBER = os.getenv("VAPI_PHONE_NUMBER", "")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID", "")
NGROK_URL = os.getenv("NGROK_URL", "")
```

### Graceful Fallback
When `VAPI_API_KEY` or `VAPI_PHONE_NUMBER` is empty:
- Voice call is skipped with a warning log
- Returns fallback URL: `POST /approval/approve/{incident_id}`
- System works fully without Vapi — just use the REST endpoints

### Webhook Payload Handling
```python
# Vapi sends function-call messages:
{
    "message": {
        "type": "function-call",
        "functionCall": {
            "name": "approve",  # or "reject"
            "parameters": {"incident_id": 1}
        }
    }
}
```

---

## 12. Approval & Remediation Flow

### Approval Endpoint (`POST /approval/approve/{incident_id}`)
1. Validate incident exists and is not already RESOLVED/REJECTED
2. Transition to APPROVED → audit log "approved"
3. Extract `action_type` from `suggested_solution` string:
   - Looks for `[action: restart]` or `[action: scale]` (case-insensitive)
   - Default: `none`
4. Execute remediation via InfraController:
   - `restart` → `_controller.restart_service(service_name)`
   - `scale` → `_controller.scale_service(service_name, 2)`
   - `none` → "No infrastructure action required"
5. Transition to ACTION_TAKEN → audit log "action:{type}"
6. If action succeeded OR action_type is "none" → transition to RESOLVED → audit log "resolved"

### Rejection Endpoint (`POST /approval/reject/{incident_id}`)
1. Validate incident exists
2. Transition to REJECTED → audit log "rejected"

---
## 13. Microservice Implementation

### Service Pattern (A, B, C share the same structure)

**main.py:**
```python
app = FastAPI(title="Service A", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
app.include_router(process_router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "service-a"}
```

**process.py (Service A — calls B):**
```python
@router.get("/process")
async def process(
    fail: Optional[str] = Query(None),      # timeout, error, high_latency
    fail_at: Optional[str] = Query(None),   # service-a, service-b, service-c
    x_trace_id: Optional[str] = Header(None),
):
    trace_id = x_trace_id or str(uuid.uuid4())  # Generate if entry point
    start_time = time.time()

    # 1. If failure targets THIS service, simulate it
    if fail and (fail_at is None or fail_at == SERVICE_NAME):
        await simulate_failure(fail, SERVICE_NAME)

    # 2. Call downstream with trace propagation
    response = await client.get(
        f"{SERVICE_B_URL}/process",
        params={"fail": fail, "fail_at": fail_at},  # propagate fail params
        headers={"X-Trace-Id": trace_id},            # propagate trace
    )

    # 3. Handle downstream errors
    if response.status_code != 200:
        await send_log(trace_id, SERVICE_NAME, "ERROR", ...)
        raise HTTPException(502, f"received error from service-b: {detail}")

    # 4. Success path
    duration_ms = round((time.time() - start_time) * 1000, 2)
    status_label = "LATENCY" if duration_ms > 3000 else "SUCCESS"
    await send_log(trace_id, SERVICE_NAME, status_label, ...)
    return {"service": SERVICE_NAME, "traceId": trace_id, "downstream": result}
```

**Service B:** Same pattern, calls Service C.  
**Service C:** Same pattern, NO downstream call (leaf node).

### Failure Simulator
```python
async def simulate_failure(fail, service_name):
    if fail == "timeout":    await asyncio.sleep(30); raise HTTPException(504)
    if fail == "error":      raise HTTPException(500, f"{service_name} encountered an internal error")
    if fail == "high_latency": await asyncio.sleep(5); return  # slow but succeeds
```

### Log Sender (Fire-and-Forget)
```python
async def send_log(trace_id, service_name, status, error_type=None, message=None, duration_ms=None):
    async with httpx.AsyncClient(timeout=5.0) as client:
        await client.post(f"{ADMIN_SERVICE_URL}/logs/", json=payload)
    # Wrapped in try/except — logging never breaks the service
```

---
## 14. Frontend Implementation

### Technology
- React 19 with Vite
- Tailwind CSS 4 via `@tailwindcss/vite` plugin
- No additional UI libraries

### Vite Proxy Configuration
```javascript
server: {
    port: 5173,
    proxy: {
        '/api': {
            target: 'http://localhost:8000',
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/api/, ''),
        },
        '/service-a': {
            target: 'http://localhost:8001',
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/service-a/, ''),
        },
    },
},
```

### API Client (`src/api/client.js`)
All API calls go through a central `fetchJson()` helper. Key functions:
- `getLogs(params)` → `GET /api/logs/`
- `getIncidents(params)` → `GET /api/incidents/`
- `getAllStatuses()` → `GET /api/infra/status`
- `approveIncident(id)` → `POST /api/approval/approve/{id}`
- `rejectIncident(id)` → `POST /api/approval/reject/{id}`
- `triggerProcess(fail, failAt)` → `GET /service-a/process?fail=...&fail_at=...`
- `restartService(name)` → `POST /api/infra/restart/{name}`
- `scaleService(name, replicas)` → `POST /api/infra/scale/{name}?replicas=...`

### Polling Hook (`usePolling`)
```javascript
// Custom hook: calls fetcher every intervalMs, returns { data, error, loading, refresh }
const logs = usePolling(fetchLogs, 4000);
const incidents = usePolling(fetchIncidents, 5000);
const statuses = usePolling(fetchStatuses, 5000);
```

### Components
1. **ServiceCard** — Shows service name, green/red status, replicas, simulate error/timeout/latency buttons
2. **TrafficMetrics** — Computes from logs: total requests, success count, error count, avg latency, error rate %
3. **ActionPanel** — Buttons: Send Normal Request, Burst 4 Errors (C), Burst 4 Latency (C), Restart/Scale per service
4. **IncidentTimeline** — Lists incidents with severity badge, status, approve/reject buttons
5. **LogsView** — Table: timestamp, service, status, error_type, duration, traceId

---

## 15. Docker Configuration

### docker-compose.yml
```yaml
version: "3.8"
services:
  admin-service:
    build: ./services/admin-service
    container_name: admin-service
    ports: ["8000:8000"]
    env_file: [.env]
    networks: [devops-net]
    volumes: [admin-data:/app/data]

  service-a:
    build: ./services/service-a
    container_name: service-a
    ports: ["8001:8001"]
    env_file: [.env]
    depends_on: [admin-service]
    networks: [devops-net]

  service-b:
    build: ./services/service-b
    container_name: service-b
    ports: ["8002:8002"]
    env_file: [.env]
    depends_on: [admin-service]
    networks: [devops-net]

  service-c:
    build: ./services/service-c
    container_name: service-c
    ports: ["8003:8003"]
    env_file: [.env]
    depends_on: [admin-service]
    networks: [devops-net]

  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    ports: ["6333:6333"]
    volumes: [qdrant-data:/qdrant/storage]
    networks: [devops-net]

networks:
  devops-net:
    driver: bridge

volumes:
  admin-data:
  qdrant-data:
```

### Dockerfile (same pattern for all services)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "<PORT>"]
```
Port varies: admin=8000, service-a=8001, service-b=8002, service-c=8003.

---

## 16. Dependencies

### Service A/B/C (`requirements.txt`)
```
fastapi==0.104.1
uvicorn==0.24.0
httpx==0.25.2
python-dotenv==1.0.0
```

### Admin Service (`requirements.txt`)
```
fastapi==0.104.1
uvicorn==0.24.0
httpx==0.25.2
python-dotenv==1.0.0
sqlalchemy==2.0.23
aiosqlite==0.19.0
qdrant-client==1.7.0
sentence-transformers>=2.6.0
docker==6.1.3
```

### Seed Script (`seed_requirements.txt`)
```
qdrant-client==1.7.0
sentence-transformers>=2.6.0
```

### Frontend (`package.json` key deps)
```json
{
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.0.0",
    "@vitejs/plugin-react": "^4.x",
    "tailwindcss": "^4.0.0",
    "vite": "^6.x"
  }
}
```

---

## 17. API Endpoints — Complete Reference

### All Services

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Returns `{"status": "healthy", "service": "<name>"}` |
| GET | `/process` | Process request with optional `fail` and `fail_at` query params |

### Admin Service Only

| Method | Path | Description |
|--------|------|-------------|
| POST | `/logs/` | Ingest a structured log entry |
| GET | `/logs/` | Query logs. Params: `service`, `trace_id`, `status`, `limit` (max 1000) |
| GET | `/incidents/` | List incidents. Params: `service`, `status`, `limit` (max 500) |
| GET | `/incidents/{id}` | Get single incident |
| PATCH | `/incidents/{id}/status` | Update status. Body: `{"status": "ANALYZED"}` |
| POST | `/approval/approve/{id}` | Approve + auto-execute remediation. Param: `approved_by` |
| POST | `/approval/reject/{id}` | Reject incident. Params: `rejected_by`, `reason` |
| POST | `/approval/notify/{id}` | Trigger Vapi voice call |
| POST | `/approval/vapi-webhook` | Vapi callback for call events |
| POST | `/infra/restart/{service}` | Restart container. Param: `incident_id` |
| POST | `/infra/scale/{service}` | Scale replicas. Params: `replicas` (1-10), `incident_id` |
| GET | `/infra/status/{service}` | Single service status |
| GET | `/infra/status` | All service statuses |
| POST | `/qdrant/query` | Query runbook. Body: `{"description": "...", "top_k": 3}` |
| GET | `/qdrant/search` | Search runbook. Params: `q`, `top_k` |
| GET | `/audit/` | Audit trail. Params: `incident_id`, `limit` |

---

## 18. Build Steps (Ordered)

This is the order in which the project was built, and the recommended order for rebuilding:

### Step 1: Scaffold & Base Apps
- Create folder structure with `app/`, `routers/`, `models/`, `services/`, `utils/` per service
- Create `__init__.py` files everywhere
- Create `main.py` per service with FastAPI app + `/health` endpoint
- Create `Dockerfile` per service
- Create `docker-compose.yml` with all services + Qdrant
- Create `.env` with all URLs
- Create `requirements.txt` per service
- Create virtual environments and install deps
- **Verify:** All 4 services start and respond to `/health`

### Step 2: Service Communication & Failure Simulation
- Create `process.py` router in each service
- Service A calls B, B calls C via httpx
- Generate `traceId` (UUID4) at Service A, propagate via `X-Trace-Id` header
- Create `failure_simulator.py` — handle `fail=timeout|error|high_latency`
- Add `fail_at` param for targeting specific service in the chain
- **Verify:** `curl "http://localhost:8001/process?fail=error&fail_at=service-c"` shows cascading error

### Step 3: Logging & DB Schema
- Create `database.py` with SQLAlchemy engine, session, Base class
- Create `tables.py` with all 5 table models
- Create `schemas.py` with Pydantic request/response models
- Create `logs.py` router — `POST /logs/` and `GET /logs/` with filters
- Create `log_sender.py` utility in each service — fire-and-forget POST to admin
- Wire log sending into `process.py` for every outcome (success, error, latency, timeout)
- Call `init_db()` on admin startup
- **Verify:** Make requests → check `curl http://localhost:8000/logs/` shows entries

### Step 4: Watchdog & Incident Detection
- Create `watchdog.py` with sliding window detection logic
- Register `watchdog_loop()` as background task on startup
- Create `incidents.py` router — list, get, update status
- Implement 3 detection rules: service down, high error rate, latency spike
- Add deduplication (skip if active incident exists)
- **Verify:** Send 4+ errors → wait 12s → check `curl http://localhost:8000/incidents/`

### Step 5: Qdrant Integration
- Add Qdrant container to docker-compose
- Create `seed_qdrant.py` with 15 runbook entries
- Create `seed_requirements.txt`
- Create `qdrant_service.py` in admin service (lazy model loading, query, get_best_solution)
- Create `qdrant.py` router — POST /qdrant/query, GET /qdrant/search
- Wire watchdog to auto-query Qdrant on incident creation → attach solution → transition to ANALYZED
- **Verify:** Seed Qdrant → trigger incident → check incident has `suggested_solution`

### Step 6: Infra Controller
- Create `infra_controller.py` abstract base class with `ActionResult` and `ServiceStatus`
- Create `docker_controller.py` with Docker SDK implementation
- Create `kubernetes_controller.py` placeholder
- Create `infra.py` router — restart, scale, status endpoints
- Wire audit logging and service_state updates into infra actions
- **Verify:** `curl -X POST http://localhost:8000/infra/restart/service-c` (works in Docker)

### Step 7: Vapi Integration
- Create `vapi_service.py` — trigger voice call with incident context
- Create `approval.py` router — approve, reject, notify, vapi-webhook
- Implement action extraction from `suggested_solution` string
- Wire remediation execution into approval flow
- Add graceful fallback when Vapi not configured
- **Verify:** `curl -X POST http://localhost:8000/approval/approve/1` → incident resolved

### Step 8: React Frontend
- Create Vite + React project in `frontend/`
- Add Tailwind CSS via `@tailwindcss/vite`
- Configure Vite proxy for `/api` and `/service-a`
- Create `client.js` with all API functions
- Create `usePolling.js` custom hook
- Build all 5 components: ServiceCard, TrafficMetrics, ActionPanel, IncidentTimeline, LogsView
- Build `App.jsx` layout with polling
- **Verify:** Open http://localhost:5173 → see live data from backend

### Step 9: Final Integration & Testing
- Create `audit.py` router — GET /audit/ with incident_id filter
- Test all 3 scenarios end-to-end
- Verify audit trail completeness
- Document curl commands and demo steps in RUN_GUIDE.md

---

## 19. Key Design Patterns

1. **Fire-and-forget logging** — Services send logs asynchronously, wrapped in try/except. Logging failure never breaks the service.

2. **Singleton controllers** — `DockerController()` is instantiated once at module level in `infra.py` and `approval.py`. Docker daemon connection is established once.

3. **Lazy model loading** — The sentence-transformers model in `qdrant_service.py` is loaded on first query, not on startup. This avoids slowing down service boot.

4. **Deduplication** — Watchdog checks for existing active incidents before creating new ones. Prevents alert storms.

5. **Graceful degradation** — Every external dependency (Docker, Qdrant, Vapi) handles unavailability gracefully. The system works with varying levels of functionality.

6. **Audit everything** — The audit trail is the source of truth for what happened. Three audit entries per approval: `approved` → `action:type` → `resolved`.

7. **Status as a state machine** — Incident status follows a strict lifecycle. Invalid transitions are rejected with 400 errors.

---

## 20. Common Gotchas & Troubleshooting

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| PowerShell `curl` returns HTML | PowerShell aliases `curl` to `Invoke-WebRequest` | Use `curl.exe` instead |
| Watchdog not detecting incidents | Fewer than 3 logs in 30s window | Send ≥4 errors within 30 seconds |
| Incidents show `action_type: none` | Qdrant not seeded (no runbooks to match) | Run `python seed_qdrant.py` |
| `infra/restart` returns `success: false` | Services running locally, not as Docker containers | Expected behavior — use Docker for infra actions |
| sentence-transformers download fails | Network/firewall blocking HuggingFace | Pre-download model or use offline cache |
| SQLite `check_same_thread` error | SQLAlchemy + SQLite threading issue | Already handled via `connect_args={"check_same_thread": False}` |
| Frontend shows no data | Backend not running or wrong port | Ensure admin service on 8000, Vite proxy routes correctly |
| Qdrant connection refused | Qdrant container not running | `docker-compose up qdrant -d` |
| Multiple incidents for same service | Not possible — deduplication logic prevents this | Working as designed |

---

## 21. Port Map

| Service | Port | Container Name |
|---------|------|---------------|
| Admin Service | 8000 | admin-service |
| Service A | 8001 | service-a |
| Service B | 8002 | service-b |
| Service C | 8003 | service-c |
| Qdrant | 6333 | qdrant |
| Frontend (dev) | 5173 | N/A (local) |

---

## 22. ngrok Integration

For Vapi voice calls, the admin service needs to be publicly accessible:

```powershell
ngrok http 8000
# Copy the https URL → set NGROK_URL in .env → restart admin service
```

- All admin APIs are ngrok-compatible: CORS open (`*`), no auth, standard JSON REST
- Vapi callback: `POST https://<ngrok-url>/approval/vapi-webhook`
- `NGROK_URL` is auto-used as `serverUrl` in Vapi call configuration

---

## 23. Testing Scenarios

### Scenario 1: Downstream Failure → Restart
```
Trigger: 4x curl "http://localhost:8001/process?fail=error&fail_at=service-c"
Wait: 12s for watchdog
Expected: Incident DETECTED → ANALYZED (Qdrant: restart) → Approve → RESOLVED
Audit: approved → action:restart → resolved
```

### Scenario 2: Latency Spike → Scale
```
Trigger: 4x curl "http://localhost:8001/process?fail=high_latency&fail_at=service-c"
Wait: 12s for watchdog
Expected: Incident DETECTED → ANALYZED (Qdrant: scale) → Approve → RESOLVED
Audit: approved → action:scale → resolved
```

### Scenario 3: Non-Infra Error → No Action
```
Trigger: 4x curl "http://localhost:8001/process?fail=error"
Wait: 12s for watchdog
Expected: Incident DETECTED → ANALYZED (Qdrant: none) → Approve → RESOLVED with action:none
Audit: approved → action:none → resolved
```

### Scenario 4: Rejection
```
Trigger: After any incident is created
Action: curl -X POST "http://localhost:8000/approval/reject/<ID>?reason=False+positive"
Expected: Incident → REJECTED, no infra action
Audit: rejected
```

---