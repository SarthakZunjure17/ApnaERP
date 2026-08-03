# ADR-0026: Inventory Domain Completion Architecture (Batch, Serial, Lot, Stock Reservation, Cycle Count)

## Status
Accepted

## Context
Milestone `v0.6.3` completes the entire Enterprise Inventory Domain within ApnaERP.
Enterprise operations require tracking individual product instances (Serial Numbers), groups of manufactured/purchased stock (Batches & Lots), enforcing stock reservations for pending demand without altering physical inventory, performing physical audit counts with automatic ledger adjustments (Cycle Counts), generating executive reports/analytics, and supporting bulk CSV import/export.

## Decision
1. **Batch & Lot Management (`Batch`, `Lot`)**:
   - Model `Batch` with manufacturing and expiration dates, supplier references, and active/expired/consumed status.
   - Implement FEFO (First-Expired, First-Out) and FIFO allocation strategies.
   - Background Celery task `scan_batch_expiries_task` daily marks expired batches and emits `BatchExpired` domain events.

2. **Serial Number Tracking (`SerialNumber`)**:
   - Model `SerialNumber` with globally unique constraints (`serial_number`).
   - Maintain JSONB `history` for lifecycle state transitions (`Available`, `Reserved`, `Sold`, `Returned`, `Scrapped`).

3. **Stock Reservation Engine (`StockReservation`)**:
   - Reservations guarantee stock for downstream demand (Sales/Manufacturing/Procurement/Internal) without modifying physical `StockLedger`.
   - Update read-optimized `StockBalance.available_quantity` calculation (`available_qty = total_qty - reserved_qty`).
   - Invalidate Redis caches on creation/cancellation. Automatic cleanup of expired reservations via Celery task `cleanup_expired_reservations_task`.

4. **Cycle Count Audit (`CycleCount`, `CycleCountItem`)**:
   - Store physical audit counts and system balances.
   - Approval of `CycleCount` with non-zero variance automatically generates and applies immutable `StockLedger` entries with direction `ADJUSTMENT` via `InventoryAdjustmentService`.

5. **Reports, Analytics & Global Search**:
   - Real-time Stock Valuation Report, Inventory Aging Report (0-30, 31-60, 61-90, 90+ days), and Movement Analysis Report (Fast, Slow, Dead Stock).
   - Redis-cached Executive Dashboard Analytics with daily background snapshot task.
   - Global Search API searching SKUs, Barcodes, Batches, Serials, Lots, Warehouses, and Locations.

6. **Import/Export Engine & Domain Events**:
   - Support streaming CSV export and batch CSV import.
   - Emits structured domain events (`StockReceived`, `StockIssued`, `StockTransferred`, `StockReserved`, `BatchExpired`, `InventoryAdjusted`, `StockCountCompleted`).

## Consequences
- The Inventory Domain is 100% complete and fully integrated with existing Stock Ledger, RBAC, Celery, and Redis infrastructure.
- Zero direct stock mutation rule is strictly preserved.
