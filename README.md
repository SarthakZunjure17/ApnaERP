# ApnaERP - Enterprise Resource Planning Backend API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Celery](https://img.shields.io/badge/Celery-5.4+-37B24D.svg?style=flat&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D.svg?style=flat&logo=redis&logoColor=white)](https://redis.io)

ApnaERP is a production-grade, modular, high-performance Enterprise Resource Planning (ERP) backend built using Python, FastAPI, PostgreSQL, Redis, Celery, Alembic, JWT, Role-Based Access Control (RBAC), Generic CRUD Framework, Enterprise Audit Logging, Enterprise File Management, Enterprise Notification System, Enterprise Celery Task Processing Platform, Department Management Module, Core Employee Domain, Digital Personnel Files (Employee Documents), Job Positions & Employment Structure, HR Configuration & Organization Policies, Enterprise Shift Management, Enterprise Holiday Calendar, Enterprise Attendance Engine, Enterprise Salary Components, Enterprise Salary Structures, Employee Compensation Management, Enterprise Payroll Processing Engine, Enterprise Payroll Runs & Payslips, Enterprise Statutory Compliance Engine, Enterprise Payroll Finalization Suite, and Docker.

## Finance Operations & Financial Reporting (Release v1.1.0)

### Overview
The **Finance Operations & Financial Reporting** module (`app/models/finance_ops.py`, `app/services/finance_ops_services.py`, `app/repositories/finance_ops_repos.py`, `app/schemas/finance_ops.py`, `app/api/v1/endpoints/finance_*.py`) completes the entire Finance Domain for ApnaERP. It extends the central double-entry Journal Engine to power all operational financial workflows: Accounts Receivable, Accounts Payable, Payment & Receipt Vouchers, Bank Accounts & Bank Statement Reconciliation, Fixed Assets & Depreciation, Annual/Departmental Budgets, Financial Statements, Period Closings, Executive Analytics, and Domain Events.

### Key Technical Capabilities
- **Accounts Receivable (`CustomerInvoice`, `CustomerLedgerEntry`, `CustomerCreditNote`, `CustomerDebitNote`)**: Complete AR sales invoicing, posting to GL via Journal Engine, real-time customer sub-ledgers, aging analysis (Current, 30, 60, 90+ days), and customer statements.
- **Accounts Payable (`SupplierBill`, `SupplierLedgerEntry`, `SupplierCreditNote`, `SupplierDebitNote`)**: Vendor bill processing, posting to GL via Journal Engine, real-time supplier sub-ledgers, aging analysis, and vendor statements.
- **Payments & Vouchers (`ReceiptVoucher`, `PaymentVoucher`, `PaymentAllocation`)**: Outbound payments and inbound payment receipts with partial allocation against open invoices/bills and GL posting.
- **Bank Management & Reconciliation (`BankAccount`, `BankTransaction`, `BankStatement`, `BankReconciliation`)**: Multi-bank account tracking, bank statement imports (CSV/OFX), automated rule-based transaction matching, manual match override, and unreconciled item auditing without altering posted journal entries.
- **Fixed Assets & Depreciation (`AssetCategory`, `FixedAsset`, `DepreciationSchedule`)**: Fixed asset register, acquisition journal posting, straight-line and written-down value depreciation schedule calculation, and automated monthly depreciation journal posting.
- **Budget Management (`Budget`, `BudgetLine`)**: Annual and departmental budget headers and lines, approval workflow routing, revisions, and real-time budgeted vs actual variance analysis.
- **Financial Statements & Reports (`FinancialStatementSnapshot`)**: Real-time generation and snapshotting of Trial Balance, Balance Sheet, Profit & Loss, Cash Flow Statement, Day Book, Cash Book, Bank Book, and Tax Summaries.
- **Financial Closing (`ClosingService`)**: Period closing, year-end closing, opening balance carry forward, and period locking against posted transactions.
- **Finance Analytics (`AnalyticsService`)**: Financial metrics (Revenue, Expenses, Net Margin, Cash Position, AR/AP Outstanding, Asset Value, Financial Ratios: Current, Quick, Debt-to-Equity) with Redis caching.

---

## Finance Core — Central Accounting Engine (Release v1.0.0)

### Overview
The Finance Core (`app/models/finance.py`, `app/services/finance_services.py`, `app/repositories/finance_repos.py`, `app/schemas/finance.py`, `app/api/v1/endpoints/finance_*.py`) implements the central accounting foundation for ApnaERP. It establishes double-entry ledger bookkeeping, hierarchical Chart of Accounts, Fiscal Calendar with Period Locks, Multi-Currency Exchange Engine, Cost Center & Dimension Allocations, Tax Rules, Immutability & Reversals, and Automated Financial Posting Queues for cross-domain integration (Payroll, Procurement, Sales, Inventory).

### Key Technical Capabilities
- **Hierarchical Chart of Accounts (`AccountGroup`, `ChartOfAccount`)**: Multi-level parent-child group structures and GL account master supporting Assets, Liabilities, Equity, Income, and Expense types.
- **Fiscal Calendar & Period Locking (`FiscalYear`, `FiscalPeriod`)**: Multi-period fiscal calendar with automated 12-month period generation, status lifecycle (Draft, Open, Closed), and period locking against posted transactions.
- **Multi-Currency & Exchange Engine (`Currency`, `ExchangeRate`)**: Base currency designation, daily exchange rate tracking, cross-currency conversion, and foreign exchange gain/loss support.
- **Cost Center & Dimension Accounting (`CostCenter`, `AccountingDimension`)**: Departmental cost center hierarchies and multidimensional ledger allocations (Branch, Project, Region, Cost Center).
- **Tax Configuration & Compliance Engine (`TaxCategory`, `TaxRate`)**: Input/Output VAT, GST, and Tax category configuration with effective date sensitivity and percentage rates.
- **Double-Entry Engine & Immutability (`JournalType`, `Journal`, `JournalLine`)**: Mandatory double-entry ledger engine enforcing `Total Debit == Total Credit`. Posted journals are immutable; reversals create counter-balancing `REV-` journals linked to the original entry.
- **Automated Financial Posting Queue (`PostingRule`, `AccountingEvent`, `FinancialPostingQueue`)**: Event-driven posting engine that consumes domain events from Payroll, Procurement, Sales, and Inventory, matching configurable `PostingRules` to generate and post General Ledger Journals automatically.

---

## CRM Domain — Enterprise Customer Relationship Management (Release v0.9.0)

### Overview
The CRM Domain (`app/models/crm.py`, `app/services/crm_services.py`, `app/repositories/crm_repos.py`, `app/schemas/crm.py`) implements the complete Customer Relationship Management platform for ApnaERP. It manages the full customer acquisition lifecycle: Lead Management, Opportunity Pipeline, Activity Tracking, Calendar & Meetings, Task Dependencies, Marketing Campaigns, Unified Customer Timeline, Lead Conversion Engine with Customer Reuse, Executive CRM Analytics, Global CRM Search, and CSV Import/Export.

### Key Technical Capabilities
- **Lead Management (`Lead`, `LeadSource`, `LeadTag`, `LeadNote`)**: Automated lead scoring engine, duplicate detection, lead assignment, tags, rich notes, and lead merging.
- **Opportunity Pipeline (`Opportunity`, `OpportunityStage`)**: Stage pipeline management with default win probabilities, expected revenue forecasting, closing date tracking, and win/loss reason logging.
- **Activity & Calendar Management (`Activity`, `Meeting`, `Task`)**: Calls, meetings, appointments, tasks, follow-ups, and reminders. Tasks feature parent-child dependency trees.
- **Campaign Management (`Campaign`, `CampaignMember`)**: Marketing campaigns across Email, Event, Referral, and Social channels. Tracks budgets, actual costs, revenues, and automated ROI calculation.
- **Lead Conversion Engine & Customer Reuse**: Converts Leads into Opportunities while searching for existing Sales `Customer` records (by email, phone, or company). Reuses existing `Customer` entries without creating duplicates, or generates a new `Customer` via `CustomerService` when no match exists.
- **Unified Interaction Timeline (`TimelineEvent`)**: Aggregates interaction events across Leads, Opportunities, Customers, Meetings, Activities, Tasks, Sales Orders, Quotations, and Deliveries.
- **CRM Analytics & Search**: Lead funnel reports, forecast revenue calculation, Redis executive summary caching, and multi-entity global search across Leads, Opportunities, and Tasks.

---

## Sales Domain — Enterprise Order-to-Cash Architecture (Release v0.8.0)

### Overview
The Sales Domain (`app/models/customer.py`, `app/models/pricing.py`, `app/models/sales_quotation.py`, `app/models/sales_order.py`, `app/models/delivery_order.py`, `app/models/sales_return.py`, `app/models/sales_report_snapshot.py`, `app/services/customer_services.py`, `app/services/sales_order_services.py`, `app/services/delivery_services.py`, `app/services/sales_return_services.py`, `app/services/tax_and_invoice_services.py`) implements the complete Enterprise Sales & Distribution platform for ApnaERP. It manages the full Order-to-Cash lifecycle: Customer Master Management, Price Lists & Discount Engine, Sales Quotations, Sales Orders, Delivery Orders (Shipments), Sales Returns, Sales Analytics, and Invoice Payload Generation for downstream Finance consumption.

### Key Technical Capabilities
- **Customer Master Management (`Customer`, `CustomerCategory`, `CustomerContact`, `CustomerAddress`, `CustomerDocument`)**: Enterprise Customer Master storing corporate tax IDs, credit limits, payment terms, currency, credit lock status, preferred status, and financial balances. Features credit limit verification and credit lock enforcement.
- **Pricing & Discount Engine (`PriceList`, `PricingRule`, `DiscountRule`)**: Multi-tier pricing rules with min-quantity thresholds and validity windows. Evaluates item-level and document-level discounts automatically.
- **Sales Quotations (`SalesQuotation`, `SalesQuotationItem`)**: Commercial quotes supporting revision history (`revision_number`), tax calculations, line item discounts, and approval workflow integration (`WF_SALES_QUOTATION`).
- **Sales Orders (`SalesOrder`, `SalesOrderItem`)**: Sales Orders with credit limit verification, multi-warehouse delivery destinations, item status tracking (`Pending`, `Partial`, `Delivered`, `Cancelled`), and approval workflow integration (`WF_SALES_ORDER`).
- **Delivery Orders & Goods Issue Integration (`DeliveryOrder`, `DeliveryOrderItem`)**: Shipments executing physical inventory deduction via `GoodsIssueService` (`create_issue`, `approve_issue`, `issue_issue`) and `WarehouseExecutionService`, generating immutable `StockLedger` OUT entries (`SALES_ISSUE`).
- **Sales Returns & Stock Reversals (`SalesReturn`, `SalesReturnItem`)**: Customer returns executing physical inventory addition via `GoodsReceiptService` (`create_receipt`, `approve_receipt`, `receive_receipt`) and `WarehouseExecutionService`, generating immutable `StockLedger` IN entries (`SALES_RETURN`).
- **Finance Decoupling & Invoice Payload Generation (`SalesInvoicePayload`)**: Sales exposes clean invoice payload contracts (`InvoicePayloadService.generate_invoice_payload`) for future Accounts Receivable / GL modules without introducing direct accounting entries.
- **Sales Analytics, Reports & Global Search**: Real-time Sales Register, Customer Ledger, Redis-cached executive dashboard KPIs, periodic snapshotting (`SalesReportSnapshot`), and global search across Customers, Quotations, Orders, Deliveries, and Products.

---

## Procurement Domain — Enterprise Purchasing Architecture (Release v0.7.0)

### Overview
The Procurement Domain (`app/models/supplier.py`, `app/models/purchase_requisition.py`, `app/models/rfq.py`, `app/models/supplier_quotation.py`, `app/models/purchase_order.py`, `app/models/purchase_return.py`, `app/services/supplier_services.py`, `app/services/purchase_order_services.py`, `app/services/purchase_return_services.py`) implements the complete Enterprise Procurement platform for ApnaERP. It manages the full purchasing lifecycle: Supplier Master Management, Purchase Requisitions (PR), Requests For Quotations (RFQ), Supplier Bids/Quotations, Purchase Orders (PO), and Purchase Returns.

### Key Technical Capabilities
- **Supplier Master Management (`Supplier`, `SupplierCategory`, `SupplierContact`, `SupplierAddress`, `SupplierDocument`, `SupplierRating`)**: Comprehensive Vendor Master storing corporate tax IDs, GST/VAT numbers, credit limits, payment terms, currency, bank details, ratings, on-time delivery rates, and cumulative spend. Includes supplier blacklisting and rating aggregation.
- **Purchase Requisitions (`PurchaseRequisition`, `PurchaseRequisitionItem`)**: Internal demand requests initiated by departments or employees. Integrates with `ApprovalEngineService` (`WF_PURCHASE_REQUISITION`). Requisition items track partial/full fulfillment upon conversion to POs.
- **Request For Quotations & Sourcing (`RFQ`, `RFQSupplier`, `RFQComparisonMatrix`)**: Sourcing documents issued to invited suppliers. Features dynamic Quotation Comparison Matrix generation (`get_comparison_matrix`) comparing unit prices, total amounts, lead times, payment terms, and vendor quality ratings across submitted bids.
- **Supplier Quotations (`SupplierQuotation`, `SupplierQuotationItem`)**: Commercial bids submitted by suppliers with itemized pricing, tax percentages, discounts, lead times, and expiration tracking (`check_expiring_quotations_task`).
- **Purchase Order & Goods Receipt Integration (`PurchaseOrder`, `PurchaseOrderItem`)**: Legally binding purchase orders supporting revision history, multi-warehouse line item delivery destinations, and approval workflow integration (`WF_PURCHASE_ORDER`). Physical stock receiving via `receive_goods` invokes `GoodsReceiptService.create_receipt` and `WarehouseExecutionService.execute_goods_receipt` without code duplication, generating immutable `StockLedger` IN entries (`PURCHASE_RECEIPT`) and updating PO line item counters (`received_quantity`).
- **Purchase Returns & Stock Reversals (`PurchaseReturn`, `PurchaseReturnItem`)**: Physical stock returns back to vendors. Executing a return via `process_return` triggers stock reversal through `StockLedgerService` (`RETURN_OUT`), updating PO `returned_quantity` counters and inventory balances.
- **Finance Decoupling & Event-Driven Architecture**: Procurement is completely decoupled from Finance. Broadcasts domain events (`SupplierCreated`, `PurchaseRequisitionSubmitted`, `RFQIssued`, `QuotationReceived`, `PurchaseOrderApproved`, `PurchaseOrderCancelled`, `GoodsReceived`, `PurchaseReturned`) for downstream financial or analytical event consumers.

---

## Inventory Domain — Advanced Domain Completion (Milestone Inventory Domain Completion v0.6.3)


### Overview
The Advanced Inventory Domain (`app/models/batch.py`, `app/models/serial_number.py`, `app/models/lot.py`, `app/models/stock_reservation.py`, `app/models/cycle_count.py`, `app/services/inventory_advanced_services.py`, `app/services/inventory_report_services.py`) completes the Enterprise Inventory Domain within ApnaERP. It introduces Batch Management, FEFO/FIFO Batch Allocation, Serial Number Tracking, Lot Traceability, Stock Reservations without stock mutation, Cycle Count Audits with automatic adjustment generation, Executive Reports & Analytics, Global Multi-field Search, Bulk CSV Import/Export, and structured Domain Event publishing.

### Key Technical Capabilities
- **Batch Management & FEFO/FIFO Allocation (`Batch`)**: Batch creation with manufacturing/expiry dates, supplier references, and active/expired/consumed status tracking. Built-in FEFO (First-Expired, First-Out) and FIFO allocation strategies. Scheduled daily Celery task (`scan_batch_expiries_task`) scans expiries and fires `BatchExpired` events.
- **Serial Number Lifecycle Tracking (`SerialNumber`)**: Tracks individual high-value items with globally unique serial numbers. Maintains JSONB history log tracking transitions (`Available` -> `Reserved` -> `Sold` -> `Returned` -> `Scrapped`).
- **Lot Tracking & Lineage (`Lot`)**: Production and supplier lot tracking with extended lineage and QA test metadata.
- **Stock Reservation Engine (`StockReservation`)**: Secures physical inventory for pending demand (Sales/Manufacturing/Procurement/Internal) without modifying physical `StockLedger`. Reduces available quantity calculation (`available_qty = total_qty - reserved_qty`). Celery task `cleanup_expired_reservations_task` automatically releases expired reservations.
- **Cycle Count Audit & Variance Adjustment (`CycleCount`, `CycleCountItem`)**: Physical stock audit document. Approval of a cycle count with non-zero variance automatically generates and applies immutable `StockLedger` entries with direction `ADJUSTMENT`.
- **Executive Reports, Analytics & Search**: Real-time Stock Valuation Report, Inventory Aging Report (0-30, 31-60, 61-90, 90+ days), Movement Analysis Report (Fast, Slow, Dead Stock), Redis-cached Dashboard Analytics, and Global Search API searching SKUs, Barcodes, Batches, Serials, Lots, Warehouses, and Locations.
- **CSV Import/Export Engine & Domain Events**: Streaming CSV export and bulk import engine. Emits structured domain events (`StockReceived`, `StockIssued`, `StockTransferred`, `StockReserved`, `BatchExpired`, `InventoryAdjusted`, `StockCountCompleted`).

---

## Inventory Domain — Warehouse Operations Engine (Milestone Warehouse Operations Engine v0.6.2)


### Overview
The Warehouse Operations Engine (`app/models/goods_receipt.py`, `app/models/goods_issue.py`, `app/models/stock_transfer.py`, `app/services/warehouse_operations_services.py`) implements independent warehouse execution operations for ApnaERP. It manages physical inventory execution documents for incoming inventory (`GoodsReceipt`), outgoing inventory (`GoodsIssue`), and internal stock transfers (`StockTransfer`). All warehouse operations execute physical inventory movement exclusively through `StockLedgerService`, ensuring that direct stock balance modifications are strictly prohibited and every physical movement generates immutable `StockLedger` entries.

### Key Technical Capabilities
- **Goods Receipt Execution (`GoodsReceipt`, `GoodsReceiptItem`)**: Incoming stock document supporting 3-stage lifecycle (`Draft` -> `Approved` -> `Received` | `Cancelled`). Receiving physical stock automatically generates `StockLedger` IN entries with transaction type `PURCHASE_RECEIPT`.
- **Goods Issue Execution (`GoodsIssue`, `GoodsIssueItem`)**: Outgoing stock document supporting 3-stage lifecycle (`Draft` -> `Approved` -> `Issued` | `Cancelled`). Issuing inventory validates negative stock rules against `Product.allow_negative_stock` and automatically generates `StockLedger` OUT entries (`SALES_ISSUE` or `PRODUCTION_CONSUMPTION`).
- **Stock Transfer Execution (`StockTransfer`, `StockTransferItem`)**: Warehouse stock transfer document supporting 4-stage lifecycle (`Draft` -> `Approved` -> `In Transit` [Dispatch OUT] -> `Completed` [Receive IN] | `Cancelled`). Preserves total system inventory quantity while moving stock between different warehouses or storage locations.
- **Stock Ledger Integration Rule**: Warehouse execution documents NEVER modify `StockBalance` directly. All movements invoke `StockLedgerService.create_ledger_entry`.
- **Document Immutability**: Executed or terminal documents (`Received`, `Issued`, `Completed`, `Cancelled`) are strictly immutable and read-only.
- **Cancelled Document Guarantee**: Cancelled documents generate zero `StockLedger` entries.
- **Validation Guards**: Validates active warehouses and storage locations, source and destination warehouse distinction (`source_warehouse_id != destination_warehouse_id`), and product inventory eligibility.
- **Redis Caching & Celery Telemetry**: Automatic Redis cache invalidation (`stock_balance:*`, `warehouse_summary:*`), background task (`send_warehouse_notification_task`), and audit logging (`GOODS_RECEIPT_*`, `GOODS_ISSUE_*`, `STOCK_TRANSFER_*`).
- **RBAC Security**: Protected by 19 permissions (`inventory.receipt.*`, `inventory.issue.*`, `inventory.transfer.*`, `inventory.execute.warehouse`).

---

## Inventory Domain — Stock Management Engine (Milestone Inventory Stock Management Engine v0.6.1)

### Overview
The Inventory Stock Management Engine (`app/models/inventory_transaction_type.py`, `app/models/stock_ledger.py`, `app/models/stock_balance.py`, `app/models/inventory_adjustment.py`, `app/models/opening_stock.py`, `app/services/stock_engine_services.py`) implements the enterprise stock engine for ApnaERP. ALL physical inventory movement across products, warehouses, and storage locations must be recorded through an immutable stock ledger (`StockLedger`). Current stock balances are derived from ledger history, with `StockBalance` serving as a read-optimized projection and cache table.

### Key Technical Capabilities
- **Immutable Stock Ledger (`StockLedger`)**: Central physical transaction log storing product, warehouse, location, transaction type, quantity, direction, unit, and calculated `running_balance`. Ledger entries are strictly insert-only and read-only. Updates or deletions are prohibited.
- **Inventory Transaction Classifications (`InventoryTransactionType`)**: 13 transaction types (`OPENING_STOCK`, `PURCHASE_RECEIPT`, `SALES_ISSUE`, `STOCK_ADJUSTMENT`, `TRANSFER_IN`, `TRANSFER_OUT`, `PRODUCTION_RECEIPT`, `PRODUCTION_CONSUMPTION`, `RETURN_IN`, `RETURN_OUT`, `CYCLE_COUNT`, `SYSTEM_CORRECTION`) with direction flags (`IN`, `OUT`, `TRANSFER`, `ADJUSTMENT`, `SYSTEM`).
- **Derived Balance Projections (`StockBalance`)**: Read-optimized table aggregating current available, reserved, damaged, and in-transit quantities. Derived from `StockLedger` history with forced recalculation and auto-repair background tasks.
- **Negative Stock Validation**: Evaluates transactions against `Product.allow_negative_stock`. If disabled (`False`), transactions that would reduce total running balance below zero are blocked with `ValidationException`.
- **Inventory Adjustment Workflow (`InventoryAdjustment`)**: Manages physical count discrepancies via 3-stage lifecycle (`Draft` -> `Approved` -> `Applied`). Applying an adjustment generates a `STOCK_ADJUSTMENT` ledger entry.
- **Opening Stock Initialization (`OpeningStock`)**: Manages initial warehouse stock onboarding with duplicate reference and product location guards.
- **Redis Caching & Celery Telemetry**: Automatic Redis cache invalidation (`stock_balance:*`, `warehouse_summary:*`, `product_stock:*`), background tasks (`refresh_stock_balance_task`, `detect_balance_inconsistencies_task`, `send_stock_notification_task`), and audit logging (`STOCK_LEDGER_CREATE`, `OPENING_STOCK_CREATE`, `INVENTORY_ADJUSTMENT_*`).
- **RBAC Security**: Protected by 8 permissions (`inventory.transaction.read`, `inventory.ledger.read`, `inventory.balance.read`, `inventory.opening.create`, `inventory.adjustment.create`, `inventory.adjustment.approve`, `inventory.adjustment.apply`).

---

## Inventory Domain — Inventory Foundation (Milestone Inventory Foundation v0.6.0 - Inventory Domain Opened)

### Overview
The Inventory Foundation (`app/models/product_category.py`, `app/models/unit_of_measure.py`, `app/models/brand.py`, `app/models/warehouse.py`, `app/models/storage_location.py`, `app/models/product.py`, `app/models/product_attribute.py`, `app/models/product_document.py`, `app/services/inventory_services.py`) OPENS the Inventory Domain for ApnaERP. It establishes the Product Master catalog, unit measurement rules, warehouse/location structures, flexible key-value product attributes, and document attachments required for future stock ledger transactions, inventory movements, batch tracking, procurement, and sales.

### Key Technical Capabilities
- **Product Categories (`ProductCategory`)**: Infinite parent-child hierarchy tree support with circular parent reference prevention and code uniqueness validation.
- **Units of Measure (`UnitOfMeasure`)**: Standardized measurement unit catalog with precision configuration, symbol uniqueness, and base unit references.
- **Brands (`Brand`)**: Manufacturer and brand catalog management.
- **Warehouses (`Warehouse`)**: Physical storage facilities with contact details and address management.
- **Storage Locations (`StorageLocation`)**: Sub-locations (Shelf, Rack, Bin, Floor, Cold Storage, Quarantine, Receiving, Dispatch) with infinite hierarchy nesting scoped to a specific warehouse.
- **Product Master Catalog (`Product`)**: Master records with SKU, Barcode, Product Type, Inventory flags, UOM references, Default Warehouse link, and lifecycle state machine (`Draft` -> `Active` -> `Discontinued` -> `Archived`).
- **Product Immutability Guard**: `Archived` products are strictly read-only and reject any modification attempts.
- **Product Attributes & Documents (`ProductAttribute`, `ProductDocument`)**: Extensible key-value attribute definitions and attached file document management.
- **Redis Caching & Celery Telemetry**: Redis caching for hierarchy trees (`category:tree`, `location:tree`), audit logging (`CATEGORY_*`, `WAREHOUSE_*`, `STORAGE_LOCATION_*`, `PRODUCT_*`), and background Celery notification task (`send_inventory_notification_task`).
- **RBAC Security**: Protected by 24 permissions (`inventory.category.*`, `inventory.unit.*`, `inventory.brand.*`, `inventory.warehouse.*`, `inventory.location.*`, `inventory.product.*`, `inventory.attribute.*`, `inventory.document.*`).

---

## Payroll Domain — Enterprise Payroll Finalization Suite (Milestone Payroll Finalization Suite v0.5.6 - Payroll Domain Complete)

### Overview
The Enterprise Payroll Finalization Suite (`app/models/payroll_adjustment.py`, `app/models/payroll_report_snapshot.py`, `app/models/payroll_closing.py`, `app/models/financial_posting_queue.py`, `app/services/payroll_finalization_services.py`) COMPLETES and CLOSES the Enterprise Payroll domain for ApnaERP. It handles post-calculation adjustments, formal report snapshotting, executive analytics, bank disbursement exports, period closing/reopening/archival lifecycle, and exposes clean financial posting queue interfaces for future General Ledger integration.

### Key Technical Capabilities
- **Payroll Adjustments (`PayrollAdjustment`)**: Manages one-time earnings and deductions (Bonus, Incentive, Commission, Overtime, Arrears, Reimbursements, Loan Recovery, Manual Additions/Deductions) with approval workflow state machine (`Pending`, `Approved`, `Rejected`, `Applied`).
- **Period Immutability Guard**: Enforces that Closed and Archived payroll periods are strictly immutable and reject any adjustment modifications or additions.
- **Formal Payroll Reports & Snapshots (`PayrollReportSnapshot`)**: Generates and stores formal report snapshots (Salary Register, Department-wise Payroll, Employee Salary History, Payroll Summary, Deduction Summary, Earnings Summary, Cost Center Report, Monthly Payroll Register) in PDF, EXCEL, or CSV formats with file storage integration.
- **Real-Time Payroll Analytics (`PayrollAnalyticsResponse`)**: Real-time aggregated metrics including total payroll cost, average salary, highest/lowest salary, department cost breakdowns, and period trend analysis.
- **Bank Export CSV Generation**: Generates bank-compatible payment export CSV files containing employee bank accounts and net payable amounts for direct salary disbursement.
- **Period Closing Lifecycle (`PayrollClosing`)**: Period closing (`Closed`), audited reopening (`Open` with mandatory reason logging), and permanent archival locking (`Archived`).
- **Decoupled Financial Integration Interface (`FinancialPostingQueue`)**: Exposes standardized journal entry payloads (`debit_gross_salary_expense`, `credit_statutory_deductions_liability`, `credit_net_payroll_payable`) for future Finance module ingestion without implementing accounting tables in this milestone.
- **Redis Caching & Celery Telemetry**: Real-time audit logging (`PAYROLL_ADJUSTMENT_*`, `PAYROLL_REPORT_*`, `PAYROLL_PERIOD_CLOSE`, `PAYROLL_FINANCIAL_PUBLISH`) and background Celery notification task (`send_payroll_finalization_notification_task`).
- **RBAC Security**: Protected by 10 permissions (`payroll.adjustment.create/update/delete`, `payroll.report.generate`, `payroll.analytics.read`, `payroll.bank.export`, `payroll.close`, `payroll.reopen`, `payroll.archive`, `payroll.financial.publish`).

---

## Payroll Domain — Enterprise Statutory Compliance Engine (Milestone Payroll-6 v0.5.5)

### Overview
The Enterprise Statutory Compliance Engine (`app/models/country.py`, `app/models/statutory_rule.py`, `app/models/employee_statutory_profile.py`, `app/services/statutory_compliance.py`) calculates statutory payroll deductions (Provident Fund, ESI, Professional Tax, Income Tax, and custom deductions) driven by effective-dated rules and tiered salary slabs without hardcoded logic. Built-in support for India is provided initially, while establishing a future-proof foundation for global expansion (USA, UK, UAE, etc.).

### Key Technical Capabilities
- **Country Independence**: `Country` jurisdiction model (`code`, `name`, `currency`, `is_active`) reusable across all ERP modules.
- **Configurable Deduction Rule Engine**: Defines statutory rules (`StatutoryRule`) with rule types (`Provident Fund`, `ESI`, `Professional Tax`, `Income Tax`, `Other`), calculation methods (`Fixed`, `Percentage`, `Slab`), priority evaluation ordering, and effective dating (`effective_from`, `effective_to`).
- **Tiered Salary Slab Calculations**: `StatutoryRuleSlab` configures ranges (`min_amount <= gross_salary <= max_amount`) with associated fixed amounts and percentage rates.
- **Employee Statutory Profiles**: Manages `EmployeeStatutoryProfile` holding tax IDs, PF/ESI numbers, feature flags (`pf_enabled`, `esi_enabled`, etc.), and enforcing **Single Active Profile** per employee.
- **Redis Caching & Celery Telemetry**: Real-time Redis caching (`country:*`, `statutory_rule:*`, `statutory_profile:*`), audit logging (`COUNTRY_*`, `STATUTORY_*`), and Celery notification task (`send_statutory_rule_notification_task`).
- **RBAC Security**: Protected by permissions (`country.create/read/update/delete`, `statutory_rule.create/read/update/delete`, `statutory_profile.create/read/update`).

---

## Payroll Domain — Enterprise Payroll Runs & Payslips (Milestone Payroll-5 v0.5.4)

### Overview
The Enterprise Payroll Runs & Payslips module (`app/models/payroll_run.py`, `app/models/payslip.py`, `app/services/payroll_run.py`, `app/utils/pdf_generator.py`) organizes batch execution runs and generates ReportLab PDF payslip documents with File Storage integration and publication security controls.

### Key Technical Capabilities
- **Batch Execution (`PayrollRun`)**: Groups payroll executions by `Run Type` (`Regular`, `Off Cycle`, `Adjustment`) with unique constraint `(payroll_period_id, run_type)` and lifecycle states (`Draft`, `Processing`, `Completed`, `Locked`).
- **ReportLab PDF Payslip Generation**: Generates clean PDF payslips in memory (`generate_payslip_pdf_bytes`) formatted with company branding, employee details, period info, itemized earnings/deductions, gross/net totals, disclaimers, and currency formatting.
- **File Storage Integration**: Stores PDF files via `FileService.upload_bytes()` with SHA256 checksum deduplication and `File` record linking (`pdf_file_id`).
- **Publication Workflow & Immutability**: Manages payslip state (`Draft` -> `Generated` -> `Published`). Employees access and download PDF streams (`/api/v1/payslips/{id}/download`) only after payslips are explicitly published by HR/Payroll Managers.
- **Permanent Lock Guard**: Locking a `PayrollRun` (`status = "Locked"`) permanently prevents further execution or payslip modification.
- **Redis Caching & Celery Telemetry**: Real-time Redis caching (`payroll_run:*`, `payslip:*`), audit logging (`PAYROLL_RUN_*`, `PAYSLIP_*`), and background Celery notification tasks (`send_payroll_run_notification_task`, `send_payslip_published_notification_task`).
- **RBAC Security**: Protected by permissions (`payroll_run.create`, `payroll_run.read`, `payroll_run.update`, `payroll_run.lock`, `payslip.generate`, `payslip.publish`, `payslip.read`).

---

## Payroll Domain — Enterprise Payroll Processing Engine (Milestone Payroll-4 v0.5.3)

### Overview
The Enterprise Payroll Processing Engine (`app/models/payroll_period.py`, `app/services/payroll_engine.py`) generates and stores employee payroll records for processing periods by combining active `EmployeeCompensation` policies, `SalaryStructureComponent` definitions, `Attendance` logs (present vs half-days), and `LeaveRequest` approvals (paid vs unpaid leave).

### Key Technical Capabilities
- **Payroll Period Lifecycle**: Creates and manages processing cycles (`period_code`, `start_date`, `end_date`, `status`: `Draft`, `Processing`, `Completed`, `Locked`).
- **Attendance & Leave Proration**: Computes proration ratios based on attendance present days and approved paid leave days against total period working days.
- **Line-Item Component Breakdown**: Calculates exact line-item earnings and deductions (`PayrollRecordComponent`) derived from active salary structure templates.
- **Single Record & Period Lock Semantics**: Enforces `unique(payroll_period_id, employee_id)` and prevents any recalculation or modification on `Locked` periods.
- **Redis Caching & Celery Telemetry**: Real-time Redis caching (`payroll:*`), audit logging (`PAYROLL_*`), and background notification dispatch (`send_payroll_notification_task`).
- **RBAC Security**: Protected by permissions (`payroll.generate`, `payroll.read`, `payroll.approve`, `payroll.lock`).

---

## Payroll Domain — Employee Compensation Management (Milestone Payroll-3 v0.5.2)

### Overview
The Employee Compensation Management module (`app/models/employee_compensation.py`, `app/services/employee_compensation.py`) assigns Salary Structure templates to employees while maintaining complete effective date history, revision tracking, and state transitions (`Draft`, `Active`, `Expired`, `Cancelled`).

### Key Technical Capabilities
- **Employee Compensation Policies**: Assigns `SalaryStructure` templates to employees with `annual_ctc`, `monthly_gross_salary`, `effective_from`, and `effective_to`.
- **Single Active Policy Enforcement**: Enforces that only ONE compensation policy can be `Active` per employee. Activating a new policy automatically sets the previous active policy status to `Expired`.
- **Revision Tracking**: Links compensation revisions to `previous_compensation_id` and automatically increments `revision_number`.
- **Date Overlap Prevention**: Prevents overlapping effective date ranges for the same employee across active/draft compensation policies.
- **Redis Caching & Celery Telemetry**: Real-time Redis caching (`employee_compensation:*`), audit logging (`COMPENSATION_*`), and background notification dispatch (`send_compensation_notification_task`).
- **RBAC Security**: Protected by permissions (`compensation.create`, `compensation.read`, `compensation.update`, `compensation.activate`, `compensation.cancel`, `compensation.delete`).

---

## Payroll Domain — Enterprise Salary Structures (Milestone Payroll-2 v0.5.1)

### Overview
The Enterprise Salary Structures module (`app/models/salary_structure.py`, `app/services/salary_structure.py`) provides reusable compensation template structures composed of multiple ordered Salary Components with baseline values and optional overrides.

### Key Technical Capabilities
- **Reusable Compensation Templates**: Structure templates (`code`, `name`, `currency`, `effective_from`, `effective_to`) ready for employee assignment.
- **Component Mapping & Ordering**: Maps `SalaryComponent` instances to `SalaryStructure` with explicit `component_order` and baseline `component_value`.
- **Component Duplication Prevention**: Enforces `unique(salary_structure_id, salary_component_id)` to prevent component duplication within the same structure.
- **Effective Date Validation**: Validates `effective_to >= effective_from`.
- **Redis Caching & Celery Telemetry**: Real-time Redis caching (`salary_structure:*`), audit logging (`SALARY_STRUCTURE_*`), and background notification dispatch (`send_payroll_structure_notification_task`).
- **RBAC Security**: Protected by permissions (`salary_structure.create`, `salary_structure.read`, `salary_structure.update`, `salary_structure.delete`, `salary_structure.restore`).

---

## Payroll Domain — Enterprise Salary Components (Milestone Payroll-1 v0.5.0)

### Overview
The Enterprise Salary Components module (`app/models/salary_component.py`, `app/services/salary_component.py`) provides an organization-wide catalog defining payroll building blocks (Earnings: Basic, HRA, Allowances, Bonus; Deductions: PF, ESI, Professional Tax, Income Tax).

### Key Technical Capabilities
- **Organization-Wide Component Catalog**: Standardized component definitions decoupled from individual employee records.
- **Categorization & Calculation Methods**:
  - `type`: `Earning` or `Deduction`.
  - `calculation_method`: `Fixed`, `Percentage`, or `Formula` (reserved for future calculation evaluation).
- **Statutory & Tax Rule Indicators**: Flags for `is_taxable`, `is_pf_applicable`, `is_esi_applicable`.
- **Display Ordering & Uniqueness Rules**: Enforces unique `code`, unique `name`, and unique `display_order` across active components.
- **Calculation Validation Rules**: Validates that `Percentage` calculation method includes valid `percentage_value` (0.01 to 100.0) and `Fixed` includes valid `default_value`.
- **Redis Caching & Celery Telemetry**: Real-time Redis caching (`salary_component:*`), audit logging (`SALARY_COMPONENT_CREATE/UPDATE/DELETE/RESTORE`), and background notification dispatch (`send_payroll_component_notification_task`).
- **RBAC Security**: Protected by permissions (`salary_component.create`, `salary_component.read`, `salary_component.update`, `salary_component.delete`, `salary_component.restore`).

---

## Platform Domain — Enterprise Approval Workflow Engine (Milestone Platform v0.4.5)

### Overview
The Enterprise Approval Workflow Engine (`app/models/approval_workflow.py`, `app/services/approval_engine.py`) provides a generic, domain-agnostic, reusable multi-step approval framework at the Platform layer. Any business domain module (Leave, Expense, Purchase Orders, Assets, Payroll, Inventory) plugs into this engine using `entity_type` and `entity_id`.

### Key Technical Capabilities
- **Generic Domain Decoupling**: Target business entities plug into the approval engine via `entity_type` and `entity_id` strings, maintaining zero dependency on domain-specific tables.
- **Sequenced Role-Based Approval Steps**: Multi-step workflows (`ApprovalStep`) enforce assigned `Role` authorization (`approver_role_id`) or superuser privileges for each sequential step.
- **Strict State Machine Workflow**:
  - `Draft` -> `Pending` (Step 1)
  - `Pending` (Step N) -> `Pending` (Step N+1) if more steps remain
  - `Pending` (Step N) -> `Approved` if no steps remain (Terminal State)
  - `Pending` (Step N) -> `Rejected` upon step rejection (Terminal State)
  - `Pending` (Step N) -> `Cancelled` upon submitter/admin cancellation (Terminal State)
  - Rejects invalid state transitions (`INVALID_WORKFLOW_TRANSITION`) and prevents step skipping.
- **Immutable Approval Audit History**: Every action (`Submitting`, `Approved Step`, `Rejected`, `Cancelled`, `Completed Workflow`) creates an unmodifiable `ApprovalHistory` record recording step number, action, performer, timestamp, and comments.
- **Redis Caching & Celery Telemetry**: Real-time Redis caching (`approval:request:*`), audit logging (`APPROVAL_WORKFLOW_START`, `APPROVAL_STEP_APPROVE`, `APPROVAL_STEP_REJECT`, `APPROVAL_WORKFLOW_CANCEL`), and Celery notification dispatch (`send_approval_notification_task`).
- **RBAC Security**: Protected by permissions (`workflow.create`, `workflow.read`, `workflow.update`, `workflow.delete`, `approval.read`, `approval.approve`, `approval.reject`).

---

## HR Domain — Enterprise Leave Request Workflow (Milestone HR-12)

### Overview
The Enterprise Leave Request Workflow module (`app/models/leave_request.py`, `app/services/leave_request.py`) provides a state-machine driven engine for employee leave applications, working day calculations, policy enforcement, overlap prevention, leave balance updating, and workflow notifications.

### Key Technical Capabilities
- **Strict State Machine Workflow**:
  - `Draft` -> `Pending` (Submission)
  - `Pending` -> `Approved` (Approval)
  - `Pending` -> `Rejected` (Rejection)
  - `Approved` -> `Cancelled` (Cancellation prior to start date)
  - Terminal States: `Rejected`, `Cancelled`, `Completed`. Rejects invalid transitions (`INVALID_WORKFLOW_TRANSITION`).
- **Working Day Calculation Engine**:
  - Automatically calculates net working days between `start_date` and `end_date` inclusive, excluding Saturdays, Sundays, and organizational `Holiday` records. Supports half-day applications (`total_days = 0.5`).
- **Policy & Overlap Validation Rules**:
  - Half-day permission check (`HALF_DAY_NOT_PERMITTED`).
  - Max consecutive days cap (`EXCEEDS_MAX_CONSECUTIVE_DAYS`).
  - Gender restriction validation (`GENDER_RESTRICTION_MISMATCH`).
  - Overlap prevention rejecting active overlapping leave applications (`OVERLAPPING_LEAVE_REQUEST`).
  - Leave balance validation (`INSUFFICIENT_LEAVE_BALANCE`).
- **Leave Balance Updating**:
  - Upon approval, automatically updates `LeaveBalance.availed_days` and recalculates `remaining_days`. Restores availed days if an approved leave is cancelled prior to start date.
- **Redis Caching & Celery Telemetry**:
  - Redis caching (`leave_request:employee:{emp_id}:*`), audit trails (`LEAVE_REQUEST_CREATE`, `LEAVE_REQUEST_SUBMIT`, `LEAVE_REQUEST_APPROVE`, `LEAVE_REQUEST_REJECT`, `LEAVE_REQUEST_CANCEL`, `LEAVE_REQUEST_COMPLETE`), and background notification dispatch (`send_leave_request_notification_task`).
- **RBAC Security**: Protected by permissions (`leave_request.create`, `leave_request.read`, `leave_request.submit`, `leave_request.approve`, `leave_request.reject`, `leave_request.cancel`).

---

## HR Domain — Enterprise Leave Balance Management (Milestone HR-11)

### Overview
The Enterprise Leave Balance Management module (`app/models/leave_balance.py`, `app/services/leave_balance.py`) serves as the authoritative single source of truth for employee leave availability across leave types and calendar years.

### Key Technical Capabilities
- **Mathematical Balance Derivation**: Automatically calculates available remaining leave days using:
  `remaining_days = opening_balance + allocated_days + earned_days + carried_forward_days - availed_days - encashed_days`.
- **Negative Balance Policy Guard**: Strictly prevents negative remaining balances (`NEGATIVE_LEAVE_BALANCE`) unless the target `LeaveType` explicitly enables `allow_negative_balance == True`.
- **Uniqueness & Carry Forward Enforcement**: Enforces composite uniqueness on `(employee_id, leave_type_id, leave_year)` and validates carry-forward caps against `LeaveType.max_carry_forward`.
- **Manual Balance Adjustments**: `PATCH /leave-balances/{id}/adjust` permits audited component adjustments (`allocated`, `earned`, `availed`, `encashed`, `opening`, `carried_forward`) with mandatory business justification.
- **Future Integration Ready**: Provides authoritative leave availability lookups for future Leave Application engines and Payroll Encashment/Deduction processing.
- **Redis Caching & Celery Telemetry**: Real-time Redis caching (`leave_balance:employee:{emp_id}:{year}`), audit trails (`LEAVE_BALANCE_CREATE`, `LEAVE_BALANCE_UPDATE`, `LEAVE_BALANCE_ADJUST`, `LEAVE_BALANCE_DELETE`, `LEAVE_BALANCE_RESTORE`), and background notification dispatch (`send_leave_balance_adjustment_notification_task`).
- **RBAC Security**: Protected by permissions (`leave_balance.create`, `leave_balance.read`, `leave_balance.update`, `leave_balance.adjust`, `leave_balance.delete`, `leave_balance.restore`).

---

## HR Domain — Enterprise Leave Types & Policies (Milestone HR-10)

### Overview
The Enterprise Leave Types & Policies module (`app/models/leave_type.py`, `app/services/leave_type.py`) provides an organization-wide policy registry defining leave rules, annual allocations, carry-forward caps, consecutive day limits, half-day permissions, approval requirements, and gender restrictions.

### Key Technical Capabilities
- **Reusable Policy Registry**: Defines entitlement policies (`Annual Leave`, `Sick Leave`, `Casual Leave`, `Maternity Leave`, `Paternity Leave`, `Work From Home`, `Unpaid Leave`) applicable across all enterprise employees.
- **Strict Business Validation Rules**:
  - Code & Name Uniqueness (`DUPLICATE_LEAVE_CODE`, `DUPLICATE_LEAVE_NAME`).
  - `annual_allocation >= 0`.
  - `max_carry_forward <= annual_allocation`.
  - If `carry_forward_allowed` is `False`, `max_carry_forward` must be `0`.
  - `max_consecutive_days > 0`.
- **Policy Restoration Support**: `PATCH /leave-types/{id}/restore` endpoint and `restore()` repository method for restoring soft-deleted policies.
- **Future Module Integration**: Designed for direct integration with Leave Request Engines, Leave Balance Calculation Services, and Payroll Overtime/Unpaid Leave Deduction systems.
- **Redis Caching & Celery Telemetry**: Automatic Redis caching (`leave_type:list`, `leave_type:detail:{id}`) with pattern invalidation, audit logging (`LEAVE_TYPE_CREATE`, `LEAVE_TYPE_UPDATE`, `LEAVE_TYPE_DELETE`, `LEAVE_TYPE_RESTORE`), and background notification dispatch (`send_leave_policy_change_notification_task`).
- **RBAC Security**: Protected by permissions (`leave_type.create`, `leave_type.read`, `leave_type.update`, `leave_type.delete`, `leave_type.restore`).

---

## HR Domain — Enterprise Shift Assignment & Scheduling (Milestone HR-9)

### Overview
The Shift Assignment & Scheduling module (`app/models/shift_assignment.py`, `app/services/shift_assignment.py`) enables effective-dated shift scheduling (`effective_from`, `effective_to`) for employees. Attendance calculations dynamically resolve shift schedules by date history rather than relying on static employee profiles.

### Key Technical Capabilities
- **Effective-Dated Scheduling**: Supports `Permanent`, `Temporary`, and `Rotation` schedule assignments with explicit start dates and optional open-ended end dates (`NULL`).
- **Date Overlap Prevention**: Strict interval validation (`check_overlap`) prevents overlapping active shift assignments for an employee.
- **Historical Attendance Shift Resolution**: Attendance Engine resolves the effective shift for any historical date `D` via `ShiftAssignment` -> `Shift` -> `Attendance Engine`.
- **Locked Attendance Protection**: Prevents modifying, ending, or soft-deleting shift assignments if an `Attendance` record in that date range is locked for payroll (`is_locked = True`).
- **Redis High-Performance Caching & Celery Telemetry**: Caches active shift lookups (`shift_assignment:active:{emp_id}:{date}`) with automatic cache invalidation upon assignment updates. Dispatches Celery background tasks (`send_shift_assignment_notification_task`) and records audit events (`SHIFT_ASSIGNMENT_CREATE`, `SHIFT_ASSIGNMENT_UPDATE`, `SHIFT_ASSIGNMENT_END`, `SHIFT_ASSIGNMENT_DELETE`).
- **RBAC Enforcement**: Secured via permissions (`shift_assignment.create`, `shift_assignment.read`, `shift_assignment.update`, `shift_assignment.delete`).

---

## HR Domain — Enterprise Attendance Engine (Milestone HR-8)

### Overview
The Attendance Engine (`app/models/attendance.py`, `app/services/attendance_engine.py`, `app/services/attendance.py`) provides a domain-driven business rules engine that dynamically synthesizes data from `Employee`, `Shift`, `Holiday Calendar`, and `HR Configuration` to evaluate daily attendance statuses, worked/expected minutes, tardiness, and early departures.

### Key Technical Capabilities
- **Deterministic Business Rules Engine (`AttendanceEngine`)**: Isolated domain service computing status (`Present`, `Late`, `Half Day`, `Absent`, `Holiday`, `Weekend`, `On Leave`, `Missing Check-in`, `Missing Check-out`) and timing metrics independently from API controllers.
- **Overnight Shift Calculations**: Supports shifts spanning midnight (`end_time <= start_time`, e.g. 22:00 to 06:00), evaluating grace periods and tardiness across date boundaries.
- **Weekend & Holiday Integration**: Automatically checks `HRConfiguration.weekend_configuration` and `HolidayRepository` lookups to assign non-working statuses.
- **Locked Record Guard**: Records locked (`is_locked = True`) for payroll processing block check-ins, check-outs, and manual corrections (HTTP 400 `ATTENDANCE_LOCKED`).
- **Manual HR Corrections & Audit Trail**: Requires mandatory justification notes for manual corrections and records audit events (`ATTENDANCE_CHECKIN`, `ATTENDANCE_CHECKOUT`, `ATTENDANCE_CORRECT`, `ATTENDANCE_LOCK`).
- **Redis Caching & Celery Telemetry**: Caches active attendance listings (`attendance:today`) and dispatches Celery background tasks (`send_attendance_notification_task`).
- **RBAC Enforcement**: Protected by permissions (`attendance.read`, `attendance.checkin`, `attendance.checkout`, `attendance.correct`, `attendance.lock`).

---

## HR Domain — Enterprise Holiday Calendar (Milestone HR-7)

### Overview
The Holiday Calendar module (`app/models/holiday.py`, `app/services/holiday.py`) serves as the authoritative single source of truth for organization, national, and regional holiday definitions. Downstream modules (Attendance, Leave, Payroll, Reporting) consume this registry to determine non-working days, leave balance deductions, and holiday overtime multipliers.

### Key Technical Capabilities
- **Location-Aware Regional Scoping**: Supports `National`, `Regional`, `Company`, and `Optional` holiday classifications across specified countries and state/regions.
- **Annual Recurring Projection Algorithm**: Holidays marked `is_recurring_annually = True` automatically apply across all calendar years without manual re-creation. Year queries (`GET /api/v1/holidays/year/{year}`) project recurring holidays onto target years seamlessly.
- **Strict Deduplication**: Enforces unique holiday codes and unique `(holiday_date, country, state_region)` combinations among non-deleted records.
- **Redis Caching & Celery Telemetry**: Caches holiday listings (`holiday:list`) with automatic invalidation. Dispatches Celery background tasks (`send_holiday_notification_task`) and logs enterprise audit events (`HOLIDAY_CREATE`, `HOLIDAY_UPDATE`, `HOLIDAY_DELETE`, `HOLIDAY_RESTORE`).
- **RBAC Enforcement**: Protected by permissions (`holiday.create`, `holiday.read`, `holiday.update`, `holiday.delete`, `holiday.restore`).

---

## HR Domain — Enterprise Shift Management (Milestone HR-6)

### Overview
The Shift Management module (`app/models/shift.py`, `app/services/shift.py`) provides reusable, enterprise-grade work schedule definitions. It extends `Employee` with a nullable `shift_id` FK, establishing baseline shift timings consumed downstream by Attendance (working hours, tardiness, grace period) and Payroll (overtime calculation).

### Key Technical Capabilities
- **Overnight & Night Shift Support**: Shifts spanning across midnight (`end_time <= start_time`, e.g. 22:00 to 06:00) are automatically detected and calculated (`(24.0 - start_time) + end_time`). The `is_night_shift` flag is automatically validated.
- **Duration & Sanity Constraints**:
  - `break_duration_minutes`: Break duration in hours must be strictly less than total shift duration.
  - `grace_period_minutes`: Grace period in hours must be strictly less than total shift duration.
  - `minimum_working_hours`: Must not exceed `maximum_working_hours`.
- **Active Employee Shift Deletion Guard**: Soft-deleting a shift (`DELETE /api/v1/shifts/{id}`) is explicitly blocked (HTTP 400 `ASSIGNED_EMPLOYEES_EXIST`) if active employees are assigned to the shift schedule.
- **Nullable Employee Integration**: `Employee.shift_id` nullable FK allows flexible schedule assignments while falling back to `HRConfiguration` defaults when unassigned.
- **Redis Caching & Celery Telemetry**: Caches shift listings and details (`shift:list`, `shift:detail:{id}`) with automatic invalidation. Dispatches Celery background tasks (`send_shift_notification_task`) and logs enterprise audit events (`SHIFT_CREATE`, `SHIFT_UPDATE`, `SHIFT_DELETE`, `SHIFT_RESTORE`).
- **RBAC Enforcement**: Protected by permissions (`shift.create`, `shift.read`, `shift.update`, `shift.delete`, `shift.restore`).

---

## HR Domain — HR Configuration & Organization Policies (Milestone HR-5)

### Overview
The HR Configuration module (`app/models/hr_configuration.py`, `app/services/hr_configuration.py`) acts as the centralized single source of truth for organization-wide HR policies. It stores enterprise parameters that future HR modules (Attendance, Leave, Payroll, Recruitment, Performance, Shift Scheduling) consume directly, avoiding duplicate settings across sub-systems.

### Key Technical Capabilities
- **Singleton Active Configuration**: Guarantees exactly one active configuration (`is_active=True`) per organization code. Creating or activating a policy automatically deactivates previous active policies.
- **Active Deletion Guard**: Soft-deletion (`DELETE /api/v1/hr/configuration/{id}`) is explicitly blocked if the configuration is currently active (`is_active == True`), protecting enterprise policy continuity.
- **Domain Validation**:
  - Timezone validation via standard library `zoneinfo` (e.g. `Asia/Kolkata`, `UTC`).
  - Weekend configuration day name checks (`Monday` through `Sunday`).
  - Working hours sanity checks (`minimum_working_hours <= standard_working_hours_per_day`).
  - Currency ISO 3-letter code checks and non-empty country strings.
- **Redis Caching Strategy**: Active configurations are cached (`hr_configuration:active:{organization_code}`) with automatic invalidation on any policy mutation or activation.
- **RBAC & Enterprise Audit**: Protected by permissions (`hr_configuration.read`, `hr_configuration.create`, `hr_configuration.update`, `hr_configuration.activate`, `hr_configuration.delete`, `hr_configuration.restore`) and logs all audit events (`HR_CONFIG_CREATE`, `HR_CONFIG_UPDATE`, `HR_CONFIG_ACTIVATE`, `HR_CONFIG_DELETE`, `HR_CONFIG_RESTORE`).

### Future HR Module Integrations
- **Attendance Module**: Consumes `timezone`, `standard_working_hours_per_day`, `grace_period_minutes`, and `minimum_working_hours` for calculating late arrivals and half-day credits.
- **Leave Module**: Consumes `weekend_configuration` and `leave_year_start_month` for calculating working day leave deductions and annual quota resets.
- **Payroll Module**: Consumes `currency`, `payroll_cycle`, and `fiscal_year_start_month` for pay run frequency and tax year reporting.
- **Recruitment Module**: Consumes `default_probation_period_days` when onboarding new hires.

---

## Directory Structure

```
ApnaERP/
├── alembic/                  # Alembic database migrations
├── app/                      # Application source code
│   ├── api/                  # API endpoints and dependency injection
│   │   ├── deps.py           # Dependency injection providers
│   │   └── v1/               # API version 1 routers
│   │       ├── api.py        # Master v1 router
│   │       └── endpoints/    # Route handlers (audit, auth, departments, employee_documents, employees, files, health, hr_configurations, notifications, positions, rbac, root, templates)
│   ├── core/                 # App configuration, logging, events, security, storage & Celery
│   ├── db/                   # Database session and connection setup
│   ├── models/               # SQLAlchemy ORM models (User, Role, AuditLog, File, Notification, Department, Employee, EmployeeDocument, Position, HRConfiguration, etc.)
│   ├── repositories/         # Clean Architecture repository layer (DepartmentRepository, EmployeeRepository, PositionRepository, HRConfigurationRepository, etc.)
│   ├── schemas/              # Pydantic v2 data models & validation (HRConfigurationCreate, HRConfigurationResponse, etc.)
│   ├── services/             # Clean Architecture business service layer (DepartmentService, EmployeeService, PositionService, HRConfigurationService, etc.)
│   ├── tasks/                # Centralized Celery task registry (department_tasks, employee_tasks, document_tasks, position_tasks, hr_config_tasks, system_tasks)
│   └── main.py               # FastAPI application entrypoint
├── docker/                   # Docker deployment configurations
├── docs/                     # Architecture Decision Records (ADRs)
│   └── adr/                  # ADR documents (ADR-0001 Redis, ADR-0002 Celery, ADR-0003 Department, ADR-0004 Employee, ADR-0005 Employee Documents, ADR-0006 Position Management, ADR-0007 HR Configuration)
├── workers/                  # Celery worker process entrypoints
├── tests/                    # Pytest test suite (test_hr_configurations.py, test_positions.py, test_employee_documents.py, test_employees.py, test_departments.py, test_celery.py, etc.)
├── uploads/                  # Local storage root directory
├── CHANGELOG.md              # Project release notes & changelog
├── requirements.txt          # Python production dependencies
└── README.md                 # Project documentation
```

---

## API Endpoints Overview

| HTTP Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/hr/configuration` | Retrieve active HR configuration policy | Yes (`hr_configuration.read`) |
| `GET` | `/api/v1/hr/configurations/{id}` | Retrieve HR configuration details by ID | Yes (`hr_configuration.read`) |
| `POST` | `/api/v1/hr/configuration` | Define new HR configuration policy | Yes (`hr_configuration.create`) |
| `PUT` | `/api/v1/hr/configuration/{id}` | Update HR configuration policy parameters | Yes (`hr_configuration.update`) |
| `PATCH` | `/api/v1/hr/configuration/{id}/activate` | Activate target HR configuration policy | Yes (`hr_configuration.activate`) |
| `DELETE` | `/api/v1/hr/configuration/{id}` | Soft delete inactive HR configuration policy | Yes (`hr_configuration.delete`) |
| `PATCH` | `/api/v1/hr/configuration/{id}/restore` | Restore soft-deleted HR configuration policy | Yes (`hr_configuration.restore`) |
| `GET` | `/api/v1/positions` | Paginated list of job positions | Yes (`position.read`) |
| `GET` | `/api/v1/employees` | Paginated list of employees | Yes (`employee.read`) |
| `GET` | `/api/v1/departments/tree` | Retrieve nested department tree | Yes (`department.read`) |
| `GET` | `/api/v1/health/celery` | Celery platform health diagnostics | No |
| `GET` | `/api/v1/health/redis` | Redis health diagnostics check | No |

---

## Testing

Run the complete automated test suite using `pytest`:

```bash
pytest
```

---

## License

Copyright © 2026 ApnaERP Team. All rights reserved.
