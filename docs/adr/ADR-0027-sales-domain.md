# ADR-0027: Sales Domain Architecture & Decoupled Inventory Operations

## Status
Accepted

## Date
2026-08-05

## Context
Milestone `v0.8.0` completes the entire Sales Domain for ApnaERP.
Sales manages the end-to-end sales lifecycle: Customer Master Management, Price Lists & Discount Engine, Sales Quotations, Sales Orders, Delivery Orders (Shipments), Sales Returns, Sales Analytics, and Invoice Payload Generation for downstream Finance consumption.

Key architectural requirements:
1. **Inventory Integration**: Sales must integrate with Inventory/Warehouse Operations via `GoodsIssueService` for physical stock dispatch and `GoodsReceiptService` for return stock reversal. Sales must NEVER manipulate stock ledgers directly.
2. **Finance Decoupling**: Sales exposes comprehensive `SalesInvoicePayload` data models for future Finance / Accounts Receivable. Sales must NOT create accounting entries.
3. **Credit Management**: Credit limit checks are evaluated prior to Sales Order approval to prevent over-extension.
4. **Approval Engine**: Sales Quotations and Sales Orders integrate with `ApprovalEngineService` for multi-level authorization workflows.

## Decision
1. **Model Architecture**:
   - Implemented 18 ORM models across 8 sub-modules: `CustomerCategory`, `Customer`, `CustomerContact`, `CustomerAddress`, `CustomerDocument`, `PriceList`, `PricingRule`, `DiscountRule`, `SalesQuotation`, `SalesQuotationItem`, `SalesOrder`, `SalesOrderItem`, `DeliveryOrder`, `DeliveryOrderItem`, `SalesReturn`, `SalesReturnItem`, and `SalesReportSnapshot`.

2. **Decoupled Warehouse Execution**:
   - `DeliveryService.create_delivery` invokes `GoodsIssueService` (`create_issue`, `approve_issue`, `issue_issue`) to execute physical inventory deduction via `StockLedgerService` with direction `OUT` (`SALES_ISSUE`).
   - `SalesReturnService.approve_return` invokes `GoodsReceiptService` (`create_receipt`, `approve_receipt`, `receive_receipt`) to execute physical inventory addition via `StockLedgerService` with direction `IN` (`SALES_RETURN`).

3. **Invoice Payload Engine**:
   - `InvoicePayloadService.generate_invoice_payload` builds structured, ready-to-post payload contracts containing line item breakdowns, tax computations, discount applications, and customer tax identifiers for future Finance ingestion.

4. **Analytics & Global Search**:
   - `SalesAnalyticsService` and `SalesReportService` provide executive performance summaries, revenue metrics, sales registers, customer ledgers, and snapshot generation.
   - `SalesSearchService` provides unified global search across Customers, Quotations, Orders, Deliveries, and Products.

## Consequences
- **Positive**: Complete order-to-cash sales domain with strict physical inventory decoupling, zero accounting module dependencies, comprehensive audit trail, Redis cache invalidation, and 100% test coverage.
- **Negative**: Database migration overhead managed via Alembic revision `f8a9b0c1d2e3`.
