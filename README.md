# ApnaERP - Enterprise Resource Planning Backend API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Celery](https://img.shields.io/badge/Celery-5.4+-37B24D.svg?style=flat&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D.svg?style=flat&logo=redis&logoColor=white)](https://redis.io)

ApnaERP is a production-grade, modular, high-performance Enterprise Resource Planning (ERP) backend built using Python, FastAPI, PostgreSQL, Redis, Celery, Alembic, JWT, Role-Based Access Control (RBAC), Generic CRUD Framework, Enterprise Audit Logging, Enterprise File Management, Enterprise Notification System, Enterprise Celery Task Processing Platform, Department Management Module, Core Employee Domain, Digital Personnel Files (Employee Documents), Job Positions & Employment Structure, HR Configuration & Organization Policies, Enterprise Shift Management, Enterprise Holiday Calendar, Enterprise Attendance Engine, Enterprise Salary Components, Enterprise Salary Structures, Employee Compensation Management, Enterprise Payroll Processing Engine, Enterprise Payroll Runs & Payslips, and Docker.

## Payroll Domain — Enterprise Payroll Runs & Payslips (Milestone Payroll-5 v0.5.4)

### Overview
The Enterprise Payroll Runs & Payslips module (`app/models/payroll_run.py`, `app/models/payslip.py`, `app/services/payroll_run.py`, `app/utils/pdf_generator.py`) organizes batch execution runs and generates ReportLab PDF payslip documents with File Storage integration and publication security controls.

### Key Technical Capabilities
- **Batch Execution (`PayrollRun`)**: Groups payroll executions by `Run Type` (`Regular`, `Off Cycle`, `Adjustment`) with unique constraint `(payroll_period_id, run_type)` and lifecycle states (`Draft`, `Processing`, `Completed`, `Locked`).
- **ReportLab PDF Payslip Generation**: Generates clean PDF payslips in memory (`generate_payslip_pdf_bytes`) formatted with company branding, employee details, period info, itemized earnings/deductions, gross/net totals, disclaimers, and currency formatting.
- **File Storage Integration**: Stores PDF files via `FileService.upload_bytes()` with SHA256 checksum deduplication and `File` record linking (`pdf_file_id`).
- **Publication Workflow & Immutability**: Manages payslip state (`Draft` -> `Generated` -> `Published`). Employees access and download PDF streams (`/api/v1/payslips/{id}/download`) only after payslips are explicitly published by HR/Payroll Managers.
- **Permanent Lock Guard**: Locking a `PayrollRun` (`status = "Locked"`) permanently prevents further execution or payslip modification.
- **Redis Caching & Celery Telemetry**: Real-time Redis caching (`payroll_run:*`, `payslip:*`), audit logging (`PAYROLL_RUN_*`, `PAYSLIP_*`), and background Celery notification tasks (`send_payroll_run_notification_task`, `send_payslip_published_notification_task`).
- **RBAC Security**: Protected by permissions (`payroll_run.create`, `payroll_run.read`, `payroll_run.update`, `payroll_run.lock`, `payslip.generate`, `payslip.publish`, `payslip.read`).

---

## Payroll Domain — Enterprise Payroll Processing Engine (Milestone Payroll-4 v0.5.3)

### Overview
The Enterprise Payroll Processing Engine (`app/models/payroll_period.py`, `app/services/payroll_engine.py`) generates and stores employee payroll records for processing periods by combining active `EmployeeCompensation` policies, `SalaryStructureComponent` definitions, `Attendance` logs (present vs half-days), and `LeaveRequest` approvals (paid vs unpaid leave).

### Key Technical Capabilities
- **Payroll Period Lifecycle**: Creates and manages processing cycles (`period_code`, `start_date`, `end_date`, `status`: `Draft`, `Processing`, `Completed`, `Locked`).
- **Attendance & Leave Proration**: Computes proration ratios based on attendance present days and approved paid leave days against total period working days.
- **Line-Item Component Breakdown**: Calculates exact line-item earnings and deductions (`PayrollRecordComponent`) derived from active salary structure templates.
- **Single Record & Period Lock Semantics**: Enforces `unique(payroll_period_id, employee_id)` and prevents any recalculation or modification on `Locked` periods.
- **Redis Caching & Celery Telemetry**: Real-time Redis caching (`payroll:*`), audit logging (`PAYROLL_*`), and background notification dispatch (`send_payroll_notification_task`).
- **RBAC Security**: Protected by permissions (`payroll.generate`, `payroll.read`, `payroll.approve`, `payroll.lock`).

---

## Payroll Domain — Employee Compensation Management (Milestone Payroll-3 v0.5.2)

### Overview
The Employee Compensation Management module (`app/models/employee_compensation.py`, `app/services/employee_compensation.py`) assigns Salary Structure templates to employees while maintaining complete effective date history, revision tracking, and state transitions (`Draft`, `Active`, `Expired`, `Cancelled`).

### Key Technical Capabilities
- **Employee Compensation Policies**: Assigns `SalaryStructure` templates to employees with `annual_ctc`, `monthly_gross_salary`, `effective_from`, and `effective_to`.
- **Single Active Policy Enforcement**: Enforces that only ONE compensation policy can be `Active` per employee. Activating a new policy automatically sets the previous active policy status to `Expired`.
- **Revision Tracking**: Links compensation revisions to `previous_compensation_id` and automatically increments `revision_number`.
- **Date Overlap Prevention**: Prevents overlapping effective date ranges for the same employee across active/draft compensation policies.
- **Redis Caching & Celery Telemetry**: Real-time Redis caching (`employee_compensation:*`), audit logging (`COMPENSATION_*`), and background notification dispatch (`send_compensation_notification_task`).
- **RBAC Security**: Protected by permissions (`compensation.create`, `compensation.read`, `compensation.update`, `compensation.activate`, `compensation.cancel`, `compensation.delete`).

---

## Payroll Domain — Enterprise Salary Structures (Milestone Payroll-2 v0.5.1)

### Overview
The Enterprise Salary Structures module (`app/models/salary_structure.py`, `app/services/salary_structure.py`) provides reusable compensation template structures composed of multiple ordered Salary Components with baseline values and optional overrides.

### Key Technical Capabilities
- **Reusable Compensation Templates**: Structure templates (`code`, `name`, `currency`, `effective_from`, `effective_to`) ready for employee assignment.
- **Component Mapping & Ordering**: Maps `SalaryComponent` instances to `SalaryStructure` with explicit `component_order` and baseline `component_value`.
- **Component Duplication Prevention**: Enforces `unique(salary_structure_id, salary_component_id)` to prevent component duplication within the same structure.
- **Effective Date Validation**: Validates `effective_to >= effective_from`.
- **Redis Caching & Celery Telemetry**: Real-time Redis caching (`salary_structure:*`), audit logging (`SALARY_STRUCTURE_*`), and background notification dispatch (`send_payroll_structure_notification_task`).
- **RBAC Security**: Protected by permissions (`salary_structure.create`, `salary_structure.read`, `salary_structure.update`, `salary_structure.delete`, `salary_structure.restore`).

---

## Payroll Domain — Enterprise Salary Components (Milestone Payroll-1 v0.5.0)

### Overview
The Enterprise Salary Components module (`app/models/salary_component.py`, `app/services/salary_component.py`) provides an organization-wide catalog defining payroll building blocks (Earnings: Basic, HRA, Allowances, Bonus; Deductions: PF, ESI, Professional Tax, Income Tax).

### Key Technical Capabilities
- **Organization-Wide Component Catalog**: Standardized component definitions decoupled from individual employee records.
- **Categorization & Calculation Methods**:
  - `type`: `Earning` or `Deduction`.
  - `calculation_method`: `Fixed`, `Percentage`, or `Formula` (reserved for future calculation evaluation).
- **Statutory & Tax Rule Indicators**: Flags for `is_taxable`, `is_pf_applicable`, `is_esi_applicable`.
- **Display Ordering & Uniqueness Rules**: Enforces unique `code`, unique `name`, and unique `display_order` across active components.
- **Calculation Validation Rules**: Validates that `Percentage` calculation method includes valid `percentage_value` (0.01 to 100.0) and `Fixed` includes valid `default_value`.
- **Redis Caching & Celery Telemetry**: Real-time Redis caching (`salary_component:*`), audit logging (`SALARY_COMPONENT_CREATE/UPDATE/DELETE/RESTORE`), and background notification dispatch (`send_payroll_component_notification_task`).
- **RBAC Security**: Protected by permissions (`salary_component.create`, `salary_component.read`, `salary_component.update`, `salary_component.delete`, `salary_component.restore`).

---

## Platform Domain — Enterprise Approval Workflow Engine (Milestone Platform v0.4.5)

### Overview
The Enterprise Approval Workflow Engine (`app/models/approval_workflow.py`, `app/services/approval_engine.py`) provides a generic, domain-agnostic, reusable multi-step approval framework at the Platform layer. Any business domain module (Leave, Expense, Purchase Orders, Assets, Payroll, Inventory) plugs into this engine using `entity_type` and `entity_id`.

### Key Technical Capabilities
- **Generic Domain Decoupling**: Target business entities plug into the approval engine via `entity_type` and `entity_id` strings, maintaining zero dependency on domain-specific tables.
- **Sequenced Role-Based Approval Steps**: Multi-step workflows (`ApprovalStep`) enforce assigned `Role` authorization (`approver_role_id`) or superuser privileges for each sequential step.
- **Strict State Machine Workflow**:
  - `Draft` -> `Pending` (Step 1)
  - `Pending` (Step N) -> `Pending` (Step N+1) if more steps remain
  - `Pending` (Step N) -> `Approved` if no steps remain (Terminal State)
  - `Pending` (Step N) -> `Rejected` upon step rejection (Terminal State)
  - `Pending` (Step N) -> `Cancelled` upon submitter/admin cancellation (Terminal State)
  - Rejects invalid state transitions (`INVALID_WORKFLOW_TRANSITION`) and prevents step skipping.
- **Immutable Approval Audit History**: Every action (`Submitting`, `Approved Step`, `Rejected`, `Cancelled`, `Completed Workflow`) creates an unmodifiable `ApprovalHistory` record recording step number, action, performer, timestamp, and comments.
- **Redis Caching & Celery Telemetry**: Real-time Redis caching (`approval:request:*`), audit logging (`APPROVAL_WORKFLOW_START`, `APPROVAL_STEP_APPROVE`, `APPROVAL_STEP_REJECT`, `APPROVAL_WORKFLOW_CANCEL`), and Celery notification dispatch (`send_approval_notification_task`).
- **RBAC Security**: Protected by permissions (`workflow.create`, `workflow.read`, `workflow.update`, `workflow.delete`, `approval.read`, `approval.approve`, `approval.reject`).

---

## HR Domain — Enterprise Leave Request Workflow (Milestone HR-12)

### Overview
The Enterprise Leave Request Workflow module (`app/models/leave_request.py`, `app/services/leave_request.py`) provides a state-machine driven engine for employee leave applications, working day calculations, policy enforcement, overlap prevention, leave balance updating, and workflow notifications.

### Key Technical Capabilities
- **Strict State Machine Workflow**:
  - `Draft` -> `Pending` (Submission)
  - `Pending` -> `Approved` (Approval)
  - `Pending` -> `Rejected` (Rejection)
  - `Approved` -> `Cancelled` (Cancellation prior to start date)
  - Terminal States: `Rejected`, `Cancelled`, `Completed`. Rejects invalid transitions (`INVALID_WORKFLOW_TRANSITION`).
- **Working Day Calculation Engine**:
  - Automatically calculates net working days between `start_date` and `end_date` inclusive, excluding Saturdays, Sundays, and organizational `Holiday` records. Supports half-day applications (`total_days = 0.5`).
- **Policy & Overlap Validation Rules**:
  - Half-day permission check (`HALF_DAY_NOT_PERMITTED`).
  - Max consecutive days cap (`EXCEEDS_MAX_CONSECUTIVE_DAYS`).
  - Gender restriction validation (`GENDER_RESTRICTION_MISMATCH`).
  - Overlap prevention rejecting active overlapping leave applications (`OVERLAPPING_LEAVE_REQUEST`).
  - Leave balance validation (`INSUFFICIENT_LEAVE_BALANCE`).
- **Leave Balance Updating**:
  - Upon approval, automatically updates `LeaveBalance.availed_days` and recalculates `remaining_days`. Restores availed days if an approved leave is cancelled prior to start date.
- **Redis Caching & Celery Telemetry**:
  - Redis caching (`leave_request:employee:{emp_id}:*`), audit trails (`LEAVE_REQUEST_CREATE`, `LEAVE_REQUEST_SUBMIT`, `LEAVE_REQUEST_APPROVE`, `LEAVE_REQUEST_REJECT`, `LEAVE_REQUEST_CANCEL`, `LEAVE_REQUEST_COMPLETE`), and background notification dispatch (`send_leave_request_notification_task`).
- **RBAC Security**: Protected by permissions (`leave_request.create`, `leave_request.read`, `leave_request.submit`, `leave_request.approve`, `leave_request.reject`, `leave_request.cancel`).

---

## HR Domain — Enterprise Leave Balance Management (Milestone HR-11)

### Overview
The Enterprise Leave Balance Management module (`app/models/leave_balance.py`, `app/services/leave_balance.py`) serves as the authoritative single source of truth for employee leave availability across leave types and calendar years.

### Key Technical Capabilities
- **Mathematical Balance Derivation**: Automatically calculates available remaining leave days using:
  `remaining_days = opening_balance + allocated_days + earned_days + carried_forward_days - availed_days - encashed_days`.
- **Negative Balance Policy Guard**: Strictly prevents negative remaining balances (`NEGATIVE_LEAVE_BALANCE`) unless the target `LeaveType` explicitly enables `allow_negative_balance == True`.
- **Uniqueness & Carry Forward Enforcement**: Enforces composite uniqueness on `(employee_id, leave_type_id, leave_year)` and validates carry-forward caps against `LeaveType.max_carry_forward`.
- **Manual Balance Adjustments**: `PATCH /leave-balances/{id}/adjust` permits audited component adjustments (`allocated`, `earned`, `availed`, `encashed`, `opening`, `carried_forward`) with mandatory business justification.
- **Future Integration Ready**: Provides authoritative leave availability lookups for future Leave Application engines and Payroll Encashment/Deduction processing.
- **Redis Caching & Celery Telemetry**: Real-time Redis caching (`leave_balance:employee:{emp_id}:{year}`), audit trails (`LEAVE_BALANCE_CREATE`, `LEAVE_BALANCE_UPDATE`, `LEAVE_BALANCE_ADJUST`, `LEAVE_BALANCE_DELETE`, `LEAVE_BALANCE_RESTORE`), and background notification dispatch (`send_leave_balance_adjustment_notification_task`).
- **RBAC Security**: Protected by permissions (`leave_balance.create`, `leave_balance.read`, `leave_balance.update`, `leave_balance.adjust`, `leave_balance.delete`, `leave_balance.restore`).

---

## HR Domain — Enterprise Leave Types & Policies (Milestone HR-10)

### Overview
The Enterprise Leave Types & Policies module (`app/models/leave_type.py`, `app/services/leave_type.py`) provides an organization-wide policy registry defining leave rules, annual allocations, carry-forward caps, consecutive day limits, half-day permissions, approval requirements, and gender restrictions.

### Key Technical Capabilities
- **Reusable Policy Registry**: Defines entitlement policies (`Annual Leave`, `Sick Leave`, `Casual Leave`, `Maternity Leave`, `Paternity Leave`, `Work From Home`, `Unpaid Leave`) applicable across all enterprise employees.
- **Strict Business Validation Rules**:
  - Code & Name Uniqueness (`DUPLICATE_LEAVE_CODE`, `DUPLICATE_LEAVE_NAME`).
  - `annual_allocation >= 0`.
  - `max_carry_forward <= annual_allocation`.
  - If `carry_forward_allowed` is `False`, `max_carry_forward` must be `0`.
  - `max_consecutive_days > 0`.
- **Policy Restoration Support**: `PATCH /leave-types/{id}/restore` endpoint and `restore()` repository method for restoring soft-deleted policies.
- **Future Module Integration**: Designed for direct integration with Leave Request Engines, Leave Balance Calculation Services, and Payroll Overtime/Unpaid Leave Deduction systems.
- **Redis Caching & Celery Telemetry**: Automatic Redis caching (`leave_type:list`, `leave_type:detail:{id}`) with pattern invalidation, audit logging (`LEAVE_TYPE_CREATE`, `LEAVE_TYPE_UPDATE`, `LEAVE_TYPE_DELETE`, `LEAVE_TYPE_RESTORE`), and background notification dispatch (`send_leave_policy_change_notification_task`).
- **RBAC Security**: Protected by permissions (`leave_type.create`, `leave_type.read`, `leave_type.update`, `leave_type.delete`, `leave_type.restore`).

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
