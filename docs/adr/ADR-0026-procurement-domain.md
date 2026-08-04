# ADR-0026: Procurement Domain Architecture & Decoupled Inventory Operations

## Status
Accepted

## Date
2026-08-04

## Context
Milestone `v0.7.0` introduces the complete Procurement Domain for ApnaERP.
Procurement manages the entire purchasing lifecycle: Supplier Master Management, Purchase Requisitions (PR), Requests For Quotations (RFQ), Supplier Bids/Quotations, Purchase Orders (PO), and Purchase Returns.

Key requirements:
1. Physical receiving of PO items must seamlessly integrate with existing Inventory & Warehouse Operations (`GoodsReceiptService` & `WarehouseExecutionService`) without duplicating receiving or stock ledger logic.
2. Stock returns to vendors must execute stock reversals via `StockLedgerService` with direction `OUT` and transaction code `RETURN_OUT`.
3. Procurement must remain independent from Finance/Accounts Payable. Financial posting payload models are designed to consume procurement events asynchronously without requiring schema changes.
4. Integrate with the enterprise Approval Engine (`ApprovalEngineService`) for PRs and POs.

## Decision
1. **Model Architecture**:
   - Implemented 16 ORM models across 7 sub-modules: `SupplierCategory`, `Supplier`, `SupplierContact`, `SupplierAddress`, `SupplierDocument`, `SupplierRating`, `PurchaseRequisition`, `PurchaseRequisitionItem`, `RFQ`, `RFQSupplier`, `SupplierQuotation`, `SupplierQuotationItem`, `PurchaseOrder`, `PurchaseOrderItem`, `PurchaseReturn`, `PurchaseReturnItem`, and `ProcurementReportSnapshot`.

2. **Goods Receipt Integration**:
   - `PurchaseOrderService.receive_goods` directly invokes `GoodsReceiptService.create_receipt` and `WarehouseExecutionService.execute_goods_receipt`.
   - Generates immutable `StockLedger` IN entries (`PURCHASE_RECEIPT`) and updates PO line item counters (`received_quantity`) and status (`Partially Received` or `Fully Received`).

3. **Vendor Return Stock Reversal**:
   - `PurchaseReturnService.process_return` executes stock reversal via `StockLedgerService.create_ledger_entry` with direction `OUT` (`RETURN_OUT`), updating PO `returned_quantity` and warehouse inventory balances.

4. **Event-Driven Integration**:
   - Broadcasts domain events (`SupplierCreated`, `PurchaseRequisitionSubmitted`, `RFQIssued`, `QuotationReceived`, `PurchaseOrderApproved`, `PurchaseOrderCancelled`, `GoodsReceived`, `PurchaseReturned`) for downstream event consumers.

5. **Caching & Telemetry**:
   - Invalidates Redis caches on status mutations and caches executive dashboard summary telemetry.

## Consequences
- **Positive**: Complete purchasing lifecycle with tight inventory control, zero code duplication, zero coupling with unbuilt finance modules, full audit logging, and RBAC authorization.
- **Negative**: Additional migration overhead managed via Alembic `e7f8a91b2c3d`.
