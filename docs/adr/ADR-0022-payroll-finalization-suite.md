# ADR-0022: Enterprise Payroll Finalization Suite (Payroll Finalization Suite)

## Status
Accepted

## Context
Completing the Enterprise Payroll domain requires a comprehensive finalization suite for handling post-calculation adjustments, reporting, executive analytics, bank disbursement exports, period closing/reopening lifecycle, archival, and exposing clean financial integration interfaces without introducing a complete Accounting or General Ledger module prematurely.

Key operational requirements:
- **Payroll Adjustments**: One-time earnings and deductions (Bonus, Incentive, Commission, Overtime, Arrears, Reimbursements, Loan Recovery, Manual Additions/Deductions) tied to employee and payroll period with approval workflow (`Pending`, `Approved`, `Rejected`, `Applied`).
- **Period Immutability**: Closed and Archived payroll periods must strictly reject any modification or addition of adjustments.
- **Payroll Reports**: Generation and snapshot storage of formal payroll reports (Salary Register, Department-wise Payroll, Employee Salary History, Payroll Summary, Deduction Summary, Earnings Summary, Cost Center Report, Monthly Payroll Register) in PDF, EXCEL, or CSV formats.
- **Payroll Analytics**: Real-time aggregation of total payroll cost, average salary, highest/lowest salary, department cost breakdowns, and period trend items.
- **Bank Export**: Bank-compatible CSV export generation containing employee bank details and net payable amounts for direct salary disbursement.
- **Payroll Closing Lifecycle**: Period closing, audited reopening with mandatory reason logging, and archival locking.
- **Financial Integration Interface**: Structured payload generation and queuing (`FinancialPostingQueue`) exposing journal entry summaries for future General Ledger integration without implementing an accounting module.

## Decision
We implemented `PayrollAdjustment`, `PayrollReportSnapshot`, `PayrollClosing`, and `FinancialPostingQueue` ORM entities (`app/models/payroll_adjustment.py`, `app/models/payroll_report_snapshot.py`, `app/models/payroll_closing.py`, `app/models/financial_posting_queue.py`), Pydantic v2 schemas (`app/schemas/payroll_finalization.py`), Data Repositories (`app/repositories/payroll_adjustment.py`, `app/repositories/payroll_finalization_repos.py`), Domain Services (`app/services/payroll_finalization_services.py`), Celery async task (`app/tasks/payroll_finalization_tasks.py`), RBAC permissions (`app/db/seed_rbac.py`), and REST API routers (`app/api/v1/endpoints/payroll_adjustment.py`, `app/api/v1/endpoints/payroll_report.py`, `app/api/v1/endpoints/payroll_analytics.py`, `app/api/v1/endpoints/bank_export.py`, `app/api/v1/endpoints/payroll_closing.py`, `app/api/v1/endpoints/financial_integration.py`).

### Key Architectural Attributes
1. **Clean Architecture & DDD**:
   - Strict separation between domain services, repository data layer, Pydantic schemas, and REST endpoints.
2. **Period Immutability & Auditability**:
   - Closed or Archived periods enforce strict immutability. All period closing, reopening, and adjustment actions generate audit log entries (`log_event`) and Celery notifications.
3. **Decoupled Financial Integration Interface**:
   - Exposes `FinancialPostingQueue` to publish standardized journal entry payloads (`debit_gross_salary_expense`, `credit_statutory_deductions_liability`, `credit_net_payroll_payable`) for future Finance module ingestion without implementing GL or accounting tables in this milestone.
4. **File Storage Integration**:
   - Report snapshots and bank export CSV files are stored via `file_service` with SHA256 deduplication and secure download capabilities.
5. **Comprehensive Testing**:
   - 100% test coverage across adjustment workflows, report snapshots, bank export, analytics, closing/reopening/archival, financial posting publication, and REST APIs.

## Consequences
- The Enterprise Payroll domain for ApnaERP is now **FULLY COMPLETE** and CLOSED (`v0.5.6`).
- Provides enterprise-grade payroll finalization, bank disbursement, executive analytics, and period governance.
- Cleanly interfaces with future Finance & Accounting modules via posting queue abstractions.
