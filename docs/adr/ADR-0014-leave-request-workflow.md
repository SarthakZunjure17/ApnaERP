# ADR-0014: Enterprise Leave Request Workflow Engine Architecture

## Status
Accepted

## Context
Enterprise HR platforms require a robust, workflow-driven leave request engine that enforces state machine transitions, excludes non-working days (weekends and holidays), validates organizational leave policies, prevents request overlaps, updates leave balances upon approval, and provides full auditability.

## Decision
1. **Workflow State Machine**:
   - Strictly enforced state transitions:
     - `Draft` -> `Pending` (Submission)
     - `Pending` -> `Approved` (Approval)
     - `Pending` -> `Rejected` (Rejection)
     - `Approved` -> `Cancelled` (Cancellation prior to start date)
     - `Approved` -> `Completed` (Completion after end date)
   - Terminal States: `Rejected`, `Cancelled`, `Completed`. Invalid state transitions are rejected with `INVALID_WORKFLOW_TRANSITION`.
2. **Working Day Calculation Engine**:
   - Automatically calculates net working days between `start_date` and `end_date` inclusive, excluding Saturdays, Sundays, and organizational `Holiday` records.
   - Half-day requests set `total_days = 0.5`.
3. **Policy Enforcement**:
   - Half-day permission check (`leave_type.allow_half_day`).
   - Max consecutive days check (`total_days <= leave_type.max_consecutive_days`).
   - Gender restriction check (`leave_type.gender_restriction`).
   - Overlap prevention: Active requests (`Pending` or `Approved`) overlapping dates are rejected (`OVERLAPPING_LEAVE_REQUEST`).
4. **Leave Balance Integration**:
   - Verifies available leave balance prior to submission and approval (`INSUFFICIENT_LEAVE_BALANCE`).
   - Upon `Approved` transition, updates `LeaveBalance.availed_days` by `total_days` and recalculates `remaining_days`.
   - Upon `Cancelled` transition of an approved request, restores `LeaveBalance.availed_days`.
5. **Caching & Telemetry**:
   - Redis caching (`leave_request:employee:{emp_id}:*`, `leave_request:pending:*`).
   - Audit logging via `log_audit` for all workflow transitions (`LEAVE_REQUEST_CREATE`, `LEAVE_REQUEST_SUBMIT`, `LEAVE_REQUEST_APPROVE`, `LEAVE_REQUEST_REJECT`, `LEAVE_REQUEST_CANCEL`, `LEAVE_REQUEST_COMPLETE`).
   - Background Celery notifications (`send_leave_request_notification_task`).

## Consequences
- Provides an authoritative leave application and approval workflow foundation.
- Guarantees data consistency with Leave Balances, Attendance, and Holiday Calendar modules.
- Prepares the platform for future multi-level approval routing, calendar synchronization, and Payroll leave deduction integration.
