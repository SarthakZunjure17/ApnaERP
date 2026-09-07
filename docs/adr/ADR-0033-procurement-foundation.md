# ADR-0033: Procurement Foundation Architecture & Supplier Master Lifecycle

## Context & Problem Statement

ApnaERP requires an authoritative purchasing and vendor master subsystem (`v0.7.0`) to serve as the single source of truth for supplier identities, classifications, communication channels, logistical addresses, compliance documents, and performance scorecards. Future milestones (`v0.7.1` – `v0.7.4`) will build transactional purchasing workflows (PRs, RFQs, POs, Receipts, Spend Analytics) on top of this foundation.

## Decision Drivers

1. **Strict Canonical Identity:** Establish `Supplier` as the canonical purchasing party without proliferating redundant `Vendor` or partner aliases.
2. **Boundary Isolation:** Strict separation from Inventory (no direct physical stock mutations) and Finance (banking attributes treated as master data; no AP or ledger postings).
3. **Transactional Integrity & Concurrency:** Concurrency-safe supplier numbering (`SUP-00001`), atomic single primary contact enforcement, and status transition governance (`Active`, `Inactive`, `Blacklisted`).
4. **Platform Harmony:** Seamless integration with canonical `AuditLog`, `File` storage, Pydantic v2 schemas, and RBAC permissions.

## Considered Options

- **Option 1: Ad-hoc Vendor entity coupled to Accounting/AP.**
  - *Cons:* Violates ERP bounded contexts by pulling forward unbuilt Finance modules; creates coupling between purchasing and financial ledger.
- **Option 2: Canonical Supplier Foundation with strict milestone isolation (Chosen).**
  - *Pros:* Clean domain encapsulation, robust concurrency safety, zero regression on existing Inventory/HR/Payroll suites, and seamless extensibility for subsequent purchasing milestones.

## Decision

Adopt the canonical Supplier Master architecture:
1. **Entities:** `SupplierCategory`, `Supplier`, `SupplierContact`, `SupplierAddress`, `SupplierDocument`, and `SupplierRating`.
2. **Numbering:** Auto-sequence generation format `SUP-00001` based on database max sequence query.
3. **Governance:** Status lifecycle (`Active` ↔ `Inactive` ↔ `Blacklisted`). Blacklist state requires `procurement.supplier.blacklist` and prevents silent reactivation.
4. **Primary Contact Rule:** Single primary contact enforced atomically with row-level locking.
5. **Storage:** Documents link directly to `files.id` in canonical file storage.
6. **Audit & Security:** Full audit event logging with sensitive banking number masking (`****1234`).
7. **RBAC:** Seeded `Procurement Manager` (full administrative rights) and `Procurement Viewer` (read-only rights) roles.

## Status

Accepted.

## Consequences

- All future purchasing documents (`PurchaseRequisition`, `RFQ`, `SupplierQuotation`, `PurchaseOrder`) in `v0.7.1`+ will reference the canonical `Supplier` model.
- Zero regressions across existing modules (Inventory, HR, Payroll, Platform).
