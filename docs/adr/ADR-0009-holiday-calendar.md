# ADR-0009: Enterprise Holiday Calendar & Regional Scope Architecture

## Status
Accepted

## Context
In an enterprise ERP platform, official holidays dictate working day schedules, leave quota deductions, overtime pay multipliers, and payroll processing cycles. Without a centralized, authoritative holiday registry, downstream modules (Attendance, Leave Management, Payroll, Shift Scheduling, and Enterprise Reporting) would be forced to duplicate holiday logic or rely on hardcoded dates, leading to inconsistency across regions.

Milestone HR-7 introduces a centralized Holiday Calendar module (`Holiday` model) acting as the single source of truth for company, national, and regional holiday observations.

## Decision

1. **Holiday Calendar Data Model**:
   - `Holiday` entity containing: `code` (unique, indexed), `name` (indexed), `description`, `holiday_date` (`datetime.date`), `holiday_type` (`National`, `Regional`, `Company`, `Optional`), `country`, `state_region` (nullable), `is_half_day`, `is_recurring_annually`, `is_active`, and soft deletion fields.

2. **Regional Holiday Scoping**:
   - National holidays apply to all employees in the designated `country`.
   - Regional holidays apply to employees operating within a specific `state_region`.
   - The repository enforces uniqueness on `(holiday_date, country, state_region)` among active records to prevent duplicate holiday definitions on the same date for a single location.

3. **Annual Recurring Projection Algorithm**:
   - Holidays with `is_recurring_annually = True` (e.g., Independence Day on Aug 15 or New Year's Day on Jan 1) automatically apply to every calendar year.
   - When querying holidays for a target year via `HolidayService.get_holidays_by_year(year)`, the repository retrieves non-recurring holidays in `year` PLUS all annual recurring holidays from any year, projecting their `holiday_date` onto the target `year`.

4. **Caching, Audit & Telemetry**:
   - Redis caching (`holiday:list`) with automatic invalidation on mutating operations.
   - Enterprise audit logging (`HOLIDAY_CREATE`, `HOLIDAY_UPDATE`, `HOLIDAY_DELETE`, `HOLIDAY_RESTORE`).
   - Celery background task `send_holiday_notification_task` for event notification processing.

5. **Downstream Integration Contracts**:
   - **Attendance Module**: Checks `get_holidays_by_date(date, country, region)` to exclude holidays from tardiness/absence evaluations and calculate holiday shift overtime multipliers.
   - **Leave Module**: Excludes official holidays when calculating working day leave deductions from employee balances.
   - **Payroll Module**: Reads holiday calendars to calculate holiday pay rates and pay cycle working day counts.

## Consequences
- Establishes a clean, single source of truth for all enterprise holiday calculations.
- Eliminates manual year-by-year re-creation of fixed annual holidays via annual recurring projection logic.
- Guarantees location-aware compliance for multi-region workforce operations.
