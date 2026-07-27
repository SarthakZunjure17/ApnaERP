# ADR-0018: Employee Compensation Management (Payroll-3)

## Status
Accepted

## Context
Enterprise payroll processing requires assigning Salary Structure templates to individual employees with complete effective date history, revision tracking, and state management (`Draft`, `Active`, `Expired`, `Cancelled`).

Future payroll calculation engines must depend exclusively on this module to identify the active compensation policy, annual CTC, and gross salary for any given pay period.

## Decision
We implemented `EmployeeCompensation` ORM model (`app/models/employee_compensation.py`) and service layer (`app/services/employee_compensation.py`).

### Key Architectural Attributes
1. **Single Active Compensation Policy**:
   - Only ONE compensation policy can be `Active` for an employee at any point in time.
   - Activating a new compensation policy (`activate_compensation`) automatically sets the currently active policy status to `Expired` and sets its `effective_to` date.
2. **Revision History Tracking**:
   - Salary revisions (`revise_compensation`) link to `previous_compensation_id` and automatically increment `revision_number = previous.revision_number + 1`.
3. **Effective Date Overlap Prevention**:
   - `check_overlapping_effective_dates` prevents overlapping date ranges for the same employee across active/draft compensation policies.
4. **Approval & Activation Audit**:
   - Records `approved_by` (User ID) and `approved_at` timestamp upon activation.
5. **Platform Integration**:
   - Redis Caching: Invalidation of `employee_compensation:*` keys upon assignment, revision, activation, or cancellation.
   - Audit Logging: Tracks `COMPENSATION_ASSIGN`, `COMPENSATION_REVISE`, `COMPENSATION_ACTIVATE`, `COMPENSATION_CANCEL`, `COMPENSATION_UPDATE`, `COMPENSATION_DELETE`, and `COMPENSATION_RESTORE`.
   - Background Telemetry: Celery notification task `send_compensation_notification_task` alerts HR Administrators and Employees.

## Consequences
- Authoritative source of employee compensation policies for future Payroll Runs, Payslips, and Tax Engines.
- Complete historical record of salary revisions per employee.
- Zero ambiguity regarding active salary structure for any payroll cycle.
