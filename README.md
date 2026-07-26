# ApnaERP - Enterprise Resource Planning Backend API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Celery](https://img.shields.io/badge/Celery-5.4+-37B24D.svg?style=flat&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D.svg?style=flat&logo=redis&logoColor=white)](https://redis.io)

ApnaERP is a production-grade, modular, high-performance Enterprise Resource Planning (ERP) backend built using Python, FastAPI, PostgreSQL, Redis, Celery, Alembic, JWT, Role-Based Access Control (RBAC), Generic CRUD Framework, Enterprise Audit Logging, Enterprise File Management, Enterprise Notification System, Enterprise Celery Task Processing Platform, Department Management Module, Employee Domain (Core HR), and Docker.

---

## HR Domain — Enterprise Employee Domain (Milestone HR-2)

### Overview & Reporting Structure
The Employee domain (`app/models/employee.py`, `app/services/employee.py`) establishes the core workforce model for ApnaERP. Employees serve as the foundational entity upon which all future HR modules build.

```
Chief Executive Officer (Root Manager)
├── VP of Engineering
│   ├── Engineering Manager (Backend)
│   │   ├── Senior Software Engineer
│   │   └── Software Engineer
│   └── Engineering Manager (Frontend)
│       └── UI/UX Engineer
└── VP of Human Resources
    └── HR Operations Lead
```

### Key Technical Capabilities
- **Core Workforce Model**: Manages unique `employee_code`, `work_email`, employment contract type (`Full Time`, `Part Time`, `Contract`, `Intern`), lifecycle status (`Active`, `Probation`, `Notice Period`, `Suspended`, `Resigned`, `Terminated`), dates, department link, user link, and profile picture avatar.
- **Reporting Hierarchy**: Self-referential `manager_id` relationship providing organizational reporting hierarchy trees (`GET /api/v1/employees/hierarchy`).
- **Circular Reporting Safeguard**: `EmployeeService._validate_no_circular_manager` prevents self-management and circular manager reporting loops (e.g. A -> B -> C -> A).
- **Active Department Constraint**: Verifies `department.is_active == True` and `department.is_deleted == False` before assigning employees.
- **Redis Caching Strategy**: Caches hierarchy tree (`employee:hierarchy`) and department employee lists (`employee:department:{id}`). Automatic cache invalidation occurs on all mutation operations.
- **Asynchronous Celery Notifications**: Dispatches `send_employee_notification_task` for background event processing.
- **Audit & RBAC Enforcement**: Protected by permissions (`employee.create`, `employee.read`, `employee.update`, `employee.delete`, `employee.restore`) and logs all mutations (`EMPLOYEE_CREATE`, `EMPLOYEE_UPDATE`, `EMPLOYEE_DELETE`, `EMPLOYEE_RESTORE`).

### Future HR Integration Points
- **Attendance Module**: Will associate daily check-in/check-out time logs to `employee_id`.
- **Leave Module**: Will handle leave applications, quota balances, and manager approvals using `employee_id` and `manager_id`.
- **Payroll Module**: Will link salary structures, compensation components, and payslip generation to `employee_id`.

---

## HR Domain — Department Management Module (Milestone HR-1)

### Overview & Hierarchy Design
The Department Management module (`app/models/department.py`, `app/services/department.py`) establishes the organizational structure, serving as the parent entity for employees, cost centers, and team divisions.

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
│   │       └── endpoints/    # Route handlers (audit, auth, departments, employees, files, health, notifications, rbac, root, templates)
│   ├── core/                 # App configuration, logging, events, security, storage & Celery
│   ├── db/                   # Database session and connection setup
│   ├── models/               # SQLAlchemy ORM models (User, Role, AuditLog, File, Notification, Department, Employee, etc.)
│   ├── repositories/         # Clean Architecture repository layer (DepartmentRepository, EmployeeRepository, etc.)
│   ├── schemas/              # Pydantic v2 data models & validation (EmployeeCreate, EmployeeHierarchyResponse, etc.)
│   ├── services/             # Clean Architecture business service layer (DepartmentService, EmployeeService, etc.)
│   ├── tasks/                # Centralized Celery task registry (department_tasks, employee_tasks, system_tasks)
│   └── main.py               # FastAPI application entrypoint
├── docker/                   # Docker deployment configurations
├── docs/                     # Architecture Decision Records (ADRs)
│   └── adr/                  # ADR documents (ADR-0001 Redis, ADR-0002 Celery, ADR-0003 Department, ADR-0004 Employee)
├── workers/                  # Celery worker process entrypoints
├── tests/                    # Pytest test suite (test_employees.py, test_departments.py, test_celery.py, etc.)
├── uploads/                  # Local storage root directory
├── CHANGELOG.md              # Project release notes & changelog
├── requirements.txt          # Python production dependencies
└── README.md                 # Project documentation
```

---

## API Endpoints Overview

| HTTP Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/employees/hierarchy` | Retrieve manager reporting hierarchy tree | Yes (`employee.read`) |
| `GET` | `/api/v1/employees/department/{id}` | Get employees assigned to a department | Yes (`employee.read`) |
| `GET` | `/api/v1/employees` | Paginated list of employees | Yes (`employee.read`) |
| `GET` | `/api/v1/employees/{id}` | Get employee details by ID | Yes (`employee.read`) |
| `POST` | `/api/v1/employees` | Create new employee | Yes (`employee.create`) |
| `PUT` | `/api/v1/employees/{id}` | Update employee profile/manager/department | Yes (`employee.update`) |
| `DELETE` | `/api/v1/employees/{id}` | Soft delete employee | Yes (`employee.delete`) |
| `PATCH` | `/api/v1/employees/{id}/restore` | Restore soft-deleted employee | Yes (`employee.restore`) |
| `GET` | `/api/v1/departments/tree` | Retrieve nested department tree | Yes (`department.read`) |
| `GET` | `/api/v1/departments` | Paginated list of departments | Yes (`department.read`) |
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
