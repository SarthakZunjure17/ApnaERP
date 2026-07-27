# ADR-0012: Enterprise Leave Types & Policies Architecture

## Status
Accepted

## Context
In Enterprise ERP systems, organizational leave policies define employee entitlements, approval workflows, carry-forward rules, half-day permissions, and gender constraints. Milestone HR-10 introduces reusable `LeaveType` policy entities serving as the single source of truth for all leave definitions across the enterprise.

## Decision
1. **Model Design**:
   - `LeaveType` entity with unique `code` (e.g., `ANNUAL`, `SICK`, `MATERNITY`) and `name`.
   - Entitlement policies: `is_paid`, `requires_approval`, `allow_half_day`, `allow_negative_balance`, `annual_allocation`, `carry_forward_allowed`, `max_carry_forward`, `max_consecutive_days`, `gender_restriction`.
2. **Business Rules**:
   - Unique `code` and `name` checks across active and soft-deleted records.
   - `annual_allocation >= 0`.
   - `max_carry_forward <= annual_allocation`.
   - If `carry_forward_allowed` is `False`, `max_carry_forward` must be `0`.
   - `max_consecutive_days > 0`.
3. **Caching & Invalidation Strategy**:
   - Redis caching with keys `leave_type:list` and `leave_type:detail:{id}`.
   - Automatic cache pattern invalidation on creation, update, soft deletion, and restoration.
4. **Integration Safeguards**:
   - Audit logging via `log_audit` for `LEAVE_TYPE_CREATE`, `LEAVE_TYPE_UPDATE`, `LEAVE_TYPE_DELETE`, `LEAVE_TYPE_RESTORE`.
   - Asynchronous Celery task (`send_leave_policy_change_notification_task`) notifying HR Admins on policy changes.
   - Designed for future integration with Leave Request & Balance Engines and Payroll Overtime/Deduction Calculation.

## Consequences
- Provides a clean, decoupled policy foundation for upcoming Leave Application and Payroll processing modules.
- Ensures zero data duplication across employee leave assignments.
- Maintains strict auditability and real-time cache consistency.
