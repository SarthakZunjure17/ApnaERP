# Changelog

All notable changes to the **ApnaERP** platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.7.4] - 2026-09-07

### Milestone Procurement Finalization & Analytics

#### Added
- **Procurement Analytics Dashboard (`app/services/procurement_report_services.py`, `app/schemas/procurement.py`, `app/api/v1/endpoints/procurement_reports.py`, `app/api/v1/endpoints/procurement_analytics.py`)**:
  - `get_dashboard_summary` aggregating supplier base metrics (total, active, blacklisted), sourcing activity (open PRs, submitted PRs, pending approvals, open RFQs, submitted quotations, approved/awarded quotations), purchasing pipeline (active, dispatched, partially received, fully received POs), physical quantities (ordered, received, returned), and gross commercial purchasing spend.
  - Endpoints: `GET /api/v1/procurement/reports/dashboard`, `GET /api/v1/procurement/analytics/dashboard-summary`.
- **Operational Tabular Reports (`app/services/procurement_report_services.py`, `app/api/v1/endpoints/procurement_reports.py`)**:
  - **Purchase Order Report** (`/reports/purchase-orders`, `/purchase-register`): Detailed header and line aggregated summaries with filters for `supplier_id`, `warehouse_id`, `product_id`, `status`, and date ranges.
  - **Supplier Performance Report** (`/reports/suppliers`, `/supplier-ledger`): Scorecard with total PO value, ordered/received/returned quantities, fulfillment rate, and `SupplierRating`.
  - **Purchase Requisition Report** (`/reports/requisitions`): Pipeline volume, breakdown by status and priority, department filtering, and estimated total values.
  - **RFQ & Sourcing Report** (`/reports/rfqs`): Sourcing activity, supplier invitation count, quotation response count, and awarded contract values.
  - **Supplier Quotation Report** (`/reports/quotations`): Proposal pricing, validity dates, payment terms, and lead times.
  - **Receiving Performance Report** (`/reports/receiving`): Inbound goods receipts, received vs. rejected quantities, and receipt fulfillment rate.
  - **Purchase Return Report** (`/reports/returns`): Vendor returns, returned units, reasons, and return rates.
- **Operational Spend Analytics (`app/services/procurement_report_services.py`, `app/api/v1/endpoints/procurement_reports.py`, `app/api/v1/endpoints/procurement_analytics.py`)**:
  - `get_spend_analytics`: Commercial purchasing breakdown by top suppliers, receiving warehouses, PO approval/fulfillment statuses, and monthly expenditure run-rates (`YYYY-MM`).
- **Procurement Efficiency & Conversion Metrics (`app/services/procurement_report_services.py`, `app/api/v1/endpoints/procurement_reports.py`)**:
  - `get_efficiency_metrics`: Pipeline conversion ratios including participation rate, quotations per RFQ, quotation award ratio, award to PO conversion ratio, PO receipt completion ratio, and return ratio.
- **Synchronous Streaming CSV Export Subsystem (`app/services/procurement_import_export_services.py`, `app/api/v1/endpoints/procurement_import_export.py`)**:
  - `GET /api/v1/procurement/import-export/export` streaming CSV export supporting `purchase_orders`, `suppliers`, `receiving`, `returns`, `requisitions`, `quotations`, and `rfqs` with safe CSV escaping.
- **Security & Read-Only Invariance**:
  - Protected under `procurement.reports.read`, `procurement.analytics.read`, and `procurement.import_export.execute` permissions.
  - Strict read-only guarantee: zero entity creation, mutation, or state alteration during reporting.
  - Domain boundary enforcement: no accounting entries (no AP, GL, COGS, or invoices) and zero inventory stock mutation.
- **Automated Test Suite (`tests/test_procurement_analytics_v074.py`)**:
  - 8 comprehensive test suites verifying KPI calculation correctness, report filtering/pagination, spend aggregation, efficiency metrics, CSV exports, RBAC authorization, and database read-only invariance.
- **Documentation**:
  - `docs/procurement/procurement-analytics.md`: Complete architectural documentation for v0.7.4.

## [v0.7.3] - 2026-09-07

### Milestone Logistics & Receiving

#### Added
- **Purchase Order Goods Receiving (`app/services/purchase_order_services.py`, `app/schemas/procurement.py`, `app/api/v1/endpoints/purchase_orders.py`)**:
  - `receive_goods` domain workflow connecting approved/dispatched `PurchaseOrder`s to canonical Inventory `GoodsReceipt` generation and `StockMovementService.stock_in` physical mutation.
  - Multi-line, partial, and full receiving support with automatic `PurchaseOrderItem.received_quantity` counter increment and `PurchaseOrder.status` transition (`Partially Received` $\rightarrow$ `Fully Received`).
  - Strict over-receiving prevention enforcing $\text{received\_quantity} \le (\text{ordered\_quantity} - \text{already\_received} + \text{returned\_quantity})$.
  - Database row-level locking (`SELECT ... FOR UPDATE` via `purchase_order_repository.get_for_update`) to prevent concurrency races across simultaneous receipt requests.
  - Full compatibility with batch-tracked items (creating/updating `Batch` records) and serial-tracked items (registering `SerialNumber` records as `Available` at destination warehouse and storage location).
  - Multi-line transactional atomicity: all stock movements, ledger insertions, PO item counter updates, PO status transitions, and audit records commit or roll back together.
  - PO GoodsReceipt history retrieval endpoint (`GET /api/v1/purchase-orders/{id}/receipts`).
- **Purchase Returns & Stock Reversal Subsystem (`app/models/purchase_return.py`, `app/repositories/procurement_repos.py`, `app/services/purchase_return_services.py`, `app/schemas/procurement.py`, `app/api/v1/endpoints/purchase_returns.py`)**:
  - `PurchaseReturn` and `PurchaseReturnItem` management with database-safe sequence numbering (`PRTN-YYYY-XXXXX`).
  - Strict return validation ensuring returned items belong to the source PO, have non-zero quantities, and never exceed net received stock ($\text{return\_quantity} \le \text{received\_quantity} - \text{returned\_quantity}$).
  - Stock reversal execution via canonical `StockMovementService.stock_out` (updating `StockBalance` and inserting immutable `StockLedger` entries with `direction="OUT"` and `reference_type="PurchaseReturn"`).
  - PO item returned counter tracking (`PurchaseOrderItem.returned_quantity`).
  - Full return lifecycle support (`Draft` $\rightarrow$ `Approved` $\rightarrow$ `Processed` / `Cancelled`).
  - Dedicated return API endpoints (`GET/POST /api/v1/purchase-returns`, `PATCH /api/v1/purchase-returns/{id}`, `POST .../post`, `POST .../cancel`).
- **RBAC Security & Audit Logging (`app/db/seed_rbac.py`, `app/services/purchase_order_services.py`, `app/services/purchase_return_services.py`)**:
  - Seeded granular permissions: `procurement.receiving.read`, `procurement.receiving.create`, `procurement.receiving.post`, `procurement.purchase_return.read`, `procurement.purchase_return.create`, `procurement.purchase_return.update`, `procurement.purchase_return.approve`, `procurement.purchase_return.post`, `procurement.purchase_return.cancel`.
  - Canonical `AuditLog` integration recording `PURCHASE_RECEIPT_CREATE`, `PURCHASE_RECEIPT_POST`, `PURCHASE_ORDER_PARTIAL_RECEIVE`, `PURCHASE_ORDER_FULLY_RECEIVED`, `PURCHASE_RETURN_CREATE`, `PURCHASE_RETURN_POST`, `PURCHASE_RETURN_CANCEL`.
- **Domain Boundaries & Invariants**:
  - Zero direct stock mutation: all physical mutations strictly routed through canonical `StockMovementService`.
  - Finance boundary preserved: receiving and returns generate zero supplier invoices, zero AP entries, and zero GL journal entries.
  - Analytics boundary preserved: spend analytics and dashboards deferred to `v0.7.4`.
- **Comprehensive Automated Test Suite (`tests/test_procurement_receiving_v073.py`)**:
  - 10 comprehensive test suites covering all 46 milestone requirements: full receipts, partial/sequential receipts, multi-line atomicity, over-receiving guards, batch receiving, serial tracking, purchase return creation, return posting and stock reversal, concurrency row-locking, RBAC, and audit logging.
- **Documentation**:
  - `docs/procurement/logistics-and-receiving.md`: Complete architectural specification for v0.7.3.

## [v0.7.2] - 2026-09-07


### Milestone Commercial Purchasing

#### Added
- **Canonical Purchase Order Engine (`app/models/purchase_order.py`, `app/repositories/procurement_repos.py`, `app/services/purchase_order_services.py`, `app/schemas/procurement.py`, `app/api/v1/endpoints/purchase_orders.py`)**:
  - `PurchaseOrder` and `PurchaseOrderItem` models with database-safe sequence numbering (`PO-YYYY-XXXXX`), full validation (active suppliers, non-blacklisted suppliers, active products, active warehouses, $\text{quantity} > 0$, $\text{unit\_price} \ge 0$, and valid tax/discount rates).
  - Multi-path creation: Automated generation from awarded `SupplierQuotation` (`/from-quotation/{quotation_id}`) with strict duplicate prevention and manual creation where needed.
  - Lifecycle state machine: `Draft` $\rightarrow$ `Submitted` $\rightarrow$ `Approved` / `Rejected` $\rightarrow$ `Dispatched` $\rightarrow$ `Cancelled` / `Closed`.
  - Canonical approval integration: Triggers platform `ApprovalEngineService.start_workflow(...)` using workflow code `WF_PURCHASE_ORDER`.
  - Controlled amendment and revision management: Prohibits direct modification of approved orders, requiring controlled revision increment (`revision_number` $N \to N+1$), approval reset to `Draft`, history retention, and re-approval.
  - Commercial dispatch tracking: Transmits confirmed order to supplier (`Approved` $\rightarrow$ `Dispatched`) without physical stock movement.
  - Commercial cancellation: Supports cancellation of draft, submitted, and approved/dispatched orders prior to physical goods receipt.
- **RBAC Security & Audit Logging (`app/db/seed_rbac.py`, `app/services/purchase_order_services.py`)**:
  - Seeded granular permissions: `procurement.purchase_order.create`, `procurement.purchase_order.read`, `procurement.purchase_order.update`, `procurement.purchase_order.submit`, `procurement.purchase_order.approve`, `procurement.purchase_order.amend`, `procurement.purchase_order.cancel`, `procurement.purchase_order.dispatch`.
  - Canonical `AuditLog` integration recording all PO lifecycle events (`PURCHASE_ORDER_CREATE`, `PURCHASE_ORDER_UPDATE`, `PURCHASE_ORDER_SUBMIT`, `PURCHASE_ORDER_APPROVE`, `PURCHASE_ORDER_REJECT`, `PURCHASE_ORDER_AMEND`, `PURCHASE_ORDER_DISPATCH`, `PURCHASE_ORDER_CANCEL`).
- **Domain Boundaries & Invariants**:
  - Zero Inventory Mutation guarantee: Creating, submitting, approving, amending, dispatching, and cancelling POs creates zero `StockLedger` entries, zero `StockBalance` changes, zero `GoodsReceipt` records, and zero physical stock movements.
  - Physical goods receiving and inspection deferred exclusively to `v0.7.3`.
  - Finance boundary preserved: No supplier invoices, AP entries, or GL journal postings.
- **Comprehensive Automated Test Suite (`tests/test_procurement_purchase_orders_v072.py`)**:
  - 13 test suites covering all 34 milestone requirements including CRUD, quotation conversion, pricing, approval engine, amendments, dispatch, cancellation, safe numbering, concurrency, RBAC, audit logging, and inventory invariants.
- **Documentation**:
  - `docs/procurement/commercial-purchasing.md`: Complete architectural and domain specification for v0.7.2.

## [v0.7.1] - 2026-09-07

### Milestone Procurement Sourcing & Requisitions

#### Added
- **Purchase Requisition Subsystem (`app/models/purchase_requisition.py`, `app/repositories/procurement_repos.py`, `app/services/purchase_requisition_services.py`, `app/schemas/procurement.py`, `app/api/v1/endpoints/purchase_requisitions.py`)**:
  - `PurchaseRequisition` and `PurchaseRequisitionItem` models with database-safe sequence numbering (`PR-YYYY-XXXXX`), line validations (quantity $> 0$, active products), and Draft modification locks.
  - Integration with canonical platform `ApprovalEngineService.start_workflow(...)` using workflow code `WF_PURCHASE_REQUISITION` with duplicate request prevention and no silent auto-approval.
  - Lifecycle state management: `Draft` $\rightarrow$ `Submitted` $\rightarrow$ `Approved` / `Rejected` / `Cancelled`.
- **Request For Quotation (RFQ) Subsystem (`app/models/rfq.py`, `app/repositories/procurement_repos.py`, `app/services/rfq_services.py`, `app/schemas/procurement.py`, `app/api/v1/endpoints/rfqs.py`)**:
  - Sourcing requests linked to internal demand (`PurchaseRequisition`) with database-safe sequence numbering (`RFQ-YYYY-XXXXX`).
  - Multi-supplier invitation management with active supplier validation, unique invitation constraints, and blacklisted/inactive supplier rejection.
  - RFQ lifecycle: `Draft` $\rightarrow$ `Issued` $\rightarrow$ `Closed` / `Cancelled`.
- **Dedicated Supplier Quotation Subsystem (`app/models/supplier_quotation.py`, `app/services/supplier_quotation_services.py`, `app/api/v1/endpoints/supplier_quotations.py`)**:
  - Complete domain isolation of `SupplierQuotation` and `SupplierQuotationItem` from `SalesQuotation` via dedicated `SupplierQuotationService`.
  - Sequential quotation numbering (`SQ-YYYYMM-XXXXX`) and exact line/header total calculations (subtotal, percentage discounts, taxes, net total).
  - Validation enforcing invited active suppliers on open RFQs, active product lines, and state transitions (`Draft` $\rightarrow$ `Submitted` $\rightarrow$ `Withdrawn` / `Approved` / `Rejected`).
- **Quotation Comparison Matrix & Sourcing Award**:
  - Deterministic RFQ quotation comparison view evaluating pricing, supplier rating, lead times, payment terms, and delivery parameters sorted lowest price first.
  - Explicit quotation award (`award_quotation`) selecting the winning supplier quotation, marking winning quotation `Approved`, rejecting competing quotations, closing the RFQ, and auditing the decision.
  - Zero-mutation guarantee preserving Inventory boundary (no stock movements) and Purchase Order boundary (PO creation deferred to `v0.7.2`).
- **RBAC Security & Audit Logging**:
  - Seeded 19 granular sourcing permissions across requisitions, RFQs, supplier quotations, comparison, and award.
  - Comprehensive audit event logging (`PURCHASE_REQUISITION_*`, `RFQ_*`, `SUPPLIER_QUOTATION_*`) via `AuditLog`.
- **Comprehensive Automated Test Suite (`tests/test_procurement_sourcing_v071.py`)**:
  - 11 test suites covering all 53 milestone scenarios across PRs, RFQs, Supplier Quotations, comparison matrix, award, approval engine, safe numbering, RBAC, audit logging, inventory invariants, and regression.

## [v0.7.0] - 2026-09-07

### Milestone Procurement Foundation

#### Added
- **Authoritative Supplier Master Domain (`app/models/supplier.py`, `app/repositories/procurement_repos.py`, `app/services/supplier_services.py`, `app/schemas/procurement.py`)**:
  - `SupplierCategory`: Canonical taxonomy classifying suppliers by industry and material type with unique code constraints and protected deactivation.
  - `Supplier`: Authoritative master identity with sequential `SUP-00001` code generation, commercial defaults, sensitive banking metadata masking (`****1234`), and lifecycle state transitions (`Active`, `Inactive`, `Blacklisted`).
  - `SupplierContact`: Multi-contact registry enforcing strict single primary contact per supplier with atomic synchronization.
  - `SupplierAddress`: Multi-location logistical endpoints (`Billing`, `Shipping`, `Head Office`, `Branch`) with cross-supplier isolation.
  - `SupplierDocument`: Compliance attachments linked directly to canonical `files.id` (`File` engine) with validation and expiry tracking.
  - `SupplierRating`: Immutable performance evaluation scorecards (scores 1.00 to 5.00) and automatic calculation of aggregate `Supplier.rating`.
- **RBAC Security & Roles (`app/db/seed_rbac.py`)**:
  - Seeded granular permissions: `procurement.supplier.create`, `procurement.supplier.read`, `procurement.supplier.update`, `procurement.supplier.delete`, `procurement.supplier.blacklist`, and child entity permissions.
  - Seeded canonical roles: `Procurement Manager` (full administrative rights) and `Procurement Viewer` (read-only rights).
- **Audit Logging & Event Publication**:
  - Integrated canonical `AuditLog` for all supplier, category, contact, address, document, and rating lifecycle mutations with sensitive data masking.
  - Published domain events (`SupplierCreated`, `SupplierUpdated`, etc.) via `DomainEventPublisher`.
- **Search & Pagination**:
  - Full PostgreSQL-backed search across supplier code, legal name, tax identifiers, email, and category filters with standard pagination models (`page`, `size`, `total`, `pages`).
- **Comprehensive Automated Test Suite (`tests/test_procurement_foundation.py`)**:
  - 44 dedicated tests validating categories, suppliers, contacts, addresses, documents, ratings, RBAC, audit logging, concurrency hardening, and zero-regression compatibility.
- **Documentation & ADR**:
  - `docs/procurement/procurement-foundation.md`: Complete domain specification for v0.7.0.
  - `docs/adr/ADR-0033-procurement-foundation.md`: Architecture Decision Record for Procurement Foundation.

## [v0.6.4] - 2026-09-06

### Milestone Inventory Reports & Analytics

#### Added
- **Read-Only Operational Reports Subsystem (`app/repositories/inventory_report_repos.py`, `app/services/inventory_report_services.py`, `app/schemas/inventory_reports.py`)**:
  - `Current Stock Report`: Real-time stock visibility across products, warehouses, and storage locations with on-hand, reserved, and available quantities.
  - `Stock Movement Report`: Authoritative historical audit report querying immutable `StockLedger` movements with before/after balances, linked document references, batch numbers, and serial metadata.
  - `Warehouse Inventory Report`: Facility-level aggregation of stocked items, storage location counts, batch expiries, serial inventory, and low-stock items.
  - `Product Inventory Report`: Global catalog inventory footprint across warehouses, storage locations, active batches, and movement velocity.
  - `Batch & Expiry Report`: Lot/batch visibility tracking expiry dates, remaining shelf-life, and status cohorts (`Active`, `Expired`, `Expiring Soon`).
  - `Serial Inventory Report`: Individual serial item lifecycle status (`Available`, `Reserved`, `Issued`, `Returned`, `Scrapped`, `Lost`) and location tracking.
  - `Stock Reservation Report`: Read-only demand allocation visibility with linked document types, expiration timestamps, and status lifecycles (`Active`, `Released`, `Consumed`, `Cancelled`).
  - `Available Stock Report`: Availability-oriented read model isolating immediately allocatable stock ($\text{available} = \text{on\_hand} - \text{reserved}$).
  - `Low Stock / Reorder Visibility Report`: Threshold breach detection identifying products below configured `reorder_level` and `minimum_stock` without triggering automated purchases.
  - `Inventory Aging Report`: Stock shelf-life analytics categorized into standard aging cohorts (`0-30 days`, `31-60 days`, `61-90 days`, `90+ days`).
  - `Inventory Movement Analytics Engine`: Operational analytics calculating inbound/outbound quantities, net movement, breakdowns by movement type, product category, and warehouse, and daily timeline trends.
  - `Executive Inventory Dashboard`: Consolidated KPI executive overview summarizing global stock lines, on-hand/reserved/available quantities, low stock breaches, expired/expiring batches, and top-moving products.
- **Streaming CSV Export Engine (`app/services/inventory_report_services.py`)**:
  - Memory-efficient streaming CSV generator (`text/csv`) with sanitized string escaping to prevent CSV injection vulnerabilities across all operational reports.
- **Granular RBAC Security (`app/db/seed_rbac.py`)**:
  - Seeded 9 granular report permissions: `inventory.report.stock.read`, `inventory.report.movement.read`, `inventory.report.warehouse.read`, `inventory.report.product.read`, `inventory.report.batch.read`, `inventory.report.serial.read`, `inventory.report.reservation.read`, `inventory.report.analytics.read`, and `inventory.report.export`.
- **Comprehensive Automated Test Suite (`tests/test_inventory_reports_v064.py`)**:
  - 14 test functions covering all 44 milestone scenarios (current stock, movements, warehouse/product summaries, batch expiry, serial tracking, reservations, availability, low stock, aging, movement analytics, executive dashboard, CSV exports, RBAC authorization, read-only zero-mutation guarantee, and backward compatibility).
- **Documentation & ADR**:
  - `docs/inventory/inventory-reports.md`: Comprehensive domain specification for v0.6.4.
  - `docs/adr/ADR-0032-inventory-reports-analytics.md`: Architecture Decision Record for read-only reporting architecture.

## [v0.6.3] - 2026-09-05

### Milestone Advanced Inventory

#### Added
- **Product Tracking Strategy (`app/models/product.py`)**:
  - Extended `Product` model with `tracking_type` enum (`NONE`, `BATCH`, `SERIAL`) and property accessors `is_batch_tracked` and `is_serial_tracked`.
- **Batch & Lot Management (`app/models/batch.py`, `app/repositories/inventory_advanced_repos.py`, `app/services/inventory_advanced_services.py`)**:
  - `Batch`: Tracks production/supplier lots with `manufacturing_date`, `expiry_date`, `supplier_batch_ref`, `current_quantity`, `status` (`Active`, `Expired`, `Consumed`), and `notes`.
  - FEFO/FIFO batch allocation helper algorithms in `BatchService`.
- **Serial Number Tracking (`app/models/serial_number.py`, `app/repositories/inventory_advanced_repos.py`, `app/services/inventory_advanced_services.py`)**:
  - `SerialNumber`: Tracks individual unit items with globally unique `serial_number`, location references (`warehouse_id`, `storage_location_id`), associated `batch_id`, status transitions (`Available`, `Reserved`, `Issued`, `Returned`, `Scrapped`, `Lost`), and JSONB chronological lifecycle `history`.
  - 1-to-1 quantity validation and duplicate serial prevention during goods movements.
- **Stock Reservations Subsystem (`app/models/stock_reservation.py`, `app/repositories/inventory_advanced_repos.py`, `app/services/inventory_advanced_services.py`)**:
  - `StockReservation`: Manages logical stock allocations with `reservation_number`, `quantity`, `reserved_for_type`, `reserved_for_id`, `expires_at`, `released_at`, `consumed_at`, and status (`Active`, `Released`, `Consumed`, `Cancelled`).
  - Row-level lock acquisition on `StockBalance` prevents over-reservation and ensures strict concurrency control.
  - Zero direct `StockLedger` mutation on reservation create/release events; physical stock remains untouched.
  - Atomic reservation consumption on Goods Issue notes.
- **Stock Movement & Warehouse Operations Integration (`app/services/stock_engine_services.py`, `app/services/warehouse_operations_services.py`)**:
  - Enhanced `StockMovementService.stock_in()` and `stock_out()` with batch tracking, expiry date validation on stock-out, and serial number count/status verification.
  - Extended `StockLedger` model and schema with nullable `batch_id` and `serial_numbers` metadata.
  - Integrated `WarehouseExecutionService` with tracked Goods Receipt, Goods Issue, and Stock Transfer documents.
- **Alembic Migration (`alembic/versions/a0b1c2d3e4f5_phase_v063_advanced_inventory_tracking.py`)**:
  - Additive database migration adding tracking columns to `products`, `stock_ledger`, `goods_receipt_items`, `goods_issue_items`, `stock_transfer_items`, and creating `batches`, `serial_numbers`, `lots`, `stock_reservations` tables.
- **Granular RBAC Security (`app/db/seed_rbac.py`)**:
  - Seeded permissions: `inventory.batch.read`, `inventory.batch.create`, `inventory.batch.update`, `inventory.serial.read`, `inventory.serial.create`, `inventory.serial.update`, `inventory.reservation.read`, `inventory.reservation.create`, `inventory.reservation.release`, `inventory.reservation.consume`, `inventory.reservation.cancel`.
- **Comprehensive Test Suite (`tests/test_advanced_inventory_v063.py`)**:
  - 27 test functions covering 38 distinct scenarios for batch lifecycle, duplicate rejection, expiry validation, serial number tracking, over-reservation rejection, reservation release/consumption, transaction rollback, deadlock-free transfers, and API/RBAC verification.
- **Documentation & ADR**:
  - `docs/inventory/advanced-inventory.md`: Complete domain specification.
  - `docs/adr/ADR-0026-advanced-inventory.md`: Architecture Decision Record for v0.6.3.

## [v0.6.2] - 2026-09-05

### Milestone Warehouse Operations

#### Added
- **Warehouse Operational Business Documents (`app/models/goods_receipt.py`, `app/models/goods_issue.py`, `app/models/stock_transfer.py`)**:
  - `GoodsReceipt` & `GoodsReceiptItem`: Inbound stock receipt documents and lines with validation for active/stockable items, warehouse location ownership, and status lifecycles (`Draft` $\rightarrow$ `Posted`).
  - `GoodsIssue` & `GoodsIssueItem`: Outbound stock issue/consumption documents with negative-stock policy validation and atomic multi-line posting.
  - `StockTransfer` & `StockTransferItem`: Inter-warehouse and intra-warehouse transfers with source-to-destination location validation and single-transaction execution.
  - Backward compatibility aliases: `notes` $\leftrightarrow$ `remarks`, `received_by` $\leftrightarrow$ `approved_by`, `transferred_by` $\leftrightarrow$ `completed_by`.
- **Authoritative Stock Engine Integration (`app/services/warehouse_operations_services.py`, `app/services/stock_engine_services.py`)**:
  - `GoodsReceiptService.post_receipt`: Atomically delegates to `StockMovementService.stock_in()` for each line.
  - `GoodsIssueService.post_issue`: Atomically delegates to `StockMovementService.stock_out()` for each line, enforcing row-level locking and negative-stock rules.
  - `StockTransferService.post_transfer`: Executes Source `STOCK_OUT` and Destination `STOCK_IN` atomically within a single PostgreSQL transaction.
  - Extended `StockMovementService` with `commit: bool = True` parameter to support atomic multi-line warehouse document posting with single commit / rollback.
- **Deadlock-Free Transfer Concurrency**:
  - Implemented deterministic lexicographical lock ordering on `(product_id, warehouse_id, storage_location_id)` balance keys prior to executing transfers to eliminate database deadlocks under high concurrency.
- **REST API Routers & Dual Path Compatibility (`app/api/v1/api.py`, `app/api/v1/endpoints/`)**:
  - Mounted canonical `/api/v1/warehouse/receipts`, `/api/v1/warehouse/issues`, `/api/v1/warehouse/transfers` with dedicated `/{id}/post` and `/{id}/cancel` endpoints alongside backward-compatible `/api/v1/inventory/goods-*` endpoints.
- **Granular RBAC Security (`app/db/seed_rbac.py`)**:
  - Added permissions: `inventory.receipt.post`, `inventory.receipt.delete`, `inventory.issue.post`, `inventory.issue.delete`, `inventory.transfer.post`, `inventory.transfer.delete` mapped to `Super Admin` and `Inventory Manager` roles.
- **Audit Logging & Telemetry**:
  - Integrated `AuditLogService` across all creation, update, approval, posting, cancellation, and deletion lifecycle transitions for Goods Receipts, Goods Issues, and Stock Transfers.
- **Comprehensive Test Suite (`tests/test_warehouse_operations_v062.py`, `tests/test_warehouse_operations.py`)**:
  - Complete coverage for CRUD, multi-line atomic rollbacks on forced line failure, deterministic concurrent reverse-transfers, posting idempotency, RBAC, and dual API routes.
- **Architecture Documentation & ADR**:
  - `docs/inventory/warehouse-operations.md`: Domain specification for v0.6.2 warehouse operations.
  - `docs/adr/ADR-0025-warehouse-operations.md`: Architecture Decision Record for Milestone v0.6.2.

## [v0.6.1] - 2026-09-05

### Milestone Stock Ledger & Authoritative Stock Balances

#### Added
- **Authoritative Stock Quantity Engine (`app/models/stock_ledger.py`, `app/models/stock_balance.py`)**:
  - `StockBalance`: Authoritative current inventory quantity `quantity_on_hand` at `Product + Warehouse + StorageLocation` grain with database-level `UNIQUE(product_id, warehouse_id, storage_location_id)` constraint.
  - `StockLedger`: Append-only, immutable inventory movement ledger capturing `movement_type` (`STOCK_IN`, `STOCK_OUT`, `ADJUSTMENT`), `direction` (`IN`, `OUT`), `quantity` (> 0), `quantity_before`, `quantity_after`, `idempotency_key`, `reason`, `notes`, and metadata.
- **Alembic Database Migration (`alembic/versions/f9b0c1d2e3f5_phase_v061_enhance_stock_ledger_and_balances.py`)**:
  - Additive schema upgrade adding `quantity_before`, `quantity_after`, `idempotency_key`, `reason`, `notes`, and `movement_type` with unique idempotency indexing and foreign key protections.
- **Pydantic Validation Schemas (`app/schemas/stock_engine.py`)**:
  - Strict input validation schemas: `StockMovementCreate`, `StockMovementResponse`, `PaginatedStockMovementResponse`, and updated `StockBalanceResponse`.
- **Async Repositories (`app/repositories/stock_engine_repos.py`)**:
  - Enhanced `StockBalanceRepository` with transactional row-locking `get_for_update` and atomic `get_or_create_for_update`.
  - Enhanced `StockLedgerRepository` with `find_by_idempotency_key`, composite filtering, and immutable querying.
- **Transactional Domain Services (`app/services/stock_engine_services.py`)**:
  - `StockMovementService`: Processes `STOCK_IN`, `STOCK_OUT`, and `ADJUSTMENT` operations in a single atomic database transaction. Features PostgreSQL `SELECT ... FOR UPDATE` row locking, in-process async synchronization, negative stock policy hierarchy resolution (`Warehouse` -> `Global`), and database-enforced idempotency deduplication.
  - `StockBalanceService`: Provides real-time balance queries and aggregate quantity lookups across products, warehouses, and storage locations.
- **Granular RBAC Security (`app/db/seed_rbac.py`)**:
  - Seeded permissions: `inventory.stock.read`, `inventory.stock.movement.create`, `inventory.stock.ledger.read`, `inventory.stock.balance.read` mapped to `Super Admin` and `Inventory Manager` roles.
- **REST API Routers (`app/api/v1/endpoints/`)**:
  - Mounted `/api/v1/stock/movements` (`POST`, `GET`).
  - Mounted `/api/v1/stock/ledger` & `/api/v1/stock/ledger/{id}`.
  - Mounted `/api/v1/stock/balances` & `/api/v1/stock/balances/{id}`.
  - Mounted `/api/v1/products/{product_id}/stock`, `/api/v1/warehouses/{warehouse_id}/stock`, and `/api/v1/storage-locations/{location_id}/stock`.
- **Comprehensive Integration Test Suite (`tests/test_stock_ledger_v061.py`, `tests/test_stock_ledger_engine.py`)**:
  - 23 tests verifying Stock IN/OUT/Adjustment, negative-stock policy rules, PostgreSQL concurrency locking, idempotency deduplication, transaction rollback safety, grain uniqueness, and RBAC authorization.
- **Architecture Documentation & ADR (`docs/`)**:
  - `docs/inventory/stock-ledger-and-balances.md`: Comprehensive domain specification for the v0.6.1 authoritative stock engine.
  - `docs/adr/ADR-0024-stock-ledger-and-balances.md`: Architecture Decision Record for Milestone v0.6.1.

## [v0.6.0] - 2026-08-08

### Milestone Inventory Foundation & Master Data

#### Added
- **Multi-Warehouse & Policy ORM Models (`app/models/product_warehouse.py`, `app/models/inventory_policy.py`)**:
  - `ProductWarehouse`: Per-warehouse stocking configurations, reorder levels, reorder quantities, minimum/maximum thresholds, safety stock buffers, and preferred storage location consistency.
  - `InventoryPolicy`: Global and facility-specific valuation methods (`FIFO`, `LIFO`, `WEIGHTED_AVERAGE`, `STANDARD`), costing strategies (`STANDARD`, `ACTUAL`, `MOVING_AVERAGE`), negative stock policy rules, reorder strategies (`MIN_MAX`, `FIXED_ORDER_QTY`, `PERIODIC`), and reservation behaviors.
- **Additive Product & Warehouse Master Model Enhancements (`app/models/product.py`, `app/models/unit_of_measure.py`, `app/models/warehouse.py`, `app/models/storage_location.py`)**:
  - `Product`: Added `model_number`, `is_active`, `is_stockable`, `is_sellable`, `is_purchasable`, `reorder_level`, `reorder_quantity`, `minimum_stock`, `maximum_stock`, `lead_time_days`, `default_unit_price`, `metadata_json`, and alias properties.
  - `UnitOfMeasure`: Added unique `code` column, aliases `uom_type` and `decimal_precision`.
  - `Warehouse`: Added `warehouse_type`, `description`, structured address fields (`address_line_1`, `address_line_2`, `city`, `state`, `country`, `postal_code`), operating `timezone`, and `manager_employee_id`.
  - `StorageLocation`: Added `description`, composite unique constraint `(warehouse_id, code)`, and `parent_location_id` alias.
- **Alembic Database Migration (`alembic/versions/f1a2b3c4d5e6_phase_v060_inventory_foundation_enhancements.py`)**:
  - Complete schema upgrade script for new tables `product_warehouses` and `inventory_policies` and additive columns across master tables.
- **Pydantic Schemas (`app/schemas/inventory.py`)**:
  - Type-safe schemas with validation bounds for `ProductWarehouse`, `InventoryPolicy`, and enhanced `Product`, `Warehouse`, `StorageLocation`, `UnitOfMeasure`, and `ProductCategory`.
- **Async Repositories Layer (`app/repositories/inventory_repos.py`)**:
  - `ProductWarehouseRepository`, `InventoryPolicyRepository`, and enhanced query methods across all inventory repositories.
- **Domain Services Layer (`app/services/inventory_services.py`)**:
  - `ProductWarehouseService`, `InventoryPolicyService`, enhanced `ProductService`, `WarehouseService`, `StorageLocationService`, `CategoryService`, and `UnitOfMeasureService` with business validations, circular reference guards, safe deactivations, and audit logging.
- **RBAC Permissions (`app/db/seed_rbac.py`)**:
  - Seeded permissions (`inventory.product_warehouse.*`, `inventory.policy.*`, `inventory.uom.*`) and assigned to `Super Admin` and `Inventory Manager`.
- **REST API Endpoints (`app/api/v1/endpoints/product_warehouse.py`, `product.py`, `category.py`, `warehouse.py`, `storage_location.py`, `unit_of_measure.py`)**:
  - New endpoints: `/api/v1/product-warehouses`, `/api/v1/inventory/policies`, `/api/v1/products/search`, `/api/v1/products/{id}/warehouses`, `/api/v1/categories/{id}/children`, `/api/v1/warehouses/{id}/locations`, `/api/v1/warehouses/{id}/products`.
- **Comprehensive Pytest Suite (`tests/test_inventory_foundation.py`)**:
  - End-to-end integration tests covering all master data workflows, tree resolutions, multi-warehouse parameters, inventory policies, and RBAC authorization with 100% pass rate.
- **Documentation & Architecture Decision Record (`docs/`)**:
  - `docs/inventory/inventory-foundation.md`: Comprehensive domain overview and API reference.
  - `docs/adr/ADR-0023-inventory-foundation.md`: Architecture Decision Record for Milestone v0.6.0.

## [v1.3.0] - 2026-08-07 — Production Ready

### Milestone Enterprise Integrations & Production Readiness — Complete Platform Release

#### Added
- **Infrastructure ORM Models (`app/models/integrations.py`)**:
  - `ApiKey`: Key hash, prefix, name, owner_id, scopes, expires_at, is_revoked, usage_count, last_used_at.
  - `WebhookSubscription`: Webhook URL registrations, secret token, event_types, is_active, headers_json.
  - `WebhookDelivery`: Delivery attempt audit log, payload, status, response status/body, retry counts, next_retry_at.
  - `ProviderConfiguration`: Pluggable provider settings (type, name, settings_json, is_active, is_default).
  - `BackupMetadata`: Database and storage backup registry (name, path, file size, checksum, status, type).
  - `SystemConfiguration`: Dynamic system-wide runtime settings (config_key, config_value, value_type, category, is_encrypted).
- **Alembic Database Migration (`alembic/versions/e1f2a3b4c5d6_phase_v130_enterprise_integrations.py`)**:
  - Schema migration creating all 6 infrastructure tables, foreign key constraints, unique indices, and soft delete mixins.
- **Pydantic DTO Schemas (`app/schemas/integrations.py`)**:
  - Type-safe schemas for API Keys, Webhooks, Provider Configurations, Storage, Communication, Bulk Import/Export, Monitoring, Backups, Health Checks, System Config.
- **Async Repositories Layer (`app/repositories/integration_repos.py`)**:
  - Repositories: `ApiKeyRepository`, `WebhookSubscriptionRepository`, `WebhookDeliveryRepository`, `ProviderConfigurationRepository`, `BackupMetadataRepository`, `SystemConfigurationRepository`.
- **Pluggable Provider Abstraction Framework (`app/providers/`)**:
  - `storage/`: Abstract `StorageProvider` interface + `LocalStorage`, `MinIOStorage`, `S3Storage`, `AzureBlobStorage`, `GCSStorage`.
  - `communication/`: Abstract interfaces for `EmailProvider` (SMTP), `SMSProvider` (Twilio/AWS SNS), `WhatsAppProvider` (Meta Cloud API), `PushNotificationProvider` (FCM), plus Jinja2 template rendering engine.
  - `auth/`: OAuth2 / OpenID Connect SSO integration, LDAP / Active Directory integration, TOTP / SMS MFA.
- **Domain Services Layer (`app/services/integration_services.py`)**:
  - `ApiKeyService`, `WebhookService`, `ProviderService`, `StorageService`, `ImportExportService`, `MonitoringService`, `BackupService`, `DeploymentService`.
- **Middleware & Security Hardening (`app/middleware/`)**:
  - `security_middleware.py`: Security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options), CORS, CSRF token validation.
  - `rate_limit_middleware.py`: Redis sliding-window rate limiter with `X-RateLimit-*` headers.
  - `observability_middleware.py`: Correlation ID (`X-Correlation-ID`) & Request ID propagation, OpenTelemetry span tracking, Prometheus latency metrics.
  - `structured_logging.py`: Production JSON log formatter with sensitive parameter masking.
- **Celery Tasks (`app/tasks/integration_tasks.py`)**:
  - `deliver_webhook_task`, `execute_database_backup_task`, `cleanup_expired_backups_task`, `refresh_system_health_task`.
- **RBAC Permissions (`app/db/seed_rbac.py`)**:
  - Seeded permissions (`system.*`, `integration.*`, `monitoring.*`, `backup.*`, `apikey.*`, `webhook.*`).
- **REST API Routers (`app/api/v1/endpoints/`)**:
  - Mounted routers: `/api-keys`, `/webhooks`, `/providers`, `/storage`, `/import-export`, `/monitoring`, `/health`, `/backups`, `/system/config`.
- **DevOps & Infrastructure Artifacts**:
  - `docker-compose.prod.yml`, `nginx/nginx.conf`, `.env.production.example`, `k8s/deployment.yaml`, `Makefile`, `cli.py`.
- **CI/CD Pipeline (`.github/workflows/ci.yml`)**:
  - GitHub Actions CI/CD workflow covering linting, test suite execution, Bandit security scanning, and Docker build/release.
- **Architecture Documentation & Operations Guides (`docs/`)**:
  - `docs/architecture/` (`system_architecture.md`, `module_dependency_diagram.md`, `database_er_diagram.md`, `api_architecture.md`, `security_architecture.md`, `deployment_architecture.md`, `event_catalog.md`).
  - `docs/guides/` (`administrator_guide.md`, `developer_guide.md`, `deployment_guide.md`, `operations_guide.md`, `security_guide.md`, `api_guide.md`).
- **Integration Test Suite (`tests/test_enterprise_integrations.py`)**:
  - Test suite covering all infrastructure, security, monitoring, import/export, and backup endpoints with 100% pass rate.

## [v1.2.0] - 2026-08-07

### Milestone Enterprise Reporting & Business Intelligence — BI Engine & Reporting Suite

#### Added
- **Enterprise Reporting ORM Models (`app/models/reporting.py`)**:
  - `Dashboard` & `DashboardWidget`: Executive and module-specific dashboards with customizable layout configurations.
  - `KPI` & `KPIMetric`: Key Performance Indicators across 8 modules with target values, warning/critical threshold tracking, and historical metrics.
  - `ReportTemplate` & `SavedReport`: Pre-defined domain templates and custom user-saved reports with column selection, filtering, sorting, grouping, and calculated fields.
  - `ScheduledReport` & `ReportExecution`: Background automated report schedules with multi-format exports and recipient email notifications.
  - `AnalyticsSnapshot`: Aggregated domain metrics for historical trend analysis and period comparisons.
  - `ChartConfiguration`: Visual chart configs for Line, Bar, Area, Pie, Donut, Stacked Bar, Heatmap, and Trend charts.
- **Alembic Migration (`alembic/versions/d1e2f3a4b5c6_phase_v120_enterprise_reporting_bi.py`)**:
  - Schema migration creating all 10 reporting tables, foreign key constraints, unique indices, and soft delete mixins.
- **Pydantic DTO Schemas (`app/schemas/reporting.py`)**:
  - Type-safe Pydantic V2 schemas for Dashboards, Widgets, KPIs, Metrics, Report Templates, Saved Reports, Scheduled Reports, Report Executions, Analytics Snapshots, Chart Configurations, Export Requests, and Global Search.
- **Async Repositories (`app/repositories/reporting_repos.py`)**:
  - Async repository pattern implementation inheriting from `BaseRepository`.
- **Domain Events (`app/core/domain_events.py`)**:
  - Added constants: `ReportGenerated`, `DashboardViewed`, `ScheduledReportCompleted`, `KPIUpdated`, `AnalyticsCalculated`.
- **Domain Services Layer (`app/services/reporting_services.py`)**:
  - `DashboardService`: System dashboards (Global, HR, Payroll, Inventory, Procurement, Sales, CRM, Finance) + Custom Dashboards, Widget Management, Redis caching.
  - `KPIService`: Dynamic calculation for all KPIs across 8 modules, recording metrics over time, threshold alert detection, Redis caching.
  - `AnalyticsService`: Period comparisons, growth rate calculations (% YoY/MoM), trend aggregations across modules, forecast-ready metrics.
  - `ReportBuilderService`: Dynamic query builder reading existing domain models, custom columns, filtering, sorting, grouping, calculated fields, saved reports.
  - `ScheduledReportService`: Schedule processing, cron evaluation, trigger execution, email notification dispatch.
  - `ExportService`: Multi-format PDF, Excel, CSV, JSON report exporter integrated with core `File` repository.
  - `ChartService`: Formats data payloads into chart configs.
  - `GlobalSearchService`: Global search over reports, dashboards, KPIs, saved reports.
- **Celery Tasks (`app/tasks/reporting_tasks.py`)**:
  - `process_scheduled_reports_task`, `refresh_analytics_snapshots_task`, `refresh_kpis_task`.
- **RBAC Permissions (`app/db/seed_rbac.py`)**:
  - Seeded permissions (`report.dashboard.*`, `report.analytics.*`, `report.builder.*`, `report.kpi.*`, `report.export.*`, `report.schedule.*`).
- **REST API Endpoints (`app/api/v1/endpoints/reporting_*.py`)**:
  - Routers mounted at `/reporting/dashboards`, `/reporting/kpis`, `/reporting/analytics`, `/reporting/reports`, `/reporting/schedules`, `/reporting/exports`, `/reporting/charts`, `/reporting/search`.
- **Integration Test Suite (`tests/test_reporting_bi.py`)**:
  - 100% test coverage across 6 integration test suites.

## [v1.1.0] - 2026-08-06

### Milestone Finance Operations & Financial Reporting — Operational Accounting Suite

#### Added
- **Finance Operations ORM Models (`app/models/finance_ops.py`)**:
  - `CustomerInvoice` & `CustomerInvoiceLine`: Sales invoices with subtotal, tax, outstanding amounts, and double-entry GL journal posting.
  - `CustomerCreditNote` & `CustomerDebitNote`: Credit and debit adjustments for accounts receivable.
  - `CustomerLedgerEntry`: Immutable sub-ledger tracking debit/credit entries and running customer balances.
  - `SupplierBill` & `SupplierBillLine`: Vendor bills with subtotal, tax, outstanding amounts, and double-entry GL journal posting.
  - `SupplierCreditNote` & `SupplierDebitNote`: Credit and debit adjustments for accounts payable.
  - `SupplierLedgerEntry`: Immutable sub-ledger tracking debit/credit entries and running supplier balances.
  - `ReceiptVoucher` & `PaymentVoucher`: Inbound customer receipts and outbound supplier payments with Cash/Bank/Electronic payment modes.
  - `PaymentAllocation`: Multi-invoice/bill payment allocations supporting partial payments.
  - `BankAccount` & `BankTransaction`: Company bank account master and ledger transactions.
  - `BankStatement`, `BankStatementLine`, `BankReconciliation`, & `BankReconciliationItem`: Statement import (CSV/OFX), automated rule-based transaction matching, manual match overrides, and unreconciled item auditing.
  - `AssetCategory`, `FixedAsset`, & `DepreciationSchedule`: Asset register, acquisition journal posting, straight-line and written-down value depreciation schedule calculation, and automated monthly depreciation posting.
  - `Budget` & `BudgetLine`: Annual and departmental budgets with approval workflows and real-time budgeted vs actual variance analysis.
  - `FinancialStatementSnapshot`: Telemetry and audit snapshots of Trial Balance, Balance Sheet, Profit & Loss, and Cash Flow Statement.
- **Domain Services Layer (`app/services/finance_ops_services.py`)**:
  - `AccountsReceivableService`: AR invoicing, GL posting via `PostingEngineService`, aging analysis, and customer statements.
  - `AccountsPayableService`: AP bill processing, GL posting, aging analysis, and vendor statements.
  - `PaymentService`: Receipt and payment voucher management, GL posting, and invoice/bill allocations.
  - `BankService`: Bank account management and transaction recording.
  - `ReconciliationService`: Statement import, auto-matching, and reconciliation processing.
  - `AssetService` & `DepreciationService`: Fixed asset management and depreciation schedule calculation & journal posting.
  - `FinancialStatementService`: Real-time calculation of Trial Balance, Balance Sheet, and Profit & Loss.
  - `BudgetService`: Budget creation, line items, approval workflow, and variance analysis.
  - `ClosingService`: Period closing, year-end closing, and period locking.
  - `AnalyticsService`: Executive dashboard metrics, financial ratios (Current, Quick, Debt-to-Equity), and Redis cache integration.
- **Celery Background Tasks (`app/tasks/finance_ops_tasks.py`)**:
  - `scheduled_depreciation_task`: Monthly batch depreciation schedule calculation & journal posting.
  - `recurring_payments_task`: Auto-generating recurring payment vouchers.
  - `budget_alerts_task`: Monitoring budget utilization thresholds (>90%).
  - `statement_generation_task`: Async pre-generation of financial statement snapshots.
  - `financial_closing_checks_task`: Validating period closing readiness.
  - `analytics_refresh_task`: Refreshing Redis cache for finance analytics dashboard.
- **RBAC Security Seed (`app/db/seed_rbac.py`)**:
  - Seeded permissions: `finance.receivable.*`, `finance.payable.*`, `finance.payment.*`, `finance.bank.*`, `finance.reconciliation.*`, `finance.asset.*`, `finance.depreciation.*`, `finance.statement.*`, `finance.budget.*`, `finance.analytics.*`.
- **REST API Routers (`app/api/v1/endpoints/finance_*.py`)**:
  - `finance_receivables.py`: `/finance/receivables`
  - `finance_payables.py`: `/finance/payables`
  - `finance_payments.py`: `/finance/payments`
  - `finance_banks.py`: `/finance/banks`
  - `finance_reconciliation.py`: `/finance/reconciliation`
  - `finance_assets.py`: `/finance/assets`
  - `finance_budgets.py`: `/finance/budgets`
  - `finance_statements.py`: `/finance/statements`
  - `finance_analytics.py`: `/finance/analytics`
- **Integration Test Suite (`tests/test_finance_ops.py`)**: 6 integration test cases covering 100% of Finance Operations requirements with 100% pass rate.
- **Documentation (`docs/adr/ADR-0030-finance-operations.md`)**: Architecture Decision Record documenting Finance Operations architecture.

---

## [v1.0.0] - 2026-08-06

### Milestone Finance Core — Central Accounting Engine

#### Added
- **Finance Core ORM Models (`app/models/finance.py`)**:
  - `AccountGroup`: Hierarchical Chart of Accounts group classification structure (Asset, Liability, Equity, Income, Expense).
  - `ChartOfAccount`: General Ledger Account Master entity with multi-level parent hierarchy, currency, opening balance, and live current balance tracking.
  - `FiscalYear`: Accounting fiscal year master supporting 12-month automated periods and status lifecycle (Draft, Open, Closed).
  - `FiscalPeriod`: Monthly/quarterly sub-periods with granular period locking mechanism against posted transactions.
  - `Currency`: Multi-currency master with base currency designation and decimal precision.
  - `ExchangeRate`: Historical and effective exchange rate engine for cross-currency conversion.
  - `CostCenter`: Departmental and operational cost center hierarchy.
  - `AccountingDimension`: Multidimensional ledger tags (Branch, Project, Region, Cost Center).
  - `JournalType`: Journal voucher classifications with approval threshold routing.
  - `Journal` & `JournalLine`: Double-entry accounting transaction headers and lines enforcing `Total Debit == Total Credit`. Immutable after posting; supports counter-balancing reversal entries.
  - `TaxCategory` & `TaxRate`: Tax master rules supporting Input/Output VAT, GST, and effective date ranges.
  - `PostingRule`: Rule configuration engine mapping domain events (Payroll, Procurement, Sales, Inventory) to debit/credit GL accounts.
  - `AccountingEvent`: Immutable event store logging financial events across the enterprise.
  - `FinancialPostingQueue`: Financial queue engine for asynchronous automated GL postings.
- **Finance Core Repositories (`app/repositories/finance_repos.py`)**: 15 async repositories handling transactional database queries and hierarchy lookups.
- **Finance Pydantic DTO Schemas (`app/schemas/finance.py`)**: Complete validation schemas enforcing strict double-entry balancing rules (`Total Debit == Total Credit`).
- **Domain Services Layer (`app/services/finance_services.py`)**:
  - `ChartOfAccountsService`: COA hierarchy and account balance management.
  - `FiscalService`: Fiscal year generation and period lock enforcement.
  - `CurrencyService`: Currency master and exchange rate conversion engine.
  - `CostCenterService`: Cost center hierarchies and dimension management.
  - `TaxService`: Tax categories and rate calculation.
  - `PostingRuleService`: Domain event mapping and posting rule processing.
  - `JournalService`: Double-entry journal creation, draft validation, and approval workflow routing.
  - `PostingEngineService`: Immutable GL posting and journal reversal engine.
  - `AccountingEventService`: Immutable event auditing.
- **Celery Background Tasks (`app/tasks/finance_tasks.py`)**:
  - `process_recurring_journals_task`: Automatic recurring journal voucher generation.
  - `refresh_exchange_rates_task`: Currency exchange rate updates.
  - `fiscal_period_notifications_task`: Fiscal period closing notifications.
  - `process_financial_posting_queue_task`: Automatic processing of cross-domain posting queues from Payroll, Procurement, Sales, and Inventory.
- **RBAC Security Seed (`app/db/seed_rbac.py`)**:
  - Seeded permissions: `finance.accounts.*`, `finance.journal.*`, `finance.posting.*`, `finance.tax.*`, `finance.currency.*`, `finance.costcenter.*`, `finance.fiscal.*`.
  - Created roles: `Finance Manager` and `Chief Accountant`.
- **REST API Routers (`app/api/v1/endpoints/finance_*.py`)**:
  - `finance_accounts.py`: `/finance/accounts`
  - `finance_fiscal.py`: `/finance/fiscal`
  - `finance_currencies.py`: `/finance/currencies`
  - `finance_cost_centers.py`: `/finance/cost-centers`
  - `finance_journals.py`: `/finance/journals`
  - `finance_posting_rules.py`: `/finance/posting-rules`
  - `finance_taxes.py`: `/finance/taxes`
  - `finance_search.py`: `/finance/search`
- **Integration Test Suite (`tests/test_finance_core.py`)**: 6 comprehensive integration test cases covering 100% of Finance Core requirements with 100% pass rate.
- **Documentation (`docs/adr/ADR-0029-finance-core.md`)**: Architecture Decision Record documenting the Finance Core implementation.

---

## [v0.9.0] - 2026-08-06

### Milestone CRM Domain Completion — Enterprise Customer Relationship Management

#### Added
- **CRM Database ORM Models (`app/models/crm.py`)**:
  - `LeadSource`: Lead source master classification.
  - `LeadTag` & `lead_tags_association`: Tagging system for leads.
  - `Lead`: Lead master entity with automated scoring, duplicate detection, assignment, and status lifecycle tracking. Reuses Sales `Customer` upon conversion without creating duplicate customer records.
  - `LeadNote`: Rich text notes with pinning and privacy support.
  - `OpportunityStage`: Configurable sales pipeline stages with default win probabilities and ordering.
  - `Opportunity`: Sales opportunity pipeline tracking expected revenue, closing dates, owner, win/loss reasons, competitors, and products of interest.
  - `Activity`: Activity tracking for Calls, Meetings, Emails, Tasks, Follow-ups, and Reminders across Leads, Opportunities, Customers, and Campaigns.
  - `Meeting`: Calendar appointments, customer visits, and sales calls with start/end time and location.
  - `Task`: Personal and team tasks with parent-child task dependency hierarchy.
  - `Campaign` & `CampaignMember`: Marketing campaigns (Email, Event, Referral, Social) with budget tracking, actual cost, revenue, and ROI computation.
  - `CRMReportSnapshot`: Telemetry snapshots for funnel analytics and pipeline values.
  - `TimelineEvent`: Unified interaction timeline event logging across all CRM entities and Sales activities.
- **Pydantic DTO Schemas (`app/schemas/crm.py`)**: Validation schemas for Leads, Sources, Tags, Notes, Stages, Opportunities, Activities, Meetings, Tasks, Campaigns, Lead Conversion, Analytics, Search, and Import/Export.
- **Repository Layer (`app/repositories/crm_repos.py`)**: 13 async repositories deriving from `BaseRepository` with eager relational loading (`selectinload`).
- **Domain Event Publisher (`app/core/domain_events.py`)**: CRM event constants `LeadCreated`, `LeadAssigned`, `LeadConverted`, `OpportunityCreated`, `OpportunityWon`, `OpportunityLost`, `TaskCompleted`, `MeetingScheduled`, and `CampaignCompleted`.
- **Domain Services (`app/services/crm_services.py`)**:
  - `LeadService`: Lead lifecycle, scoring engine, deduplication, assignment, tagging, notes, and merging.
  - `OpportunityService`: Opportunity creation, pipeline stage progression, win/loss recording.
  - `ActivityService`, `MeetingService`, `TaskService`: Activity logging, calendar meetings, and task dependency resolution.
  - `CampaignService`: Campaign budget, member enrollment, and ROI calculation.
  - `LeadConversionService`: Converts Leads to Opportunities while searching and reusing existing Sales `Customer` records (or creating a new `Customer` via `CustomerService`).
  - `CRMAnalyticsService` & `CRMSearchService`: Funnel metrics, revenue forecasts, Redis dashboard caching, and global search.
  - `CRMImportExportService`: Streaming CSV lead export and bulk CSV lead import.
- **Background Celery Tasks (`app/tasks/crm_tasks.py`)**: Celery tasks `calculate_lead_scoring_task`, `refresh_crm_analytics_task`, `meeting_reminders_task`, and `task_reminders_task`.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded permissions `crm.lead.*`, `crm.opportunity.*`, `crm.activity.*`, `crm.meeting.*`, `crm.task.*`, `crm.campaign.*`, `crm.analytics.*`, `crm.search.read` and assigned to the `CRM Manager` role.
- **REST API Routers (`app/api/v1/endpoints/`)**: 9 API routers registered in `app/api/v1/api.py`.
- **Database Migration (`alembic/versions/a9b0c1d2e3f4_phase_v090_crm_domain_completion.py`)**: Alembic migration creating 13 CRM tables and indexes.
- **Architecture Decision Record (`docs/adr/ADR-0028-crm-domain.md`)**: ADR documenting CRM architecture, Sales Customer reuse, Lead Conversion Engine, and Unified Timeline.

## [v0.8.0] - 2026-08-05

### Milestone Sales Domain Completion — Enterprise Order-to-Cash Architecture

#### Added
- **Sales Database ORM Models (`app/models/`)**:
  - `CustomerCategory`: Industry and market segmentation for customer master data.
  - `Customer`: Enterprise Customer Master containing tax IDs, credit limits, payment terms, currency, credit lock status, preferred status, and financial balances.
  - `CustomerContact`: Multi-contact directory with primary flags and designation.
  - `CustomerAddress`: Multi-address directory (Billing, Shipping, Head Office, Branch).
  - `CustomerDocument`: File attachments (tax certificates, contracts, KYC compliance).
  - `PriceList`: Customer and currency-specific price lists with multi-tier pricing.
  - `PricingRule`: Tiered volume pricing rules with min-qty bounds and validity windows.
  - `DiscountRule`: Document and line-level discount calculation rules with min-order thresholds.
  - `SalesQuotation` & `SalesQuotationItem`: Customer commercial quotes with versioning (`revision_number`), tax computation, line item discounts, and approval engine integration.
  - `SalesOrder` & `SalesOrderItem`: Sales Orders with customer credit limit verification, multi-warehouse delivery destinations, item status tracking (`Pending`, `Partial`, `Delivered`, `Cancelled`), and delivery status tracking.
  - `DeliveryOrder` & `DeliveryOrderItem`: Shipments executing physical inventory deduction via `GoodsIssueService` and `StockLedgerService` (`SALES_ISSUE`).
  - `SalesReturn` & `SalesReturnItem`: Customer sales returns executing physical inventory addition via `GoodsReceiptService` and `StockLedgerService` (`SALES_RETURN`).
  - `SalesReportSnapshot`: Periodic executive telemetry snapshots for sales revenue, order volumes, customer metrics, and product performance.
- **Pydantic DTO Schemas (`app/schemas/sales.py`)**: Complete validation suite for Customers, Categories, Contacts, Addresses, Price Lists, Pricing Rules, Discount Rules, Quotations, Orders, Deliveries, Returns, Reports, Analytics, Search, and Import/Export.
- **Repository Layer (`app/repositories/sales_repos.py`)**: 14 async repositories implementing `BaseRepository` for all Sales entities with eager relational loading (`selectinload`).
- **Domain Event Publisher (`app/core/domain_events.py`)**: Emits `CustomerCreated`, `SalesQuotationSubmitted`, `SalesQuotationApproved`, `SalesOrderSubmitted`, `SalesOrderApproved`, `SalesOrderCancelled`, `DeliveryOrderDispatched`, and `SalesReturnApproved`.
- **Domain Services (`app/services/`)**:
  - `CustomerService`: Customer master lifecycle, category management, contact directory, address book, credit limit verification, and credit lock toggling.
  - `PricingService` & `DiscountService`: Price list lookups, volume pricing engine, line-item & document-level discount evaluation.
  - `QuotationService`: Quotation creation, line item math, revisioning, approval engine integration, and order conversion.
  - `SalesOrderService`: Order creation, credit checks, approval workflow integration, cancellation, and order closure.
  - `DeliveryService`: Delivery Order management and seamless integration with Warehouse Operations (`GoodsIssueService`).
  - `SalesReturnService`: Sales Return processing and inventory stock reversal execution via `GoodsReceiptService`.
  - `InvoicePayloadService`: Finance-decoupled invoice payload generation (`SalesInvoicePayload`) for future Accounts Receivable / GL modules.
  - `SalesAnalyticsService` & `SalesReportService`: Revenue metrics, Sales Register, Customer Ledger, executive performance dashboards with Redis caching, and snapshotting.
  - `SalesSearchService`: Unified multi-entity search across Customers, Orders, Quotations, Deliveries, and Products.
  - `SalesImportExportService`: Streaming CSV export and bulk CSV import engine.
- **Background Celery Tasks (`app/tasks/sales_tasks.py`)**: Celery tasks `calculate_customer_analytics_task`, `refresh_sales_analytics_task`, and `check_expiring_quotations_task`.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded 20+ permissions across `sales.customer.*`, `sales.pricing.*`, `sales.quotation.*`, `sales.order.*`, `sales.delivery.*`, `sales.return.*`, `sales.analytics.*`, `sales.reports.*`, `sales.import_export.*`, and assigned them to `Sales Manager` role.
- **REST API Routers (`app/api/v1/endpoints/`)**: 11 API routers registered in `app/api/v1/api.py`.
- **Database Migration (`alembic/versions/f8a9b0c1d2e3_phase_v080_sales_domain_completion.py`)**: Alembic migration creating 18 sales tables and indexes.
- **Architecture Decision Record (`docs/adr/ADR-0027-sales-domain.md`)**: ADR covering Sales Domain architecture, Warehouse Operations integration, credit limit checks, Finance decoupling, and invoice payload contract generation.

## [v0.7.0] - 2026-08-04

### Milestone Procurement Domain Completion — Production-Grade Purchasing Architecture

#### Added
- **Procurement Database ORM Models (`app/models/`)**:
  - `SupplierCategory`: Industry and material classification for vendor masters.
  - `Supplier`: Comprehensive Vendor Master containing GST/VAT numbers, corporate tax IDs, credit limits, payment terms, currency, bank details, ratings, on-time delivery rates, and total spend.
  - `SupplierContact`: Multi-contact directory with designation and primary contact flags.
  - `SupplierAddress`: Multi-address locator (Billing, Shipping, Head Office, Branch).
  - `SupplierDocument`: Digital file attachments (tax certificates, contracts, ISO audits).
  - `SupplierRating`: Historical evaluator score reviews and performance feedback.
  - `PurchaseRequisition` & `PurchaseRequisitionItem`: Internal demand requisitions with priority and status workflow.
  - `RFQ` & `RFQSupplier`: Sourcing documents soliciting commercial bids with invited vendor tracking.
  - `SupplierQuotation` & `SupplierQuotationItem`: Supplier commercial bids with itemized unit prices, tax percentages, discounts, lead times, and validity dates.
  - `PurchaseOrder` & `PurchaseOrderItem`: Legally binding purchase orders with multi-warehouse line item delivery destinations, revision numbers, and receiving counters (`received_quantity`).
  - `PurchaseReturn` & `PurchaseReturnItem`: Vendor return documents executing physical stock reversals via `StockLedgerService` (`RETURN_OUT`).
  - `ProcurementReportSnapshot`: Periodic executive telemetry snapshots for procurement purchasing spend, open POs, and vendor metrics.
- **Pydantic DTO Schemas (`app/schemas/procurement.py`)**: Full validation suite for Suppliers, Categories, Contacts, Addresses, Requisitions, RFQs, Quotations, Orders, Returns, Reports, Analytics, Search, and Import/Export.
- **Repository Layer (`app/repositories/procurement_repos.py`)**: 13 async repositories implementing `BaseRepository` for all Procurement entities.
- **Domain Event Publisher (`app/core/domain_events.py`)**: Event bus emitting `SupplierCreated`, `PurchaseRequisitionSubmitted`, `RFQIssued`, `QuotationReceived`, `PurchaseOrderApproved`, `PurchaseOrderCancelled`, `GoodsReceived`, and `PurchaseReturned`.
- **Domain Services (`app/services/`)**:
  - `SupplierService` & `SupplierPerformanceService`: Supplier lifecycle management, blacklisting, rating aggregation, and spend recalculation.
  - `PurchaseRequisitionService`: PR creation, editing, approval engine integration, cancellation, and fulfillment tracking.
  - `RFQService`: RFQ management, supplier invitation, issuing, and dynamic Quotation Comparison Matrix generation.
  - `QuotationService`: Supplier bid calculation, tax & discount breakdown, validity tracking, and approval.
  - `PurchaseOrderService`: PO management, revision history, approval workflow integration, and seamless Goods Receipt integration via `GoodsReceiptService.create_receipt` and `WarehouseExecutionService.execute_goods_receipt`.
  - `PurchaseReturnService`: Vendor return creation and stock reversal execution via `StockLedgerService.create_ledger_entry` (`RETURN_OUT`).
  - `ProcurementReportService` & `ProcurementAnalyticsService`: Purchase Register, Supplier Ledger, Executive Dashboard KPIs with Redis caching, and snapshotting.
  - `ProcurementSearchService`: Unified multi-field search across Suppliers, POs, RFQs, Quotations, and PRs.
  - `ProcurementImportExportService`: Streaming CSV export and bulk CSV import engine.
- **Background Celery Tasks (`app/tasks/procurement_tasks.py`)**: Scheduled tasks `calculate_supplier_performance_task`, `refresh_procurement_analytics_task`, and `check_expiring_quotations_task`.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded 20+ permissions across `procurement.supplier.*`, `procurement.requisition.*`, `procurement.rfq.*`, `procurement.quotation.*`, `procurement.purchase_order.*`, `procurement.purchase_return.*`, `procurement.analytics.*`, `procurement.reports.*`, `procurement.import_export.*`, and added the `Procurement Manager` role.
- **REST API Routers (`app/api/v1/endpoints/`)**: 10 API routers registered in `app/api/v1/api.py`.
- **Database Migration (`alembic/versions/e7f8a91b2c3d_phase_v070_procurement_domain_completion.py`)**: Alembic migration creating 17 new procurement tables and indexes.
- **Architecture Decision Record (`docs/adr/ADR-0026-procurement-domain.md`)**: ADR covering procurement domain architecture, Goods Receipt integration, vendor return stock reversals, event-driven integration, and finance decoupling.

## [v0.6.3] - 2026-08-03


### Milestone Inventory Domain Completion — Advanced Enterprise Capabilities

#### Added
- **Advanced Inventory Database Models (`app/models/`)**:
  - `Batch`: Manufacturing/expiry dates, supplier refs, status (`Active`, `Expired`, `Consumed`), and current quantity.
  - `SerialNumber`: Globally unique serial numbers with warehouse/location assignments and state transition history log (`Available`, `Reserved`, `Sold`, `Returned`, `Scrapped`).
  - `Lot`: Production and supplier lot tracking with extended lineage and QA metadata.
  - `StockReservation`: Stock reservation entity for Sales/Manufacturing/Procurement/Internal demand without modifying physical stock.
  - `CycleCount` & `CycleCountItem`: Physical stock count audit document with variance calculation and automatic adjustment generation.
  - `InventoryAnalyticsSnapshot`: Valuation, turnover ratio, warehouse utilization, and stock breakdown snapshots.
- **Pydantic DTO Schemas (`app/schemas/inventory_advanced.py`)**: DTOs for Batches, Serials, Lots, Reservations, Cycle Counts, Reports, Analytics, Search, and Import/Export.
- **Repository Layer (`app/repositories/inventory_advanced_repos.py`)**: Repositories for Batch, SerialNumber, Lot, StockReservation, CycleCount, and InventoryAnalytics.
- **Domain Event Publisher (`app/core/domain_events.py`)**: Event bus emitting `StockReceived`, `StockIssued`, `StockTransferred`, `StockReserved`, `BatchExpired`, `InventoryAdjusted`, and `StockCountCompleted`.
- **Domain Services (`app/services/`)**:
  - `BatchService`: Batch tracking, expiration scanning, and FEFO/FIFO batch allocation logic.
  - `SerialNumberService`: Unique serial tracking and lifecycle state transitions.
  - `LotService`: Production/supplier lot management and lineage search.
  - `StockReservationService`: Stock reservation engine reducing available quantity without modifying stock ledger.
  - `CycleCountService`: Physical inventory audit workflow; auto-generates and applies stock adjustments for non-zero variance items.
  - `InventoryReportService`: Stock Valuation Report, Inventory Aging Report (0-30, 31-60, 61-90, 90+ days), and Movement Analysis Report (Fast, Slow, Dead Stock).
  - `InventoryAnalyticsService`: Executive Dashboard KPIs with Redis caching and snapshotting.
  - `InventorySearchService`: Unified multi-field global search across SKUs, Barcodes, Batches, Serials, Lots, Warehouses, and Locations.
  - `InventoryImportExportService`: Streaming CSV export and bulk CSV import engine.
- **Background Celery Tasks (`app/tasks/inventory_advanced_tasks.py`)**: Scheduled tasks `scan_batch_expiries_task`, `cleanup_expired_reservations_task`, and `refresh_inventory_analytics_task`.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded 18 new permissions across `inventory.batch.*`, `inventory.serial.*`, `inventory.lot.*`, `inventory.reservation.*`, `inventory.cycle_count.*`, `inventory.reports.*`, `inventory.analytics.*`, `inventory.import_export.*`.
- **REST API Routers (`app/api/v1/endpoints/`)**: 9 API routers registered in `app/api/v1/api.py`.
- **Database Migration (`alembic/versions/d9e3f12a4b56_phase_v063_inventory_domain_completion.py`)**: Alembic migration creating `batches`, `serial_numbers`, `lots`, `stock_reservations`, `cycle_counts`, `cycle_count_items`, and `inventory_analytics_snapshots` tables and indexes.
- **Architecture Decision Record (`docs/adr/ADR-0026-inventory-domain-completion.md`)**: ADR covering batch allocation strategies, serial lifecycle tracking, stock reservation guarantees, cycle count adjustments, executive reporting, and domain events.
- **Automated Test Suite (`tests/test_advanced_inventory.py`)**: 7 comprehensive test cases verifying 100% of the advanced inventory domain.

## [v0.6.2] - 2026-07-31


### Milestone Warehouse Operations Engine — Independent Execution Documents

#### Added
- **Warehouse Operations ORM Entities (`app/models/`)**: Created 6 models across 3 independent document modules:
  - `GoodsReceipt` & `GoodsReceiptItem`: Incoming physical inventory receiving document supporting 3-stage lifecycle (`Draft` -> `Approved` -> `Received` | `Cancelled`). Executing a receipt generates immutable `StockLedger` IN entries with transaction type `PURCHASE_RECEIPT`.
  - `GoodsIssue` & `GoodsIssueItem`: Outgoing physical inventory document supporting 3-stage lifecycle (`Draft` -> `Approved` -> `Issued` | `Cancelled`). Executing an issue validates negative stock rules against `Product.allow_negative_stock` and generates `StockLedger` OUT entries (`SALES_ISSUE` or `PRODUCTION_CONSUMPTION`).
  - `StockTransfer` & `StockTransferItem`: Warehouse stock transfer document supporting 4-stage lifecycle (`Draft` -> `Approved` -> `In Transit` [Dispatch OUT] -> `Completed` [Receive IN] | `Cancelled`). Preserves total system inventory quantity across warehouses and storage locations.
- **Pydantic v2 DTO Schemas (`app/schemas/warehouse_operations.py`)**: Request/Response schemas for Goods Receipts, Goods Issues, and Stock Transfers.
- **Repository Layer (`app/repositories/warehouse_operations_repos.py`)**: `GoodsReceiptRepository`, `GoodsIssueRepository`, and `StockTransferRepository` providing status filtering, date range queries, pagination, search, and document number uniqueness validation.
- **Domain Services (`app/services/warehouse_operations_services.py`)**:
  - `WarehouseExecutionService`: High-level execution orchestrator integrating directly with `StockLedgerService.create_ledger_entry`.
  - `GoodsReceiptService`: Receipt CRUD, approval, receipt execution, and cancellation.
  - `GoodsIssueService`: Issue CRUD, approval, negative stock limits validation, issue execution, and cancellation.
  - `StockTransferService`: Transfer CRUD, approval, source warehouse dispatch (`In Transit`), destination warehouse completion (`Completed`), and cancellation. Validates that source warehouse and location are not identical to destination (`source_warehouse_id != destination_warehouse_id`).
- **Background Celery Tasks (`app/tasks/warehouse_operations_tasks.py`)**: `send_warehouse_notification_task` broadcasting alerts to Receiving, Dispatch, and Inventory Management teams on document status changes.
- **RBAC Permissions (`app/db/seed_rbac.py`)**: Seeded 19 permissions (`inventory.receipt.*`, `inventory.issue.*`, `inventory.transfer.*`, `inventory.execute.warehouse`) mapped to `Super Admin` and `Inventory Manager` roles.
- **REST API Routers (`app/api/v1/endpoints/`)**: 3 API routers (`goods_receipt.py`, `goods_issue.py`, `stock_transfer.py`) registered under `/api/v1/inventory/`.
- **Database Migration (`alembic/versions/b8b2e8a866c5_phase_v062_implement_warehouse_.py`)**: Alembic migration creating `goods_receipts`, `goods_receipt_items`, `goods_issues`, `goods_issue_items`, `stock_transfers`, `stock_transfer_items` tables and indexes.
- **Architecture Decision Record (`docs/adr/ADR-0025-warehouse-operations.md`)**: Architectural details on standalone warehouse execution lifecycle, stock ledger integration, document immutability, and validation rules.
- **Automated Test Suite (`tests/test_warehouse_operations.py`)**: 5 comprehensive tests covering Goods Receipt lifecycle, Goods Issue lifecycle & negative stock validation, Stock Transfer dispatch/completion & quantity preservation, document cancellation zero-ledger guarantee, and REST API endpoints.

---

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
