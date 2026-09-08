# ApnaERP Reporting & Executive Management Dashboard

## 1. Overview & Architecture

The **Reporting & Executive Management Dashboard** module provides a centralized, high-performance, strictly read-only reporting layer across all core domains of ApnaERP:
- **Finance & Accounting**
- **Sales & Commercial Orders**
- **Procurement & Supply Chain**
- **Inventory & Warehouse Operations**
- **Human Resources (HR)**
- **Payroll & Compensation**
- **Customer Relationship Management (CRM)**

### Key Architectural Principles
1. **Strict Read-Only Guarantee**: Reporting services and repository queries execute solely read operations. No business transactions, stock ledger movements, financial journals, payroll records, or CRM states are mutated or created.
2. **Database-Side Aggregation**: Calculations (sums, counts, averages, and group-by analyses) are performed directly within the database engine using SQL aggregations (`SUM`, `COUNT`, `AVG`, `GROUP BY`, `JOIN`).
3. **Exact Decimal Arithmetic**: Monetary and unit values utilize exact decimal precision (`Numeric(18, 4)` and `Numeric(12, 2)`) to eliminate floating-point rounding errors.
4. **RFC 4180 Compliant Exports**: Built-in CSV export service supporting streaming and formatted CSV downloads with appropriate MIME types (`text/csv`) and standard headers.
5. **Granular RBAC**: Domain-scoped permissions (`reports.dashboard.read`, `reports.finance.read`, `reports.sales.read`, etc.) enforce role-based access control.

---

## 2. API Endpoints

All reporting endpoints are registered under `/api/v1/reports`:

| Method | Route | Permission Required | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/reports/dashboard` | `reports.dashboard.read` | Executive management dashboard aggregating KPIs across all 7 domains. |
| `GET` | `/api/v1/reports/finance/profit-loss` | `reports.finance.read` | Profit & Loss statement with revenue, expenses, and net profit for date range / fiscal period. |
| `GET` | `/api/v1/reports/finance/balance-sheet` | `reports.finance.read` | Balance Sheet listing Assets, Liabilities, and Equity as of an effective date. |
| `GET` | `/api/v1/reports/finance/trial-balance` | `reports.finance.read` | Real-time Trial Balance verifying debit/credit equilibrium across accounts. |
| `GET` | `/api/v1/reports/sales/summary` | `reports.sales.read` | Sales order summaries, revenue, discounts, tax, and quotation conversion statistics. |
| `GET` | `/api/v1/reports/sales/customers` | `reports.sales.read` | Customer sales totals, order counts, and net spend breakdown. |
| `GET` | `/api/v1/reports/sales/products` | `reports.sales.read` | Sales volume and revenue aggregated by product master. |
| `GET` | `/api/v1/reports/procurement/summary` | `reports.procurement.read` | Purchase order volume, total procurement spend, and receiving/return stats. |
| `GET` | `/api/v1/reports/procurement/suppliers` | `reports.procurement.read` | Supplier purchase totals and order distribution. |
| `GET` | `/api/v1/reports/inventory/stock-by-warehouse` | `reports.inventory.read` | Stock quantities and valuation grouped by warehouse facility. |
| `GET` | `/api/v1/reports/inventory/stock-by-product` | `reports.inventory.read` | Physical and available stock levels grouped by product SKU. |
| `GET` | `/api/v1/reports/inventory/low-stock` | `reports.inventory.read` | Low-stock items where available inventory is at or below reorder level. |
| `GET` | `/api/v1/reports/hr/headcount` | `reports.hr.read` | Employee workforce headcount broken down by department and employment status. |
| `GET` | `/api/v1/reports/payroll/summary` | `reports.payroll.read` | Payroll compensation summary, gross pay, deductions, net pay, and departmental costs. |
| `GET` | `/api/v1/reports/crm/leads` | `reports.crm.read` | CRM lead pipeline, sources, conversion counts, and conversion percentage. |
| `GET` | `/api/v1/reports/crm/pipeline` | `reports.crm.read` | Opportunity pipeline broken down by sales stage with weighted forecast valuation. |
| `GET` | `/api/v1/reports/export` | `reports.export` | Universal RFC 4180 CSV export endpoint parameterized by `report_type`. |

---

## 3. Domain Report Specifications

### 3.1 Executive Management Dashboard (`GET /api/v1/reports/dashboard`)
Returns unified executive metrics:
- **Finance**: Total posted journals, period debits, period credits, revenue, expenses, net profit.
- **Sales**: Total orders count, completed orders count, total gross & net revenue, quotations count, quotation conversion rate.
- **Procurement**: Total purchase orders, approved POs, total spend, goods receipts count.
- **Inventory**: Total products count, total inventory quantity, total inventory valuation, low stock items count.
- **HR**: Total workforce headcount, active employees count, inactive employees count.
- **Payroll**: Total payroll runs count, disbursed gross pay, disbursed net pay.
- **CRM**: Open leads count, converted leads count, active opportunities count, pipeline value, weighted pipeline value.

### 3.2 Finance Reports
- **Trial Balance**: Summarizes all active Chart of Accounts with opening balance, period debit sum, period credit sum, and net closing balance. Mathematically validates debit $\equiv$ credit equilibrium.
- **Profit & Loss**: Filters posted journals for `Revenue` and `Expense` accounts across specified date ranges or fiscal periods, presenting individual account lines and computing bottom-line net profit/loss.
- **Balance Sheet**: Aggregates `Asset`, `Liability`, and `Equity` accounts to present the financial health and balance equation ($\text{Assets} = \text{Liabilities} + \text{Equity}$).

### 3.3 Sales Reports
- **Sales Summary**: Aggregates sales order counts, total order values, discounts, and taxes with status breakdown (`Draft`, `Submitted`, `Approved`, `Dispatched`, `Closed`, `Cancelled`). Computes quotation conversion rates ($\frac{\text{Converted Quotations}}{\text{Total Quotations}} \times 100$).
- **Sales by Customer**: Aggregates customer lifetime spending, average order size, and transaction counts.
- **Sales by Product**: Reports total units sold and net sales generated per product SKU.

### 3.4 Procurement Reports
- **Procurement Summary**: Tracks total purchase order commitments, approved/received/cancelled orders, total spend, goods receipts, and purchase returns.
- **Purchases by Supplier**: Details total purchasing volume and spend allocated to each vendor.

### 3.5 Inventory Reports
- **Stock by Warehouse**: Total units and inventory valuation per warehouse facility.
- **Stock by Product**: Available vs. reserved stock levels and inventory valuation per SKU.
- **Low Stock Alerts**: Identifies products whose available stock is less than or equal to their configured `reorder_level`.

### 3.6 HR & Payroll Reports
- **Headcount Summary**: Total active, inactive, full-time, part-time, and contract employees, with departmental headcounts.
- **Payroll Cost Breakdown**: Summarizes gross salaries, employer/employee deductions, net disbursements, and total payroll expenses per department.

### 3.7 CRM Reports
- **Lead Metrics**: Total leads, new/contacted/qualified counts, converted lead totals, lead source distribution, and conversion efficiency.
- **Opportunity Pipeline**: Total deals, stage-by-stage distribution, total pipeline value, and probability-weighted pipeline forecast.

---

## 4. RBAC & Permissions

The following permissions are seeded in `app/db/seed_rbac.py` and mapped to system roles:

| Permission | Description | Assigned Roles |
| :--- | :--- | :--- |
| `reports.dashboard.read` | View Executive Dashboard | Admin, Finance Manager, Sales Manager, Procurement Manager, Inventory Manager, HR Manager |
| `reports.finance.read` | View Finance Reports | Admin, Finance Manager, Accountant, Finance Viewer |
| `reports.sales.read` | View Sales Reports | Admin, Sales Manager, Sales Representative, Sales Viewer |
| `reports.procurement.read` | View Procurement Reports | Admin, Procurement Manager, Procurement Specialist, Procurement Viewer |
| `reports.inventory.read` | View Inventory Reports | Admin, Inventory Manager, Warehouse Manager, Inventory Viewer |
| `reports.hr.read` | View HR Reports | Admin, HR Manager, HR Officer, HR Viewer |
| `reports.payroll.read` | View Payroll Reports | Admin, HR Manager, Payroll Officer |
| `reports.crm.read` | View CRM Reports | Admin, CRM Manager, Sales Representative, Sales Viewer |
| `reports.export` | Export reports to CSV | Admin, Finance Manager, Sales Manager, Procurement Manager, Inventory Manager, HR Manager |

---

## 5. Exports & Performance Guarantees

- **Streaming / Standard CSV**: Reports can be downloaded directly as CSV via `/api/v1/reports/export?report_type=<type>` complying with RFC 4180.
- **Zero In-Memory Table Scans**: Queries push aggregations down to PostgreSQL, avoiding loading entire transaction tables into application memory.
- **Zero Transaction Side-Effects**: Read queries use isolated async sessions with zero write locks or database mutations.
