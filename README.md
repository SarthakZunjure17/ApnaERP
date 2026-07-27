# ApnaERP - Enterprise Resource Planning Backend API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Celery](https://img.shields.io/badge/Celery-5.4+-37B24D.svg?style=flat&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D.svg?style=flat&logo=redis&logoColor=white)](https://redis.io)

ApnaERP is a production-grade, modular, high-performance Enterprise Resource Planning (ERP) backend built using Python, FastAPI, PostgreSQL, Redis, Celery, Alembic, JWT, Role-Based Access Control (RBAC), Generic CRUD Framework, Enterprise Audit Logging, Enterprise File Management, Enterprise Notification System, Enterprise Celery Task Processing Platform, Department Management Module, Core Employee Domain, Digital Personnel Files (Employee Documents), Job Positions & Employment Structure, HR Configuration & Organization Policies, Enterprise Shift Management, Enterprise Holiday Calendar, Enterprise Attendance Engine, and Docker.

---

## HR Domain — Enterprise Shift Assignment & Scheduling (Milestone HR-9)

### Overview
The Shift Assignment & Scheduling module (`app/models/shift_assignment.py`, `app/services/shift_assignment.py`) enables effective-dated shift scheduling (`effective_from`, `effective_to`) for employees. Attendance calculations dynamically resolve shift schedules by date history rather than relying on static employee profiles.

### Key Technical Capabilities
- **Effective-Dated Scheduling**: Supports `Permanent`, `Temporary`, and `Rotation` schedule assignments with explicit start dates and optional open-ended end dates (`NULL`).
- **Date Overlap Prevention**: Strict interval validation (`check_overlap`) prevents overlapping active shift assignments for an employee.
- **Historical Attendance Shift Resolution**: Attendance Engine resolves the effective shift for any historical date `D` via `ShiftAssignment` -> `Shift` -> `Attendance Engine`.
- **Locked Attendance Protection**: Prevents modifying, ending, or soft-deleting shift assignments if an `Attendance` record in that date range is locked for payroll (`is_locked = True`).
- **Redis High-Performance Caching & Celery Telemetry**: Caches active shift lookups (`shift_assignment:active:{emp_id}:{date}`) with automatic cache invalidation upon assignment updates. Dispatches Celery background tasks (`send_shift_assignment_notification_task`) and records audit events (`SHIFT_ASSIGNMENT_CREATE`, `SHIFT_ASSIGNMENT_UPDATE`, `SHIFT_ASSIGNMENT_END`, `SHIFT_ASSIGNMENT_DELETE`).
- **RBAC Enforcement**: Secured via permissions (`shift_assignment.create`, `shift_assignment.read`, `shift_assignment.update`, `shift_assignment.delete`).

---

## HR Domain — Enterprise Attendance Engine (Milestone HR-8)

### Overview
The Attendance Engine (`app/models/attendance.py`, `app/services/attendance_engine.py`, `app/services/attendance.py`) provides a domain-driven business rules engine that dynamically synthesizes data from `Employee`, `Shift`, `Holiday Calendar`, and `HR Configuration` to evaluate daily attendance statuses, worked/expected minutes, tardiness, and early departures.

### Key Technical Capabilities
- **Deterministic Business Rules Engine (`AttendanceEngine`)**: Isolated domain service computing status (`Present`, `Late`, `Half Day`, `Absent`, `Holiday`, `Weekend`, `On Leave`, `Missing Check-in`, `Missing Check-out`) and timing metrics independently from API controllers.
- **Overnight Shift Calculations**: Supports shifts spanning midnight (`end_time <= start_time`, e.g. 22:00 to 06:00), evaluating grace periods and tardiness across date boundaries.
- **Weekend & Holiday Integration**: Automatically checks `HRConfiguration.weekend_configuration` and `HolidayRepository` lookups to assign non-working statuses.
- **Locked Record Guard**: Records locked (`is_locked = True`) for payroll processing block check-ins, check-outs, and manual corrections (HTTP 400 `ATTENDANCE_LOCKED`).
- **Manual HR Corrections & Audit Trail**: Requires mandatory justification notes for manual corrections and records audit events (`ATTENDANCE_CHECKIN`, `ATTENDANCE_CHECKOUT`, `ATTENDANCE_CORRECT`, `ATTENDANCE_LOCK`).
- **Redis Caching & Celery Telemetry**: Caches active attendance listings (`attendance:today`) and dispatches Celery background tasks (`send_attendance_notification_task`).
- **RBAC Enforcement**: Protected by permissions (`attendance.read`, `attendance.checkin`, `attendance.checkout`, `attendance.correct`, `attendance.lock`).

---

## HR Domain — Enterprise Holiday Calendar (Milestone HR-7)

### Overview
The Holiday Calendar module (`app/models/holiday.py`, `app/services/holiday.py`) serves as the authoritative single source of truth for organization, national, and regional holiday definitions. Downstream modules (Attendance, Leave, Payroll, Reporting) consume this registry to determine non-working days, leave balance deductions, and holiday overtime multipliers.

### Key Technical Capabilities
- **Location-Aware Regional Scoping**: Supports `National`, `Regional`, `Company`, and `Optional` holiday classifications across specified countries and state/regions.
- **Annual Recurring Projection Algorithm**: Holidays marked `is_recurring_annually = True` automatically apply across all calendar years without manual re-creation. Year queries (`GET /api/v1/holidays/year/{year}`) project recurring holidays onto target years seamlessly.
- **Strict Deduplication**: Enforces unique holiday codes and unique `(holiday_date, country, state_region)` combinations among non-deleted records.
- **Redis Caching & Celery Telemetry**: Caches holiday listings (`holiday:list`) with automatic invalidation. Dispatches Celery background tasks (`send_holiday_notification_task`) and logs enterprise audit events (`HOLIDAY_CREATE`, `HOLIDAY_UPDATE`, `HOLIDAY_DELETE`, `HOLIDAY_RESTORE`).
- **RBAC Enforcement**: Protected by permissions (`holiday.create`, `holiday.read`, `holiday.update`, `holiday.delete`, `holiday.restore`).

---

## HR Domain — Enterprise Shift Management (Milestone HR-6)

### Overview
The Shift Management module (`app/models/shift.py`, `app/services/shift.py`) provides reusable, enterprise-grade work schedule definitions. It extends `Employee` with a nullable `shift_id` FK, establishing baseline shift timings consumed downstream by Attendance (working hours, tardiness, grace period) and Payroll (overtime calculation).

### Key Technical Capabilities
- **Overnight & Night Shift Support**: Shifts spanning across midnight (`end_time <= start_time`, e.g. 22:00 to 06:00) are automatically detected and calculated (`(24.0 - start_time) + end_time`). The `is_night_shift` flag is automatically validated.
- **Duration & Sanity Constraints**:
  - `break_duration_minutes`: Break duration in hours must be strictly less than total shift duration.
  - `grace_period_minutes`: Grace period in hours must be strictly less than total shift duration.
  - `minimum_working_hours`: Must not exceed `maximum_working_hours`.
- **Active Employee Shift Deletion Guard**: Soft-deleting a shift (`DELETE /api/v1/shifts/{id}`) is explicitly blocked (HTTP 400 `ASSIGNED_EMPLOYEES_EXIST`) if active employees are assigned to the shift schedule.
- **Nullable Employee Integration**: `Employee.shift_id` nullable FK allows flexible schedule assignments while falling back to `HRConfiguration` defaults when unassigned.
- **Redis Caching & Celery Telemetry**: Caches shift listings and details (`shift:list`, `shift:detail:{id}`) with automatic invalidation. Dispatches Celery background tasks (`send_shift_notification_task`) and logs enterprise audit events (`SHIFT_CREATE`, `SHIFT_UPDATE`, `SHIFT_DELETE`, `SHIFT_RESTORE`).
- **RBAC Enforcement**: Protected by permissions (`shift.create`, `shift.read`, `shift.update`, `shift.delete`, `shift.restore`).

---

## HR Domain — HR Configuration & Organization Policies (Milestone HR-5)

### Overview
The HR Configuration module (`app/models/hr_configuration.py`, `app/services/hr_configuration.py`) acts as the centralized single source of truth for organization-wide HR policies. It stores enterprise parameters that future HR modules (Attendance, Leave, Payroll, Recruitment, Performance, Shift Scheduling) consume directly, avoiding duplicate settings across sub-systems.

### Key Technical Capabilities
- **Singleton Active Configuration**: Guarantees exactly one active configuration (`is_active=True`) per organization code. Creating or activating a policy automatically deactivates previous active policies.
- **Active Deletion Guard**: Soft-deletion (`DELETE /api/v1/hr/configuration/{id}`) is explicitly blocked if the configuration is currently active (`is_active == True`), protecting enterprise policy continuity.
- **Domain Validation**:
  - Timezone validation via standard library `zoneinfo` (e.g. `Asia/Kolkata`, `UTC`).
  - Weekend configuration day name checks (`Monday` through `Sunday`).
  - Working hours sanity checks (`minimum_working_hours <= standard_working_hours_per_day`).
  - Currency ISO 3-letter code checks and non-empty country strings.
- **Redis Caching Strategy**: Active configurations are cached (`hr_configuration:active:{organization_code}`) with automatic invalidation on any policy mutation or activation.
- **RBAC & Enterprise Audit**: Protected by permissions (`hr_configuration.read`, `hr_configuration.create`, `hr_configuration.update`, `hr_configuration.activate`, `hr_configuration.delete`, `hr_configuration.restore`) and logs all audit events (`HR_CONFIG_CREATE`, `HR_CONFIG_UPDATE`, `HR_CONFIG_ACTIVATE`, `HR_CONFIG_DELETE`, `HR_CONFIG_RESTORE`).

### Future HR Module Integrations
- **Attendance Module**: Consumes `timezone`, `standard_working_hours_per_day`, `grace_period_minutes`, and `minimum_working_hours` for calculating late arrivals and half-day credits.
- **Leave Module**: Consumes `weekend_configuration` and `leave_year_start_month` for calculating working day leave deductions and annual quota resets.
- **Payroll Module**: Consumes `currency`, `payroll_cycle`, and `fiscal_year_start_month` for pay run frequency and tax year reporting.
- **Recruitment Module**: Consumes `default_probation_period_days` when onboarding new hires.

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
│   │       └── endpoints/    # Route handlers (audit, auth, departments, employee_documents, employees, files, health, hr_configurations, notifications, positions, rbac, root, templates)
│   ├── core/                 # App configuration, logging, events, security, storage & Celery
│   ├── db/                   # Database session and connection setup
│   ├── models/               # SQLAlchemy ORM models (User, Role, AuditLog, File, Notification, Department, Employee, EmployeeDocument, Position, HRConfiguration, etc.)
│   ├── repositories/         # Clean Architecture repository layer (DepartmentRepository, EmployeeRepository, PositionRepository, HRConfigurationRepository, etc.)
│   ├── schemas/              # Pydantic v2 data models & validation (HRConfigurationCreate, HRConfigurationResponse, etc.)
│   ├── services/             # Clean Architecture business service layer (DepartmentService, EmployeeService, PositionService, HRConfigurationService, etc.)
│   ├── tasks/                # Centralized Celery task registry (department_tasks, employee_tasks, document_tasks, position_tasks, hr_config_tasks, system_tasks)
│   └── main.py               # FastAPI application entrypoint
├── docker/                   # Docker deployment configurations
├── docs/                     # Architecture Decision Records (ADRs)
│   └── adr/                  # ADR documents (ADR-0001 Redis, ADR-0002 Celery, ADR-0003 Department, ADR-0004 Employee, ADR-0005 Employee Documents, ADR-0006 Position Management, ADR-0007 HR Configuration)
├── workers/                  # Celery worker process entrypoints
├── tests/                    # Pytest test suite (test_hr_configurations.py, test_positions.py, test_employee_documents.py, test_employees.py, test_departments.py, test_celery.py, etc.)
├── uploads/                  # Local storage root directory
├── CHANGELOG.md              # Project release notes & changelog
├── requirements.txt          # Python production dependencies
└── README.md                 # Project documentation
```

---

## API Endpoints Overview

| HTTP Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/hr/configuration` | Retrieve active HR configuration policy | Yes (`hr_configuration.read`) |
| `GET` | `/api/v1/hr/configurations/{id}` | Retrieve HR configuration details by ID | Yes (`hr_configuration.read`) |
| `POST` | `/api/v1/hr/configuration` | Define new HR configuration policy | Yes (`hr_configuration.create`) |
| `PUT` | `/api/v1/hr/configuration/{id}` | Update HR configuration policy parameters | Yes (`hr_configuration.update`) |
| `PATCH` | `/api/v1/hr/configuration/{id}/activate` | Activate target HR configuration policy | Yes (`hr_configuration.activate`) |
| `DELETE` | `/api/v1/hr/configuration/{id}` | Soft delete inactive HR configuration policy | Yes (`hr_configuration.delete`) |
| `PATCH` | `/api/v1/hr/configuration/{id}/restore` | Restore soft-deleted HR configuration policy | Yes (`hr_configuration.restore`) |
| `GET` | `/api/v1/positions` | Paginated list of job positions | Yes (`position.read`) |
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
