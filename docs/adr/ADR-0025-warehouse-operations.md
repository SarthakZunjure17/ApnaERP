# ADR-0025: Warehouse Operations Layer & Stock Engine Integration

## Status
Accepted

## Context
In ApnaERP milestone `v0.6.2 — Warehouse Operations`, we introduce the business operational workflows for warehouse transactions:
1. **Goods Receipt**: Inbound stock receipt into a warehouse and storage location.
2. **Goods Issue**: Outbound stock issue/consumption from a warehouse and storage location.
3. **Stock Transfer**: Movement of physical stock from a source warehouse/location to a destination warehouse/location.

A critical architectural challenge in enterprise ERP systems is preventing business documents from bypassing the authoritative inventory engine, ensuring cross-line and cross-warehouse transaction atomicity, and eliminating database deadlocks during concurrent multi-warehouse transfers.

## Decisions

### 1. Business Documents Do Not Modify StockBalance Directly
Business document entities (`GoodsReceipt`, `GoodsIssue`, `StockTransfer`) and their services (`GoodsReceiptService`, `GoodsIssueService`, `StockTransferService`) MUST NOT execute direct mutations on `StockBalance` (such as `balance.available_quantity += quantity`). `StockBalance` and `StockLedger` are strictly owned and managed by the v0.6.1 stock quantity engine.

### 2. StockMovementService as the Single Authoritative Mutation Engine
All physical inventory mutations MUST delegate to `StockMovementService`:
- `GoodsReceipt` posting $\rightarrow$ `StockMovementService.stock_in()`
- `GoodsIssue` posting $\rightarrow$ `StockMovementService.stock_out()`
- `StockTransfer` posting $\rightarrow$ `StockMovementService.stock_out()` (source) + `StockMovementService.stock_in()` (destination)

`StockMovementService` is solely responsible for:
- Pessimistic row locking on `StockBalance`
- Evaluating negative-stock policies (`allow_negative_stock`)
- Recording immutable `StockLedger` audit rows with before/after quantities
- Atomic updates to `StockBalance`

### 3. Multi-Line Transactional Posting and Atomic Rollback
Posting any warehouse operation is an atomic database transaction (`commit=False` per movement step until all lines succeed):
- If any line item in a multi-line document fails (e.g., line 1 succeeds but line 2 fails due to insufficient stock), the entire PostgreSQL transaction is rolled back.
- No partial ledger entries remain, `StockBalance` remains completely unchanged, and the document stays unposted in `Draft`.

### 4. Deadlock-Free Deterministic Lock Ordering in Stock Transfers
Inter-warehouse and intra-warehouse transfers acquire row locks on multiple `StockBalance` records across source and destination locations. To prevent database deadlocks caused by concurrent opposing transfers (e.g., WH1 $\rightarrow$ WH2 vs WH2 $\rightarrow$ WH1), `StockTransferService` deterministically sorts all required `(product_id, warehouse_id, storage_location_id)` balance keys lexicographically before acquiring row locks in ascending order. This establishes a strict global lock hierarchy and eliminates circular wait conditions.

### 5. Decoupled Master Data, Procurement, and Sales Boundaries
- Master data entities (`Product`, `Warehouse`, `StorageLocation`) are reused canonically; no duplicate master entities are created.
- In v0.6.2, Goods Receipt and Goods Issue provide generic `reference_type` and `reference_id` fields. Direct automatic conversion from Purchase Orders (`PO -> GoodsReceipt`) or Sales Orders (`SO -> GoodsIssue`) is deliberately deferred to avoid premature coupling between inventory and trade domains.

### 6. Deferral of Batch, Serial, Expiry, and Reservation Logic
- Batch management, lot tracking, serial numbers, expiration dates (FEFO), ATP (Available-to-Promise), and stock reservations are deferred to `v0.6.3 — Advanced Inventory`.
- Financial valuation (FIFO/LIFO/Weighted Average) and General Ledger journal postings belong to downstream Finance milestones.

### 7. Document Immutability & Idempotency
- Once a document transitions to `Posted` (or legacy terminal states `Received`, `Issued`, `Completed`), it becomes strictly immutable. Updates and deletions on posted documents are prohibited.
- Duplicate posting attempts are rejected immediately by state-machine verification, ensuring stock cannot be double-counted.

## Consequences

### Positive
- **Guaranteed Consistency**: No divergence between `StockBalance` and `StockLedger`.
- **Zero Deadlocks**: Transfer concurrency is mathematically protected through deterministic lock ordering.
- **Auditability**: Every warehouse movement is tied to an immutable `StockLedger` entry and logged in `AuditLog`.
- **Clean Extensibility**: Clean separation enables v0.6.3 Advanced Inventory to add lot/batch tracking without rewriting core warehouse operation contracts.

### Negative / Trade-offs
- Two-phase transfers require holding locks across source and destination within the posting transaction. Deterministic sorting mitigates contention.
