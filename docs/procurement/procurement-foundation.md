# ApnaERP — Procurement Foundation Architecture (v0.7.0)

## 1. Domain Overview & Scope Boundaries

The **Procurement Foundation** milestone (`v0.7.0`) establishes the authoritative master data infrastructure for purchasing and external supplier management in ApnaERP.

### Canonical Procurement Hierarchy:
```
SupplierCategory
      ↓
Supplier (Authoritative Master)
      ├── SupplierContact  (Point-of-contact registry, 1 primary rule)
      ├── SupplierAddress  (Multi-location: Billing, Shipping, Branch, Head Office)
      ├── SupplierDocument (Compliance attachments backed by canonical File storage)
      └── SupplierRating   (Immutable evaluator scorecards & derived average rating)
```

### Scope Isolation Invariants:
- **Canonical Identity:** `Supplier` is the single, authoritative external purchasing identity. No `Vendor` or composite partner entities exist.
- **Inventory Boundary:** Procurement Supplier references Inventory master data (e.g. Products) only where relationships naturally exist. Physical stock mutations, ledger postings, goods receipts, and warehouse movements remain strictly owned by the frozen Inventory context (`v0.6.x`).
- **Finance Boundary:** Supplier commercial attributes (currency, credit limit, payment terms, bank details) are master-data attributes only. No Accounts Payable (AP), general ledger postings, voucher creations, or invoice settlements are executed in `v0.7.0`.
- **Purchasing Workflows:** Purchase Requisitions (PR), Requests for Quotation (RFQ), Supplier Quotations, Purchase Orders (PO), PO Approvals, and Purchase Returns are strictly isolated and deferred to future milestones (`v0.7.1` – `v0.7.4`).

---

## 2. Master Data Entities & Capabilities

### 2.1 SupplierCategory
- **Purpose:** Classifies suppliers by industry, material specialization, or sourcing tier.
- **Fields:** `id` (UUID), `code` (Unique), `name`, `description`, `created_at`, `updated_at`.
- **Integrity:** Deletion is protected if active suppliers are classified under the category.

### 2.2 Supplier Master
- **Purpose:** Central entity for supplier commercial identity, commercial terms, and status.
- **Numbering Sequence:** Concurrency-safe sequential code generator formatting `SUP-00001` with database sequence scanning (`MAX(CAST(SUBSTR(code, 5) AS INTEGER)) + 1`).
- **Status Machine:**
  - `Active`: Normal procurement operations permitted.
  - `Inactive`: Temporarily paused from sourcing operations.
  - `Blacklisted`: Governed blacklist state requiring `procurement.supplier.blacklist` permission. Blacklisted suppliers are immutable to general transaction activity but remain fully queryable for historical audits.
- **Sensitive Master Data Protection:** Banking metadata (`bank_account_number`) is strictly redacted and masked in logs and audit payloads (`****1234`).

### 2.3 SupplierContact
- **Purpose:** Contact persons and key procurement liaison officers.
- **Integrity:** Strictly enforced single-primary contact rule per supplier. When a contact is set or updated as `is_primary=True`, existing primary flags for the supplier are atomically cleared under row-level synchronization.
- **Isolation:** Cross-supplier contact operations are rejected with 404/400 errors.

### 2.4 SupplierAddress
- **Purpose:** Physical premises and logistical endpoints (Billing, Shipping, Head Office, Branch).
- **Integrity:** Foreign key enforcement to parent Supplier with cascade deletion on supplier removal.

### 2.5 SupplierDocument
- **Purpose:** Compliance attachments (GST/Tax certificates, ISO audit reports, NDAs).
- **Storage:** Direct foreign key reference to canonical `files.id` (`File` engine). Validates file existence prior to attachment.
- **Metadata:** Expiry date, document type, verification notes.

### 2.6 SupplierRating
- **Purpose:** Immutable evaluation scorecard submitted by procurement reviewers (scores 1.00 to 5.00).
- **Aggregation:** Maintains complete evaluation history while atomically calculating aggregate average rating on the parent `Supplier.rating` field.

---

## 3. RBAC & Security Matrix

| Permission Code | Role: Procurement Manager | Role: Procurement Viewer | Description |
|---|:---:|:---:|---|
| `procurement.supplier.create` | ✅ | ❌ | Create suppliers, categories, ratings |
| `procurement.supplier.read` | ✅ | ✅ | List, view, and search supplier master data |
| `procurement.supplier.update` | ✅ | ❌ | Edit suppliers, contacts, addresses, documents |
| `procurement.supplier.delete` | ✅ | ❌ | Soft delete unreferenced suppliers/categories |
| `procurement.supplier.blacklist` | ✅ | ❌ | Governance action to blacklist suppliers |

---

## 4. Audit Logging & Observability

Every state mutation logs to the canonical `AuditLog` table with user context, entity ID, action type, and masked values:
- `SUPPLIER_CREATE`, `SUPPLIER_UPDATE`, `SUPPLIER_ACTIVATE`, `SUPPLIER_DEACTIVATE`, `SUPPLIER_BLACKLIST`, `SUPPLIER_DELETE`
- `SUPPLIER_CATEGORY_CREATE`, `SUPPLIER_CATEGORY_UPDATE`, `SUPPLIER_CATEGORY_DELETE`
- `SUPPLIER_CONTACT_CREATE`, `SUPPLIER_CONTACT_UPDATE`, `SUPPLIER_CONTACT_DELETE`
- `SUPPLIER_ADDRESS_CREATE`, `SUPPLIER_ADDRESS_UPDATE`, `SUPPLIER_ADDRESS_DELETE`
- `SUPPLIER_DOCUMENT_CREATE`, `SUPPLIER_DOCUMENT_UPDATE`, `SUPPLIER_DOCUMENT_DELETE`
- `SUPPLIER_RATING_CREATE`

---

## 5. Roadmap Isolation & Deferred Features

1. **v0.7.1 Sourcing & Requisitions:** Purchase Requisition (PR), Requests for Quotation (RFQ), Supplier Quotation management, Quotation Comparison matrix.
2. **v0.7.2 Commercial Purchasing:** Purchase Orders (PO), PO Revisions, PO Approval Workflows.
3. **v0.7.3 Logistics & Receiving:** Goods Receipt Note (GRN) integration, Delivery tracking, Purchase Returns & Stock reversals.
4. **v0.7.4 Procurement Analytics & Finalization:** Spend analytics, vendor scorecards, automated KPI computation.
