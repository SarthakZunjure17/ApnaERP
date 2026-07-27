# ADR-0010: Enterprise Attendance Engine & Business Rules Architecture

## Status
Accepted

## Context
In an Enterprise Resource Planning (ERP) platform, daily attendance tracking must do far more than store raw check-in/out timestamps. Attendance evaluation must dynamically compute tardiness, early departures, effective working hours, half-day thresholds, missing check-in/out flags, weekend schedules, and official holiday observations across multi-region workforces.

Milestone HR-8 introduces the **Enterprise Attendance Engine** (`AttendanceEngine` domain service, `Attendance` model) as a pure, deterministic business rules engine powering attendance processing across ApnaERP.

## Decision

1. **Domain Engine Architecture (`AttendanceEngine`)**:
   - Implemented as a standalone, deterministic domain service (`app/services/attendance_engine.py`) independent of FastAPI HTTP controllers.
   - Evaluates attendance status and calculated metrics (`worked_minutes`, `expected_minutes`, `late_minutes`, `early_departure_minutes`) by synthesizing four distinct domain inputs:
     - `Employee`: Identity, active status, country/region, and assigned shift.
     - `Shift`: Start time, end time (with overnight shift support), break duration, grace period, and minimum working hours.
     - `Holiday Calendar`: Official holiday lookup for target date and employee location.
     - `HR Configuration`: Organization timezone, weekend configuration (e.g. `["Saturday", "Sunday"]`), standard working hours, and default grace period.

2. **Attendance State Machine**:
   - Status classifications: `Present`, `Late`, `Half Day`, `Absent`, `Holiday`, `Weekend`, `On Leave`, `Missing Check-in`, `Missing Check-out`.

3. **Overnight Shift Calculations**:
   - Handles shifts spanning midnight (`end_time <= start_time`, e.g. 22:00 to 06:00).
   - Dynamically constructs the shift reference window spanning `[attendance_date, attendance_date + 1 day]`, correctly evaluating late check-ins and early departures across day boundaries.

4. **Locked Attendance Guard**:
   - Attendance records locked (`is_locked = True`) for payroll processing cannot be edited, re-evaluated, check-in/out updated, or manually corrected. Modifying locked records raises HTTP 400 (`ATTENDANCE_LOCKED`).

5. **Future Module Integration Contracts**:
   - **Leave Module**: When an approved leave request covers an attendance date, the engine assigns `attendance_status = "On Leave"`, overriding default `Absent` evaluations.
   - **Payroll Module**: Reads `worked_minutes`, `expected_minutes`, `late_minutes`, `early_departure_minutes`, and `attendance_status` from locked attendance records to calculate monthly salary deductions, overtime pay multipliers, and attendance allowances.

6. **Caching & Asynchronous Notifications**:
   - Multi-level Redis caching (`attendance:today`, `attendance:monthly:{emp_id}:{year}:{month}`).
   - Asynchronous Celery background task `send_attendance_notification_task` for late arrival alerts, missing check-outs, and manual correction audit events.

## Consequences
- Establishes a pure, reusable, deterministic business rules engine isolated from API framework dependencies.
- Prevents invalid or fraudulent check-in modifications on finalized payroll periods via immutable lock guards.
- Provides complete auditability for all manual HR corrections with required justification notes.
