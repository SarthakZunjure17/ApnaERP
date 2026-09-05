# ADR-0026: Advanced Inventory Tracking & Stock Reservations

## Status
Accepted

## Context
In ApnaERP milestone `v0.6.3 — Advanced Inventory`, we introduce enterprise tracking dimensions and allocation capabilities:
1. **Batch / Lot Management**: Tracking product lots with manufacturing dates, expiration dates, supplier references, and current quantities.
2. **Serial Number Management**: Individual item unit tracking with strict 1-to-1 quantity validation and lifecycle state management (`Available`, `Reserved`, `Issued`, `Returned`, `Scrapped`, `Lost`).
3. **Expiry Tracking & Policy Validation**: Enforcing expiry date constraints on stock movements to prevent issuing expired inventory.
4. **Stock Reservations**: Logical stock allocations against physical on-hand inventory to prevent oversubscription while ensuring transactional concurrency.

A core architectural challenge is ensuring these capabilities seamlessly extend the v0.6.1 authoritative stock engine and v0.6.2 warehouse execution flows without creating a competing stock engine or modifying physical on-hand inventory during reservation lifecycle events.

## Decisions

### 1. Unified Stock Engine Invariant
All physical stock mutations MUST continue to execute exclusively through `StockMovementService` (`stock_in()` and `stock_out()`). No advanced inventory service may directly mutate `StockBalance.available_quantity` or create rogue ledger rows.

### 2. Normalized Tracking Dimensions
- `Batch` belongs to exactly one `Product`. Batch numbers are unique per product/system scope.
- `SerialNumber` represents a single individually identifiable physical unit. Serial numbers are globally unique and carry an immutable chronological audit trail in JSONB `history`.
- `StockLedger` is extended with nullable `batch_id` and `serial_numbers` metadata for full historical movement traceability.

### 3. Separation of Physical Stock vs. Logical Reservations
- **Physical On-Hand Inventory** is strictly tracked by `StockBalance.quantity_on_hand` and proven by `StockLedger`.
- **Reservations** are logical allocations represented by `StockReservation` with states (`Active`, `Released`, `Consumed`, `Expired`, `Cancelled`).
- Reservation creation and release NEVER create `StockLedger` entries and do not mutate `quantity_on_hand`.
- Available-to-promise inventory is derived as:
  $$\text{Available} = \text{quantity\_on\_hand} - \text{reserved\_quantity}$$

### 4. Authoritative PostgreSQL Concurrency Control
- Stock reservations use pessimistic row-level locking (`SELECT ... FOR UPDATE` via `StockBalanceRepository.get_or_create_for_update`) to prevent race conditions and over-reservation.
- Concurrency correctness relies on database transactions and row locks, NOT process-local locks, Redis locks, or asynchronous Celery workers.

### 5. Atomic Reservation Consumption on Stock Issue
When a Goods Issue note consumes a reservation:
1. The reservation is validated for active status and sufficient unconsumed quantity.
2. `StockMovementService.stock_out()` executes the physical inventory reduction and creates the `StockLedger` record.
3. The reservation is reduced or marked `Consumed` in the same atomic database transaction.
4. If any step fails, the entire transaction rolls back cleanly.

### 6. Strict Tracking Validation in Warehouse Operations
- **Goods Receipt**: Batch creation/linkage is required for batch-tracked items; serial numbers matching exact quantity are required for serial-tracked items.
- **Goods Issue**: Validates batch availability, enforces expiry date restrictions, and ensures serialized units are currently `Available` and located at the source warehouse.
- **Stock Transfer**: Moves batch and serial identities across source and destination while preserving deterministic lock ordering across all affected balances.

## Consequences

### Positive
- **Complete Traceability**: Every unit or batch movement is immutably recorded in `StockLedger`.
- **Zero Race Conditions**: PostgreSQL row-level locks prevent over-reservation under high concurrency.
- **Strict Backward Compatibility**: Non-tracked items (`tracking_type = "NONE"`) continue to operate with standard decimal quantity semantics without overhead.
- **Clean Domain Boundaries**: Procurement and Sales remain decoupled from inventory internals; downstream modules interact via standard reference IDs.

### Negative / Trade-offs
- Serial tracking requires serial number validation per individual unit during warehouse execution.
- Complex warehouse transfers with multi-item tracking require acquiring row locks in strict ascending key order.
