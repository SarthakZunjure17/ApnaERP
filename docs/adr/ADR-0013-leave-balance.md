# ADR-0013: Enterprise Leave Balance Management Architecture

## Status
Accepted

## Context
Enterprise ERP systems require an authoritative single source of truth for employee leave availability. Milestone HR-11 introduces `LeaveBalance` records tracking opening balance, allocated days, earned accruals, availed days, encashment, and carried-forward days per employee, leave type, and calendar leave year.

## Decision
1. **Mathematical Balance Derivation**:
   - `remaining_days` is derived using the standard formula:
     `remaining_days = opening_balance + allocated_days + earned_days + carried_forward_days - availed_days - encashed_days`.
2. **Negative Balance Enforcement**:
   - `remaining_days < 0` is strictly prohibited unless the associated `LeaveType` explicitly permits `allow_negative_balance == True`.
3. **Carry Forward Constraints**:
   - `carried_forward_days` is validated against `LeaveType.max_carry_forward` and `LeaveType.carry_forward_allowed`.
4. **Data Integrity & Constraints**:
   - Composite unique constraint `(employee_id, leave_type_id, leave_year)` guarantees exactly one active balance record per employee-type-year combination.
5. **Caching & Telemetry**:
   - Redis caching with keys `leave_balance:employee:{emp_id}:{year}` and `leave_balance:detail:{id}`.
   - Audit logging via `log_audit` for `LEAVE_BALANCE_CREATE`, `LEAVE_BALANCE_UPDATE`, `LEAVE_BALANCE_ADJUST`, `LEAVE_BALANCE_DELETE`, `LEAVE_BALANCE_RESTORE`.
   - Asynchronous Celery task (`send_leave_balance_adjustment_notification_task`) broadcasting alerts to HR on manual adjustments.

## Consequences
- Provides real-time leave entitlement verification for future Leave Request Application and Approval engines.
- Ensures seamless integration with future Payroll Leave Encashment and Unpaid Leave Deduction processing.
- Maintains strict auditability and real-time cache consistency across enterprise organizational structures.
