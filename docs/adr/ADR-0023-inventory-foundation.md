# ADR-0023: Inventory Foundation & Product Master Catalog

## Status
Accepted

## Context
As ApnaERP expands into physical enterprise operations, establishing the Inventory domain is critical. Milestone `v0.6.0` establishes the foundational primitives and master data structures required before stock ledger transactions, inventory movements, batch tracking, or procurement can be built.

The foundation requires tracking:
1. Product Categories (supporting infinite parent-child hierarchy trees).
2. Units of Measure (with precision, conversion base unit definitions, and categorization).
3. Brands (manufacturer / brand management).
4. Warehouses (physical storage facilities with contact details).
5. Storage Locations (racks, shelves, bins, zones, cold storage nested within warehouses).
6. Product Master Records (SKU, Barcode, Product Type, Inventory flags, UOM references, Default Warehouse link, and lifecycle status).
7. Custom Product Attributes (Extensible key-value definitions with typed values).
8. Product Documents (Attaching uploaded specifications, compliance certificates, manuals, and images).

## Decision
We implemented the Inventory Foundation following Clean Architecture, Domain Driven Design (DDD), Repository Pattern, and SOLID principles:

1. **Domain Models & Entities**:
   - Built 9 dedicated ORM models (`ProductCategory`, `UnitOfMeasure`, `Brand`, `Warehouse`, `StorageLocation`, `Product`, `ProductAttribute`, `ProductAttributeValue`, `ProductDocument`).
   - Integrated `ProductCategory` and `StorageLocation` with self-referential parent-child relationships for infinite hierarchical tree rendering.
   - Enforced uniqueness constraints on Category Code, UOM Name/Symbol, Brand Name, Warehouse Code, Storage Location Code per Warehouse, Product SKU, Product Barcode, and Attribute Code.

2. **Domain Logic & Validation**:
   - Implemented strict circular reference validation for Category and Storage Location hierarchy updates.
   - Storage Location parent-child links require both nodes to belong to the same `warehouse_id`.
   - Product status state machine (`Draft` -> `Active` -> `Discontinued` -> `Archived`).
   - `Archived` products are immutable (read-only) and reject modification requests.

3. **Performance & Infrastructure**:
   - Redis caching for hierarchical tree structures (`category:tree`, `location:tree`) and entity lookup invalidations on mutation events.
   - Asynchronous Celery background notifications (`send_inventory_notification_task`) dispatched when warehouses are created/updated or products are archived.
   - Audit event logging integrated into all mutation operations.

4. **Security & RBAC**:
   - Seeded 24 granular permissions (`inventory.category.*`, `inventory.unit.*`, `inventory.brand.*`, `inventory.warehouse.*`, `inventory.location.*`, `inventory.product.*`, `inventory.attribute.*`, `inventory.document.*`).
   - Assigned permissions to `Super Admin` and `Inventory Manager` roles.

## Consequences
- **Positive**:
  - Provides a standardized, extensible Product Master catalog for the entire ERP system.
  - Hierarchical tree structures allow flexible multi-level categorization and warehouse layout modeling.
  - Strict status immutability guarantees data integrity for archived products.
- **Negative**:
  - Requires cache invalidation management across hierarchical tree updates.

## Compliance
- Clean Architecture / Domain Driven Design (DDD).
- ISO / ERP industry standard product master representations.
- SOLID principles and Async-first FastAPI / SQLAlchemy 2.0 / Pydantic v2 implementation.
