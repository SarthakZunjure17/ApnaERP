# ApnaERP - Enterprise Resource Planning Backend API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063.svg?style=flat&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)

ApnaERP is a production-grade, modular, high-performance Enterprise Resource Planning (ERP) backend built using Python, FastAPI, PostgreSQL, Redis, Celery, Alembic, and Docker.

---

## Technical Architecture & Core Principles

- **Repository Pattern**: Decouples domain logic from database access mechanisms (`app/repositories/`).
- **Service Layer**: Encapsulates business processes and domain validation (`app/services/`).
- **Dependency Injection**: Utilizes FastAPI's native `Depends` system for runtime dependency binding.
- **SQLAlchemy 2.0 Typed ORM**: Declarative base models with explicit PostgreSQL constraint naming conventions (`app/db/base.py`).
- **Timestamp & UUID Mixins**: Standardized `UUIDMixin` (v4 primary keys) and `TimestampMixin` (`created_at`, `updated_at` with UTC timezone support) in `app/db/mixins.py`.
- **Alembic Migrations**: Fully configured transactional database schema migrations (`alembic/`).
- **Pydantic v2**: High-performance data validation and configuration management (`pydantic-settings`).
- **Clean Architecture & SOLID**: Layered separation of concerns with clear domain boundaries.
- **Structured Logging**: Standardized JSON/console request and event logging (`app/core/logging.py`).
- **Prometheus & Grafana**: Built-in metrics instrumentation (`/metrics`).

---

## Directory Structure

```
ApnaERP/
├── alembic/                  # Alembic database migrations
│   ├── env.py                # Migration runtime environment
│   ├── script.py.mako        # Revision script template
│   └── versions/             # Database migration revisions
├── app/                      # Application source code
│   ├── api/                  # API endpoints and dependency injection
│   │   ├── deps.py           # Dependency injection providers (get_db)
│   │   └── v1/               # API version 1 routers
│   │       ├── api.py        # Master v1 router
│   │       └── endpoints/    # Route handlers (health, root, etc.)
│   ├── core/                 # App configuration, logging, and events
│   │   ├── config.py         # Pydantic v2 Settings configuration
│   │   ├── events.py         # FastAPI lifespan context manager
│   │   └── logging.py        # Structured logging setup
│   ├── db/                   # Database session and connection setup
│   │   ├── base.py           # DeclarativeBase & constraint naming conventions
│   │   ├── mixins.py         # UUIDMixin and TimestampMixin
│   │   └── session.py        # SQLAlchemy 2.0 async engine & session factory
│   ├── middleware/           # FastAPI request timing & CORS middleware
│   │   └── logging_middleware.py
│   ├── models/               # SQLAlchemy ORM models package
│   ├── repositories/         # Clean Architecture base repository interface
│   │   └── base.py           # Generic BaseRepository[Model, CreateSchema, UpdateSchema]
│   ├── schemas/              # Pydantic v2 data models & validation
│   │   └── health.py         # System & database health response schemas
│   ├── services/             # Clean Architecture base service layer
│   │   └── base.py           # Generic BaseService contract
│   ├── utils/                # Helper utilities and common tools
│   │   └── helpers.py        # Utility helper functions
│   ├── workers/              # Celery background task worker initialization
│   │   └── celery_app.py     # Celery app configuration
│   └── main.py               # FastAPI application entrypoint
├── docker/                   # Docker deployment configurations
│   ├── Dockerfile            # Container build instructions
│   ├── docker-compose.yml    # Multi-service stack (API, DB, Redis, Celery, Prometheus)
│   └── entrypoint.sh         # Container startup script
├── docs/                     # Documentation and phase specifications
│   ├── ARCHITECTURE.md       # Architecture design document
│   └── PHASE_0.md            # Phase 0 foundation document
├── scripts/                  # Shell launcher scripts
│   └── run.sh                # Server launcher script
├── tests/                    # Pytest test suite
│   ├── conftest.py           # Pytest fixtures and AsyncClient setup
│   ├── test_db_health.py     # Database connectivity tests
│   ├── test_health.py        # Health endpoint tests
│   └── test_root.py          # Root endpoint tests
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
├── alembic.ini               # Alembic configuration
├── requirements.txt          # Python production dependencies
└── README.md                 # Project documentation
```

---

## Environment Setup & Quick Start

### 1. Prerequisites
- Python 3.10+
- Docker & Docker Compose
- Git

### 2. Virtual Environment Setup

Clone the repository and create a Python virtual environment:

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate
```

Copy the environment template file:

```bash
cp .env.example .env
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Database Management & Migrations

### 1. Starting PostgreSQL with Docker Compose

Start the PostgreSQL database container in detached mode:

```bash
docker compose -f docker/docker-compose.yml up -d db
```

To stop the PostgreSQL container:

```bash
docker compose -f docker/docker-compose.yml stop db
```

### 2. Running Alembic Migrations

To apply all pending database migrations to PostgreSQL:

```bash
alembic upgrade head
```

To roll back the last applied migration:

```bash
alembic downgrade -1
```

To generate a new auto-detected migration after creating ORM models:

```bash
alembic revision --autogenerate -m "Add new model"
```

---

## Launching the Application

Launch the FastAPI development server with hot-reloading:

```bash
uvicorn app.main:app --reload
```

Or run directly via Python:

```bash
python -m app.main
```

The API server will start at: `http://127.0.0.1:8000`

---

## Interactive API Documentation (Swagger & ReDoc)

Once the application is running, access the documentation at:

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI JSON**: [http://127.0.0.1:8000/api/v1/openapi.json](http://127.0.0.1:8000/api/v1/openapi.json)
- **Prometheus Metrics**: [http://127.0.0.1:8000/metrics](http://127.0.0.1:8000/metrics)

---

## API Health Check Endpoints

| HTTP Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Root endpoint returning API metadata |
| `GET` | `/health` | Overall system health including DB status |
| `GET` | `/health/db` | Dedicated PostgreSQL live `SELECT 1` connectivity check |
| `GET` | `/api/v1/health/db` | Dedicated PostgreSQL live connectivity check (v1 API) |
| `GET` | `/metrics` | Prometheus metrics endpoint |

---

## Testing

Run the full automated test suite using `pytest`:

```bash
pytest
```

---

## Common Troubleshooting Tips

1. **Database Connection Refused (`connection to server at "localhost", port 5432 failed`)**:
   - Ensure the PostgreSQL Docker container is running: `docker compose -f docker/docker-compose.yml ps`.
   - Start the database container: `docker compose -f docker/docker-compose.yml up -d db`.
   - Verify environment variables in `.env` match `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, and `POSTGRES_PORT`.

2. **Alembic Migration Conflicts (`Target database is not up to date`)**:
   - Run `alembic heads` to check head revisions.
   - Run `alembic upgrade head` to bring your database schema up to the latest revision.

3. **ModuleNotFoundError when running scripts**:
   - Ensure your virtual environment `.venv` is activated.
   - Set `PYTHONPATH=.` if running standalone scripts outside of `pytest` or `uvicorn`.

---

## License

Copyright © 2026 ApnaERP Team. All rights reserved.
