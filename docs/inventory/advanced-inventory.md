# Advanced Inventory Tracking & Stock Reservations (v0.6.3)

## 1. Overview & Architecture

Milestone `v0.6.3 — Advanced Inventory` extends the authoritative inventory engine (`v0.6.1` Stock Ledger & Stock Balances) and warehouse execution workflows (`v0.6.2` Warehouse Operations) with advanced tracking dimensions:
1. **Batch / Lot Management**: Full tracking of manufacturing batches, lot numbers, production dates, expiry dates, supplier references, and current batch quantities.
2. **Serial Number Tracking**: Individual unit identity tracking, 1-to-1 quantity validation, lifecycle status transitions (`Available`, `Reserved`, `Issued`, `Scrapped`, `Returned`), and complete chronological movement audit history.
3. **Expiry Tracking & Validation**: Configurable expiry date verification preventing physical stock-out of expired items while maintaining full traceability.
4. **Stock Reservations**: Logical stock allocations for upcoming demand (Sales, Manufacturing, Procurement, Internal) without directly creating `StockLedger` movements, reducing available-to-promise projections safely under PostgreSQL row-level locking.

### Authoritative Architecture Flow

```
+-------------------------------------------------------------------+
|                        Business Documents                         |
|  Goods Receipt / Goods Issue / Stock Transfer / Stock Reservation |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|               Advanced Tracking & Validation Layer                |
|  - Product tracking strategy enforcement (NONE / BATCH / SERIAL)  |
|  - Serial count vs item quantity equality validation              |
|  - Duplicate serial & active status verification                  |
|  - Batch expiry date policy validation                            |
|  - Reservation availability calculation under row locking         |
+-------------------------------------------------------------------+
                                  |
         +------------------------+------------------------+
         |                                                 |
         v (Physical Stock Movement)                       v (Logical Allocation)
+-----------------------------------+             +-----------------------------------+
|       StockMovementService        |             |      StockReservationService      |
|  - Pessimistic Row Lock on Bal    |             |  - Row Lock on StockBalance       |
|  - stock_in() / stock_out()       |             |  - Update reserved_quantity proj  |
|  - Batch & Serial Transition      |             |  - Zero StockLedger mutation      |
+-----------------------------------+             +-----------------------------------+
         |                                                 |
         +------------------------+------------------------+
                                  |
                                  v
+---------------------------------+---------------------------------+
|                                 |                                 |
v                                 v                                 v
+-----------------------+ +-----------------------+ +-----------------------+
|     StockBalance      | |      StockLedger      | |   StockReservation    |
| Authoritative Physical| |  Immutable Movement   | |  Logical Demand Lock  |
| on_hand & reserved    | |  Audit with Tracking  | |  (Active/Released/    |
| projections           | |  batch_id & serial_no | |   Consumed/Cancelled) |
+-----------------------+ +-----------------------+ +-----------------------+
```

---

## 2. Core Invariants & Rules

1. **No Competing Stock Engine**: v0.6.3 extends the existing stock balance and ledger architecture. All physical movements MUST flow through `StockMovementService`.
2. **Authoritative Stock Definitions**:
   - $\text{Physical On-Hand} = \text{StockBalance.quantity\_on\_hand}$ (authoritative physical inventory)
   - $\text{Active Reserved} = \sum \text{StockReservation.quantity}$ where $\text{status} = \text{'Active'}$
   - $\text{Available to Promise} = \text{quantity\_on\_hand} - \text{reserved\_quantity}$
3. **Reservations Do Not Create Ledger Records**: Creating, updating, or releasing a reservation NEVER generates `StockLedger` rows and does not mutate `quantity_on_hand`.
4. **Atomic Reservation Consumption**: When physical stock is issued against a reservation:
   - Reservation validity and available reserved quantity are verified.
   - `StockMovementService.stock_out()` executes physical movement and writes immutable `StockLedger` entry.
   - The reservation is consumed/reduced atomically in the same database transaction.
5. **Serial Quantity Invariance**: For serial-tracked products (`tracking_type = "SERIAL"`), the movement quantity MUST strictly equal the number of provided serial numbers ($1 \text{ serial} = 1.0 \text{ qty}$).
6. **Unique Active Identity**: Serial numbers are globally unique. A serial cannot be received twice without being previously issued or returned.
7. **Batch Expiry Restrictions**: Goods issue of expired batches is strictly prohibited by default.

---

## 3. Product Tracking Configuration

A `Product` defines its tracking strategy via:
- `tracking_type`: `"NONE"`, `"BATCH"`, or `"SERIAL"`
- Helper property flags: `is_batch_tracked`, `is_serial_tracked`

| Tracking Type | Batch Required | Serial Required | Quantity Semantics |
| :--- | :--- | :--- | :--- |
| `NONE` | No | No | Arbitrary decimal quantity |
| `BATCH` | Yes | No | Decimal quantity associated with specific batch |
| `SERIAL` | Optional | Yes | Integer quantity matching exact serial count |

---

## 4. API Endpoints

### Batches
- `POST /api/v1/inventory/batches` - Create a new batch
- `GET /api/v1/inventory/batches` - List batches (filtered by product, status, search)
- `GET /api/v1/inventory/batches/{id}` - Retrieve batch details
- `PUT /api/v1/inventory/batches/{id}` - Update batch metadata / expiry

### Serial Numbers
- `POST /api/v1/inventory/serial-numbers` - Register serial numbers
- `GET /api/v1/inventory/serial-numbers` - List serial numbers (filtered by product, warehouse, status)
- `GET /api/v1/inventory/serial-numbers/{id}` - Get serial number details and movement history

### Stock Reservations
- `POST /api/v1/inventory/stock-reservations` - Create stock reservation under row lock
- `GET /api/v1/inventory/stock-reservations` - List reservations (filtered by product, warehouse, status)
- `GET /api/v1/inventory/stock-reservations/{id}` - Get reservation details
- `POST /api/v1/inventory/stock-reservations/{id}/release` - Release active reservation
- `POST /api/v1/inventory/stock-reservations/{id}/consume` - Manually consume reservation
- `POST /api/v1/inventory/stock-reservations/{id}/cancel` - Cancel active reservation
