# Changelog

All notable changes to the **ApnaERP** platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v0.3.0] - 2026-07-26

### Milestone HR-5 — HR Configuration & Organization Policies

#### Added
- **HRConfiguration ORM Model (`app/models/hr_configuration.py`)**: Centralized organization-wide policy model storing organization name, organization code, IANA timezone, country, currency ISO code, standard daily working hours, standard weekly working days, weekend configuration JSON, default shift name, grace period minutes, minimum working hours for half-day credit, default probation period days, leave year start month, payroll cycle frequency (`Monthly`, `Biweekly`, `Weekly`), fiscal year start month, active status flag, and soft deletion.
- **Pydantic v2 Schemas (`app/schemas/hr_configuration.py`)**: `PayrollCycle` Enum, `HRConfigurationCreate`, `HRConfigurationUpdate`, `HRConfigurationResponse`, `HRConfigurationListResponse`.
- **HRConfiguration Repository (`app/repositories/hr_configuration.py`)**: Extends `BaseRepository` with `get_active_configuration`, `get_by_organization_code`, and `deactivate_all_active_configurations`.
- **HRConfiguration Service Layer (`app/services/hr_configuration.py`)**: Business service implementing IANA timezone validation (`zoneinfo`), weekend day name checks, working hours sanity checks (`minimum_working_hours <= standard_working_hours_per_day`), currency ISO validation, singleton active configuration enforcement (deactivates previous active configuration when activating a new policy), active policy deletion guard (`ACTIVE_CONFIG_DELETION_PROHIBITED`), Redis caching (`hr_configuration:active`), audit logging (`HR_CONFIG_CREATE`, `HR_CONFIG_UPDATE`, `HR_CONFIG_ACTIVATE`, `HR_CONFIG_DELETE`, `HR_CONFIG_RESTORE`), and Celery telemetry.
- **Background Notification Task (`app/tasks/hr_config_tasks.py`)**: Asynchronous Celery task (`send_hr_config_notification_task`) processing HR configuration creation, update, and activation events.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Added permissions `hr_configuration.read`, `hr_configuration.create`, `hr_configuration.update`, `hr_configuration.activate`, `hr_configuration.delete`, `hr_configuration.restore` bound to `Super Admin` and `HR Manager` roles.
- **HR Configuration API Router (`app/api/v1/endpoints/hr_configurations.py`)**: RESTful endpoints (`GET /hr/configuration`, `GET /hr/configurations/{id}`, `POST /hr/configuration`, `PUT /hr/configuration/{id}`, `PATCH /hr/configuration/{id}/activate`, `DELETE /hr/configuration/{id}`, `PATCH /hr/configuration/{id}/restore`).
- **Database Migration (`alembic/versions/f3515986f924_phase_hr5_implement_hr_configurations_.py`)**: Applied database migration for `hr_configurations` table.
- **Architecture Decision Record (`docs/adr/ADR-0007-hr-configuration.md`)**: Documented single source of truth architecture, singleton active policy pattern, active deletion guard, and integration contracts for future HR modules (Attendance, Leave, Payroll, Recruitment, Performance, Shift Scheduling).
- **Test Suite (`tests/test_hr_configurations.py`)**: Comprehensive pytest test suite validating repository methods, service validations, singleton active enforcement, active policy deletion guard, REST API endpoints, RBAC authorization, audit logging, Redis caching, Celery telemetry, and full regression across all 80+ platform tests.

---

### Milestone HR-4 — Job Positions & Employment Structure

#### Added
- **Position ORM Model (`app/models/position.py`)**: Enterprise job position model supporting unique code, title, department link, parent position self-referential hierarchy, employment category (`Permanent`, `Contract`, `Temporary`, `Internship`), grade, level, maximum/current headcount capacity, managerial flag, active status, and soft deletion.
- **Employee Extension (`app/models/employee.py`)**: Extended `Employee` model with `position_id` (FK to `positions.id`), `employment_start_date`, `employment_end_date`, and `position` relationship.
- **Pydantic v2 Schemas (`app/schemas/position.py`)**: `PositionCreate`, `PositionUpdate`, `PositionResponse`, `PositionSummary`, `PositionTreeResponse`, `PositionListResponse`, and `EmploymentCategory` Enum. Updated `app/schemas/employee.py`.
- **Position Repository (`app/repositories/position.py`)**: Extends `BaseRepository` with `get_by_code`, `get_by_department_and_title`, `get_by_department`, `get_children`, `get_tree`, and `exists_by_code`.
- **Position Service Layer (`app/services/position.py`)**: Business service layer enforcing unique code/title validation, inactive/deleted department guards, circular position loop checks (`_validate_no_circular_position`), headcount constraints (`maximum_headcount` vs `current_headcount`), Redis tree caching (`position:tree`), audit logging (`POSITION_CREATE`, `POSITION_UPDATE`, `POSITION_DELETE`, `POSITION_RESTORE`), and Celery telemetry.
- **Employee Service Integration (`app/services/employee.py`)**: Integrated automatic position headcount increments/decrements upon employee assignment, removal, or update. Enforces `HEADCOUNT_LIMIT_EXCEEDED` guard.
- **Background Notification Task (`app/tasks/position_tasks.py`)**: Asynchronous task (`send_position_notification_task`) processing position mutation and headcount limit warning notifications.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Added `position.create`, `position.read`, `position.update`, `position.delete`, `position.restore` permissions bound to `Super Admin` and `HR Manager` roles.
- **Position API Router (`app/api/v1/endpoints/positions.py`)**: Exposed RESTful endpoints (`GET /positions`, `GET /positions/{id}`, `GET /positions/tree`, `GET /departments/{department_id}/positions`, `POST /positions`, `PUT /positions/{id}`, `DELETE /positions/{id}`, `PATCH /positions/{id}/restore`).
- **Database Migration (`alembic/versions/7178a901bcde_phase_hr4_implement_positions_table_and_.py`)**: Applied migration for `positions` table and `employees` extensions.
- **Architecture Decision Record (`docs/adr/ADR-0006-position-management.md`)**: Documented decision, headcount capacity controls, position hierarchy, and future module integration.
- **Test Suite (`tests/test_positions.py`)**: Built comprehensive pytest test suite verifying repository methods, service validations, circular hierarchy checks, headcount constraint enforcement, auto-increment/decrement on employee assignment, Redis caching, Celery tasks, RBAC, and API endpoints.

---

### Milestone HR-3 — Employee Documents & Digital Personnel Files

#### Added
- **EmployeeDocument ORM Model (`app/models/employee_document.py`)**: Digital personnel document model linking `Employee` and `File` entities, supporting document types (`Aadhaar`, `PAN`, `Passport`, `Driving License`, `Resume`, `Offer Letter`, `Contract`, `NDA`, etc.), verification status (`Pending`, `Verified`, `Rejected`), verifier user link, timestamps, notes, mandatory flags, and soft deletion.
- **Pydantic v2 Schemas (`app/schemas/employee_document.py`)**: `EmployeeDocumentCreate`, `EmployeeDocumentUpdate`, `EmployeeDocumentResponse`, `EmployeeDocumentListResponse`, `DocumentVerifyRequest`, `DocumentRejectRequest`, `DocumentType`, and `VerificationStatus` Enums.
- **EmployeeDocument Repository (`app/repositories/employee_document.py`)**: Extends `BaseRepository` with `get_by_employee`, `get_by_file`, `exists_mandatory_document_type`, and `get_expiring_documents`.
- **EmployeeDocument Service Layer (`app/services/employee_document.py`)**: Business service implementing active employee and storage file validation, date sanity (`expiry_date >= issue_date`), duplicate mandatory document protection, verification and rejection workflows (`verify_document`, `reject_document`), Redis caching (`employee_document:list:{id}`), audit logging (`DOCUMENT_UPLOAD`, `DOCUMENT_VERIFY`, `DOCUMENT_REJECT`, etc.), and background Celery task dispatching.
- **Background Notification Task (`app/tasks/document_tasks.py`)**: Asynchronous task (`send_document_notification_task`) processing document upload, verification, and rejection background notifications.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Added `employee_document.create`, `employee_document.read`, `employee_document.update`, `employee_document.delete`, `employee_document.verify`, `employee_document.restore` permissions bound to `Super Admin` and `HR Manager` roles.
- **Employee Document API Router (`app/api/v1/endpoints/employee_documents.py`)**: RESTful endpoints (`GET /employee-documents`, `GET /employee-documents/{id}`, `GET /employees/{employee_id}/documents`, `POST /employee-documents`, `PUT /employee-documents/{id}`, `DELETE /employee-documents/{id}`, `PATCH /employee-documents/{id}/restore`, `PATCH /employee-documents/{id}/verify`, `PATCH /employee-documents/{id}/reject`).
- **Database Migration (`alembic/versions/903d8105712c_phase_hr3_implement_employee_documents_.py`)**: Applied migration for `employee_documents` table.
- **Architecture Decision Record (`docs/adr/ADR-0005-employee-documents.md`)**: Documented digital personnel files architecture, verification workflow, and storage provider reuse.
- **Test Suite (`tests/test_employee_documents.py`)**: Built comprehensive pytest test suite verifying repository methods, service validations, verification/rejection workflow, mandatory document check, Redis caching, Celery tasks, RBAC, and API endpoints.

---

### Milestone HR-2 — Enterprise Employee Domain (Core)

#### Added
- **Employee ORM Model (`app/models/employee.py`)**: Core `Employee` model featuring employee code, work/personal email, department assignment, manager reporting link, employment type (`Full Time`, `Part Time`, `Contract`, `Intern`), status (`Active`, `Probation`, `Notice Period`, `Suspended`, `Resigned`, `Terminated`), dates, profile photo file reference, and soft deletion.
- **Pydantic v2 Schemas (`app/schemas/employee.py`)**: `EmployeeCreate`, `EmployeeUpdate`, `EmployeeResponse`, `EmployeeSummary`, `EmployeeListResponse`, `EmployeeHierarchyResponse`, and `EmploymentType`/`EmploymentStatus` Enums.
- **Employee Repository (`app/repositories/employee.py`)**: Extends `BaseRepository` with `get_by_code`, `get_by_work_email`, `get_by_user_id`, `get_by_department`, `get_direct_reports`, and existence check methods.
- **Employee Service Layer (`app/services/employee.py`)**: Business service layer implementing unique code/email checks, date sanity checks (`joining_date` <= `exit_date`), self-management prevention, circular manager reporting hierarchy loop validation, active department validation, Redis caching (`employee:hierarchy`, `employee:department:{id}`), audit logging, and background Celery task dispatching.
- **Background Notification Task (`app/tasks/employee_tasks.py`)**: Asynchronous task (`send_employee_notification_task`) processing employee creation, update, and deletion background event notifications.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Added `employee.create`, `employee.read`, `employee.update`, `employee.delete`, `employee.restore` permissions bound to `Super Admin` and `HR Manager` roles.
- **Employee API Router (`app/api/v1/endpoints/employees.py`)**: RESTful endpoints (`GET /employees/hierarchy`, `GET /employees/department/{department_id}`, `GET /employees`, `GET /employees/{id}`, `POST /employees`, `PUT /employees/{id}`, `DELETE /employees/{id}`, `PATCH /employees/{id}/restore`).
- **Database Migration (`alembic/versions/d04dad64b43e_phase_hr2_implement_employees_table.py`)**: Applied migration for `employees` table.
- **Architecture Decision Record (`docs/adr/ADR-0004-employee-domain.md`)**: Documented decision, trade-offs, and future module integration points.
- **Test Suite (`tests/test_employees.py`)**: Built comprehensive test suite covering repository operations, service validations, circular reporting checks, inactive department checks, Redis caching, Celery tasks, RBAC, and API endpoints.

---

### Milestone HR-1 — Department Management Module

#### Added
- **Department ORM Model (`app/models/department.py`)**: `Department` model supporting self-referential parent-child relationships, manager assignments, unique code/name constraints, soft deletion, and timestamp tracking.
- **Pydantic v2 Schemas (`app/schemas/department.py`)**: Created `DepartmentCreate`, `DepartmentUpdate`, `DepartmentResponse`, `DepartmentSummary`, `DepartmentTreeResponse`, and `DepartmentListResponse`.
- **Department Repository (`app/repositories/department.py`)**: Implemented `DepartmentRepository` extending `BaseRepository` with `get_by_code`, `get_by_name`, `get_children`, `get_tree`, `exists_by_code`, `exists_by_name`.
- **Department Service Layer (`app/services/department.py`)**: Business service enforcing unique code/name validation, circular parent reference prevention, active child deletion protection, Redis caching (`department:tree`), audit logging, and background Celery task dispatching.
- **Background Notification Task (`app/tasks/department_tasks.py`)**: Asynchronous Celery task (`send_department_notification_task`) processing department mutation notifications.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Added `department.create`, `department.read`, `department.update`, `department.delete`, `department.restore` permissions bound to `Super Admin` and `HR Manager` roles.
- **Department API Router (`app/api/v1/endpoints/departments.py`)**: Exposed RESTful endpoints (`GET /departments/tree`, `GET /departments`, `GET /departments/{id}`, `POST /departments`, `PUT /departments/{id}`, `DELETE /departments/{id}`, `PATCH /departments/{id}/restore`).
- **Database Migration (`alembic/versions/d45778acc419_phase_hr1_implement_departments_table.py`)**: Created and applied Alembic migration for `departments` table.
- **Architecture Decision Record (`docs/adr/ADR-0003-department-domain.md`)**: Documented design drivers, decision, and trade-offs.
- **Test Suite (`tests/test_departments.py`)**: Built comprehensive pytest test suite verifying repository, service, circular reference validation, child deletion guard, Redis caching, audit logging, Celery integration, and API endpoints.

---

## [v0.2.2] - 2026-07-26

### Milestone 0.2.2 — Enterprise Task Processing Platform (Celery Infrastructure)

#### Added
- **Celery Application Infrastructure (`app/core/celery.py`)**: Configured Celery application instance (`celery_app`) with JSON serialization, Kombu priority queues (`default`, `high_priority`, `low_priority`, `periodic`), and task routing.
- **Reusable Task Base Classes (`app/tasks/base.py`)**: Implemented `BaseTask`, `RetryTask`, `PeriodicTask`, and `LoggingTask`.
- **Infrastructure System Tasks (`app/tasks/system_tasks.py`)**: Implemented `system_ping_task` and `system_health_check_task`.
- **Health Telemetry Endpoints (`app/api/v1/endpoints/health.py`)**: Added `GET /health/celery` and `GET /health/workers`.

---

## [v0.2.1] - 2026-07-26

### Milestone 0.2.1 — Redis Infrastructure

#### Added
- **Redis Infrastructure Layer (`app/core/redis.py`)**: Implemented `RedisManager` with `redis.asyncio` connection pooling and operation wrappers.

---

## [v0.2.0] - 2026-07-26

### Core Platform Infrastructure

#### Added
- Authentication, RBAC, Generic CRUD Framework, Enterprise Audit Logging, File Management Service, Notification System.
