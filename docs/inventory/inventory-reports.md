# Inventory Reports & Analytics (v0.6.4)

## 1. Overview & Architecture

Milestone `v0.6.4 — Inventory Reports & Analytics` represents the **final milestone** in the ApnaERP Inventory domain. It establishes a high-performance, read-only reporting and analytics layer built on top of the authoritative inventory data foundation established across milestones `v0.6.0` through `v0.6.3`.

### Core Architectural Principle

Reporting sits strictly **above** the transactional inventory systems as a pure consumer:

```
Authoritative Master Data:
Product, ProductCategory, UnitOfMeasure, Warehouse, StorageLocation
                             │
                             ▼
Authoritative Operational Records:
StockBalance (Physical on_hand), StockLedger (Immutable movement history),
Batch, SerialNumber, StockReservation (Active logical demand allocations)
                             │
                             ▼
Read-Only Reporting Layer:
InventoryReportRepository (SQL aggregation, joins, filtering)
                             │
                             ▼
InventoryReportService (Pagination, summaries, CSV streaming export)
                             │
                             ▼
REST Endpoints & Executive Dashboards:
GET /api/v1/inventory/reports/*, GET /api/v1/inventory/analytics/*
```

### Strict Invariants & Architectural Guarantees

1. **Read-Only Invariant**: No report endpoint or reporting query may mutate physical stock, write ledger entries, or alter reservation, batch, or serial statuses.
2. **No Financial Valuation**: Financial costing (FIFO/LIFO layers, COGS, weighted average cost calculations, GL journal entries) is explicitly out of scope for the inventory domain and belongs to future finance milestones.
3. **Authoritative Consistency**: Reports execute PostgreSQL-level aggregations (`SUM`, `COUNT`, `GROUP BY`, `ORDER BY`) directly over authoritative operational tables without introducing redundant or out-of-sync caching tables.
4. **No Side-Effects**: Reports do not automatically generate Purchase Orders, Sales Orders, or replenishment tasks.

---

## 2. Business Definitions & Formulas

| Metric | Definition | Authoritative Source / Formula |
| :--- | :--- | :--- |
| **Physical On-Hand (`quantity_on_hand`)** | Total physical quantity of item physically present in warehouse/location. | `StockBalance.available_quantity` |
| **Reserved Quantity (`reserved_quantity`)** | Total quantity allocated to pending demand (e.g. Sales Orders, Transfers). | `StockBalance.reserved_quantity` or $\sum \text{StockReservation.quantity}$ (`status='Active'`) |
| **Available Stock (`available_quantity`)** | Free stock immediately available for new allocations. | $\max(0, \text{quantity\_on\_hand} - \text{reserved\_quantity})$ |
| **Low Stock (`below_reorder_level`)** | Flag indicating physical on-hand is below configured reorder threshold. | $\text{quantity\_on\_hand} \le \text{Product.reorder\_level}$ (when $\text{reorder\_level} > 0$) |
| **Below Minimum Stock (`below_minimum_stock`)** | Flag indicating physical on-hand is below minimum safety stock. | $\text{quantity\_on\_hand} < \text{Product.minimum\_stock}$ (when $\text{minimum\_stock} > 0$) |
| **Expired Batch** | Tracked batch whose expiry date has passed relative to UTC `now()`. | $\text{Batch.expiry\_date} < \text{UTC\_NOW()}$ |
| **Expiring Soon Batch** | Tracked batch whose expiry date falls within a future window (e.g. 30/60/90 days). | $\text{UTC\_NOW()} \le \text{Batch.expiry\_date} \le \text{UTC\_NOW()} + N\text{ days}$ |
| **Inbound Movement** | Stock receipt or positive ledger transaction. | `StockLedger.direction == 'IN'` |
| **Outbound Movement** | Stock issue or negative ledger transaction. | `StockLedger.direction == 'OUT'` |

---

## 3. Operational Reports Catalog

### 1. Current Stock Report
- **Endpoint**: `GET /api/v1/inventory/reports/stock`
- **CSV Export**: `GET /api/v1/inventory/reports/stock/export`
- **Description**: Real-time view of inventory across products, warehouses, and storage locations with on-hand, reserved, and available quantities.
- **Filters**: `product_id`, `warehouse_id`, `storage_location_id`, `category_id`, `tracking_type`, `active_only`, `search`, `page`, `size`.

### 2. Stock Movement Report
- **Endpoint**: `GET /api/v1/inventory/reports/movements`
- **CSV Export**: `GET /api/v1/inventory/reports/movements/export`
- **Description**: Comprehensive audit log of all physical movements derived from immutable `StockLedger` entries with before/after balances, reference links, batch IDs, and serial numbers.
- **Filters**: `product_id`, `warehouse_id`, `storage_location_id`, `movement_type`, `direction`, `batch_id`, `reference_type`, `date_from`, `date_to`, `search`, `page`, `size`.

### 3. Warehouse Inventory Report
- **Endpoint**: `GET /api/v1/inventory/reports/warehouses`
- **CSV Export**: `GET /api/v1/inventory/reports/warehouses/export`
- **Description**: Facility-level aggregation summarizing total stocked products, total storage locations, total on-hand, reserved, active batches, tracked serials, and low-stock count.
- **Filters**: `warehouse_id`, `is_active`, `search`, `page`, `size`.

### 4. Product Inventory Report
- **Endpoint**: `GET /api/v1/inventory/reports/products`
- **CSV Export**: `GET /api/v1/inventory/reports/products/export`
- **Description**: Product-centric summary of global stock distribution across warehouses, storage locations, active batches, serials, and recent movement velocity.
- **Filters**: `category_id`, `tracking_type`, `status`, `search`, `page`, `size`.

### 5. Batch & Expiry Report
- **Endpoint**: `GET /api/v1/inventory/reports/batches/expiry`
- **CSV Export**: `GET /api/v1/inventory/reports/batches/expiry/export`
- **Description**: Batch traceability tracking manufacturing dates, expiry dates, days until expiry, and status (`Active`, `Expired`, `Expiring Soon`).
- **Filters**: `product_id`, `warehouse_id`, `expiry_status` (`Active`, `Expired`, `Expiring Soon`), `expiring_within_days`, `date_from`, `date_to`, `search`, `page`, `size`.

### 6. Serial Inventory Report
- **Endpoint**: `GET /api/v1/inventory/reports/serials`
- **CSV Export**: `GET /api/v1/inventory/reports/serials/export`
- **Description**: Unit-level lifecycle tracking for serial-managed items displaying current warehouse/location, status (`Available`, `Reserved`, `Issued`, `Returned`, `Scrapped`, `Lost`), and associated batch.
- **Filters**: `product_id`, `warehouse_id`, `storage_location_id`, `batch_id`, `status`, `search`, `page`, `size`.

### 7. Stock Reservation Report
- **Endpoint**: `GET /api/v1/inventory/reports/reservations`
- **CSV Export**: `GET /api/v1/inventory/reports/reservations/export`
- **Description**: Read-only log of logical demand allocations with reservation numbers, linked document references (`SALES_ORDER`, `TRANSFER`), expiration timestamps, and status lifecycles (`Active`, `Released`, `Consumed`, `Cancelled`).
- **Filters**: `product_id`, `warehouse_id`, `storage_location_id`, `batch_id`, `status`, `reserved_for_type`, `date_from`, `date_to`, `search`, `page`, `size`.

### 8. Available Stock Report
- **Endpoint**: `GET /api/v1/inventory/reports/availability`
- **CSV Export**: `GET /api/v1/inventory/reports/availability/export`
- **Description**: Availability-oriented read model isolating immediately allocatable stock from locked reservations across warehouses and sub-locations.
- **Filters**: `product_id`, `warehouse_id`, `storage_location_id`, `category_id`, `tracking_type`, `search`, `page`, `size`.

### 9. Low Stock / Reorder Visibility Report
- **Endpoint**: `GET /api/v1/inventory/reports/low-stock`
- **CSV Export**: `GET /api/v1/inventory/reports/low-stock/export`
- **Description**: Identifies items breaching configured reorder levels and safety minimums, calculating precise shortages without triggering automated purchases.
- **Filters**: `warehouse_id`, `category_id`, `below_reorder_only`, `below_min_only`, `search`, `page`, `size`.

### 10. Inventory Aging Report
- **Endpoint**: `GET /api/v1/inventory/reports/aging`
- **CSV Export**: `GET /api/v1/inventory/reports/aging/export`
- **Description**: Analyzes stock shelf-life based on days since last inbound movement and days since last transaction, categorized into standard aging buckets (`0-30 days`, `31-60 days`, `61-90 days`, `90+ days`).
- **Filters**: `warehouse_id`, `aging_bucket`, `search`, `page`, `size`.

### 11. Movement Analytics Engine
- **Endpoint**: `GET /api/v1/inventory/reports/analytics`
- **Description**: Operational movement trends including total inbound/outbound volumes, net flows, breakdowns by movement type, category, and warehouse, and daily timeline aggregations.
- **Filters**: `date_from`, `date_to`, `product_id`, `warehouse_id`, `category_id`.

### 12. Executive Inventory Dashboard
- **Endpoint**: `GET /api/v1/inventory/reports/dashboard` (and alias `/api/v1/inventory/analytics/dashboard`)
- **Description**: Consolidated KPI summary presenting global stock lines, total on-hand/reserved/available quantities, low-stock counts, expired/expiring batch metrics, period movement volume, warehouse utilization, and top-moving products.
- **Filters**: `date_from`, `date_to`, `warehouse_id`.

---

## 4. RBAC & Security Matrix

All report and analytics endpoints are secured via the platform RBAC dependency system `Security(require_permission(...))` or `Security(has_any_permission(...))`:

| Permission Code | Description | Role Assignments |
| :--- | :--- | :--- |
| `inventory.report.stock.read` | View Current Stock & Availability reports | `Super Admin`, `Inventory Manager` |
| `inventory.report.movement.read` | View Stock Movement history reports | `Super Admin`, `Inventory Manager` |
| `inventory.report.warehouse.read` | View Warehouse-level inventory reports | `Super Admin`, `Inventory Manager` |
| `inventory.report.product.read` | View Product-level inventory reports | `Super Admin`, `Inventory Manager` |
| `inventory.report.batch.read` | View Batch & Expiry reports | `Super Admin`, `Inventory Manager` |
| `inventory.report.serial.read` | View Serial Number inventory reports | `Super Admin`, `Inventory Manager` |
| `inventory.report.reservation.read` | View Stock Reservation reports | `Super Admin`, `Inventory Manager` |
| `inventory.report.analytics.read` | View Movement Analytics & Executive Dashboard | `Super Admin`, `Inventory Manager` |
| `inventory.report.export` | Execute CSV exports for inventory reports | `Super Admin`, `Inventory Manager` |

---

## 5. Streaming CSV Exports

CSV exports utilize memory-efficient streaming generators (`text/csv`) with sanitized string escaping to prevent CSV injection vulnerabilities. Each export respects all applied query filters, sort criteria, and RBAC permissions.
