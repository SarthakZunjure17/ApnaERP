# ADR-0023: Inventory Foundation & Product Master Catalog (v0.6.0)

## Status
Accepted

## Context
As ApnaERP scales into full enterprise operations, establishing the Inventory domain is critical. Milestone `v0.6.0` establishes the canonical foundational primitives and master data structures required before stock ledger transactions, inventory movements, batch tracking, or procurement can be built.

The foundation establishes canonical master data for:
1. Product Master Catalog (SKU, Barcode, Model Number, Product Type, Inventory flags `is_stockable`, `is_sellable`, `is_purchasable`, UOM references, Default Warehouse link, stock thresholds, lead times, pricing, flexible metadata, and lifecycle status).
2. Product Categories (supporting infinite parent-child hierarchy trees with circular reference prevention and child node querying).
3. Units of Measure (with precision boundaries 0-6, conversion base unit definitions, categorization, and unique codes).
4. Brands (manufacturer and brand cataloging).
5. Warehouses (multi-facility architecture with types `MAIN`, `DISTRIBUTION`, `RETAIL`, `VIRTUAL`, `TRANSIT`, structured address fields, operating timezone, and facility managers).
6. Storage Locations (hierarchical racks, shelves, bins, zones, and cold storage with composite uniqueness per facility).
7. Multi-Warehouse Stocking Configurations (`ProductWarehouse` mapping items to facilities with specific reorder points, reorder quantities, min/max thresholds, safety stocks, and preferred location consistency).
8. Inventory Policies (`InventoryPolicy` establishing valuation methods FIFO/LIFO/Weighted Average/Standard, costing methods, negative stock permissions, replenishment strategies, and reservation behaviors).
9. Custom Product Attributes (Extensible key-value definitions with typed values).
10. Product Documents (Attaching uploaded specifications, compliance certificates, manuals, and images).

## Decision
We implemented the Inventory Foundation following Clean Architecture, Domain Driven Design (DDD), Repository Pattern, and SOLID principles:

1. **Additive Entity Evolution & Persistence**:
   - Evolved existing models (`Product`, `ProductCategory`, `UnitOfMeasure`, `Warehouse`, `StorageLocation`, `Brand`, `ProductAttribute`, `ProductDocument`) additively with canonical fields and backward-compatible aliases.
   - Introduced dedicated ORM models `ProductWarehouse` and `InventoryPolicy` with composite unique constraints and cascading foreign keys.
   - Preserved all existing table structures and column names to ensure strict zero-regression compatibility with Procurement, Sales, and Accounting domains.

2. **Domain Logic & Validation**:
   - Implemented strict circular reference validation for Category and Storage Location hierarchy updates.
   - Storage Location parent-child links require both nodes to belong to the same `warehouse_id`.
   - `ProductWarehouse` requires `preferred_location_id` to belong strictly to the configured `warehouse_id`.
   - Reorder threshold sanity validations (`minimum_stock <= maximum_stock`, non-negative quantities).
   - Safe deactivation guards preventing hard-deletes of referenced products, categories, or warehouses.
   - Product status state machine (`Draft` &rarr; `Active` &rarr; `Discontinued` &rarr; `Archived`) where `Archived` products are immutable (read-only).

3. **Performance & Infrastructure**:
   - Redis caching for hierarchical tree structures (`category:tree`, `location:tree`) and entity lookup invalidations on mutation events.
   - Asynchronous Celery background notifications (`send_inventory_notification_task`) dispatched when warehouses are created/updated or products are archived.
   - Audit event logging integrated into all mutation operations.

4. **Security & RBAC**:
   - Seeded granular permissions (`inventory.product.*`, `inventory.product_warehouse.*`, `inventory.policy.*`, `inventory.category.*`, `inventory.unit.*`, `inventory.uom.*`, `inventory.brand.*`, `inventory.warehouse.*`, `inventory.location.*`, `inventory.attribute.*`, `inventory.document.*`).
   - Assigned permissions to `Super Admin` and `Inventory Manager` roles.

## Consequences
- **Positive**:
  - Provides a standardized, extensible Product Master catalog for the entire ERP system.
  - Multi-warehouse stocking parameters allow localized supply chain optimization per facility.
  - Canonical inventory policies provide clear rules for downstream Stock Ledger and Valuation modules.
  - Strict status immutability guarantees data integrity for archived products.
- **Negative**:
  - Requires cache invalidation management across hierarchical tree updates.

## Compliance
- Clean Architecture / Domain Driven Design (DDD).
- ISO / ERP industry standard product master representations.
- SOLID principles and Async-first FastAPI / SQLAlchemy 2.0 / Pydantic v2 implementation.
