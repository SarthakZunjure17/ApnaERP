# ADR-0020: Enterprise Payroll Runs & Payslip Generation (Payroll-5)

## Status
Accepted

## Context
Enterprise payroll execution requires organizing calculation runs into batch executions (`PayrollRun`) and generating individual employee payslips (`Payslip`) with formatted PDF documents.

Generating and delivering payslips requires strict operational control:
- Organizing executions by `Run Type` (`Regular`, `Off Cycle`, `Adjustment`).
- Generating ReportLab PDF payslips containing company branding, employee details, period info, itemized earnings/deductions, gross/net totals, and disclaimers.
- Storing generated PDF binaries securely using the existing `FileService` abstraction with SHA256 checksum deduplication.
- Controlling employee visibility: Payslips remain in `Generated` state until explicitly published (`Published` status), preventing premature access.
- Permanent record locking: Once a `PayrollRun` is `Locked`, its state and generated payslips cannot be altered.

## Decision
We implemented `PayrollRun` and `Payslip` ORM models (`app/models/payroll_run.py`, `app/models/payslip.py`), ReportLab PDF generator utility (`app/utils/pdf_generator.py`), Extended `FileService.upload_bytes` (`app/services/file.py`), domain service `PayrollRunService` (`app/services/payroll_run.py`), Celery async notifications (`app/tasks/payroll_run_tasks.py`), and REST endpoints (`app/api/v1/endpoints/payroll_run.py`, `app/api/v1/endpoints/payslip.py`).

### Key Architectural Attributes
1. **Batch Payroll Execution (`PayrollRun`)**:
   - Unique constraint `(payroll_period_id, run_type)` permits distinct execution runs per period (e.g. Regular vs Off-Cycle bonus run).
   - Lifecycle state transitions: `Draft` -> `Processing` -> `Completed` -> `Locked`.
2. **ReportLab PDF Payslip Generation**:
   - `generate_payslip_pdf_bytes()` creates in-memory PDF binary documents formatted with ReportLab flowables, tables, and custom styling.
   - Integrates with `FileService.upload_bytes()` to store PDF files with SHA256 checksum deduplication and `File` entity linking (`pdf_file_id`).
3. **Immutability & Publication Workflow**:
   - `Payslip` lifecycle: `Draft` -> `Generated` -> `Published`.
   - Employees gain access to view and download PDF streams (`/api/v1/payslips/{id}/download`) only after payslips are explicitly published by HR/Payroll Managers.
   - Locking a `PayrollRun` (`status = "Locked"`) permanently freezes all runs and payslips against modifications or regeneration.
4. **Platform Infrastructure & Governance**:
   - Redis Caching: Invalidation of `payroll_run:*` and `payslip:*` cache patterns on status changes.
   - Audit Logging: Captures `PAYROLL_RUN_CREATE`, `PAYROLL_RUN_START`, `PAYROLL_RUN_COMPLETE`, `PAYROLL_RUN_LOCK`, `PAYSLIP_GENERATE`, and `PAYSLIP_PUBLISH` events.
   - Celery Async Tasks: `send_payroll_run_notification_task` alerts Payroll Team; `send_payslip_published_notification_task` notifies employees upon publication.

## Consequences
- End-to-end operational payroll batch execution and PDF payslip delivery system for ApnaERP.
- Reliable, deduplicated storage of PDF documents linked to `FileService`.
- Multi-tier RBAC authorization securing payslip viewing and download operations.
