# ADR-0021: Enterprise Statutory Compliance Engine (Payroll-6)

## Status
Accepted

## Context
Enterprise payroll processing across multi-national organizations requires evaluating statutory payroll deductions (Provident Fund, ESI, Professional Tax, Income Tax, and custom statutory deductions) based on country jurisdiction policies and employee profiles.

Key operational requirements:
- The engine must be country-independent and future-ready (supporting India built-in initially, with zero redesign required for USA, UK, UAE, etc.).
- Statutory calculation logic must be completely driven by configurable rules (`StatutoryRule`) and tiered salary slabs (`StatutoryRuleSlab`), with zero hardcoded formulas in python code.
- Deduction methods supported: Fixed, Percentage, and Tiered Slab calculations.
- Rules must support priority ordering, active status flags, and effective dating (`effective_from`, `effective_to`).
- Employees have configurable statutory profiles (`EmployeeStatutoryProfile`) linking them to a Country jurisdiction, holding official tax/PF/ESI identifiers, feature flags (`pf_enabled`, `esi_enabled`, `professional_tax_enabled`, `income_tax_enabled`), and enforcing single active profile per employee.

## Decision
We implemented `Country`, `StatutoryRule`, `StatutoryRuleSlab`, and `EmployeeStatutoryProfile` ORM models (`app/models/country.py`, `app/models/statutory_rule.py`, `app/models/employee_statutory_profile.py`), Pydantic v2 schemas (`app/schemas/country.py`, `app/schemas/statutory_rule.py`, `app/schemas/employee_statutory_profile.py`), Data Repositories (`app/repositories/country.py`, `app/repositories/statutory_rule.py`, `app/repositories/employee_statutory_profile.py`), Domain Service `StatutoryComplianceService` (`app/services/statutory_compliance.py`), Celery async notifications (`app/tasks/statutory_tasks.py`), RBAC permissions (`app/db/seed_rbac.py`), and REST API endpoints (`app/api/v1/endpoints/country.py`, `app/api/v1/endpoints/statutory_rule.py`, `app/api/v1/endpoints/employee_statutory_profile.py`).

### Key Architectural Attributes
1. **Country Independence & Global Reusability**:
   - `Country` jurisdiction entity (`code`, `name`, `currency`, `is_active`) establishes global scope reusable across ERP domains.
2. **Configurable Deduction Rule Engine**:
   - `StatutoryRule` specifies `rule_type` (`Provident Fund`, `ESI`, `Professional Tax`, `Income Tax`, `Other`) and `calculation_method` (`Fixed`, `Percentage`, `Slab`).
   - Supports rule evaluation priority sorting (`priority` ASC) and effective date filtering (`effective_from <= target_date <= effective_to`).
3. **Tiered Slab Calculation Model**:
   - `StatutoryRuleSlab` defines ranges (`min_amount <= gross_salary <= max_amount`) with associated `fixed_amount` and `percentage` rates.
4. **Single Active Employee Statutory Profile**:
   - `EmployeeStatutoryProfile` enforces that an employee possesses exactly ONE active statutory profile at any given time. Activating a new profile automatically deactivates/expires the prior active profile.
5. **Platform Integration**:
   - Redis Caching: Invalidation of `country:*`, `statutory_rule:*`, and `statutory_profile:*` cache keys upon write operations.
   - Audit Logging: Tracks `COUNTRY_*`, `STATUTORY_RULE_*`, `STATUTORY_SLAB_*`, and `STATUTORY_PROFILE_*` events.
   - Celery Async Tasks: `send_statutory_rule_notification_task` alerts Payroll Administrators when statutory rules/slabs are modified.

## Consequences
- Authoritative, country-agnostic statutory deduction calculation engine for ApnaERP.
- Configurable rule and slab definitions eliminate hardcoded statutory logic.
- Built-in India compliance rules established while enabling instant multi-country expansion.
