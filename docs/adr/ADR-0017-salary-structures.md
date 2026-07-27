# ADR-0017: Enterprise Salary Structures (Payroll-2)

## Status
Accepted

## Context
Enterprise payroll management requires reusable Salary Structure templates that combine multiple Salary Components into defined compensation models (e.g. Executive Package, Engineering Band 3 Structure, Sales Compensation Structure).

Each Salary Structure defines currency, effective date range (`effective_from`, `effective_to`), and mapped components with component ordering, baseline component values, and optional calculation method overrides.

## Decision
We implemented `SalaryStructure` and `SalaryStructureComponent` ORM models (`app/models/salary_structure.py`).

### Key Architectural Attributes
1. **Structure Templates (`SalaryStructure`)**:
   - Unique `code` and unique `name`.
   - `currency`: Default "INR".
   - Effective date range (`effective_from`, `effective_to`): Validates that `effective_to >= effective_from`.
   - Soft deletion and restoration mixins.

2. **Component Mapping (`SalaryStructureComponent`)**:
   - Unique constraint `(salary_structure_id, salary_component_id)` prevents duplicating a component within the same structure.
   - `component_order`: Sequential integer ordering for payslip composition and calculation hierarchy.
   - `component_value`: Default or baseline value override.
   - `calculation_method_override`: Optional calculation method override.

3. **Platform Integration**:
   - Redis caching: Automatic invalidation of `salary_structure:*` keys upon structure or component mapping changes.
   - Audit Logging: Tracks `SALARY_STRUCTURE_CREATE`, `SALARY_STRUCTURE_UPDATE`, `SALARY_STRUCTURE_DELETE`, `SALARY_STRUCTURE_RESTORE`, `SALARY_STRUCTURE_COMPONENT_ADD`, `SALARY_STRUCTURE_COMPONENT_UPDATE`, and `SALARY_STRUCTURE_COMPONENT_REMOVE`.
   - Background Telemetry: Celery notification task `send_payroll_structure_notification_task` alerts Payroll Administrators.

## Consequences
- Reusable salary templates ready for future Employee Salary Assignment and Payroll Execution engines.
- Strict component uniqueness within structures prevents calculation ambiguity.
- Decoupled from individual employee records.
