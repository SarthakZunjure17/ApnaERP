# ApnaERP - Enterprise Resource Planning Backend API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063.svg?style=flat&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)

ApnaERP is a production-grade, modular, high-performance Enterprise Resource Planning (ERP) backend built using Python, FastAPI, PostgreSQL, Redis, Celery, and Docker.

---

## Technical Architecture & Core Principles

- **Repository Pattern**: Decouples domain logic from database access mechanisms (`app/repositories/`).
- **Service Layer**: Encapsulates business processes and domain validation (`app/services/`).
- **Dependency Injection**: Utilizes FastAPI's native `Depends` system for runtime dependency binding.
- **Pydantic v2**: High-performance data validation and configuration management (`pydantic-settings`).
- **Clean Architecture & SOLID**: Layered separation of concerns with clear domain boundaries.
- **Structured Logging**: Standardized JSON/console request and event logging (`app/core/logging.py`).
- **Prometheus & Grafana**: Built-in metrics instrumentation (`/metrics`).

---

## Directory Structure

```
ApnaERP/
├── app/                      # Application source code
│   ├── api/                  # API endpoints and dependency injection
│   │   ├── deps.py           # Dependency injection providers
│   │   └── v1/               # API version 1 routers
│   │       ├── api.py        # Master v1 router
│   │       └── endpoints/    # Route handler modules (health, root, etc.)
│   ├── core/                 # App configuration, logging, and events
│   │   ├── config.py         # Pydantic v2 Settings configuration
│   │   ├── events.py         # FastAPI lifespan context manager
│   │   └── logging.py        # Structured logging setup
│   ├── db/                   # Database session and connection setup
│   │   └── session.py        # SQLAlchemy 2.0 async engine & session factory
│   ├── middleware/           # FastAPI request timing & CORS middleware
│   │   └── logging_middleware.py
│   ├── models/               # SQLAlchemy ORM models (Phase 1+)
│   ├── repositories/         # Clean Architecture base repository interface
│   │   └── base.py           # Generic BaseRepository[Model, CreateSchema, UpdateSchema]
│   ├── schemas/              # Pydantic v2 data models & validation
│   │   └── health.py         # System health & root response schemas
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
│   ├── test_health.py        # Health endpoint tests
│   └── test_root.py          # Root endpoint tests
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
├── requirements.txt          # Python production dependencies
└── README.md                 # Project documentation
```

---

## Getting Started

### 1. Prerequisites
- Python 3.10+
- Git
- Docker & Docker Compose (Optional for containerized run)

### 2. Environment Setup

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

Install production dependencies:

```bash
pip install -r requirements.txt
```

---

## Running the Application

### Option A: Local Development with Uvicorn

To launch the FastAPI development server with hot-reloading:

```bash
uvicorn app.main:app --reload
```

Or run directly via python:

```bash
python -m app.main
```

The API server will start at: `http://127.0.0.1:8000`

### Option B: Running with Docker Compose

To start the full stack including PostgreSQL, Redis, Celery worker, Prometheus, and Grafana:

```bash
docker-compose -f docker/docker-compose.yml up --build
```

---

## Interactive API Documentation (Swagger & ReDoc)

Once the application is running, open your browser to access the auto-generated documentation:

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI JSON**: [http://127.0.0.1:8000/api/v1/openapi.json](http://127.0.0.1:8000/api/v1/openapi.json)
- **Prometheus Metrics**: [http://127.0.0.1:8000/metrics](http://127.0.0.1:8000/metrics)

---

## API Endpoints (Phase 0)

| HTTP Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Root endpoint returning API metadata and documentation link |
| `GET` | `/health` | System health check returning status, version, and timestamp |
| `GET` | `/api/v1/health` | System health check (API v1) |
| `GET` | `/metrics` | Prometheus metrics endpoint |

---

## Testing

Run the automated test suite using `pytest`:

```bash
pytest
```

---

## License

Copyright © 2026 ApnaERP Team. All rights reserved.
