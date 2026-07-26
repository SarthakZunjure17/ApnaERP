# ADR-0008: Enterprise Shift Management & Workforce Schedule Architecture

## Status
Accepted

## Context
As ApnaERP expands into core HR domains, workforce scheduling is required to establish baseline time parameters. Future modules such as Attendance (evaluating work hours, tardiness, and grace period compliance), Payroll (calculating overtime thresholds and shift differential pay), and Shift Roster Planning will rely on standardized shift schedule definitions.

Prior to Milestone HR-6, employee scheduling rules were unassigned, leaving working hour baselines implicitly bound to organization-wide defaults. To support enterprise workforce requirements, ApnaERP requires reusable, structured shift schedule entities (`Shift` model) with nullable assignment to core `Employee` records (`shift_id` FK).

## Decision

1. **Shift Schedule Entity Structure**:
   - `Shift` model defined with unique, indexed `code` (e.g., `SHIFT-DAY-01`) and `name` (e.g., `Morning Shift`).
   - Time boundaries: `start_time` and `end_time` (`datetime.time`).
   - Operational parameters: `break_duration_minutes`, `grace_period_minutes`, `minimum_working_hours` (half-day threshold), `maximum_working_hours` (overtime cap), `is_night_shift`, `is_flexible_shift`, and `is_active`.

2. **Overnight Shift Calculation Algorithm**:
   - Overnight shifts spanning across midnight (`end_time <= start_time`, e.g., 22:00:00 to 06:00:00) are automatically detected by the service layer and `Shift.duration_hours` property using standard modulo arithmetic:
     $$\text{Duration} = \frac{(24 \times 3600 - \text{start\_seconds}) + \text{end\_seconds}}{3600}$$
   - When `end_time <= start_time`, the `is_night_shift` flag is enforced/auto-set to `True`.

3. **Validation & Business Sanity Rules**:
   - `break_duration_minutes`: Break duration in hours must be strictly less than total shift duration.
   - `grace_period_minutes`: Grace period in hours must be strictly less than total shift duration.
   - `minimum_working_hours`: Must not exceed `maximum_working_hours`.
   - Code and Name: Case-insensitive unique checks against active and deleted records.

4. **Active Employee Shift Deletion Guard**:
   - `ShiftService.delete_shift(shift_id)` checks `ShiftRepository.get_assigned_employee_count(shift_id)`.
   - If active employees are assigned to the target shift (`count > 0`), soft-deletion is rejected with HTTP 400 (`ASSIGNED_EMPLOYEES_EXIST`).

5. **Nullable Employee Integration**:
   - `Employee` model extended with `shift_id` nullable FK referencing `shifts.id` (`ondelete="SET NULL"`).
   - If an employee has `shift_id = None`, downstream Attendance and Payroll modules fall back to organization defaults stored in `HRConfiguration`.

6. **Caching, Audit, & Async Telemetry**:
   - Redis caching (`shift:list`, `shift:detail:{id}`) with automatic invalidation on mutating operations.
   - Enterprise audit logging (`SHIFT_CREATE`, `SHIFT_UPDATE`, `SHIFT_DELETE`, `SHIFT_RESTORE`).
   - Celery background task `send_shift_notification_task` for event notification dispatch.

## Consequences
- Clean separation of shift schedule definitions from individual employee assignments.
- Foundation established for Attendance (calculating late arrivals against `grace_period_minutes` and half-day credits against `minimum_working_hours`) and Payroll (overtime calculations).
- Guarantees data integrity by preventing the removal of active shift definitions in use by employees.
