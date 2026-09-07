# Procurement: Sourcing & Requisitions (v0.7.1)

## 1. Overview & Purpose
The **Sourcing & Requisitions** milestone (`v0.7.1`) delivers the upstream procurement lifecycle in ApnaERP, bridging internal operational demand and external supplier bidding without violating platform domain boundaries.

```
+---------------------------+
|    Purchase Requisition   |  (Internal Purchasing Demand)
+---------------------------+
              |
              v (Approved / Sourced)
+---------------------------+
|    Request For Quotation  |  (Solicitation to Invited Suppliers)
|           (RFQ)           |
+---------------------------+
              |
              v (Responses Submitted)
+---------------------------+
|    Supplier Quotations    |  (Commercial Bids & Delivery Terms)
+---------------------------+
              |
              v (Deterministic Matrix Evaluation)
+---------------------------+
|   Quotation Comparison    |  (Price, Rating, Lead Time, Terms)
+---------------------------+
              |
              v (Explicit User Selection)
+---------------------------+
|      Quotation Award      |  (Winning Bid Selected, RFQ Closed)
+---------------------------+
              |
              v (v0.7.2 Milestone Hand-off)
       [ Purchase Order ]
```

---

## 2. Purchase Requisition Subsystem

### 2.1 Domain Model & Line Items
- **Entity**: `PurchaseRequisition` (`purchase_requisitions`)
- **Child Items**: `PurchaseRequisitionItem` (`purchase_requisition_items`)
- **Purpose**: Represents internal demand initiated by employees or departments.
- **Key Fields**:
  - `requisition_number`: Database-safe sequence `PR-YYYY-XXXXX`
  - `requester_id`: User initiating demand (validated against `User`)
  - `department_id`: Department requesting materials (validated against `Department`)
  - `required_date`: Expected delivery date
  - `priority`: `Low`, `Medium`, `High`, `Urgent`
  - `status`: `Draft`, `Submitted`, `Approved`, `Rejected`, `Cancelled`, `Partially Fulfilled`, `Fulfilled`
  - `total_estimated_amount`: Aggregate estimated cost of items
  - `items`: Quantity ($> 0$), unit, estimated unit price ($\ge 0$), active product validation.

### 2.2 Requisition Lifecycle
```
[Draft]  <--->  [Update Draft]
   |
   v (Submit)
[Submitted] ---> ApprovalEngineService.start_workflow(...)
   |
   +---> [Approved] (Immutable / Locked)
   |
   +---> [Rejected] (Can return to Draft)
   |
   v (Cancel)
[Cancelled] (Terminal state; line items cancelled)
```

### 2.3 Canonical Approval Engine Integration
- Requisitions integrate directly with the platform's canonical `ApprovalEngineService.start_workflow(...)` using workflow code `WF_PURCHASE_REQUISITION`.
- If no workflow is configured, the requisition remains `Submitted` and requires explicit approval (no silent auto-approval).
- Duplicate submissions are safely rejected without creating orphan approval requests.

---

## 3. Request For Quotation (RFQ) Subsystem

### 3.1 Domain Model & Supplier Invitations
- **Entity**: `RFQ` (`rfqs`)
- **Junction**: `RFQSupplier` (`rfq_suppliers`)
- **Purpose**: Sourcing instrument to invite pre-qualified active suppliers to submit commercial bids.
- **Key Fields**:
  - `rfq_number`: Database-safe sequence `RFQ-YYYY-XXXXX`
  - `title`: Descriptive sourcing title
  - `requisition_id`: Optional source `PurchaseRequisition` linkage
  - `submission_deadline`: Bidding deadline
  - `status`: `Draft`, `Issued`, `Closed`, `Cancelled`
  - `terms_and_conditions`: Commercial and delivery stipulations

### 3.2 Supplier Invitation Rules
- Suppliers must exist and have status `Active`.
- Blacklisted or inactive suppliers cannot be invited.
- Unique constraint `(rfq_id, supplier_id)` prevents duplicate invitations.
- Suppliers can be added or removed while the RFQ is in `Draft`.

---

## 4. Supplier Quotation Subsystem

### 4.1 Domain Isolation (Procurement vs Sales)
`SupplierQuotation` and `SupplierQuotationItem` belong exclusively to the **Procurement** domain and are handled by `SupplierQuotationService`. They are strictly decoupled and isolated from `SalesQuotation` and `SalesQuotationItem`.

### 4.2 Lifecycle & Validations
```
[Draft] ---> [Submitted] ---> [Under Review] ---> [Approved] (Awarded)
   |                                                    |
   +---> [Withdrawn]                                    +---> [Rejected]
```
- **Validation Rules**:
  - Quoting supplier must exist and be `Active`.
  - Linked RFQ must not be Closed or Cancelled.
  - Quoting supplier must be an invited participant in the RFQ.
  - Quoted products must exist and be active.
  - Quantity $> 0$, Unit Price $\ge 0$, Discount/Tax percentages $0 \le p \le 100$.

### 4.3 Total Calculations
- $\text{Line Subtotal} = \text{quantity} \times \text{unit\_price}$
- $\text{Line Discount} = \text{Line Subtotal} \times (\text{discount\_pct} / 100)$
- $\text{Taxable Amount} = \text{Line Subtotal} - \text{Line Discount}$
- $\text{Line Tax} = \text{Taxable Amount} \times (\text{tax\_pct} / 100)$
- $\text{Line Total} = \text{Taxable Amount} + \text{Line Tax}$
- $\text{Quotation Total} = \text{subtotal} - \text{discount\_amount} + \text{tax\_amount}$

---

## 5. Quotation Comparison & Selection

### 5.1 Comparison Matrix
- RFQ comparison endpoint `/api/v1/rfqs/{id}/comparison` returns a deterministic comparison matrix across all submitted quotations.
- Aggregates:
  - Supplier name, code, and authoritative performance rating
  - Quoted total amount and currency
  - Promised lead time in days
  - Validity date and payment terms
  - Item counts and status
- Sorted deterministically by `total_amount` ascending (lowest price first).
- No AI/blackbox heuristic ranking; purely deterministic operational data.

### 5.2 Explicit Quotation Award
- Authorized procurement managers explicitly select the winning quotation via `/api/v1/rfqs/{id}/award/{quotation_id}`.
- Winning quotation is marked `Approved`.
- Competing active quotations on the same RFQ are marked `Rejected`.
- RFQ status transitions to `Closed`.
- Comprehensive audit event `SUPPLIER_QUOTATION_AWARD` is recorded.

---

## 6. Architecture & Domain Boundaries

### 6.1 Inventory Boundary Invariant
- Creating or updating PRs, RFQs, and Supplier Quotations creates **zero** inventory movement.
- Awarding a quotation creates **zero** inventory movement.
- `StockLedger`, `StockBalance`, `GoodsReceipt`, `GoodsIssue`, `StockTransfer`, and `StockReservation` remain completely untouched.

### 6.2 Purchase Order Boundary Invariant
- Awarding a quotation selects the winning commercial bid but does **NOT** create a `PurchaseOrder`.
- Purchase Order generation, revisions, approval, and dispatch are reserved for **v0.7.2 (Commercial Purchasing)**.

### 6.3 Finance Boundary Invariant
- Commercial quotation values are operational procurement metadata.
- No Accounts Payable invoices, payments, vouchers, or General Ledger entries are created.

---

## 7. Safe Document Numbering
Document sequences are generated using database-level maximum suffix scans over the current period, preventing race conditions and count-based collisions:
- **Purchase Requisition**: `PR-YYYY-XXXXX` (e.g. `PR-2026-00001`)
- **RFQ**: `RFQ-YYYY-XXXXX` (e.g. `RFQ-2026-00001`)
- **Supplier Quotation**: `SQ-YYYYMM-XXXXX` (e.g. `SQ-202609-00001`)

---

## 8. Role-Based Access Control (RBAC)
Granular permissions registered and mapped to canonical roles:

| Permission Code | Description | Procurement Manager | Procurement Viewer |
| :--- | :--- | :---: | :---: |
| `procurement.requisition.create` | Create purchase requisitions | Yes | No |
| `procurement.requisition.read` | View purchase requisitions | Yes | Yes |
| `procurement.requisition.update` | Modify draft requisitions | Yes | No |
| `procurement.requisition.submit` | Submit requisitions for approval | Yes | No |
| `procurement.requisition.approve` | Approve/reject requisitions | Yes | No |
| `procurement.requisition.cancel` | Cancel requisitions | Yes | No |
| `procurement.rfq.create` | Create RFQs | Yes | No |
| `procurement.rfq.read` | View RFQs and invited suppliers | Yes | Yes |
| `procurement.rfq.update` | Modify draft RFQs and invite suppliers | Yes | No |
| `procurement.rfq.issue` | Issue RFQs to suppliers | Yes | No |
| `procurement.rfq.cancel` | Cancel RFQs | Yes | No |
| `procurement.quotation.create` | Create supplier quotations | Yes | No |
| `procurement.quotation.read` | View supplier quotations | Yes | Yes |
| `procurement.quotation.update` | Modify draft supplier quotations | Yes | No |
| `procurement.quotation.submit` | Submit supplier quotations | Yes | No |
| `procurement.quotation.withdraw` | Withdraw supplier quotations | Yes | No |
| `procurement.quotation.approve` | Approve supplier quotations | Yes | No |
| `procurement.sourcing.read` | View sourcing summary | Yes | Yes |
| `procurement.sourcing.compare` | View RFQ comparison matrix | Yes | Yes |
| `procurement.quotation.award` | Explicitly award winning quotation | Yes | No |

---

## 9. Audit Logging
Every business lifecycle action records structured audit entries via `AuditLog`:
- `PURCHASE_REQUISITION_CREATE`, `PURCHASE_REQUISITION_UPDATE`, `PURCHASE_REQUISITION_SUBMIT`, `PURCHASE_REQUISITION_APPROVE`, `PURCHASE_REQUISITION_REJECT`, `PURCHASE_REQUISITION_CANCEL`
- `RFQ_CREATE`, `RFQ_UPDATE`, `RFQ_ISSUE`, `RFQ_CANCEL`, `RFQ_SUPPLIER_INVITED`
- `SUPPLIER_QUOTATION_CREATE`, `SUPPLIER_QUOTATION_UPDATE`, `SUPPLIER_QUOTATION_SUBMIT`, `SUPPLIER_QUOTATION_WITHDRAW`, `SUPPLIER_QUOTATION_AWARD`
