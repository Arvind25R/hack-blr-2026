# File Structure

```
test/
├── .env
├── .gitignore
├── DETAILS.md
├── docker-compose.yml
├── FILE_STRUCTURE.md
├── HIGH_LEVEL_IDEA.md
├── PLAN.md
├── PROMPT.md
├── RUN_GUIDE.md
├── seed_qdrant.py
├── seed_requirements.txt
├── frontend/
│   ├── .gitignore
│   ├── eslint.config.js
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── README.md
│   ├── vite.config.js
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons.svg
│   └── src/
│       ├── App.jsx
│       ├── index.css
│       ├── main.jsx
│       ├── api/
│       │   └── client.js
│       ├── assets/
│       │   ├── hero.png
│       │   ├── react.svg
│       │   └── vite.svg
│       ├── components/
│       │   ├── ActionPanel.jsx
│       │   ├── IncidentTimeline.jsx
│       │   ├── LogsView.jsx
│       │   ├── ServiceCard.jsx
│       │   └── TrafficMetrics.jsx
│       └── hooks/
│           └── usePolling.js
├── infra/
└── services/
    ├── admin-service/
    │   ├── admin.db
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   └── app/
    │       ├── __init__.py
    │       ├── main.py
    │       ├── models/
    │       │   ├── __init__.py
    │       │   ├── database.py
    │       │   ├── schemas.py
    │       │   └── tables.py
    │       ├── routers/
    │       │   ├── __init__.py
    │       │   ├── approval.py
    │       │   ├── audit.py
    │       │   ├── incidents.py
    │       │   ├── infra.py
    │       │   ├── logs.py
    │       │   └── qdrant.py
    │       ├── services/
    │       │   ├── __init__.py
    │       │   ├── docker_controller.py
    │       │   ├── infra_controller.py
    │       │   ├── kubernetes_controller.py
    │       │   ├── qdrant_service.py
    │       │   ├── vapi_service.py
    │       │   └── watchdog.py
    │       └── utils/
    │           └── __init__.py
    ├── service-a/
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   └── app/
    │       ├── __init__.py
    │       ├── main.py
    │       ├── models/
    │       │   └── __init__.py
    │       ├── routers/
    │       │   ├── __init__.py
    │       │   └── process.py
    │       ├── services/
    │       │   └── __init__.py
    │       └── utils/
    │           ├── __init__.py
    │           ├── failure_simulator.py
    │           └── log_sender.py
    ├── service-b/
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   └── app/
    │       ├── __init__.py
    │       ├── main.py
    │       ├── models/
    │       │   └── __init__.py
    │       ├── routers/
    │       │   ├── __init__.py
    │       │   └── process.py
    │       ├── services/
    │       │   └── __init__.py
    │       └── utils/
    │           ├── __init__.py
    │           ├── failure_simulator.py
    │           └── log_sender.py
    └── service-c/
        ├── Dockerfile
        ├── requirements.txt
        └── app/
            ├── __init__.py
            ├── main.py
            ├── models/
            │   └── __init__.py
            ├── routers/
            │   ├── __init__.py
            │   └── process.py
            ├── services/
            │   └── __init__.py
            └── utils/
                ├── __init__.py
                ├── failure_simulator.py
                └── log_sender.py
```