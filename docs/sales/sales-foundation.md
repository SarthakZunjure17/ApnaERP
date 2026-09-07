# Sales Foundation & Core Order Flow (v0.8.0)

## 1. Overview & Purpose
The **Sales Foundation & Core Order Flow** milestone (`v0.8.0`) establishes the core Sales domain and customer-to-order lifecycle in ApnaERP. It provides clean, scalable master data management for customers, commercial quotation generation, revision control, quotation-to-order conversion, credit limit validations, Approval Engine integration, and strict domain boundaries against Inventory, Finance, and CRM.

```
+=============================================================================+
|                                CUSTOMER MASTER                              |
|   (Customer, Categories, Contacts, Addresses, Credit Limits, Statuses)      |
+=============================================================================+
                                      |
                                      v
+=============================================================================+
|                               SALES QUOTATION                               |
|        (SQ-YYYY-XXXXX, Line Discounts, Taxes, Revision History)             |
+=============================================================================+
                                      |
                                      v (Submit -> Approved)
+=============================================================================+
|                      QUOTATION -> SALES ORDER CONVERSION                    |
|             (Atomic line copy, commercial terms, duplicate guard)           |
+=============================================================================+
                                      |
                                      v
+=============================================================================+
|                                 SALES ORDER                                 |
|            (SO-YYYY-XXXXX, Status Lifecycle, ApprovalEngineService)          |
+=============================================================================+
                                      |
                                      v (Approved & Committed)
+-----------------------------------------------------------------------------+
|                        READY FOR FUTURE FULFILLMENT                         |
|     (Clean Inventory Boundary: Goods Issue & Physical Stock Hand-off)       |
+-----------------------------------------------------------------------------+
```

---

## 2. Customer Subsystem

### 2.1 Canonical Entity Structure
- **Entity Model**: `Customer` (`customers` table)
- **Support Models**: `CustomerCategory`, `CustomerContact`, `CustomerAddress`, `CustomerDocument`
- **Key Fields**:
  - `id`: UUID primary key
  - `customer_code`: Unique client identifier (`CUST-XXXXX`)
  - `name`: Business or legal customer name
  - `email`, `phone`, `website`, `tax_id` (GSTIN / VAT)
  - `credit_limit`: Exact `Numeric(18, 2)` approved credit ceiling
  - `credit_days`: Default payment window in days
  - `payment_terms`: `Net 30`, `Immediate`, `COD`, etc.
  - `status`: `Active`, `Inactive`, `Blacklisted`
  - `is_preferred`: Flag for VIP client accounts
  - `rating`: Risk / relationship score (`0.00` to `5.00`)

### 2.2 Customer Operations
- **Creation & Update**: Validates unique customer code and category; transactional relationship creation for addresses and contacts.
- **Activation & Deactivation**: Dedicated lifecycle endpoints (`POST /api/v1/customers/{id}/activate`, `POST /api/v1/customers/{id}/deactivate`) with audit logging. Inactive and Blacklisted customers are strictly blocked from new quotations and orders.
- **Credit Limit Verification**: Enforces credit limits and active customer status prior to sales order approvals.

---

## 3. Sales Quotation Subsystem

### 3.1 Entity Structure
- **Header**: `SalesQuotation` (`sales_quotations` table)
- **Line Items**: `SalesQuotationItem` (`sales_quotation_items` table)
- **Numbering**: Concurrency-safe sequential numbering `SQ-YYYY-XXXXX`
- **Quotation Lifecycle**:
  `Draft` -> `Submitted` -> `Approved` / `Rejected` -> `Converted` / `Cancelled` / `Expired`

### 3.2 Commercial Calculations
For each quotation line item:
$$\text{Gross Amount} = \text{Quantity} \times \text{Unit Price}$$
$$\text{Line Discount} = \text{Calculate}(\text{Gross}, \text{Discount Type}, \text{Discount Value})$$
$$\text{Taxable Amount} = \text{Gross Amount} - \text{Line Discount}$$
$$\text{Tax Amount} = \text{Taxable Amount} \times \frac{\text{Tax Rate}}{100}$$
$$\text{Line Total} = \text{Taxable Amount} + \text{Tax Amount}$$

Header totals (`subtotal_amount`, `discount_amount`, `tax_amount`, `total_amount`) are derived from line items with exact Decimal precision.

---

## 4. Sales Order Subsystem

### 4.1 Entity Structure
- **Header**: `SalesOrder` (`sales_orders` table)
- **Line Items**: `SalesOrderItem` (`sales_order_items` table)
- **Numbering**: Concurrency-safe sequential numbering `SO-YYYY-XXXXX`
- **Order Lifecycle**:
  `Draft` -> `Submitted` -> `Approved` / `Rejected` -> `Ready for Fulfillment` -> `Fully Delivered` / `Closed` / `Cancelled`

### 4.2 Quotation to Order Conversion
- **Endpoint**: `POST /api/v1/sales-orders/from-quotation/{quotation_id}`
- **Validation**:
  - Source quotation must exist and be in `Approved` status.
  - Quotation cannot be already `Converted`.
  - Customer must be `Active`.
- **Atomic Execution**: Copies quotation lines, pricing, discounts, taxes, and customer terms to a new `Draft` Sales Order and marks the source quotation as `Converted`.

### 4.3 Approval Engine Integration
- When a Sales Order is submitted, it triggers the canonical platform `ApprovalEngineService.start_workflow(...)` using workflow code `WF_SALES_ORDER`.
- Order approval validates customer credit limits and active status before transitioning to `Approved`.

---

## 5. Domain Boundaries & Isolation

### 5.1 Sales Quotation vs. Supplier Quotation Isolation
- **SalesQuotation**: Represents outbound commercial offers to customers (owned by Sales domain).
- **SupplierQuotation**: Represents inbound supplier bids for RFQs (owned by Procurement domain).
- Completely distinct tables, repositories, services, and API routes with zero shared mutations.

### 5.2 Sales / Inventory Boundary
- **Sales owns**: Commercial agreements, customer requirements, ordered quantities.
- **Inventory owns**: Physical stock balances (`StockBalance`), inventory transaction ledger (`StockLedger`), and goods issues (`GoodsIssue`).
- **Rule**: Sales operations never directly insert into `StockLedger` or update `StockBalance`. Physical stock dispatch is handed off to Warehouse Operations via delivery orders and goods issues.

### 5.3 Finance Boundary
- Sales Order totals remain commercial figures. Invoicing, accounts receivable, payment schedules, and general ledger journal postings remain isolated in the Finance domain.

### 5.4 CRM Boundary
- Customer identity acts as the sales master. Lead capture, opportunities, sales funnels, and marketing campaigns remain isolated in the CRM domain.

---

## 6. RBAC & Audit Logging

### 6.1 RBAC Permissions
| Resource | Code | Description |
|---|---|---|
| **Customer** | `sales.customer.create` | Create customer master records |
| | `sales.customer.read` | View customer master records |
| | `sales.customer.update` | Update customer master records |
| | `sales.customer.delete` | Soft delete customer master records |
| **Quotation** | `sales.quotation.create` | Create sales quotations |
| | `sales.quotation.read` | View sales quotations |
| | `sales.quotation.update` | Update draft sales quotations |
| | `sales.quotation.submit` | Submit quotations for approval |
| | `sales.quotation.approve` | Approve / reject sales quotations |
| | `sales.quotation.cancel` | Cancel sales quotations |
| **Sales Order** | `sales.order.create` | Create sales orders & convert from quotation |
| | `sales.order.read` | View sales orders |
| | `sales.order.update` | Update draft sales orders |
| | `sales.order.submit` | Submit sales orders for approval |
| | `sales.order.approve` | Approve / reject sales orders |
| | `sales.order.cancel` | Cancel sales orders |
| | `sales.order.fulfill` | Trigger fulfillment handover |

### 6.2 Audit Trail
Every critical mutation generates structured entries in canonical `AuditLog`:
- `CUSTOMER_CREATE`, `CUSTOMER_UPDATE`, `CUSTOMER_ACTIVATE`, `CUSTOMER_DEACTIVATE`
- `SALES_QUOTATION_CREATE`, `SALES_QUOTATION_UPDATE`, `SALES_QUOTATION_SUBMIT`, `SALES_QUOTATION_APPROVE`, `SALES_QUOTATION_REJECT`, `SALES_QUOTATION_CANCEL`
- `SALES_ORDER_CREATE`, `SALES_ORDER_UPDATE`, `SALES_ORDER_SUBMIT`, `SALES_ORDER_APPROVE`, `SALES_ORDER_REJECT`, `SALES_ORDER_CANCEL`, `SALES_ORDER_CLOSE`, `SALES_ORDER_REOPEN`
