# Changelog

All notable changes to the **ApnaERP** platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.6.1] - 2026-07-30

### Milestone Inventory Stock Management Engine — Enterprise Stock Ledger Engine

#### Added
- **Stock Ledger Engine ORM Entities (`app/models/`)**: Created 5 models:
  - `InventoryTransactionType`: Classification for inventory movements (`OPENING_STOCK`, `PURCHASE_RECEIPT`, `SALES_ISSUE`, `STOCK_ADJUSTMENT`, etc.) with direction flags (`IN`, `OUT`, `TRANSFER`, `ADJUSTMENT`, `SYSTEM`).
  - `StockLedger`: Immutable physical stock ledger storing product, warehouse, location, transaction type, quantity, direction, unit, and calculated `running_balance`. Direct updates/deletions prohibited.
  - `StockBalance`: Read-optimized projection/cache table aggregating available, reserved, damaged, and in-transit quantities derived from ledger history.
  - `InventoryAdjustment`: Stock adjustment proposal entity supporting 3-stage lifecycle (`Draft` -> `Approved` -> `Applied`). Applying an adjustment generates a `STOCK_ADJUSTMENT` ledger entry.
  - `OpeningStock`: Initial stock initialization record for warehouse onboarding.
- **Pydantic v2 DTO Schemas (`app/schemas/stock_engine.py`)**: Request/Response schemas for Transaction Types, Stock Ledger, Stock Balances, Warehouse Summaries, Product Summaries, Opening Stock, and Inventory Adjustments.
- **Repository Layer (`app/repositories/stock_engine_repos.py`)**: `InventoryTransactionTypeRepository`, `StockLedgerRepository` (latest running balance lookup, multi-column ledger queries with pagination/search, derived ledger balance calculation), `StockBalanceRepository` (upsert balance projections, product/warehouse/location balance queries), `OpeningStockRepository` (duplicate reference and product location guards), and `InventoryAdjustmentRepository`.
- **Domain Services (`app/services/stock_engine_services.py`)**:
  - `InventoryTransactionTypeService`: Transaction classification lookups.
  - `StockLedgerService`: Immutable ledger entry execution, running balance calculation, **negative stock enforcement** against `Product.allow_negative_stock`, Redis cache invalidation (`stock_balance:*`, `warehouse_summary:*`, `product_stock:*`), and audit logging (`STOCK_LEDGER_CREATE`).
  - `StockBalanceService`: Projection calculation directly from ledger history, cached warehouse/product summaries, and forced recalculations.
  - `OpeningStockService`: Initial stock creation, duplicate guards, and automatic `OPENING_STOCK` ledger entry generation.
  - `InventoryAdjustmentService`: Adjustment proposal lifecycle (`Draft` -> `Approved` -> `Applied`), variance calculation, and automatic `STOCK_ADJUSTMENT` ledger entry generation.
- **Background Celery Tasks (`app/tasks/stock_engine_tasks.py`)**: `refresh_stock_balance_task` (async projection refresh), `detect_balance_inconsistencies_task` (reconciliation and auto-repair), and `send_stock_notification_task` (stock telemetry alerts).
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded 13 default `InventoryTransactionType` records and 8 permissions (`inventory.transaction.read`, `inventory.ledger.read`, `inventory.balance.read`, `inventory.opening.create`, `inventory.adjustment.create`, `inventory.adjustment.approve`, `inventory.adjustment.apply`) mapped to `Super Admin` and `Inventory Manager` roles.
- **REST API Routers (`app/api/v1/endpoints/`)**: 5 API routers (`inventory_transaction_type.py`, `stock_ledger.py`, `opening_stock.py`, `inventory_adjustment.py`, `stock_balance.py`) registered under `/api/v1`.
- **Database Migration (`alembic/versions/c8a97096a1e6_phase_v061_implement_stock_ledger_engine.py`)**: Migration creating inventory transaction types, stock ledgers, stock balances, inventory adjustments, and opening stocks tables and indexes.
- **Architecture Decision Record (`docs/adr/ADR-0024-stock-ledger.md`)**: Architectural details on immutable ledger pattern, derived balance projections, negative stock enforcement, and adjustment workflows.
- **Automated Test Suite (`tests/test_stock_ledger_engine.py`)**: 7 comprehensive tests covering transaction type seeding, opening stock creation, duplicate prevention, adjustment lifecycle, negative stock validation, balance recalculation, and API endpoints.

---

## [v0.6.0] - 2026-07-29

### Milestone Inventory Foundation — Product Master Catalog (Inventory Domain Opened)

#### Added
- **Inventory ORM Entities (`app/models/`)**: Created 9 models: `ProductCategory`, `UnitOfMeasure`, `Brand`, `Warehouse`, `StorageLocation`, `Product`, `ProductAttribute`, `ProductAttributeValue`, and `ProductDocument`.
- **Pydantic v2 DTO Schemas (`app/schemas/inventory.py`)**: Schemas and tree DTOs for Categories, Units of Measure, Brands, Warehouses, Storage Locations, Products, Attributes, and Documents.
- **Repository Layer (`app/repositories/inventory_repos.py`)**: Repositories for all 9 entities with multi-column search, filtering, SKU/code uniqueness lookups, and hierarchy tree resolution.
- **Domain Services (`app/services/inventory_services.py`)**:
  - `CategoryService` & `StorageLocationService`: Infinite parent-child hierarchy tree resolution and circular reference validation.
  - `UnitOfMeasureService` & `BrandService`: Standard unit definitions and brand catalog management with uniqueness guards.
  - `WarehouseService`: Storage facility management and contact details.
  - `ProductService`: Product Master catalog operations, multi-column search/filtering, SKU/barcode uniqueness validation, status state machine (`Draft` -> `Active` -> `Discontinued` -> `Archived`), and read-only enforcement for `Archived` products.
  - `ProductAttributeService` & `ProductDocumentService`: Custom key-value attribute definitions and document file attachments.
- **Background Celery Task (`app/tasks/inventory_tasks.py`)**: `send_inventory_notification_task` broadcasting alerts on warehouse creation/updates and product archival.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded 24 permissions across `inventory.category.*`, `inventory.unit.*`, `inventory.brand.*`, `inventory.warehouse.*`, `inventory.location.*`, `inventory.product.*`, `inventory.attribute.*`, and `inventory.document.*`.
- **REST API Routers (`app/api/v1/endpoints/`)**: 8 API routers (`category.py`, `unit_of_measure.py`, `brand.py`, `warehouse.py`, `storage_location.py`, `product.py`, `product_attribute.py`, `product_document.py`) registered under `/api/v1`.
- **Database Migration (`alembic/versions/00f4c360a213_phase_v060_implement_inventory_.py`)**: Migration creating inventory tables and indexes.
- **Architecture Decision Record (`docs/adr/ADR-0023-inventory-foundation.md`)**: Architectural details on product master catalog, infinite category/location trees, status rules, and cache invalidation.

---

## [v0.5.6] - 2026-07-29

### Milestone Payroll Finalization Suite — Enterprise Payroll Finalization Suite (Payroll Domain Completed)

#### Added
- **`PayrollAdjustment`, `PayrollReportSnapshot`, `PayrollClosing`, and `FinancialPostingQueue` ORM Entities (`app/models/payroll_adjustment.py`, `app/models/payroll_report_snapshot.py`, `app/models/payroll_closing.py`, `app/models/financial_posting_queue.py`)**: Models representing post-calculation adjustments (`PayrollAdjustment`: `employee_id`, `payroll_period_id`, `adjustment_type`, `amount`, `currency`, `description`, `status`, `approved_by`, `approved_at`), generated report snapshots (`PayrollReportSnapshot`: `payroll_period_id`, `report_type`, `format`, `generated_by`, `generated_at`, `file_id`, `metadata_json`), period closing/reopening/archival state (`PayrollClosing`: `payroll_period_id`, `closed_by`, `closed_at`, `reopened_by`, `reopened_at`, `closing_remarks`, `status`), and decoupled financial integration queue items (`FinancialPostingQueue`: `payroll_period_id`, `posting_status`, `payload`, `posted_at`).
- **Pydantic v2 DTO Schemas (`app/schemas/payroll_finalization.py`)**: Schemas for Adjustments (`PayrollAdjustmentCreate`, `PayrollAdjustmentUpdate`, `PayrollAdjustmentResponse`), Reports (`PayrollReportGenerateRequest`, `PayrollReportSnapshotResponse`), Analytics (`PayrollAnalyticsResponse`, `DepartmentPayrollCost`, `PayrollTrendItem`), Bank Export (`BankExportRequest`, `BankExportResponse`), Period Closing (`PayrollClosingRequest`, `PayrollReopenRequest`, `PayrollClosingResponse`), and Financial Queue (`FinancialPostingQueueResponse`).
- **Repository Layer (`app/repositories/payroll_adjustment.py`, `app/repositories/payroll_finalization_repos.py`)**: Repositories providing filtering, period lookups, approved adjustment retrieval, snapshot querying, closing state management, and pending posting queue retrieval with pagination and sorting.
- **Domain Services (`app/services/payroll_finalization_services.py`)**:
  - `PayrollAdjustmentService`: Adjustments creation, update, approval (`Approved`), rejection (`Rejected`), deletion, and period immutability guard.
  - `PayrollAnalyticsService`: Real-time executive metrics calculation (total cost, average salary, total earnings/deductions, highest/lowest salary, department cost breakdown, period trends).
  - `PayrollReportService`: Formal payroll report generation and file snapshot storage in PDF, EXCEL, and CSV formats.
  - `BankExportService`: Generation and file upload of bank-compatible payment export CSV files.
  - `PayrollClosingService`: Period closing (`Closed`), audited reopening (`Open` with required reason log), and permanent archival (`Archived`).
  - `FinancialIntegrationService`: Generation and publication of structured financial posting payloads (`FinancialPostingQueue`) exposing journal entry summaries for future GL integration without implementing an accounting module.
- **Background Celery Task (`app/tasks/payroll_finalization_tasks.py`)**: `send_payroll_finalization_notification_task` broadcasting notification alerts on adjustment approvals/rejections, period closing/reopening, and financial posting payload publications.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded 10 permissions `payroll.adjustment.create`, `payroll.adjustment.update`, `payroll.adjustment.delete`, `payroll.report.generate`, `payroll.analytics.read`, `payroll.bank.export`, `payroll.close`, `payroll.reopen`, `payroll.archive`, `payroll.financial.publish`.
- **REST API Routers (`app/api/v1/endpoints/payroll_adjustment.py`, `app/api/v1/endpoints/payroll_report.py`, `app/api/v1/endpoints/payroll_analytics.py`, `app/api/v1/endpoints/bank_export.py`, `app/api/v1/endpoints/payroll_closing.py`, `app/api/v1/endpoints/financial_integration.py`)**: Endpoints for Adjustments, Reports generation & download, Analytics, Bank Export, Closing/Reopening/Archival, and Financial Integration payload publication.
- **Database Migration (`alembic/versions/00f67d39bb21_phase_v056_implement_payroll_.py`)**: Applied migration creating `payroll_adjustments`, `payroll_report_snapshots`, `payroll_closings`, and `financial_posting_queue` tables.
- **Architecture Decision Record (`docs/adr/ADR-0022-payroll-finalization-suite.md`)**: Documented finalization architecture, period immutability, report snapshotting, bank export, closing state machine, and financial integration queue abstractions.

---

## [v0.5.5] - 2026-07-29

### Milestone Payroll-6 — Enterprise Statutory Compliance Engine

#### Added
- **`Country`, `StatutoryRule`, `StatutoryRuleSlab`, and `EmployeeStatutoryProfile` ORM Entities (`app/models/country.py`, `app/models/statutory_rule.py`, `app/models/employee_statutory_profile.py`)**: Models representing reusable country jurisdictions (`Country`), statutory deduction policies (`StatutoryRule`: `rule_code`, `rule_name`, `country_id`, `rule_type`, `calculation_method`, `effective_from`, `effective_to`, `priority`, `is_active`), tiered salary slab boundaries (`StatutoryRuleSlab`: `min_amount`, `max_amount`, `percentage`, `fixed_amount`, `sequence`), and employee compliance profiles (`EmployeeStatutoryProfile`: `employee_id`, `country_id`, `pf_enabled`, `esi_enabled`, `professional_tax_enabled`, `income_tax_enabled`, `tax_identification_number`, `pf_number`, `esi_number`, `effective_from`, `effective_to`, `is_active`).
- **Pydantic v2 DTO Schemas (`app/schemas/country.py`, `app/schemas/statutory_rule.py`, `app/schemas/employee_statutory_profile.py`)**: Schemas for Countries, Statutory Rules, Rule Slabs, Employee Profiles, and Statutory Deduction Calculation requests/responses.
- **Repository Layer (`app/repositories/country.py`, `app/repositories/statutory_rule.py`, `app/repositories/employee_statutory_profile.py`)**: Data repositories providing filtering, code lookups, priority sorting, date-effective rule resolution, and pagination.
- **Statutory Compliance Domain Service (`app/services/statutory_compliance.py`)**: Domain service implementing country management, statutory rules & slabs management, employee profile assignment with **single active profile enforcement**, effective rule resolution, calculation engine (Fixed, Percentage, Slab), Redis cache invalidation (`country:*`, `statutory_rule:*`, `statutory_profile:*`), and audit logging (`COUNTRY_*`, `STATUTORY_RULE_*`, `STATUTORY_SLAB_*`, `STATUTORY_PROFILE_*`).
- **Background Celery Task (`app/tasks/statutory_tasks.py`)**: `send_statutory_rule_notification_task` alerting Payroll Administrators on rule creation, modification, activation, or deactivation.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded permissions `country.create`, `country.read`, `country.update`, `country.delete`, `statutory_rule.create`, `statutory_rule.read`, `statutory_rule.update`, `statutory_rule.delete`, `statutory_profile.create`, `statutory_profile.read`, `statutory_profile.update`.
- **REST API Routers (`app/api/v1/endpoints/country.py`, `app/api/v1/endpoints/statutory_rule.py`, `app/api/v1/endpoints/employee_statutory_profile.py`)**: Endpoints (`GET/POST/PUT/DELETE /countries`, `GET/POST/PUT/DELETE /statutory-rules`, `POST/PUT/DELETE /statutory-rules/slabs`, `POST /statutory-rules/calculate`, `GET/POST/PUT /employee-statutory-profiles`, `GET /employees/{id}/statutory-profile`).
- **Database Migration (`alembic/versions/87b928321932_phase_v055_implement_statutory_.py`)**: Applied database migration creating `countries`, `statutory_rules`, `statutory_rule_slabs`, and `employee_statutory_profiles` tables with foreign keys and indexes.
- **Architecture Decision Record (`docs/adr/ADR-0021-statutory-compliance-engine.md`)**: Documented country-independent architecture, rule & slab calculation model, effective dating, and security controls.

---

## [v0.5.4] - 2026-07-29

### Milestone Payroll-5 — Enterprise Payroll Runs & Payslips

#### Added
- **`PayrollRun` & `Payslip` ORM Entities (`app/models/payroll_run.py`, `app/models/payslip.py`)**: Models representing execution batches (`PayrollRun`: `payroll_period_id`, `run_number`, `run_type`, `status`, `started_by`, `started_at`, `completed_at`, `locked_at`, `remarks`, unique constraint `(payroll_period_id, run_type)`) and employee payslip documents (`Payslip`: `payroll_record_id`, `payslip_number`, `employee_id`, `payroll_period_id`, `gross_salary`, `total_earnings`, `total_deductions`, `net_salary`, `pdf_file_id`, `generated_at`, `published_at`, `status`).
- **Pydantic v2 DTO Schemas (`app/schemas/payroll_run.py`, `app/schemas/payslip.py`)**: `PayrollRunCreate`, `PayrollRunUpdate`, `PayrollRunResponse`, `PayslipResponse`, and status/type enums.
- **Repository Layer (`app/repositories/payroll_run.py`, `app/repositories/payslip.py`)**: Repositories providing run lookup, period filtering, employee history, and pagination/sorting capabilities.
- **ReportLab PDF Generator Utility (`app/utils/pdf_generator.py`)**: Utility (`generate_payslip_pdf_bytes`) compiling ReportLab PDF payslip documents in memory with company branding, employee details, period info, itemized earnings/deductions, gross/net totals, disclaimers, and currency formatting.
- **File Storage Integration (`app/services/file.py`)**: Extended `FileService` with `upload_bytes()` to store binary PDF files in storage with SHA256 checksum deduplication and `File` record creation.
- **Payroll Run & Payslip Service (`app/services/payroll_run.py`)**: Domain service managing run lifecycle (`Draft` -> `Processing` -> `Completed` -> `Locked`), ReportLab PDF batch generation, publication workflows (`Draft` -> `Generated` -> `Published`), streaming binary downloads (`download_payslip_pdf`), Redis cache invalidation (`payroll_run:*`, `payslip:*`), audit logging (`PAYROLL_RUN_CREATE`, `PAYROLL_RUN_START`, `PAYROLL_RUN_COMPLETE`, `PAYROLL_RUN_LOCK`, `PAYSLIP_GENERATE`, `PAYSLIP_PUBLISH`), and Celery notification task dispatch.
- **Background Celery Tasks (`app/tasks/payroll_run_tasks.py`)**: `send_payroll_run_notification_task` (alerts Payroll Team on run completion/lock) and `send_payslip_published_notification_task` (notifies employees when payslips are published).
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded permissions `payroll_run.create`, `payroll_run.read`, `payroll_run.update`, `payroll_run.lock`, `payslip.generate`, `payslip.publish`, `payslip.read`.
- **REST API Routers (`app/api/v1/endpoints/payroll_run.py`, `app/api/v1/endpoints/payslip.py`)**: Endpoints (`GET /payroll-runs`, `POST /payroll-runs`, `GET /payroll-runs/{id}`, `POST /payroll-runs/{id}/start`, `POST /payroll-runs/{id}/complete`, `POST /payroll-runs/{id}/lock`, `POST /payroll-runs/{id}/generate-payslips`, `POST /payroll-runs/{id}/publish-payslips`, `GET /payslips`, `GET /payslips/{id}`, `GET /employees/{id}/payslips`, `GET /payslips/{id}/download`).
- **Database Migration (`alembic/versions/769cb83590b7_phase_v054_implement_payroll_runs_and_.py`)**: Applied database migration creating `payroll_runs` and `payslips` tables with foreign keys and unique constraints.
- **Architecture Decision Record (`docs/adr/ADR-0020-payroll-runs-payslips.md`)**: Documented batch execution architecture, ReportLab PDF generation, File Storage integration, publication immutability, and security controls.

---

## [v0.5.3] - 2026-07-27

### Milestone Payroll-4 — Enterprise Payroll Processing Engine

#### Added
- **Payroll Period & Record ORM Entities (`app/models/payroll_period.py`)**: Models representing discrete payroll cycles (`PayrollPeriod`: `period_code`, `start_date`, `end_date`, `status`), employee payroll run outputs (`PayrollRecord`: `payroll_period_id`, `employee_id`, `employee_compensation_id`, `working_days`, `present_days`, `leave_days`, `paid_leave_days`, `unpaid_leave_days`, `overtime_hours`, `gross_salary`, `total_earnings`, `total_deductions`, `net_salary`, `status`, unique constraint `(payroll_period_id, employee_id)`), and line-item breakdown (`PayrollRecordComponent`: `payroll_record_id`, `salary_component_id`, `component_name`, `component_type`, `amount`).
- **Pydantic v2 DTOs (`app/schemas/payroll_period.py`)**: `PayrollPeriodCreate`, `PayrollPeriodResponse`, `PayrollPeriodListResponse`, `PayrollRecordResponse`, `PayrollRecordListResponse`, `PayrollRecordComponentResponse`, `PayrollSummaryResponse`.
- **Repository Layer (`app/repositories/payroll_period.py`)**: `PayrollPeriodRepository`, `PayrollRecordRepository`, and `PayrollRecordComponentRepository` providing period lookup, date range queries, employee history retrieval, and component breakdown queries.
- **Payroll Engine Service (`app/services/payroll_engine.py`)**: Core calculation engine integrating `EmployeeCompensation`, `SalaryStructureComponent` mappings, `Attendance` logs, and `LeaveRequest` approvals. Calculates proration ratios, gross salary, component earnings/deductions, net salary, period locking semantics, Redis cache invalidation (`payroll:*`), audit logging (`PAYROLL_PERIOD_CREATE`, `PAYROLL_GENERATE`, `PAYROLL_RECALCULATE`, `PAYROLL_APPROVE`, `PAYROLL_LOCK`), and Celery notification task dispatch.
- **Background Notification Task (`app/tasks/payroll_engine_tasks.py`)**: Asynchronous Celery task (`send_payroll_notification_task`) broadcasting payroll generation, approval, and locking alerts to Payroll Team, HR, and Finance.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded permissions `payroll.generate`, `payroll.read`, `payroll.approve`, `payroll.lock` bound to `Super Admin` and `HR Manager` roles.
- **Payroll Engine REST API Router (`app/api/v1/endpoints/payroll_engine.py`)**: Endpoints (`GET /payroll-periods`, `POST /payroll-periods`, `GET /payroll-periods/{id}`, `POST /payroll-periods/{id}/generate`, `POST /payroll-periods/{id}/approve`, `POST /payroll-periods/{id}/lock`, `GET /payroll-records`, `GET /payroll-records/{id}`, `GET /employees/{id}/payroll`).
- **Database Migration (`alembic/versions/ec95e52571cb_phase_v053_implement_payroll_engine.py`)**: Applied database migration creating `payroll_periods`, `payroll_records`, and `payroll_record_components` tables with foreign keys and unique constraints.
- **Architecture Decision Record (`docs/adr/ADR-0019-payroll-engine.md`)**: Documented payroll calculation engine architecture, attendance/leave proration integration, period locking rules, and future tax engine hooks.

---

## [v0.5.2] - 2026-07-27

### Milestone Payroll-3 — Employee Compensation Management

#### Added
- **EmployeeCompensation ORM Entity (`app/models/employee_compensation.py`)**: Model representing employee compensation policies (`employee_id`, `salary_structure_id`, `effective_from`, `effective_to`, `annual_ctc`, `monthly_gross_salary`, `monthly_net_salary`, `status`, `revision_number`, `previous_compensation_id`, `remarks`, `approved_by`, `approved_at`, soft deletion & timestamp mixins).
- **Pydantic v2 DTOs (`app/schemas/employee_compensation.py`)**: `EmployeeCompensationCreate`, `EmployeeCompensationRevise`, `EmployeeCompensationUpdate`, `EmployeeCompensationResponse`, `EmployeeCompensationListResponse`, `CompensationStatusEnum`.
- **Employee Compensation Repository (`app/repositories/employee_compensation.py`)**: `EmployeeCompensationRepository` providing active compensation lookup, compensation history retrieval, future policy queries, effective date overlap checks, soft deletion, and entity restoration.
- **Employee Compensation Service (`app/services/employee_compensation.py`)**: Service layer enforcing single active compensation policy constraints (auto-expires previous active compensation policy upon new activation), non-overlapping effective dates, revision numbering, Redis cache invalidation (`employee_compensation:*`), audit logging (`COMPENSATION_ASSIGN`, `COMPENSATION_REVISE`, `COMPENSATION_ACTIVATE`, `COMPENSATION_CANCEL`, `COMPENSATION_UPDATE`, `COMPENSATION_DELETE`, `COMPENSATION_RESTORE`), and Celery notification task dispatch.
- **Background Notification Task (`app/tasks/compensation_tasks.py`)**: Asynchronous Celery task (`send_compensation_notification_task`) broadcasting compensation policy modification alerts to HR and Employees.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded permissions `compensation.create`, `compensation.read`, `compensation.update`, `compensation.activate`, `compensation.cancel`, `compensation.delete` bound to `Super Admin` and `HR Manager` roles.
- **Employee Compensation API Router (`app/api/v1/endpoints/employee_compensation.py`)**: Endpoints (`GET /employee-compensations`, `GET /employee-compensations/{id}`, `GET /employees/{id}/compensation`, `GET /employees/{id}/compensation/history`, `POST /employee-compensations`, `PUT /employee-compensations/{id}`, `POST /employee-compensations/{id}/activate`, `POST /employee-compensations/{id}/cancel`, `DELETE /employee-compensations/{id}`, `PATCH /employee-compensations/{id}/restore`).
- **Database Migration (`alembic/versions/a3cad77f4bbb_phase_v052_implement_employee_.py`)**: Applied database migration creating `employee_compensations` table with foreign keys and indexes.
- **Architecture Decision Record (`docs/adr/ADR-0018-employee-compensation.md`)**: Documented employee compensation architecture, revision history, effective dating, and future payroll processing hooks.

---

## [v0.5.1] - 2026-07-27

### Milestone Payroll-2 — Enterprise Salary Structures

#### Added
- **SalaryStructure & SalaryStructureComponent ORM Entities (`app/models/salary_structure.py`)**: Models representing reusable salary structure templates (`code`, `name`, `description`, `currency`, `effective_from`, `effective_to`, `is_active`, soft deletion & timestamp mixins) and structure component mappings (`salary_structure_id`, `salary_component_id`, `component_order`, `component_value`, `calculation_method_override`, `is_active`, unique constraint `(salary_structure_id, salary_component_id)`).
- **Pydantic v2 DTOs (`app/schemas/salary_structure.py`)**: `SalaryStructureCreate`, `SalaryStructureUpdate`, `SalaryStructureResponse`, `SalaryStructureListResponse`, `SalaryStructureComponentCreate`, `SalaryStructureComponentUpdate`, `SalaryStructureComponentResponse`.
- **Salary Structure Repository (`app/repositories/salary_structure.py`)**: `SalaryStructureRepository` and `SalaryStructureComponentRepository` providing structure CRUD, component mapping lookup, soft deletion, and entity restoration.
- **Salary Structure Service (`app/services/salary_structure.py`)**: Service layer enforcing unique code and name constraints, effective date range validity (`effective_to >= effective_from`), component duplication prevention, Redis cache invalidation (`salary_structure:*`), audit logging (`SALARY_STRUCTURE_CREATE`, `SALARY_STRUCTURE_UPDATE`, `SALARY_STRUCTURE_DELETE`, `SALARY_STRUCTURE_RESTORE`, `SALARY_STRUCTURE_COMPONENT_ADD`, `SALARY_STRUCTURE_COMPONENT_UPDATE`, `SALARY_STRUCTURE_COMPONENT_REMOVE`), and Celery notification task dispatch.
- **Background Notification Task (`app/tasks/payroll_structure_tasks.py`)**: Asynchronous Celery task (`send_payroll_structure_notification_task`) broadcasting structure modification alerts to Payroll Administrators.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded permissions `salary_structure.create`, `salary_structure.read`, `salary_structure.update`, `salary_structure.delete`, `salary_structure.restore` bound to `Super Admin` and `HR Manager` roles.
- **Salary Structure API Router (`app/api/v1/endpoints/salary_structure.py`)**: Endpoints (`GET /salary-structures`, `GET /salary-structures/{id}`, `POST /salary-structures`, `PUT /salary-structures/{id}`, `DELETE /salary-structures/{id}`, `PATCH /salary-structures/{id}/restore`, `POST /salary-structures/{id}/components`, `PUT /salary-structures/{id}/components/{componentId}`, `DELETE /salary-structures/{id}/components/{componentId}`).
- **Database Migration (`alembic/versions/553f93450df0_phase_v051_implement_salary_structure.py`)**: Applied database migration creating `salary_structures` and `salary_structure_components` tables with foreign keys and unique constraints.
- **Architecture Decision Record (`docs/adr/ADR-0017-salary-structures.md`)**: Documented salary structures architecture, component mapping rules, statutory indicators, and future employee assignment hooks.

---

## [v0.5.0] - 2026-07-27

### Milestone Payroll-1 — Enterprise Salary Components

#### Added
- **SalaryComponent ORM Entity (`app/models/salary_component.py`)**: Entity representing organization-wide payroll component definitions (`code`, `name`, `description`, `type`, `calculation_method`, `default_value`, `percentage_value`, `is_taxable`, `is_pf_applicable`, `is_esi_applicable`, `is_active`, `display_order`, soft deletion & timestamp mixins).
- **Pydantic v2 DTOs (`app/schemas/salary_component.py`)**: `SalaryComponentCreate`, `SalaryComponentUpdate`, `SalaryComponentResponse`, `SalaryComponentListResponse`, `ComponentTypeEnum`, `CalculationMethodEnum`.
- **Salary Component Repository (`app/repositories/salary_component.py`)**: `SalaryComponentRepository` providing CRUD operations, lookup by code/name/display_order, active components query, soft deletion, and entity restoration.
- **Salary Component Service (`app/services/salary_component.py`)**: Service layer enforcing unique code, name, and display order constraints, calculation method rules (`Percentage` requires `percentage_value > 0`), Redis cache invalidation (`salary_component:*`), audit logging (`SALARY_COMPONENT_CREATE`, `SALARY_COMPONENT_UPDATE`, `SALARY_COMPONENT_DELETE`, `SALARY_COMPONENT_RESTORE`), and Celery notification task dispatch.
- **Background Notification Task (`app/tasks/payroll_component_tasks.py`)**: Asynchronous Celery task (`send_payroll_component_notification_task`) broadcasting component change alerts to Payroll Administrators.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded permissions `salary_component.create`, `salary_component.read`, `salary_component.update`, `salary_component.delete`, `salary_component.restore` bound to `Super Admin` and `HR Manager` roles.
- **Salary Component API Router (`app/api/v1/endpoints/salary_component.py`)**: Endpoints (`GET /salary-components`, `GET /salary-components/{id}`, `POST /salary-components`, `PUT /salary-components/{id}`, `DELETE /salary-components/{id}`, `PATCH /salary-components/{id}/restore`).
- **Database Migration (`alembic/versions/0c3454e55b21_phase_v050_implement_salary_component.py`)**: Applied database migration creating `salary_components` table with unique indexes on `code`, `name`, and `display_order`.
- **Architecture Decision Record (`docs/adr/ADR-0016-salary-components.md`)**: Documented salary components architecture, calculation method rules, statutory indicators, and future payroll integration hooks.

---

## [v0.4.5] - 2026-07-27

### Milestone Platform — Enterprise Approval Workflow Engine

#### Added
- **Approval Workflow & Request ORM Entities (`app/models/approval_workflow.py`)**: Models `ApprovalWorkflow`, `ApprovalStep`, `ApprovalRequest`, `ApprovalHistory` representing reusable approval workflow definitions, sequenced role steps, active workflow execution requests, and immutable audit history logs.
- **Pydantic v2 DTOs (`app/schemas/approval_workflow.py`)**: `ApprovalWorkflowCreate`, `ApprovalWorkflowUpdate`, `ApprovalWorkflowResponse`, `ApprovalStepCreate`, `ApprovalStepResponse`, `ApprovalRequestCreate`, `ApprovalActionRequest`, `ApprovalRequestResponse`, `ApprovalHistoryResponse`.
- **Approval Repository Layer (`app/repositories/approval_workflow.py`)**: `ApprovalWorkflowRepository`, `ApprovalStepRepository`, `ApprovalRequestRepository`, `ApprovalHistoryRepository` providing CRUD operations, step sequence lookup, active request retrieval, soft deletion, and entity restoration.
- **Approval Engine & Workflow Services (`app/services/approval_engine.py`, `app/services/approval_workflow.py`)**: Platform service layer enforcing multi-step sequential role approvals, state transitions (`Draft` -> `Pending` -> `Approved` / `Rejected` -> `Cancelled`), role authorization checks, immutable history logging, Redis cache invalidation (`approval:request:*`), audit logging (`APPROVAL_WORKFLOW_START`, `APPROVAL_STEP_APPROVE`, `APPROVAL_STEP_REJECT`, `APPROVAL_WORKFLOW_CANCEL`), and Celery notification task dispatch.
- **Background Notification Task (`app/tasks/approval_tasks.py`)**: Asynchronous Celery task (`send_approval_notification_task`) processing workflow start, step approval, rejection, and completion alerts.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded permissions `workflow.create`, `workflow.read`, `workflow.update`, `workflow.delete`, `approval.read`, `approval.approve`, `approval.reject` for Super Admin and HR Manager roles.
- **Approval Engine API Router (`app/api/v1/endpoints/approval.py`)**: Endpoints (`GET /approval-workflows`, `POST /approval-workflows`, `PUT /approval-workflows/{id}`, `GET /approval-requests`, `GET /approval-requests/{id}`, `POST /approval-requests`, `POST /approval-requests/{id}/approve`, `POST /approval-requests/{id}/reject`, `POST /approval-requests/{id}/cancel`).
- **Database Migration (`alembic/versions/bffc0a831a09_phase_v045_implement_approval_engine.py`)**: Applied database migration creating `approval_workflows`, `approval_steps`, `approval_requests`, and `approval_histories` tables with foreign keys and indexes.
- **Architecture Decision Record (`docs/adr/ADR-0015-approval-engine.md`)**: Documented approval engine architecture, multi-step role-based state machine, extension guide, and cache/audit integrations.

---

## [v0.4.4] - 2026-07-27

### Milestone HR-12 — Enterprise Leave Request Workflow

#### Added
- **LeaveRequest ORM Model (`app/models/leave_request.py`)**: Entity managing workflow leave applications (`employee_id`, `leave_type_id`, `start_date`, `end_date`, `total_days`, `is_half_day`, `half_day_session`, `reason`, `status`, `submitted_at`, `reviewed_at`, `reviewed_by`, `reviewer_comments`, soft deletion & timestamp mixins).
- **Pydantic v2 Schemas (`app/schemas/leave_request.py`)**: `LeaveRequestCreate`, `LeaveRequestUpdate`, `LeaveRequestReviewRequest`, `LeaveRequestCancelRequest`, `LeaveRequestResponse`, `LeaveRequestListResponse`, `LeaveRequestStatusEnum`, `HalfDaySessionEnum`.
- **Leave Request Repository (`app/repositories/leave_request.py`)**: `LeaveRequestRepository` providing employee request queries (`get_employee_requests_paginated`), overlap detection (`get_overlapping_requests`), pending approval queries (`get_pending_requests_paginated`), soft deletion, and entity restoration (`restore`).
- **Leave Request Service (`app/services/leave_request.py`)**: Workflow service layer implementing state machine transitions (`Draft` -> `Pending` -> `Approved` / `Rejected` -> `Cancelled`), working day calculation engine (excluding weekends & organizational holidays), policy checks (half-day, max consecutive days, gender restrictions, overlap prevention), leave balance updates upon approval/cancellation, Redis caching (`leave_request:employee:{emp_id}:*`), audit logging (`LEAVE_REQUEST_CREATE`, `LEAVE_REQUEST_SUBMIT`, `LEAVE_REQUEST_APPROVE`, `LEAVE_REQUEST_REJECT`, `LEAVE_REQUEST_CANCEL`, `LEAVE_REQUEST_COMPLETE`), and Celery notification dispatch.
- **Background Notification Task (`app/tasks/leave_request_tasks.py`)**: Asynchronous Celery task (`send_leave_request_notification_task`) broadcasting workflow alerts to managers, employees, and HR.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded permissions `leave_request.create`, `leave_request.read`, `leave_request.submit`, `leave_request.approve`, `leave_request.reject`, `leave_request.cancel` bound to `Super Admin` and `HR Manager` roles.
- **Leave Request API Router (`app/api/v1/endpoints/leave_request.py`)**: Endpoints (`GET /leave-requests`, `GET /leave-requests/{id}`, `GET /employees/{id}/leave-requests`, `POST /leave-requests`, `POST /leave-requests/{id}/submit`, `POST /leave-requests/{id}/approve`, `POST /leave-requests/{id}/reject`, `POST /leave-requests/{id}/cancel`).
- **Database Migration (`alembic/versions/2c2104f01875_phase_hr12_implement_leave_request.py`)**: Applied database migration creating `leave_requests` table with indexes on `employee_id`, `leave_type_id`, `start_date`, `end_date`, `status`, and `reviewed_by`.
- **Architecture Decision Record (`docs/adr/ADR-0014-leave-request-workflow.md`)**: Documented workflow state machine matrix, working day calculation engine, policy checks, leave balance reservation/updating, and future integration hooks.

---

## [v0.4.3] - 2026-07-27

### Milestone HR-11 — Enterprise Leave Balance Management

#### Added
- **LeaveBalance ORM Model (`app/models/leave_balance.py`)**: Authoritative entity storing employee leave entitlements (`employee_id`, `leave_type_id`, `leave_year`, `opening_balance`, `allocated_days`, `earned_days`, `availed_days`, `encashed_days`, `carried_forward_days`, `remaining_days`, `last_updated_by`, `is_active`, soft deletion & timestamp mixins). Composite unique constraint on `(employee_id, leave_type_id, leave_year)`.
- **Pydantic v2 Schemas (`app/schemas/leave_balance.py`)**: `LeaveBalanceCreate`, `LeaveBalanceUpdate`, `LeaveBalanceAdjustmentRequest`, `LeaveBalanceResponse`, `LeaveBalanceListResponse`.
- **Leave Balance Repository (`app/repositories/leave_balance.py`)**: `LeaveBalanceRepository` providing employee/year lookups (`get_by_employee_type_year`), paginated employee queries (`get_employee_balances_paginated`), soft deletion, and entity restoration (`restore`).
- **Leave Balance Service (`app/services/leave_balance.py`)**: Service layer implementing mathematical balance derivation (`opening + allocated + earned + carried_forward - availed - encashed`), negative balance policy enforcement (`NEGATIVE_LEAVE_BALANCE`), carry-forward validations, manual balance adjustments (`adjust_leave_balance`), Redis caching (`leave_balance:employee:{emp_id}:{year}`), audit logging (`LEAVE_BALANCE_CREATE`, `LEAVE_BALANCE_UPDATE`, `LEAVE_BALANCE_ADJUST`, `LEAVE_BALANCE_DELETE`, `LEAVE_BALANCE_RESTORE`), and Celery notification dispatch.
- **Background Notification Task (`app/tasks/leave_balance_tasks.py`)**: Asynchronous Celery task (`send_leave_balance_adjustment_notification_task`) broadcasting manual balance adjustment alerts to HR.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded permissions `leave_balance.create`, `leave_balance.read`, `leave_balance.update`, `leave_balance.adjust`, `leave_balance.delete`, `leave_balance.restore` bound to `Super Admin` and `HR Manager` roles.
- **Leave Balance API Router (`app/api/v1/endpoints/leave_balance.py`)**: Endpoints (`GET /leave-balances`, `GET /leave-balances/{id}`, `GET /employees/{id}/leave-balances`, `POST /leave-balances`, `PUT /leave-balances/{id}`, `PATCH /leave-balances/{id}/adjust`, `DELETE /leave-balances/{id}`, `PATCH /leave-balances/{id}/restore`).
- **Database Migration (`alembic/versions/bafb9849085f_phase_hr11_implement_leave_balance.py`)**: Applied database migration creating `leave_balances` table with composite unique index `(employee_id, leave_type_id, leave_year)`.
- **Architecture Decision Record (`docs/adr/ADR-0013-leave-balance.md`)**: Documented mathematical balance formula, negative balance guards, carry-forward rules, caching, and future Leave Request / Payroll integration hooks.

---

## [v0.4.2] - 2026-07-27

### Milestone HR-10 — Enterprise Leave Types & Policies

#### Added
- **LeaveType ORM Model (`app/models/leave_type.py`)**: Entity representing organizational leave policies (`code`, `name`, `description`, `is_paid`, `requires_approval`, `allow_half_day`, `allow_negative_balance`, `annual_allocation`, `carry_forward_allowed`, `max_carry_forward`, `max_consecutive_days`, `gender_restriction`, `is_active`, soft deletion & timestamp mixins).
- **Pydantic v2 Schemas (`app/schemas/leave_type.py`)**: `LeaveTypeCreate`, `LeaveTypeUpdate`, `LeaveTypeResponse`, `LeaveTypeListResponse`, `GenderRestrictionEnum`.
- **Leave Type Repository (`app/repositories/leave_type.py`)**: `LeaveTypeRepository` providing code/name lookups, soft deletion, and entity restoration (`restore`).
- **Leave Type Service (`app/services/leave_type.py`)**: Service layer enforcing policy validations (code/name uniqueness, carry forward caps, consecutive day limits), Redis caching (`leave_type:list`, `leave_type:detail:{id}`), audit logging (`LEAVE_TYPE_CREATE`, `LEAVE_TYPE_UPDATE`, `LEAVE_TYPE_DELETE`, `LEAVE_TYPE_RESTORE`), and background notification dispatch.
- **Background Notification Task (`app/tasks/leave_type_tasks.py`)**: Asynchronous Celery task (`send_leave_policy_change_notification_task`) broadcasting policy change events to HR Admins.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded permissions `leave_type.create`, `leave_type.read`, `leave_type.update`, `leave_type.delete`, `leave_type.restore` bound to `Super Admin` and `HR Manager` roles.
- **Leave Type API Router (`app/api/v1/endpoints/leave_type.py`)**: Endpoints (`GET /leave-types`, `GET /leave-types/{id}`, `POST /leave-types`, `PUT /leave-types/{id}`, `DELETE /leave-types/{id}`, `PATCH /leave-types/{id}/restore`).
- **Database Migration (`alembic/versions/49c913ab7229_phase_hr10_implement_leave_type.py`)**: Applied database migration creating `leave_types` table with unique indexes on `code` and `name`.
- **Architecture Decision Record (`docs/adr/ADR-0012-leave-types.md`)**: Documented organizational leave policy architecture, carry-forward validation rules, cache invalidation, and integration points for future Leave Request & Payroll modules.

---

## [v0.4.1] - 2026-07-27

### Milestone HR-9 — Enterprise Shift Assignment & Scheduling

#### Added
- **ShiftAssignment ORM Model (`app/models/shift_assignment.py`)**: Entity representing effective-dated employee shift assignments (`employee_id`, `shift_id`, `effective_from`, `effective_to`, `assignment_type`, `reason`, `assigned_by`, `is_active`, soft deletion & timestamp mixins).
- **Pydantic v2 Schemas (`app/schemas/shift_assignment.py`)**: `AssignmentType` Enum (`Permanent`, `Temporary`, `Rotation`), `ShiftAssignmentCreate`, `ShiftAssignmentUpdate`, `ShiftAssignmentEndRequest`, `ShiftAssignmentResponse`, `ShiftAssignmentListResponse`.
- **Shift Assignment Repository (`app/repositories/shift_assignment.py`)**: `ShiftAssignmentRepository` providing active assignment resolution for dates, overlap detection (`check_overlap`), paginated queries, and locked attendance detection (`has_locked_attendance_in_range`).
- **Shift Assignment Service (`app/services/shift_assignment.py`)**: Business logic for `assign_shift`, `update_assignment`, `end_assignment`, `delete_assignment`, and `resolve_shift_for_date`. Implements date range validation, overlap prevention, locked attendance immutability, Redis caching (`shift_assignment:active`), audit logging (`SHIFT_ASSIGNMENT_CREATE`, `SHIFT_ASSIGNMENT_UPDATE`, `SHIFT_ASSIGNMENT_END`, `SHIFT_ASSIGNMENT_DELETE`), and Celery notification dispatch.
- **Attendance Engine Integration (`app/services/attendance.py`)**: Updated `AttendanceService` to resolve shifts historically via `ShiftAssignmentService.resolve_shift_for_date` rather than depending on static `Employee.shift_id`.
- **Background Notification Task (`app/tasks/shift_assignment_tasks.py`)**: Asynchronous Celery task (`send_shift_assignment_notification_task`) processing shift assignment alerts to employees and managers.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded permissions `shift_assignment.create`, `shift_assignment.read`, `shift_assignment.update`, `shift_assignment.delete` bound to `Super Admin` and `HR Manager` roles.
- **Shift Assignment API Router (`app/api/v1/endpoints/shift_assignment.py`)**: Endpoints (`GET /shift-assignments`, `GET /employees/{id}/shift-assignments`, `GET /shift-assignments/{id}`, `POST /shift-assignments`, `PUT /shift-assignments/{id}`, `PATCH /shift-assignments/{id}/end`, `DELETE /shift-assignments/{id}`).
- **Database Migration (`alembic/versions/b05ba39bc33a_phase_hr9_implement_shift_assignment.py`)**: Applied database migration creating `shift_assignments` table with composite index `(employee_id, effective_from, effective_to)`.
- **Architecture Decision Record (`docs/adr/ADR-0011-shift-assignment.md`)**: Documented effective-dated scheduling architecture, overlap validation logic, attendance resolution, locked attendance guards, and cache invalidation rules.
- **Test Suite (`tests/test_shift_assignments.py`)**: Comprehensive test suite verifying CRUD operations, date overlap detection, historical shift resolution, attendance engine integration, locked attendance immutability, Redis cache invalidation, Celery task dispatch, RBAC enforcement, and audit trail logging.

---

## [v0.4.0] - 2026-07-27

### Milestone HR-8 — Enterprise Attendance Engine

#### Added
- **Attendance ORM Model (`app/models/attendance.py`)**: Daily attendance record entity storing `employee_id`, `attendance_date`, `shift_id`, `check_in_time`, `check_out_time`, `break_minutes`, `worked_minutes`, `expected_minutes`, `late_minutes`, `early_departure_minutes`, `attendance_status`, `is_manual_correction`, `corrected_by_user_id`, `correction_notes`, `is_locked`, and soft deletion fields. Unique constraint on `(employee_id, attendance_date)`.
- **Attendance Engine Domain Service (`app/services/attendance_engine.py`)**: Pure, deterministic business rules engine evaluating attendance status (`Present`, `Late`, `Half Day`, `Absent`, `Holiday`, `Weekend`, `On Leave`, `Missing Check-in`, `Missing Check-out`) and calculating worked minutes, expected minutes, tardiness, and early departure across day and overnight shift boundaries.
- **Pydantic v2 Schemas (`app/schemas/attendance.py`)**: `AttendanceStatus` Enum, `CheckInRequest`, `CheckOutRequest`, `AttendanceCorrectionRequest`, `AttendanceLockRequest`, `AttendanceResponse`, `AttendanceSummary`, `AttendanceListResponse`.
- **Attendance Repository (`app/repositories/attendance.py`)**: Extends `BaseRepository` with `get_by_employee_and_date`, `get_monthly_attendance`, `get_department_attendance`, and aggregated range `get_summary`.
- **Attendance Service Layer (`app/services/attendance.py`)**: Coordinates business validations, check-in, check-out, manual HR corrections with audit notes, payroll record locking, Redis caching (`attendance:today`), enterprise audit logging (`ATTENDANCE_CHECKIN`, `ATTENDANCE_CHECKOUT`, `ATTENDANCE_CORRECT`, `ATTENDANCE_LOCK`), and Celery notification dispatch.
- **Background Notification Task (`app/tasks/attendance_tasks.py`)**: Asynchronous Celery task (`send_attendance_notification_task`) processing late arrival alerts, missing check-outs, and manual corrections.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded permissions `attendance.read`, `attendance.checkin`, `attendance.checkout`, `attendance.correct`, `attendance.lock` bound to `Super Admin` and `HR Manager` roles.
- **Attendance API Router (`app/api/v1/endpoints/attendance.py`)**: RESTful endpoints (`GET /attendance`, `GET /attendance/{id}`, `GET /attendance/employee/{id}`, `GET /attendance/month`, `POST /attendance/checkin`, `POST /attendance/checkout`, `PATCH /attendance/correct`, `PATCH /attendance/lock`). Registered in `app/api/v1/api.py`.
- **Database Migration (`alembic/versions/184caa5625f2_phase_hr8_implement_attendance_engine_.py`)**: Applied database migration creating `attendance` table.
- **Architecture Decision Record (`docs/adr/ADR-0010-attendance-engine.md`)**: Documented attendance engine architecture, state machine, overnight shift calculation rules, locked record protection, and integration contracts for Leave and Payroll modules.
- **Test Suite (`tests/test_attendance.py`)**: Pytest suite validating domain calculations, overnight shifts, holiday/weekend scenarios, check-in/out workflows, manual corrections, record locking, RBAC permissions, audit logging, Redis caching, Celery telemetry, and full regression testing.

---

## [v0.3.0] - 2026-07-26

### Milestone HR-7 — Enterprise Holiday Calendar

#### Added
- **Holiday ORM Model (`app/models/holiday.py`)**: Official holiday schedule entity storing `code` (unique, indexed), `name` (indexed), `description`, `holiday_date`, `holiday_type` (`National`, `Regional`, `Company`, `Optional`), `country`, `state_region`, `is_half_day`, `is_recurring_annually`, `is_active`, and soft deletion fields.
- **Pydantic v2 Schemas (`app/schemas/holiday.py`)**: `HolidayType` Enum, `HolidayCreate`, `HolidayUpdate`, `HolidayResponse`, `HolidaySummary`, `HolidayListResponse`.
- **Holiday Repository (`app/repositories/holiday.py`)**: Extends `BaseRepository` with `get_by_code`, `exists_by_code`, `get_by_date_and_region`, `get_holidays_by_year` (with annual recurring holiday projection), and `get_holidays_by_date`.
- **Holiday Service Layer (`app/services/holiday.py`)**: Business service implementing holiday validations, unique code check, duplicate date+region check, year/date holiday queries with annual recurring logic, Redis caching (`holiday:list`), enterprise audit logging (`HOLIDAY_CREATE`, `HOLIDAY_UPDATE`, `HOLIDAY_DELETE`, `HOLIDAY_RESTORE`), and Celery telemetry.
- **Background Notification Task (`app/tasks/holiday_tasks.py`)**: Asynchronous Celery task (`send_holiday_notification_task`) processing holiday creation, update, and deletion events.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded permissions `holiday.create`, `holiday.read`, `holiday.update`, `holiday.delete`, `holiday.restore` bound to `Super Admin` and `HR Manager` roles.
- **Holiday API Router (`app/api/v1/endpoints/holidays.py`)**: RESTful endpoints (`GET /holidays`, `GET /holidays/{id}`, `GET /holidays/year/{year}`, `GET /holidays/date/{date}`, `POST /holidays`, `PUT /holidays/{id}`, `DELETE /holidays/{id}`, `PATCH /holidays/{id}/restore`). Registered in `app/api/v1/api.py`.
- **Database Migration (`alembic/versions/9871e1fb35a0_phase_hr7_implement_holiday_calendar_.py`)**: Applied database migration creating `holidays` table.
- **Architecture Decision Record (`docs/adr/ADR-0009-holiday-calendar.md`)**: Documented holiday calendar architecture, regional scoping, annual recurring projection algorithm, and integration contracts for Attendance, Leave, and Payroll modules.
- **Test Suite (`tests/test_holidays.py`)**: Pytest suite validating repository methods, service validations, duplicate date+region checks, annual recurring holiday projections, REST API endpoints, RBAC authorization, audit logging, Redis caching, Celery telemetry, and full regression testing.

---

### Milestone HR-6 — Enterprise Shift Management

#### Added
- **Shift ORM Model (`app/models/shift.py`)**: Reusable shift schedule entity storing `code` (unique, indexed), `name` (unique, indexed), `description`, `start_time`, `end_time`, `break_duration_minutes`, `grace_period_minutes`, `minimum_working_hours`, `maximum_working_hours`, `is_night_shift`, `is_flexible_shift`, `is_active`, and soft deletion fields. Includes `@property def duration_hours` for calculating shift length across day/night boundaries.
- **Employee Model Integration (`app/models/employee.py`)**: Extended `Employee` model with nullable `shift_id` FK (`ondelete="SET NULL"`) referencing `shifts.id` and `shift` relationship (`lazy="selectin"`).
- **Pydantic v2 Schemas (`app/schemas/shift.py`)**: `ShiftCreate`, `ShiftUpdate`, `ShiftResponse`, `ShiftSummary`, `ShiftListResponse`. Extended `app/schemas/employee.py` with optional `shift_id` and `shift_name`.
- **Shift Repository (`app/repositories/shift.py`)**: Extends `BaseRepository` with `get_by_code`, `get_by_name`, `exists_by_code`, `exists_by_name`, and `get_assigned_employee_count`.
- **Shift Service Layer (`app/services/shift.py`)**: Business service implementing shift duration calculations, overnight shift auto-detection, break duration sanity checks (`break_duration_minutes < shift_duration_hours`), grace period sanity checks (`grace_period_minutes < shift_duration_hours`), working hour bounds validation (`minimum_working_hours <= maximum_working_hours`), active employee deletion guard (`ASSIGNED_EMPLOYEES_EXIST`), Redis caching (`shift:list`, `shift:detail:{id}`), enterprise audit logging (`SHIFT_CREATE`, `SHIFT_UPDATE`, `SHIFT_DELETE`, `SHIFT_RESTORE`), and Celery telemetry.
- **Background Notification Task (`app/tasks/shift_tasks.py`)**: Asynchronous Celery task (`send_shift_notification_task`) processing shift creation, update, and deletion events.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded permissions `shift.create`, `shift.read`, `shift.update`, `shift.delete`, `shift.restore` bound to `Super Admin` and `HR Manager` roles.
- **Shift API Router (`app/api/v1/endpoints/shifts.py`)**: RESTful endpoints (`GET /shifts`, `GET /shifts/{id}`, `POST /shifts`, `PUT /shifts/{id}`, `DELETE /shifts/{id}`, `PATCH /shifts/{id}/restore`). Registered in `app/api/v1/api.py`.
- **Database Migration (`alembic/versions/9eb88bfb9c06_phase_hr6_implement_shifts_table_and_.py`)**: Applied database migration creating `shifts` table and adding `shift_id` FK column to `employees`.
- **Architecture Decision Record (`docs/adr/ADR-0008-shift-management.md`)**: Documented shift architecture, overnight shift calculation algorithm, active shift deletion guard, and integration contracts for Attendance and Payroll modules.
- **Test Suite (`tests/test_shifts.py`)**: Pytest suite validating repository methods, service validations, overnight duration calculations, break/grace period bounds, active employee assignment deletion guard, REST API endpoints, RBAC authorization, audit logging, Redis caching, Celery telemetry, and full regression testing.

---

### Milestone HR-5 — HR Configuration & Organization Policies

#### Added
- **HRConfiguration ORM Model (`app/models/hr_configuration.py`)**: Centralized organization-wide policy model storing organization name, organization code, IANA timezone, country, currency ISO code, standard daily working hours, standard weekly working days, weekend configuration JSON, default shift name, grace period minutes, minimum working hours for half-day credit, default probation period days, leave year start month, payroll cycle frequency (`Monthly`, `Biweekly`, `Weekly`), fiscal year start month, active status flag, and soft deletion.
- **Pydantic v2 Schemas (`app/schemas/hr_configuration.py`)**: `PayrollCycle` Enum, `HRConfigurationCreate`, `HRConfigurationUpdate`, `HRConfigurationResponse`, `HRConfigurationListResponse`.
- **HRConfiguration Repository (`app/repositories/hr_configuration.py`)**: Extends `BaseRepository` with `get_active_configuration`, `get_by_organization_code`, and `deactivate_all_active_configurations`.
- **HRConfiguration Service Layer (`app/services/hr_configuration.py`)**: Business service implementing IANA timezone validation (`zoneinfo`), weekend day name checks, working hours sanity checks (`minimum_working_hours <= standard_working_hours_per_day`), currency ISO validation, singleton active configuration enforcement (deactivates previous active configuration when activating a new policy), active policy deletion guard (`ACTIVE_CONFIG_DELETION_PROHIBITED`), Redis caching (`hr_configuration:active`), audit logging (`HR_CONFIG_CREATE`, `HR_CONFIG_UPDATE`, `HR_CONFIG_ACTIVATE`, `HR_CONFIG_DELETE`, `HR_CONFIG_RESTORE`), and Celery telemetry.
- **Background Notification Task (`app/tasks/hr_config_tasks.py`)**: Asynchronous Celery task (`send_hr_config_notification_task`) processing HR configuration creation, update, and activation events.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Added permissions `hr_configuration.read`, `hr_configuration.create`, `hr_configuration.update`, `hr_configuration.activate`, `hr_configuration.delete`, `hr_configuration.restore` bound to `Super Admin` and `HR Manager` roles.
- **HR Configuration API Router (`app/api/v1/endpoints/hr_configurations.py`)**: RESTful endpoints (`GET /hr/configuration`, `GET /hr/configurations/{id}`, `POST /hr/configuration`, `PUT /hr/configuration/{id}`, `PATCH /hr/configuration/{id}/activate`, `DELETE /hr/configuration/{id}`, `PATCH /hr/configuration/{id}/restore`).
- **Database Migration (`alembic/versions/f3515986f924_phase_hr5_implement_hr_configurations_.py`)**: Applied database migration for `hr_configurations` table.
- **Architecture Decision Record (`docs/adr/ADR-0007-hr-configuration.md`)**: Documented single source of truth architecture, singleton active policy pattern, active deletion guard, and integration contracts for future HR modules (Attendance, Leave, Payroll, Recruitment, Performance, Shift Scheduling).
- **Test Suite (`tests/test_hr_configurations.py`)**: Comprehensive pytest test suite validating repository methods, service validations, singleton active enforcement, active policy deletion guard, REST API endpoints, RBAC authorization, audit logging, Redis caching, Celery telemetry, and full regression across all 80+ platform tests.

---

### Milestone HR-4 — Job Positions & Employment Structure

#### Added
- **Position ORM Model (`app/models/position.py`)**: Enterprise job position model supporting unique code, title, department link, parent position self-referential hierarchy, employment category (`Permanent`, `Contract`, `Temporary`, `Internship`), grade, level, maximum/current headcount capacity, managerial flag, active status, and soft deletion.
- **Employee Extension (`app/models/employee.py`)**: Extended `Employee` model with `position_id` (FK to `positions.id`), `employment_start_date`, `employment_end_date`, and `position` relationship.
- **Pydantic v2 Schemas (`app/schemas/position.py`)**: `PositionCreate`, `PositionUpdate`, `PositionResponse`, `PositionSummary`, `PositionTreeResponse`, `PositionListResponse`, and `EmploymentCategory` Enum. Updated `app/schemas/employee.py`.
- **Position Repository (`app/repositories/position.py`)**: Extends `BaseRepository` with `get_by_code`, `get_by_department_and_title`, `get_by_department`, `get_children`, `get_tree`, and `exists_by_code`.
- **Position Service Layer (`app/services/position.py`)**: Business service layer enforcing unique code/title validation, inactive/deleted department guards, circular position loop checks (`_validate_no_circular_position`), headcount constraints (`maximum_headcount` vs `current_headcount`), Redis tree caching (`position:tree`), audit logging (`POSITION_CREATE`, `POSITION_UPDATE`, `POSITION_DELETE`, `POSITION_RESTORE`), and Celery telemetry.
- **Employee Service Integration (`app/services/employee.py`)**: Integrated automatic position headcount increments/decrements upon employee assignment, removal, or update. Enforces `HEADCOUNT_LIMIT_EXCEEDED` guard.
- **Background Notification Task (`app/tasks/position_tasks.py`)**: Asynchronous task (`send_position_notification_task`) processing position mutation and headcount limit warning notifications.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Added `position.create`, `position.read`, `position.update`, `position.delete`, `position.restore` permissions bound to `Super Admin` and `HR Manager` roles.
- **Position API Router (`app/api/v1/endpoints/positions.py`)**: Exposed RESTful endpoints (`GET /positions`, `GET /positions/{id}`, `GET /positions/tree`, `GET /departments/{department_id}/positions`, `POST /positions`, `PUT /positions/{id}`, `DELETE /positions/{id}`, `PATCH /positions/{id}/restore`).
- **Database Migration (`alembic/versions/7178a901bcde_phase_hr4_implement_positions_table_and_.py`)**: Applied migration for `positions` table and `employees` extensions.
- **Architecture Decision Record (`docs/adr/ADR-0006-position-management.md`)**: Documented decision, headcount capacity controls, position hierarchy, and future module integration.
- **Test Suite (`tests/test_positions.py`)**: Built comprehensive pytest test suite verifying repository methods, service validations, circular hierarchy checks, headcount constraint enforcement, auto-increment/decrement on employee assignment, Redis caching, Celery tasks, RBAC, and API endpoints.

---

### Milestone HR-3 — Employee Documents & Digital Personnel Files

#### Added
- **EmployeeDocument ORM Model (`app/models/employee_document.py`)**: Digital personnel document model linking `Employee` and `File` entities, supporting document types (`Aadhaar`, `PAN`, `Passport`, `Driving License`, `Resume`, `Offer Letter`, `Contract`, `NDA`, etc.), verification status (`Pending`, `Verified`, `Rejected`), verifier user link, timestamps, notes, mandatory flags, and soft deletion.
- **Pydantic v2 Schemas (`app/schemas/employee_document.py`)**: `EmployeeDocumentCreate`, `EmployeeDocumentUpdate`, `EmployeeDocumentResponse`, `EmployeeDocumentListResponse`, `DocumentVerifyRequest`, `DocumentRejectRequest`, `DocumentType`, and `VerificationStatus` Enums.
- **EmployeeDocument Repository (`app/repositories/employee_document.py`)**: Extends `BaseRepository` with `get_by_employee`, `get_by_file`, `exists_mandatory_document_type`, and `get_expiring_documents`.
- **EmployeeDocument Service Layer (`app/services/employee_document.py`)**: Business service implementing active employee and storage file validation, date sanity (`expiry_date >= issue_date`), duplicate mandatory document protection, verification and rejection workflows (`verify_document`, `reject_document`), Redis caching (`employee_document:list:{id}`), audit logging (`DOCUMENT_UPLOAD`, `DOCUMENT_VERIFY`, `DOCUMENT_REJECT`, etc.), and background Celery task dispatching.
- **Background Notification Task (`app/tasks/document_tasks.py`)**: Asynchronous task (`send_document_notification_task`) processing document upload, verification, and rejection background notifications.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Added `employee_document.create`, `employee_document.read`, `employee_document.update`, `employee_document.delete`, `employee_document.verify`, `employee_document.restore` permissions bound to `Super Admin` and `HR Manager` roles.
- **Employee Document API Router (`app/api/v1/endpoints/employee_documents.py`)**: RESTful endpoints (`GET /employee-documents`, `GET /employee-documents/{id}`, `GET /employees/{employee_id}/documents`, `POST /employee-documents`, `PUT /employee-documents/{id}`, `DELETE /employee-documents/{id}`, `PATCH /employee-documents/{id}/restore`, `PATCH /employee-documents/{id}/verify`, `PATCH /employee-documents/{id}/reject`).
- **Database Migration (`alembic/versions/903d8105712c_phase_hr3_implement_employee_documents_.py`)**: Applied migration for `employee_documents` table.
- **Architecture Decision Record (`docs/adr/ADR-0005-employee-documents.md`)**: Documented digital personnel files architecture, verification workflow, and storage provider reuse.
- **Test Suite (`tests/test_employee_documents.py`)**: Built comprehensive pytest test suite verifying repository methods, service validations, verification/rejection workflow, mandatory document check, Redis caching, Celery tasks, RBAC, and API endpoints.

---

### Milestone HR-2 — Enterprise Employee Domain (Core)

#### Added
- **Employee ORM Model (`app/models/employee.py`)**: Core `Employee` model featuring employee code, work/personal email, department assignment, manager reporting link, employment type (`Full Time`, `Part Time`, `Contract`, `Intern`), status (`Active`, `Probation`, `Notice Period`, `Suspended`, `Resigned`, `Terminated`), dates, profile photo file reference, and soft deletion.
- **Pydantic v2 Schemas (`app/schemas/employee.py`)**: `EmployeeCreate`, `EmployeeUpdate`, `EmployeeResponse`, `EmployeeSummary`, `EmployeeListResponse`, `EmployeeHierarchyResponse`, and `EmploymentType`/`EmploymentStatus` Enums.
- **Employee Repository (`app/repositories/employee.py`)**: Extends `BaseRepository` with `get_by_code`, `get_by_work_email`, `get_by_user_id`, `get_by_department`, `get_direct_reports`, and existence check methods.
- **Employee Service Layer (`app/services/employee.py`)**: Business service layer implementing unique code/email checks, date sanity checks (`joining_date` <= `exit_date`), self-management prevention, circular manager reporting hierarchy loop validation, active department validation, Redis caching (`employee:hierarchy`, `employee:department:{id}`), audit logging, and background Celery task dispatching.
- **Background Notification Task (`app/tasks/employee_tasks.py`)**: Asynchronous task (`send_employee_notification_task`) processing employee creation, update, and deletion background event notifications.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Added `employee.create`, `employee.read`, `employee.update`, `employee.delete`, `employee.restore` permissions bound to `Super Admin` and `HR Manager` roles.
- **Employee API Router (`app/api/v1/endpoints/employees.py`)**: RESTful endpoints (`GET /employees/hierarchy`, `GET /employees/department/{department_id}`, `GET /employees`, `GET /employees/{id}`, `POST /employees`, `PUT /employees/{id}`, `DELETE /employees/{id}`, `PATCH /employees/{id}/restore`).
- **Database Migration (`alembic/versions/d04dad64b43e_phase_hr2_implement_employees_table.py`)**: Applied migration for `employees` table.
- **Architecture Decision Record (`docs/adr/ADR-0004-employee-domain.md`)**: Documented decision, trade-offs, and future module integration points.
- **Test Suite (`tests/test_employees.py`)**: Built comprehensive test suite covering repository operations, service validations, circular reporting checks, inactive department checks, Redis caching, Celery tasks, RBAC, and API endpoints.

---

### Milestone HR-1 — Department Management Module

#### Added
- **Department ORM Model (`app/models/department.py`)**: `Department` model supporting self-referential parent-child relationships, manager assignments, unique code/name constraints, soft deletion, and timestamp tracking.
- **Pydantic v2 Schemas (`app/schemas/department.py`)**: Created `DepartmentCreate`, `DepartmentUpdate`, `DepartmentResponse`, `DepartmentSummary`, `DepartmentTreeResponse`, and `DepartmentListResponse`.
- **Department Repository (`app/repositories/department.py`)**: Implemented `DepartmentRepository` extending `BaseRepository` with `get_by_code`, `get_by_name`, `get_children`, `get_tree`, `exists_by_code`, `exists_by_name`.
- **Department Service Layer (`app/services/department.py`)**: Business service enforcing unique code/name validation, circular parent reference prevention, active child deletion protection, Redis caching (`department:tree`), audit logging, and background Celery task dispatching.
- **Background Notification Task (`app/tasks/department_tasks.py`)**: Asynchronous Celery task (`send_department_notification_task`) processing department mutation notifications.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Added `department.create`, `department.read`, `department.update`, `department.delete`, `department.restore` permissions bound to `Super Admin` and `HR Manager` roles.
- **Department API Router (`app/api/v1/endpoints/departments.py`)**: Exposed RESTful endpoints (`GET /departments/tree`, `GET /departments`, `GET /departments/{id}`, `POST /departments`, `PUT /departments/{id}`, `DELETE /departments/{id}`, `PATCH /departments/{id}/restore`).
- **Database Migration (`alembic/versions/d45778acc419_phase_hr1_implement_departments_table.py`)**: Created and applied Alembic migration for `departments` table.
- **Architecture Decision Record (`docs/adr/ADR-0003-department-domain.md`)**: Documented design drivers, decision, and trade-offs.
- **Test Suite (`tests/test_departments.py`)**: Built comprehensive pytest test suite verifying repository, service, circular reference validation, child deletion guard, Redis caching, audit logging, Celery integration, and API endpoints.

---

## [v0.2.2] - 2026-07-26

### Milestone 0.2.2 — Enterprise Task Processing Platform (Celery Infrastructure)

#### Added
- **Celery Application Infrastructure (`app/core/celery.py`)**: Configured Celery application instance (`celery_app`) with JSON serialization, Kombu priority queues (`default`, `high_priority`, `low_priority`, `periodic`), and task routing.
- **Reusable Task Base Classes (`app/tasks/base.py`)**: Implemented `BaseTask`, `RetryTask`, `PeriodicTask`, and `LoggingTask`.
- **Infrastructure System Tasks (`app/tasks/system_tasks.py`)**: Implemented `system_ping_task` and `system_health_check_task`.
- **Health Telemetry Endpoints (`app/api/v1/endpoints/health.py`)**: Added `GET /health/celery` and `GET /health/workers`.

---

## [v0.2.1] - 2026-07-26

### Milestone 0.2.1 — Redis Infrastructure

#### Added
- **Redis Infrastructure Layer (`app/core/redis.py`)**: Implemented `RedisManager` with `redis.asyncio` connection pooling and operation wrappers.

---

## [v0.2.0] - 2026-07-26

### Core Platform Infrastructure

#### Added
- Authentication, RBAC, Generic CRUD Framework, Enterprise Audit Logging, File Management Service, Notification System.
