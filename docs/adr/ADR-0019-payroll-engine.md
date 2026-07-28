# ADR-0019: Enterprise Payroll Processing Engine (Payroll-4)

## Status
Accepted

## Context
Enterprise payroll processing requires calculating gross salary, earnings, deductions, and net salary for all employees across discrete pay periods (`PayrollPeriod`).

The calculation must dynamically integrate active `EmployeeCompensation` structures, `SalaryStructureComponent` definitions, `Attendance` logs (present vs half-days), and `LeaveRequest` approvals (paid vs unpaid leave) to determine proration ratios.

## Decision
We implemented `PayrollPeriod`, `PayrollRecord`, and `PayrollRecordComponent` ORM models (`app/models/payroll_period.py`) and service layer (`app/services/payroll_engine.py`).

### Key Architectural Attributes
1. **Proration Ratio & Attendance/Leave Integration**:
   - Calculates total working days `(end_date - start_date + 1)`.
   - Proration Ratio = `(present_days + paid_leave_days) / working_days` (clamped 0 to 1.0).
   - Prorates baseline component amounts from `SalaryStructureComponent` definitions.
2. **Single Record Per Employee Per Period**:
   - Enforces unique constraint `(payroll_period_id, employee_id)` to prevent duplicate payroll records within the same processing period.
3. **Period Locking Semantics**:
   - Status transition: `Draft` -> `Processing` -> `Completed` -> `Locked`.
   - Setting period status to `Locked` permanently prevents further payroll generation, recalculation, or record deletion.
4. **Decoupled Future Engine Hooks**:
   - Does NOT calculate Income Tax (TDS), PF, or ESI contributions in this milestone.
   - Clean domain separation allows future Tax Engine and PDF Payslip modules to wrap around `PayrollRecord` outputs seamlessly.
5. **Platform Integration**:
   - Redis Caching: Invalidation of `payroll:*` keys upon period creation, generation, approval, or locking.
   - Audit Logging: Tracks `PAYROLL_PERIOD_CREATE`, `PAYROLL_GENERATE`, `PAYROLL_RECALCULATE`, `PAYROLL_APPROVE`, and `PAYROLL_LOCK`.
   - Celery Telemetry: `send_payroll_notification_task` alerts Payroll Team, HR, and Finance.

## Consequences
- Authoritative payroll calculation engine for ApnaERP.
- Complete line-item auditing of earnings and deductions per employee per period.
- Strict period locking guarantees financial compliance.
