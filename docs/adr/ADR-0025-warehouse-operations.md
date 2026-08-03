# ADR-0025: Warehouse Execution Operations Engine & Stock Ledger Integration

## Status
Accepted

## Context
In ApnaERP Release `v0.6.2`, physical inventory movement requires an independent execution module to record incoming goods (`GoodsReceipt`), outgoing inventory (`GoodsIssue`), and internal warehouse stock transfers (`StockTransfer`). These warehouse execution operations must function independently even when future Procurement, Purchasing, or Sales modules are not yet installed.

A critical design requirement is that warehouse operations must NEVER directly manipulate `StockBalance` tables or compute manual balance totals. Every inventory movement across warehouses and storage locations must generate immutable `StockLedger` entries through the central `StockLedgerService` to enforce auditability, traceability, and running balance integrity.

## Decision
1. **Document Entities & State Machines**:
   - **GoodsReceipt** (`Draft` -> `Approved` -> `Received` | `Cancelled`): Receiving creates `IN` ledger entries with transaction type `PURCHASE_RECEIPT`.
   - **GoodsIssue** (`Draft` -> `Approved` -> `Issued` | `Cancelled`): Issuing validates negative stock rules against `Product.allow_negative_stock` and creates `OUT` ledger entries (`SALES_ISSUE` or `PRODUCTION_CONSUMPTION`).
   - **StockTransfer** (`Draft` -> `Approved` -> `In Transit` [Dispatch] -> `Completed` [Receive] | `Cancelled`): Dispatching creates `TRANSFER_OUT` ledger entries from source warehouse. Completion creates `TRANSFER_IN` ledger entries into destination warehouse. Total system stock is strictly preserved.
2. **Stock Ledger Integration**:
   - All document execution methods invoke `StockLedgerService.create_ledger_entry`.
   - Document completion updates `StockBalance` projections through the stock engine.
3. **Immutability & Terminal States**:
   - Executed documents (`Received`, `Issued`, `Completed`, `Cancelled`) are immutable and read-only.
   - Cancelled documents generate zero ledger entries.
4. **Validation Rules**:
   - Source and destination warehouses must exist and be active.
   - For transfers, `source_warehouse_id != destination_warehouse_id` (or distinct locations if internal).
   - Storage locations must belong to the respective warehouse.
   - Only inventory-enabled, non-archived products can be included in warehouse documents.

## Consequences
- **Decoupled Architecture**: Warehouse execution operations run standalone and can be reused by future Procurement and Sales modules without modifying core stock ledger logic.
- **Data Integrity**: Stock balances remain derived and consistent with immutable ledger history.
- **Traceability**: Audit log events and background Celery telemetry notifications track all document lifecycle events.
