# ApnaERP - Enterprise Resource Planning Backend API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Celery](https://img.shields.io/badge/Celery-5.4+-37B24D.svg?style=flat&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D.svg?style=flat&logo=redis&logoColor=white)](https://redis.io)

ApnaERP is a production-grade, modular, high-performance Enterprise Resource Planning (ERP) backend built using Python, FastAPI, PostgreSQL, Redis, Celery, Alembic, JWT, Role-Based Access Control (RBAC), Generic CRUD Framework, Enterprise Audit Logging, Enterprise File Management, Enterprise Notification System, Enterprise Celery Task Processing Platform, Department Management Module, and Docker.

---

## HR Domain — Department Management Module (Milestone HR-1)

### Overview & Hierarchy Design
The Department Management module (`app/models/department.py`, `app/services/department.py`) establishes the organizational hierarchy for ApnaERP, serving as the foundational parent entity for employees, cost centers, and future HR operations.

```
Company (Root)
├── Human Resources (HR)
├── Information Technology (IT)
│   ├── Backend Engineering
│   ├── Frontend Engineering
│   └── DevOps & Infrastructure
└── Finance & Accounting
```

### Key Technical Capabilities
- **Self-Referential Hierarchy**: Self-referential `parent_id` linking to `departments.id` with `children` relationships.
- **Circular Parent Safeguard**: Business logic in `DepartmentService._validate_no_circular_parent` traverses ancestry to prevent circular parent loops (e.g. A -> B -> C -> A).
- **Active Children Deletion Protection**: Blocks soft-deleting any department that contains active child sub-departments.
- **Redis Caching Strategy**: Caches hierarchy tree responses (`GET /api/v1/departments/tree`) under `department:tree`. Automatic cache invalidation occurs on all mutation operations (Create, Update, Delete, Restore).
- **Asynchronous Celery Notifications**: Offloads background event notifications (`send_department_notification_task`) without blocking HTTP response handlers.
- **Enterprise Audit Logging**: Records structured audit events (`DEPARTMENT_CREATE`, `DEPARTMENT_UPDATE`, `DEPARTMENT_DELETE`, `DEPARTMENT_RESTORE`).
- **RBAC Security Guards**: Protected by permissions (`department.create`, `department.read`, `department.update`, `department.delete`, `department.restore`).

---

## Celery Asynchronous Task Processing Platform Architecture

### Overview & Queue Design
ApnaERP features a centralized, asynchronous task processing platform (`app/core/celery.py`) powered by Celery and Kombu queue routing over Redis:
- **`default` Queue**: Standard background task execution.
- **`high_priority` Queue**: High-urgency tasks (system health, security alerts, department/notification alerts).
- **`low_priority` Queue**: Bulk heavy operations (reports, analytics, exports).
- **`periodic` Queue**: Celery Beat scheduled cron/interval jobs.

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
│   │       └── endpoints/    # Route handlers (audit, auth, departments, files, health, notifications, rbac, root, templates)
│   ├── core/                 # App configuration, logging, events, security, storage & Celery
│   ├── db/                   # Database session and connection setup
│   ├── models/               # SQLAlchemy ORM models (User, Role, AuditLog, File, Notification, Department, etc.)
│   ├── repositories/         # Clean Architecture repository layer (DepartmentRepository, etc.)
│   ├── schemas/              # Pydantic v2 data models & validation (DepartmentCreate, DepartmentTreeResponse, etc.)
│   ├── services/             # Clean Architecture business service layer (DepartmentService, etc.)
│   ├── tasks/                # Centralized Celery task registry (department_tasks, system_tasks)
│   └── main.py               # FastAPI application entrypoint
├── docker/                   # Docker deployment configurations
├── docs/                     # Architecture Decision Records (ADRs)
│   └── adr/                  # ADR documents (ADR-0001 Redis, ADR-0002 Celery, ADR-0003 Department)
├── workers/                  # Celery worker process entrypoints
├── tests/                    # Pytest test suite (test_departments.py, test_celery.py, etc.)
├── uploads/                  # Local storage root directory
├── CHANGELOG.md              # Project release notes & changelog
├── requirements.txt          # Python production dependencies
└── README.md                 # Project documentation
```

---

## API Endpoints Overview

| HTTP Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/departments/tree` | Retrieve nested department tree | Yes (`department.read`) |
| `GET` | `/api/v1/departments` | Paginated list of departments | Yes (`department.read`) |
| `GET` | `/api/v1/departments/{id}` | Get department details by ID | Yes (`department.read`) |
| `POST` | `/api/v1/departments` | Create new department | Yes (`department.create`) |
| `PUT` | `/api/v1/departments/{id}` | Update department | Yes (`department.update`) |
| `DELETE` | `/api/v1/departments/{id}` | Soft delete department | Yes (`department.delete`) |
| `PATCH` | `/api/v1/departments/{id}/restore` | Restore soft-deleted department | Yes (`department.restore`) |
| `GET` | `/api/v1/health/celery` | Celery platform health diagnostics | No |
| `GET` | `/api/v1/health/redis` | Redis health diagnostics check | No |

---

## Testing

Run the complete automated test suite using `pytest`:

```bash
pytest
```

---

## License

Copyright © 2026 ApnaERP Team. All rights reserved.
