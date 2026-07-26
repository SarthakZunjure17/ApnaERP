# Changelog

All notable changes to the **ApnaERP** platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v0.3.0] - 2026-07-26

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
