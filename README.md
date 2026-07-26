# ApnaERP - Enterprise Resource Planning Backend API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Celery](https://img.shields.io/badge/Celery-5.4+-37B24D.svg?style=flat&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D.svg?style=flat&logo=redis&logoColor=white)](https://redis.io)

ApnaERP is a production-grade, modular, high-performance Enterprise Resource Planning (ERP) backend built using Python, FastAPI, PostgreSQL, Redis, Celery, Alembic, JWT, Role-Based Access Control (RBAC), Generic CRUD Framework, Enterprise Audit Logging, Enterprise File Management, Enterprise Notification System, Enterprise Celery Task Processing Platform, and Docker.

---

## Celery Asynchronous Task Processing Platform Architecture

### Overview & Queue Design
ApnaERP features a centralized, asynchronous task processing platform (`app/core/celery.py`) powered by Celery and Kombu queue routing over Redis:
- **`default` Queue**: Standard background task execution.
- **`high_priority` Queue**: High-urgency tasks (system health, security alerts, realtime notifications).
- **`low_priority` Queue**: Bulk heavy operations (reports, analytics, exports).
- **`periodic` Queue**: Celery Beat scheduled cron/interval jobs.

```
[ FastAPI Endpoint ] ──> task.delay(...) / task.apply_async(...)
                              │
                              ▼
                      Redis Broker (Kombu Priority Queues)
                      - high_priority (x-max-priority: 10)
                      - default       (x-max-priority: 10)
                      - low_priority  (x-max-priority: 10)
                      - periodic
                              │
                              ▼
                      Celery Worker Nodes (workers/celery_worker.py)
                              │
                              ▼
                      Redis Result Backend
```

### Reusable Task Base Classes (`app/tasks/base.py`)
All tasks inherit from standardized base classes:
- **`BaseTask(celery.Task)`**: Abstract base task managing correlation tracking, structured logging, and lifecycle callbacks (`on_success`, `on_failure`, `on_retry`).
- **`RetryTask(BaseTask)`**: Configured with exponential backoff and jitter (`autoretry_for=(Exception,)`, `retry_backoff=True`, `max_retries=3`).
- **`PeriodicTask(BaseTask)`**: Scheduled task base class routed to the `periodic` queue.
- **`LoggingTask(BaseTask)`**: Telemetry-enhanced task class logging execution runtime duration in milliseconds.

### Task Routing & Worker Configuration
- **Task Routing Rules**:
  - `app.tasks.system_tasks.*` ──> `high_priority`
  - `app.tasks.notification_tasks.*` ──> `high_priority`
  - `app.tasks.report_tasks.*` ──> `low_priority`
- **Time Limits**: `task_time_limit=300` seconds (hard cutoff), `task_soft_time_limit=240` seconds.

### Environment Configuration
```env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_TIMEZONE=UTC
CELERY_WORKER_CONCURRENCY=4
CELERY_TASK_SERIALIZER=json
CELERY_RESULT_SERIALIZER=json
CELERY_ACCEPT_CONTENT=["json"]
CELERY_TASK_ALWAYS_EAGER=false
```

### Celery Health & Inspection Endpoints
- **`GET /health/celery`**: Returns broker status, result backend connection state, registered tasks list, and configured Kombu queues.
- **`GET /health/workers`**: Inspects active background worker nodes, ping responses, worker statistics, and active running tasks.

---

## Directory Structure

```
ApnaERP/
├── alembic/                  # Alembic database migrations
├── app/                      # Application source code
│   ├── api/                  # API endpoints and dependency injection
│   │   ├── deps.py           # Dependency injection providers
│   │   └── v1/               # API version 1 routers
│   │       ├── api.py        # Master v1 router
│   │       └── endpoints/    # Route handlers (audit, auth, files, health, notifications, rbac, root, templates)
│   ├── core/                 # App configuration, logging, events, security, storage & Celery
│   │   ├── celery.py         # Celery app, Kombu queues, task routing
│   │   ├── config.py         # Settings (JWT, DB, Redis, File, Email, Celery)
│   │   ├── redis.py          # RedisManager & connection pooling
│   │   └── storage/          # Storage Provider Abstraction layer
│   ├── db/                   # Database session and connection setup
│   ├── dependencies/         # Reusable dependency injection helpers
│   ├── exceptions/           # Domain exception hierarchy and FastAPI handlers
│   ├── middleware/           # Request timing, context & CORS middleware
│   ├── models/               # SQLAlchemy ORM models
│   ├── repositories/         # Clean Architecture repository layer
│   ├── schemas/              # Pydantic v2 data models & validation
│   ├── services/             # Clean Architecture business service layer
│   ├── tasks/                # Centralized Celery task registry
│   │   ├── __init__.py       # Package exports
│   │   ├── base.py           # BaseTask, RetryTask, PeriodicTask, LoggingTask
│   │   └── system_tasks.py   # system_ping_task, system_health_check_task
│   ├── utils/                # Helper utilities
│   └── main.py               # FastAPI application entrypoint
├── docker/                   # Docker deployment configurations
│   ├── Dockerfile            # Container build script
│   └── docker-compose.yml    # API, DB, Redis, Celery Worker, Celery Beat, Prometheus, Grafana
├── docs/                     # Architecture Decision Records (ADRs)
│   └── adr/                  # ADR documents (ADR-0001 Redis, ADR-0002 Celery)
├── workers/                  # Celery worker process entrypoints
│   ├── __init__.py
│   └── celery_worker.py      # Worker entrypoint module
├── tests/                    # Pytest test suite
│   ├── test_celery.py        # Celery Task Platform unit tests
│   ├── test_redis.py         # Redis Infrastructure unit tests
│   └── ...                   # Test files (audit, auth, files, generic_crud, health, notifications, rbac)
├── uploads/                  # Local storage root directory
├── CHANGELOG.md              # Project release notes & changelog
├── alembic.ini               # Alembic configuration
├── requirements.txt          # Python production dependencies
└── README.md                 # Project documentation
```

---

## API Endpoints Overview

| HTTP Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/health/celery` | Celery platform health diagnostics | No |
| `GET` | `/health/workers` | Celery background worker inspection | No |
| `GET` | `/health/redis` | Redis health diagnostics check | No |
| `GET` | `/health` | Overall system health check | No |
| `GET` | `/notifications` | List user's notifications | Yes (Bearer) |
| `POST` | `/files/upload` | Multipart file upload with SHA256 deduplication | Yes (Bearer) |
| `POST` | `/auth/login` | Login with username/email & password | No |
| `GET` | `/audit/logs` | List audit logs | Yes (Super Admin) |

---

## Testing

Run the complete automated test suite using `pytest`:

```bash
pytest
```

---

## License

Copyright © 2026 ApnaERP Team. All rights reserved.
