# ADR-0016: Enterprise Salary Components (Payroll-1)

## Status
Accepted

## Context
Enterprise payroll processing requires standardized, organization-wide definitions for earnings (e.g. Basic Salary, House Rent Allowance, Medical Allowance, Travel Allowance, Special Allowance, Bonus, Commission) and deductions (e.g. Provident Fund, ESI, Professional Tax, Income Tax, Loan Recovery).

These Salary Components must be organization-wide definitions, independent of individual employees or specific salary structures.

## Decision
We implemented the `SalaryComponent` domain model (`app/models/salary_component.py`) representing standardized payroll component definitions.

### Key Architectural Attributes
1. **Component Category (`type`)**: `Earning` or `Deduction`.
2. **Calculation Method (`calculation_method`)**: `Fixed`, `Percentage`, or `Formula` (reserved for future calculation evaluation).
3. **Statutory & Tax Indicators**:
   - `is_taxable`: Indicates Income Tax applicability.
   - `is_pf_applicable`: Indicates Provident Fund (PF) contribution applicability.
   - `is_esi_applicable`: Indicates Employee State Insurance (ESI) applicability.
4. **Display Order (`display_order`)**: Enforces unique, sequential positioning across active components for payslip layout and payroll processing sequence.
5. **Validation Rules**:
   - Unique constraints on `code`, `name`, and `display_order`.
   - `Percentage` method requires `percentage_value` between 0.01 and 100.0.
   - `Fixed` method requires valid non-negative `default_value`.

### Decoupled Platform Architecture
- Organization-wide registry: Salary Components are not bound to individual employee records.
- Redis caching: Invalidation of `salary_component:*` keys on any CRUD operation.
- Audit Logging: Tracks `SALARY_COMPONENT_CREATE`, `SALARY_COMPONENT_UPDATE`, `SALARY_COMPONENT_DELETE`, and `SALARY_COMPONENT_RESTORE`.
- Background Telemetry: Celery notification task `send_payroll_component_notification_task` alerts Payroll Administrators.

## Consequences
- Single, authoritative catalog of salary components for future Salary Structure definitions, Employee Salary Assignments, and Payroll Execution engines.
- Strict display order uniqueness prevents ambiguous calculation sequences.
- Zero coupling between component definitions and employee entities.
