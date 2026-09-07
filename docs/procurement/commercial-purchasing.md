# Procurement: Commercial Purchasing (v0.7.2)

## 1. Overview & Purpose
The **Commercial Purchasing** milestone (`v0.7.2`) delivers the core commercial purchasing engine in ApnaERP. A **Purchase Order (PO)** represents the legally binding commercial commitment made by the enterprise to purchase goods or services from a supplier under agreed pricing, tax, discount, payment, and delivery terms.

```
+---------------------------+
|    Purchase Requisition   |  (Internal Purchasing Demand)
+---------------------------+
              |
              v (v0.7.1)
+---------------------------+
|    Request For Quotation  |  (Solicitation to Invited Suppliers)
|           (RFQ)           |
+---------------------------+
              |
              v (v0.7.1)
+---------------------------+
|    Supplier Quotation     |  (Commercial Bids)
+---------------------------+
              |
              v (Awarded)
+===========================+
|      PURCHASE ORDER       |  <--- [v0.7.2 Commercial Purchasing]
|        (Canonical)        |
+===========================+
              |
              v (Commercial Approval & Dispatch)
+---------------------------+
|     PO Dispatched         |  (Transmitted to Supplier)
+---------------------------+
              |
              v (v0.7.3 Future Hand-off)
       [ Goods Receipt ]
```

---

## 2. Purchase Order Subsystem

### 2.1 Canonical Entity Structure
- **Header**: `PurchaseOrder` (`purchase_orders`)
- **Line Items**: `PurchaseOrderItem` (`purchase_order_items`)
- **Purpose**: Canonical representation of an agreed commercial commitment with a supplier.
- **Key Header Fields**:
  - `id`: UUID primary key
  - `po_number`: Concurrency-safe sequence `PO-YYYY-XXXXX`
  - `origin_type`: Traceability origin (`Quotation`, `Requisition`, `Manual`)
  - `origin_document_id`: UUID reference to origin quotation or requisition
  - `supplier_id`: FK reference to `Supplier`
  - `order_date`: Date PO was issued/created
  - `expected_delivery_date`: Target fulfillment date
  - `payment_terms`, `currency`, `shipping_address`, `billing_address`, `notes`
  - `status`: `Draft`, `Submitted`, `Approved`, `Rejected`, `Dispatched`, `Partially Received`, `Fully Received`, `Closed`, `Cancelled`
  - `subtotal`, `tax_amount`, `discount_amount`, `total_amount`: Exact `Numeric(18, 4)` / `Decimal` totals
  - `revision_number`: Integer revision counter (starts at 1)
  - `created_by`, `approved_by`, `approved_at`, `created_at`, `updated_at`

- **Line Item Fields**:
  - `product_id`: FK reference to active `Product`
  - `description`: Product line description
  - `quantity`: Quantity ordered ($> 0$)
  - `unit_price`: Agreed unit price ($\ge 0$)
  - `discount_pct`: Line discount percentage ($0 \le \text{pct} \le 100$)
  - `tax_pct`: Line tax percentage ($0 \le \text{pct} \le 100$)
  - `total_price`: Calculated line total ($(\text{Gross} - \text{Discount}) + \text{Tax}$)
  - `warehouse_id`: Target receiving warehouse FK reference
  - `storage_location_id`: Optional storage location FK reference
  - `expected_delivery_date`: Optional item-specific delivery date
  - `received_quantity`: Quantity received tracking counter (Metadata only in v0.7.2, mutation handled in v0.7.3)
  - `returned_quantity`: Quantity returned tracking counter (Metadata only in v0.7.2, mutation handled in v0.7.3)
  - `status`: Item status (`Pending`, `Partially Received`, `Fully Received`, `Cancelled`)

---

## 3. Creation Paths & Validation

### 3.1 Creation from Awarded Supplier Quotation
```http
POST /api/v1/purchase-orders/from-quotation/{quotation_id}
```
1. Validates `SupplierQuotation` exists and is in `Approved` status.
2. Validates the referenced `Supplier` is active and not blacklisted.
3. Validates target `Warehouse` exists and is active.
4. Enforces duplicate prevention: Rejects PO creation if a PO already references this quotation (`origin_type="Quotation"` and `origin_document_id=quotation.id`).
5. Copies items, pricing, discount, tax, currency, and payment terms directly from the quotation into a new PO in `Draft` state.

### 3.2 Manual PO Creation
```http
POST /api/v1/purchase-orders
```
1. Validates supplier exists, is active, and is not blacklisted.
2. Validates all line items have valid active products, active warehouses, $\text{quantity} > 0$, $\text{unit\_price} \ge 0$, and valid discount/tax rates ($0-100\%$).
3. Generates safe sequence number `PO-YYYY-XXXXX` and initializes in `Draft` state.

---

## 4. Lifecycle & State Machine

```
[Draft] <======================== (Amend Rev +1) <=======================+
   |                                                                      |
   +---> (Submit) ---> [Submitted]                                       |
                           |                                              |
                           +---> (Approve) ---> [Approved]                |
                           |                       |                      |
                           |                       +---> (Dispatch) ---> [Dispatched]
                           |                       |                         |
                           v                       v                         v
                       [Rejected]             [Cancelled]          [v0.7.3 Receiving]
```

### 4.1 Lifecycle States
- **Draft**: Fully editable. Header, lines, supplier, quantities, and pricing may be updated. Cancellable.
- **Submitted**: Immutable against normal edits. Triggers platform `ApprovalEngineService.start_workflow(...)`. Transitions to `Approved` upon approval or `Rejected` upon rejection.
- **Approved**: Commercial commitment approved. Normal PATCH updates are prohibited. Can be amended via revision workflow or dispatched.
- **Dispatched**: Commercial transmission to supplier confirmed. Ready for logistics receiving.
- **Cancelled**: Allowed for `Draft`, `Submitted`, and `Approved`/`Dispatched` orders prior to the start of physical receiving ($\text{total\_received} == 0$). Prohibited once receiving commences.
- **Closed**: Administrative closure.

---

## 5. Amendments & Revision Control
Approved or Dispatched purchase orders cannot be modified directly via normal PATCH endpoints. To amend an approved PO:
```http
POST /api/v1/purchase-orders/{id}/amend
```
1. Validates PO is in `Approved` or `Dispatched` state and has not started physical receiving ($\sum \text{received\_quantity} == 0$).
2. Increments `revision_number` ($N \to N+1$).
3. Resets status to `Draft`, clearing previous approval metadata (`approved_by=None`, `approved_at=None`).
4. Replaces/updates items, delivery dates, terms, and notes with amendment justification.
5. Recalculates all commercial totals and creates a `PURCHASE_ORDER_AMEND` audit event.
6. The amended PO must be re-submitted and re-approved through standard workflow channels.

---

## 6. Document Numbering
Purchase Order numbering utilizes the established sequence generation pattern:
- **Format**: `PO-YYYY-XXXXX` (e.g. `PO-2026-00001`, `PO-2026-00002`)
- **Safe Generation**: `get_max_number_suffix(db, prefix="PO-YYYY-")` extracts maximum existing integer suffix in database transactions, preventing race conditions.
- **Database Constraint**: `po_number` has a unique database index preventing duplicates.

---

## 7. Pricing & Commercial Calculation Rules
All calculations utilize Python `Decimal` / SQL `Numeric(18, 4)` precision:
- $\text{Gross} = \text{Quantity} \times \text{Unit Price}$
- $\text{Discount Value} = \text{Gross} \times (\text{Discount Pct} / 100)$
- $\text{Taxable Value} = \text{Gross} - \text{Discount Value}$
- $\text{Tax Value} = \text{Taxable Value} \times (\text{Tax Pct} / 100)$
- $\text{Line Total} = \text{Taxable Value} + \text{Tax Value}$
- **PO Totals**:
  - $\text{Subtotal} = \sum \text{Gross}$
  - $\text{Discount Amount} = \sum \text{Discount Value}$
  - $\text{Tax Amount} = \sum \text{Tax Value}$
  - $\text{Total Amount} = \text{Subtotal} - \text{Discount Amount} + \text{Tax Amount}$

---

## 8. Domain Boundaries & Invariants

### 8.1 Inventory Domain Boundary (FROZEN)
A Purchase Order is strictly a **commercial commitment**, not physical stock:
- Creating a PO $\implies$ Zero Inventory mutation.
- Submitting a PO $\implies$ Zero Inventory mutation.
- Approving a PO $\implies$ Zero Inventory mutation.
- Amending a PO $\implies$ Zero Inventory mutation.
- Dispatching a PO $\implies$ Zero Inventory mutation.
- Cancelling a PO $\implies$ Zero Inventory mutation.
- **Invariants**:
  - No `StockLedger` records created.
  - No `StockBalance` records modified.
  - No `GoodsReceipt` records created.
  - No physical inventory movement.

### 8.2 Finance Domain Boundary
Commercial PO totals represent operational commitments:
- No Supplier Invoices are generated.
- No Accounts Payable (AP) ledger entries are made.
- No General Ledger (GL) journal postings or COGS movements occur.

### 8.3 v0.7.3 Logistics & Receiving Boundary
Physical receiving of goods against Purchase Orders is explicitly deferred to **v0.7.3**:
- `received_quantity` and `returned_quantity` on PO items are metadata fields populated exclusively by v0.7.3 Goods Receipt and Purchase Return handlers.

---

## 9. Security, RBAC & Audit Logging

### 9.1 RBAC Permissions
| Permission | Description | Procurement Manager | Procurement Viewer |
| :--- | :--- | :---: | :---: |
| `procurement.purchase_order.create` | Create new draft PO / convert quotation | Yes | No |
| `procurement.purchase_order.read` | View purchase orders and line items | Yes | Yes |
| `procurement.purchase_order.update` | Update draft purchase orders | Yes | No |
| `procurement.purchase_order.submit` | Submit draft PO for approval | Yes | No |
| `procurement.purchase_order.approve` | Approve submitted purchase order | Yes | No |
| `procurement.purchase_order.amend` | Amend approved purchase order | Yes | No |
| `procurement.purchase_order.cancel` | Cancel purchase order | Yes | No |
| `procurement.purchase_order.dispatch` | Mark purchase order as dispatched | Yes | No |

### 9.2 Audit Log Events
All state changes record canonical `AuditLog` entries with user ID, timestamps, previous data, and new data:
- `PURCHASE_ORDER_CREATE`
- `PURCHASE_ORDER_UPDATE`
- `PURCHASE_ORDER_SUBMIT`
- `PURCHASE_ORDER_APPROVE`
- `PURCHASE_ORDER_REJECT`
- `PURCHASE_ORDER_AMEND`
- `PURCHASE_ORDER_DISPATCH`
- `PURCHASE_ORDER_CANCEL`

---

## 10. API Reference Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/purchase-orders` | List purchase orders with search, filtering, and pagination |
| `POST` | `/api/v1/purchase-orders` | Create a manual purchase order |
| `POST` | `/api/v1/purchase-orders/from-quotation/{quotation_id}` | Generate a purchase order from an awarded supplier quotation |
| `GET` | `/api/v1/purchase-orders/{id}` | Retrieve purchase order by ID with line items |
| `PATCH` | `/api/v1/purchase-orders/{id}` | Update draft purchase order header and line items |
| `POST` | `/api/v1/purchase-orders/{id}/submit` | Submit draft purchase order to approval engine |
| `POST` | `/api/v1/purchase-orders/{id}/approve` | Approve submitted purchase order |
| `POST` | `/api/v1/purchase-orders/{id}/reject` | Reject submitted purchase order with justification |
| `POST` | `/api/v1/purchase-orders/{id}/amend` | Create controlled amendment revision of approved PO |
| `POST` | `/api/v1/purchase-orders/{id}/dispatch` | Mark approved purchase order as commercially dispatched |
| `POST` | `/api/v1/purchase-orders/{id}/cancel` | Cancel purchase order prior to receiving |
| `POST` | `/api/v1/purchase-orders/{id}/close` | Close purchase order |
| `POST` | `/api/v1/purchase-orders/{id}/reopen` | Reopen closed purchase order |
