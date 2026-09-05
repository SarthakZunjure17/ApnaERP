# ADR-0024: Stock Ledger & Authoritative Stock Balances Architecture

## Status
Approved

## Date
2026-09-05

## Context
In enterprise ERP systems, inventory quantity integrity is paramount. Physical stock transactions must be completely auditable, strictly concurrency-safe, idempotent, and resilient against race conditions or data loss. A naive approach of directly incrementing or decrementing stock fields on master data models (e.g. `Product` or `Warehouse`) creates severe race conditions, loses historical context, and violates accounting audit standards.

## Decision Drivers & Core Architectural Choices

### 1. Why `StockLedger` is Append-Only & Immutable
Every physical stock change is recorded as an immutable, append-only `StockLedger` entry.
- Direct `UPDATE` or `DELETE` operations on `StockLedger` records are strictly forbidden.
- Corrections in physical stock are executed via future adjusting movements (`ADJUSTMENT` with `IN` or `OUT`), ensuring a transparent, unalterable historical audit trail.

### 2. Why `StockBalance` is the Authoritative Current Quantity
While `StockLedger` stores the immutable transaction stream, reading current stock by summing millions of historical rows on every API request is inefficient.
- `StockBalance.quantity_on_hand` (mapped to `available_quantity`) is the single authoritative state for physical inventory.
- `ProductWarehouse` remains configuration-only (`reorder_level`, `safety_stock`, etc.) and does not hold live stock quantities.
- `StockBalance` updates are executed in the exact same database transaction as the ledger record insertion.

### 3. Why Quantity is Stored at `Product + Warehouse + StorageLocation` Grain
Physical goods occupy distinct physical spaces (Warehouse facilities, and optional sub-locations such as Aisle/Rack/Shelf/Bin).
- The canonical database grain is enforced via `UNIQUE(product_id, warehouse_id, storage_location_id)` on `StockBalance`.
- Higher-level aggregations (Warehouse totals, Product enterprise totals) are dynamically derived from this fine-grained balance.

### 4. Why PostgreSQL Controls Transactional Consistency
- All inventory mutations acquire row-level locks via PostgreSQL `SELECT ... FOR UPDATE` (`with_for_update()`).
- Database constraints (positive quantities, foreign keys with `RESTRICT`, unique idempotency keys, and unique balance grain) guarantee consistency at the engine layer regardless of client concurrency.

### 5. Why Redis is NOT Authoritative
- Redis is strictly an ephemeral read-through cache for dashboard summaries and metrics.
- Stock correctness, locking, and idempotency must never depend on Redis memory state or network availability.
- PostgreSQL ACID transactions are the single source of truth.

### 6. Why Future Workflows are Not Implemented in v0.6.1
- Workflows such as Goods Receipt (GRN), Goods Issue (GIN), Stock Transfers, Reservations, ATP, Allocation, Cycle Counting, and General Ledger posting belong to later roadmap milestones (v0.6.2+).
- Implementing them prematurely would introduce unnecessary coupling and violate the frozen architectural roadmap.

### 7. How Future Workflows Will Reference the Ledger
`StockLedger` provides extensible generic reference fields:
- `reference_type`: Upstream document type (e.g., `GoodsReceipt`, `SalesDelivery`, `StockTransfer`, `OpeningStock`, `InventoryAdjustment`).
- `reference_id`: Upstream document UUID.
- `idempotency_key`: Client/Workflow deduplication key.
- `metadata_json`: Custom workflow payload attributes.

This ensures future procurement, sales, and warehouse management milestones can seamlessly generate stock movements without schema changes to the core ledger engine.

## Consequences
- **Positive**: 100% concurrency-safe stock updates, zero race conditions, fully immutable audit trail, sub-millisecond stock balance queries, and a clean foundation for upcoming inventory workflows.
- **Negative**: Requires disk storage proportional to transaction volume, managed through PostgreSQL indexing and standard data lifecycle practices.
