# ADR-0007: HR Configuration & Organization Policies Architecture

## Status
Accepted

## Date
2026-07-26

## Context
As ApnaERP expands into the Human Resources domain, subsequent enterprise modules—including Attendance, Leave, Payroll, Recruitment, Performance, and Shift Scheduling—require organization-wide policy parameters.

Without a centralized configuration management system, each HR sub-module would define and store its own duplicated settings (such as daily working hours, weekend day rules, timezone offsets, probation durations, leave year start months, and payroll frequencies). This would create data fragmentation, risk policy inconsistency, and complicate multi-tenant enterprise management.

## Decision Drivers
1. **Single Source of Truth**: Centralize all organization-wide HR policy parameters into a unified `HRConfiguration` module.
2. **Singleton Active Policy**: Guarantee that exactly one configuration record is marked `is_active=True` per organization code at any point in time.
3. **Active Policy Protection**: Prevent accidental or intentional soft-deletion of active policies to ensure policy continuity across dependent HR services.
4. **Integration Readability**: Provide low-latency, cached configuration access for future modules (Attendance, Leave, Payroll, Recruitment, Performance).
5. **Auditability & Observability**: Record comprehensive audit trails and dispatch asynchronous Celery telemetry notifications upon any configuration creation, modification, or activation event.

## Decision
We implement the **HR Configuration & Organization Policies** module (`app/models/hr_configuration.py`, `app/services/hr_configuration.py`) with the following architecture:

### 1. Data Model
`HRConfiguration` contains:
- `organization_name` & `organization_code`
- `timezone` (IANA timezone validation)
- `country` & 3-letter ISO `currency`
- `standard_working_hours_per_day` & `standard_working_days_per_week`
- `weekend_configuration` (JSON array of non-working days)
- `default_shift_name`, `grace_period_minutes`, `minimum_working_hours`
- `default_probation_period_days`, `leave_year_start_month`
- `payroll_cycle` (`Monthly`, `Biweekly`, `Weekly`)
- `fiscal_year_start_month`
- `is_active` (Boolean flag)

### 2. Singleton Active Policy Pattern
Creating a new active configuration (`is_active=True`) or explicitly activating an existing configuration (`PATCH /api/v1/hr/configuration/{id}/activate`) triggers `deactivate_all_active_configurations`, setting `is_active=False` on all previous active configurations for that organization.

### 3. Active Deletion Guard
Soft-deletion (`DELETE /api/v1/hr/configuration/{id}`) checks `is_active`. If `is_active == True`, the operation raises HTTP 400 (`ACTIVE_CONFIG_DELETION_PROHIBITED`), requiring administrators to activate a replacement policy first.

### 4. High-Performance Redis Caching
Active configurations are cached in Redis (`hr_configuration:active:{organization_code}`) with a 24-hour TTL. Cache invalidation is triggered automatically upon create, update, activate, delete, or restore operations.

### 5. Future Module Integration Contracts
- **Attendance Module**: Reads `timezone`, `standard_working_hours_per_day`, `grace_period_minutes`, and `minimum_working_hours` for calculating late arrivals and half-day credits.
- **Leave Module**: Reads `weekend_configuration` and `leave_year_start_month` for calculating working day leave deductions and annual entitlement resets.
- **Payroll Module**: Reads `currency`, `payroll_cycle`, and `fiscal_year_start_month` for pay run calculations and tax year reporting.
- **Recruitment & Probation**: Reads `default_probation_period_days` when onboarding new hires.

## Consequences

### Positive
- Prevents setting duplication across future HR sub-systems.
- Guarantees strict policy validation (timezones, weekend day names, working hour bounds).
- High performance via Redis caching with automatic invalidation.
- Complete RBAC security (`hr_configuration.*` permissions) and enterprise audit logging.

### Negative
- Requires future HR developers to query `HRConfigurationService` instead of hardcoding local settings.
