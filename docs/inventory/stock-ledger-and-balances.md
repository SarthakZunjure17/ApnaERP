# Stock Ledger & Authoritative Stock Balances (v0.6.1)

## Executive Summary

Milestone **v0.6.1** establishes the canonical, immutable, and concurrency-safe inventory quantity engine for ApnaERP.

The core architectural invariant is:
```
    STOCK LEDGER (Immutable historical transaction stream)
          ↓
    STOCK BALANCE (Authoritative current physical state projection)
          ↓
    AUTHORITATIVE CURRENT STOCK (quantity_on_hand)
```

There is strictly **one authoritative source of current inventory quantity** in the entire ERP: `StockBalance.quantity_on_hand` at the `Product + Warehouse + StorageLocation` grain.

---

## Architecture & Data Model

### 1. StockBalance (Authoritative State)
- **Table**: `stock_balances`
- **Grain**: Exactly one row per `(product_id, warehouse_id, storage_location_id)` enforced via database constraint `UNIQUE(product_id, warehouse_id, storage_location_id)`.
- **Primary Column**: `available_quantity` (aliased natively to `quantity_on_hand`).
- **Configuration Boundary**: `ProductWarehouse` master data remains configuration only (`reorder_level`, `safety_stock`, `preferred_location_id`, etc.) and does NOT hold live inventory counts.

### 2. StockLedger (Immutable Transaction Log)
- **Table**: `stock_ledgers`
- **Immutability**: Append-only log. Records cannot be updated (`PUT`) or deleted (`DELETE`) through normal application APIs.
- **Fields**:
  - `id`: UUID Primary Key
  - `product_id`: UUID (FK -> `products.id`, RESTRICT)
  - `warehouse_id`: UUID (FK -> `warehouses.id`, RESTRICT)
  - `storage_location_id`: Optional UUID (FK -> `storage_locations.id`, SET NULL)
  - `movement_type`: `STOCK_IN`, `STOCK_OUT`, `ADJUSTMENT`
  - `direction`: `IN`, `OUT`
  - `quantity`: Positive magnitude (`Numeric(18, 4)` > 0)
  - `quantity_before`: Balance quantity immediately prior to transaction (under row lock)
  - `quantity_after`: Balance quantity immediately after transaction (under row lock)
  - `running_balance`: Warehouse-level running total after transaction
  - `idempotency_key`: Optional unique client/service key (`String(255)`)
  - `reference_type`: Upstream document identifier (`ManualMovement`, `OpeningStock`, `InventoryAdjustment`, etc.)
  - `reference_id`: Upstream document UUID
  - `reason`: Business justification
  - `notes`: Descriptive notes
  - `metadata_json`: Extensible JSON metadata
  - `transaction_date`: Effective UTC timestamp
  - `created_by`: User UUID

---

## Concurrency Control & Atomicity

### Row-Level Locking
All stock movements acquire a row-level lock on the target `StockBalance` row using PostgreSQL `SELECT ... FOR UPDATE` (`with_for_update()`) and in-process synchronization.

```python
balance = await stock_balance_repository.get_or_create_for_update(
    db, product_id=product_id, warehouse_id=warehouse_id, storage_location_id=storage_location_id
)
```

### Atomic Transaction Boundary
The `StockBalance` quantity update and `StockLedger` insert occur strictly within the **same database transaction**:
```
BEGIN TRANSACTION
  1. Lock StockBalance row
  2. Validate Product (stockable, active) & Location
  3. Compute quantity_before & quantity_after
  4. Enforce Negative Stock Policy
  5. Update StockBalance.available_quantity
  6. Insert immutable StockLedger record
  7. Commit / Rollback (Atomic)
END TRANSACTION
```

If any constraint or business rule fails, the entire transaction is rolled back.

---

## Negative Stock Policy Hierarchy

When a transaction would result in `quantity_on_hand < 0`, the engine resolves policies in the following strict canonical order:

1. **Warehouse Policy**: Checks `InventoryPolicy` where `warehouse_id == target_warehouse_id` and `is_active == True`.
2. **Global Policy**: If no warehouse policy is active, checks global `InventoryPolicy` where `warehouse_id IS NULL` and `is_active == True`.
3. **Product Default**: Fallback to `Product.allow_negative_stock`.

If negative stock is disallowed, the engine raises `ValidationException` (HTTP 400), rejecting the movement and preserving the balance.

---

## Idempotency Mechanism

Every stock movement can accept an `idempotency_key`.
- If an existing `StockLedger` entry with the same `idempotency_key` is found in the database, the engine returns the existing record immediately.
- No second balance deduction or duplicate ledger entry is executed.

---

## REST API Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| `POST` | `/api/v1/stock/movements` | `inventory.stock.movement.create` | Execute atomic movement (`STOCK_IN`, `STOCK_OUT`, `ADJUSTMENT`) |
| `GET` | `/api/v1/stock/movements` | `inventory.stock.read` | List historical stock movements with multi-column filtering |
| `GET` | `/api/v1/stock/ledger` | `inventory.ledger.read` | Paginated immutable stock ledger entries |
| `GET` | `/api/v1/stock/ledger/{id}` | `inventory.ledger.read` | Retrieve single stock ledger entry |
| `GET` | `/api/v1/stock/balances` | `inventory.balance.read` | Filtered stock balance list |
| `GET` | `/api/v1/stock/balances/{id}` | `inventory.balance.read` | Retrieve single stock balance record |
| `GET` | `/api/v1/products/{product_id}/stock` | `inventory.product.read` | Live stock summary across all warehouses for a product |
| `GET` | `/api/v1/warehouses/{warehouse_id}/stock` | `inventory.warehouse.read` | Live stock summary across all products in a warehouse |
| `GET` | `/api/v1/storage-locations/{location_id}/stock` | `inventory.location.read` | Live stock balances within a storage location |
| `POST` | `/api/v1/stock/balances/recalculate` | `inventory.balance.read` | Recalculate balance projection from historical ledger |

---

## RBAC Permissions

- `inventory.stock.read`: View stock summaries, movements, and query endpoints.
- `inventory.stock.movement.create`: Execute stock IN, OUT, and Adjustment movements.
- `inventory.ledger.read`: Read immutable StockLedger logs.
- `inventory.balance.read`: Read StockBalance projections.
