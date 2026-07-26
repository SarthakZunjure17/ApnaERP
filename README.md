# ApnaERP - Enterprise Resource Planning Backend API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Celery](https://img.shields.io/badge/Celery-5.4+-37B24D.svg?style=flat&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D.svg?style=flat&logo=redis&logoColor=white)](https://redis.io)

ApnaERP is a production-grade, modular, high-performance Enterprise Resource Planning (ERP) backend built using Python, FastAPI, PostgreSQL, Redis, Celery, Alembic, JWT, Role-Based Access Control (RBAC), Generic CRUD Framework, Enterprise Audit Logging, Enterprise File Management, Enterprise Notification System, Enterprise Celery Task Processing Platform, Department Management Module, Core Employee Domain, Digital Personnel Files (Employee Documents), Job Positions & Employment Structure, and Docker.

---

## HR Domain — Job Positions & Employment Structure (Milestone HR-4)

### Overview & Position Hierarchy Design
The Position Management module (`app/models/position.py`, `app/services/position.py`) establishes role definitions owned by Departments and occupied by Employees. Positions decouple enterprise job titles, grade pay levels, and headcount capacity limits from individual personnel.

```
Engineering Department
├── Chief Technology Officer (Root Position, Headcount: 1/1)
├── Engineering Manager (Headcount: 2/2)
│   ├── Senior Backend Engineer (Headcount: 5/5)
│   └── Backend Engineer (Headcount: 8/10)
└── Junior Backend Engineer (Headcount: 2/5)
```

### Key Technical Capabilities
- **Position Hierarchy & Uniqueness**: Supports self-referential `parent_position_id` with circular reporting loop prevention (`_validate_no_circular_position`) and nested tree responses (`GET /api/v1/positions/tree`). Enforces unique Position Code and Title-in-Department uniqueness.
- **Automatic Headcount Capacity Controls**: Enforces `maximum_headcount` limits. Automatically increments `current_headcount` when employees are assigned to a position and decrements when unassigned or deleted. Raises HTTP 400 (`HEADCOUNT_LIMIT_EXCEEDED`) if capacity is exceeded, and dispatches Celery background notifications (`HEADCOUNT_LIMIT_REACHED`).
- **Employee Model Integration**: Extended `Employee` model with `position_id`, `employment_start_date`, and `employment_end_date`.
- **Department Placement Guards**: Validates that assigned departments exist, are active (`is_active == True`), and are not soft-deleted.
- **Redis Caching Strategy**: Caches position hierarchy trees (`position:tree`) and department position lists (`position:list:{department_id}`) with automatic cache invalidation on any position mutation.
- **RBAC & Enterprise Audit**: Protected by permissions (`position.create`, `position.read`, `position.update`, `position.delete`, `position.restore`) and logs all position lifecycle actions (`POSITION_CREATE`, `POSITION_UPDATE`, `POSITION_DELETE`, `POSITION_RESTORE`).

### Future HR Module Integrations
- **Attendance Module**: Shift scheduling, work hours, and overtime policies linked to Position Grade/Level.
- **Leave Module**: Entitlement matrices and leave quotas configured by Position Category and Level.
- **Payroll Module**: Base salary ranges, grade pay structures, and allowance components mapped to Position Grade and Level.
- **Recruitment Module**: Requisition requests automatically triggered when `current_headcount` < `maximum_headcount`.
- **Performance Module**: KPI and KRA evaluation templates linked to Position Title and Grade.

---

## HR Domain — Digital Personnel Files & Employee Documents (Milestone HR-3)

### Overview
The Employee Document Management module (`app/models/employee_document.py`, `app/services/employee_document.py`) implements digital personnel files linked to employee records. It reuses the centralized platform File Management service for binary storage while managing compliance metadata, document numbers, validity dates, verification status workflows (`Pending`, `Verified`, `Rejected`), and mandatory document enforcement.

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
│   │       └── endpoints/    # Route handlers (audit, auth, departments, employee_documents, employees, files, health, notifications, positions, rbac, root, templates)
│   ├── core/                 # App configuration, logging, events, security, storage & Celery
│   ├── db/                   # Database session and connection setup
│   ├── models/               # SQLAlchemy ORM models (User, Role, AuditLog, File, Notification, Department, Employee, EmployeeDocument, Position, etc.)
│   ├── repositories/         # Clean Architecture repository layer (DepartmentRepository, EmployeeRepository, EmployeeDocumentRepository, PositionRepository, etc.)
│   ├── schemas/              # Pydantic v2 data models & validation (PositionCreate, PositionResponse, PositionTreeResponse, etc.)
│   ├── services/             # Clean Architecture business service layer (DepartmentService, EmployeeService, EmployeeDocumentService, PositionService, etc.)
│   ├── tasks/                # Centralized Celery task registry (department_tasks, employee_tasks, document_tasks, position_tasks, system_tasks)
│   └── main.py               # FastAPI application entrypoint
├── docker/                   # Docker deployment configurations
├── docs/                     # Architecture Decision Records (ADRs)
│   └── adr/                  # ADR documents (ADR-0001 Redis, ADR-0002 Celery, ADR-0003 Department, ADR-0004 Employee, ADR-0005 Employee Documents, ADR-0006 Position Management)
├── workers/                  # Celery worker process entrypoints
├── tests/                    # Pytest test suite (test_positions.py, test_employee_documents.py, test_employees.py, test_departments.py, test_celery.py, etc.)
├── uploads/                  # Local storage root directory
├── CHANGELOG.md              # Project release notes & changelog
├── requirements.txt          # Python production dependencies
└── README.md                 # Project documentation
```

---

## API Endpoints Overview

| HTTP Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/positions` | Paginated list of job positions | Yes (`position.read`) |
| `GET` | `/api/v1/positions/{id}` | Get job position details by ID | Yes (`position.read`) |
| `GET` | `/api/v1/positions/tree` | Retrieve position reporting hierarchy tree | Yes (`position.read`) |
| `GET` | `/api/v1/departments/{id}/positions` | Get all positions in a department | Yes (`position.read`) |
| `POST` | `/api/v1/positions` | Define new job position | Yes (`position.create`) |
| `PUT` | `/api/v1/positions/{id}` | Update job position metadata or headcount | Yes (`position.update`) |
| `DELETE` | `/api/v1/positions/{id}` | Soft delete job position definition | Yes (`position.delete`) |
| `PATCH` | `/api/v1/positions/{id}/restore` | Restore soft-deleted job position | Yes (`position.restore`) |
| `GET` | `/api/v1/employee-documents` | Paginated list of employee documents | Yes (`employee_document.read`) |
| `GET` | `/api/v1/employees/hierarchy` | Retrieve manager reporting hierarchy tree | Yes (`employee.read`) |
| `GET` | `/api/v1/employees` | Paginated list of employees | Yes (`employee.read`) |
| `GET` | `/api/v1/departments/tree` | Retrieve nested department tree | Yes (`department.read`) |
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
