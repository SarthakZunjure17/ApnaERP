from fastapi import APIRouter
from app.api.v1.endpoints import (
    approval,
    attendance,
    audit,
    auth,
    country,
    departments,
    employee_documents,
    employees,
    employee_compensation,
    employee_statutory_profile,
    files,
    financial_integration,
    health,
    holidays,
    hr_configurations,
    leave_type,
    leave_balance,
    leave_request,
    notifications,
    bank_export,
    payroll_adjustment,
    payroll_analytics,
    payroll_closing,
    payroll_engine,
    payroll_report,
    payroll_run,
    payslip,
    positions,
    rbac,
    root,
    salary_component,
    salary_structure,
    shift_assignment,
    shifts,
    statutory_rule,
    templates,
    category,
    unit_of_measure,
    brand,
    warehouse,
    storage_location,
    product,
    product_attribute,
    product_document,
    inventory_transaction_type,
    stock_ledger,
    opening_stock,
    inventory_adjustment,
    stock_balance,
    goods_receipt,
    goods_issue,
    stock_transfer,
    batches,
    serial_numbers,
    lots,
    stock_reservations,
    cycle_counts,
    inventory_reports,
    inventory_analytics,
    inventory_search,
    inventory_import_export,
    suppliers,
    purchase_requisitions,
    rfqs,
    supplier_quotations,
    purchase_orders,
    purchase_returns,
    procurement_reports,
    procurement_analytics,
    procurement_search,
    procurement_import_export,
    customers,
    quotations,
    sales_orders,
    delivery_orders,
    sales_returns,
    pricing,
    discounts,
    sales_reports,
    sales_analytics,
    sales_search,
    sales_import_export,
    crm_leads,
    crm_opportunities,
    crm_activities,
    crm_meetings,
    crm_tasks,
    crm_campaigns,
    crm_analytics,
    crm_search,
    crm_import_export,
)


api_router = APIRouter()

# Include endpoint routers
api_router.include_router(root.router, prefix="", tags=["Root"])
api_router.include_router(health.router, prefix="", tags=["Health Check"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(rbac.router, prefix="", tags=["Role-Based Access Control"])
api_router.include_router(audit.router, prefix="", tags=["Audit Logging"])
api_router.include_router(files.router, prefix="", tags=["File & Document Management"])
api_router.include_router(notifications.router, prefix="", tags=["Notification System"])
api_router.include_router(templates.router, prefix="", tags=["Notification Templates"])
api_router.include_router(departments.router, prefix="/departments", tags=["Department Management"])
api_router.include_router(employees.router, prefix="/employees", tags=["Employee Management"])
api_router.include_router(employee_documents.router, prefix="/employees", tags=["Digital Personnel Files"])
api_router.include_router(positions.router, prefix="/positions", tags=["Position Management"])
api_router.include_router(hr_configurations.router, prefix="/hr-configurations", tags=["HR Configuration & Policies"])
api_router.include_router(shifts.router, prefix="/shifts", tags=["Shift Management"])
api_router.include_router(holidays.router, prefix="/holidays", tags=["Holiday Calendar"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["Attendance Engine"])
api_router.include_router(shift_assignment.router, prefix="/shift-assignments", tags=["Shift Assignment"])
api_router.include_router(leave_type.router, prefix="/leave-types", tags=["Leave Types Configuration"])
api_router.include_router(leave_balance.router, prefix="/leave-balances", tags=["Leave Balance Management"])
api_router.include_router(leave_request.router, prefix="/leave-requests", tags=["Leave Request Workflow"])
api_router.include_router(approval.router, prefix="/approval", tags=["Enterprise Approval Engine"])
api_router.include_router(salary_component.router, prefix="/salary-components", tags=["Salary Components Master"])
api_router.include_router(salary_structure.router, prefix="/salary-structures", tags=["Salary Structure Templates"])
api_router.include_router(employee_compensation.router, prefix="/employee-compensations", tags=["Employee Compensation Assignment"])
api_router.include_router(payroll_engine.router, prefix="/payroll", tags=["Payroll Processing Engine"])
api_router.include_router(payroll_run.router, prefix="/payroll-runs", tags=["Payroll Runs Management"])
api_router.include_router(payslip.router, prefix="/payslips", tags=["Employee Payslips Suite"])
api_router.include_router(country.router, prefix="/countries", tags=["Country & Tax Masters"])
api_router.include_router(statutory_rule.router, prefix="/statutory-rules", tags=["Statutory Compliance Engine"])
api_router.include_router(employee_statutory_profile.router, prefix="/employee-statutory-profiles", tags=["Employee Statutory Assignments"])
api_router.include_router(payroll_adjustment.router, prefix="/payroll-adjustments", tags=["Payroll Adjustments"])
api_router.include_router(payroll_report.router, prefix="/payroll-reports", tags=["Payroll Reports"])
api_router.include_router(payroll_analytics.router, prefix="/payroll-analytics", tags=["Payroll Analytics Dashboard"])
api_router.include_router(payroll_closing.router, prefix="/payroll-closing", tags=["Payroll Month End Closing"])
api_router.include_router(bank_export.router, prefix="/bank-export", tags=["Bank Payment Files Export"])
api_router.include_router(financial_integration.router, prefix="/financial-integration", tags=["Financial Posting Queue"])

# Inventory Foundation Routers
api_router.include_router(category.router, prefix="/inventory/categories", tags=["Product Categories"])
api_router.include_router(unit_of_measure.router, prefix="/inventory/units", tags=["Units of Measure"])
api_router.include_router(brand.router, prefix="/inventory/brands", tags=["Product Brands"])
api_router.include_router(warehouse.router, prefix="/inventory/warehouses", tags=["Warehouse Facilities"])
api_router.include_router(storage_location.router, prefix="/inventory/locations", tags=["Storage Locations"])
api_router.include_router(product.router, prefix="/inventory/products", tags=["Product Master"])
api_router.include_router(product_attribute.router, prefix="/inventory/attributes", tags=["Product Attributes"])
api_router.include_router(product_document.router, prefix="/inventory/documents", tags=["Product Documents"])

# Inventory Stock Engine Routers
api_router.include_router(inventory_transaction_type.router, prefix="/inventory/transaction-types", tags=["Inventory Transaction Types"])
api_router.include_router(opening_stock.router, prefix="/inventory/opening-stock", tags=["Opening Stock Entry"])
api_router.include_router(stock_ledger.router, prefix="/inventory/ledger", tags=["Stock Ledger Engine"])
api_router.include_router(inventory_adjustment.router, prefix="/inventory/adjustments", tags=["Stock Adjustments"])
api_router.include_router(stock_balance.router, prefix="/inventory/balance", tags=["Stock Balance Snapshot"])

# Warehouse Operations Engine Routers
api_router.include_router(goods_receipt.router, prefix="/inventory/goods-receipts", tags=["Goods Receipt Note (GRN)"])
api_router.include_router(goods_issue.router, prefix="/inventory/goods-issues", tags=["Goods Issue Note (GIN)"])
api_router.include_router(stock_transfer.router, prefix="/inventory/stock-transfers", tags=["Inter-Warehouse Stock Transfers"])

# Inventory Advanced Domain Completion Routers
api_router.include_router(batches.router, prefix="/inventory/batches", tags=["Batch Management"])
api_router.include_router(serial_numbers.router, prefix="/inventory/serials", tags=["Serial Number Tracking"])
api_router.include_router(lots.router, prefix="/inventory/lots", tags=["Lot Tracking"])
api_router.include_router(stock_reservations.router, prefix="/inventory/reservations", tags=["Stock Reservations"])
api_router.include_router(cycle_counts.router, prefix="/inventory/cycle-counts", tags=["Cycle Counting"])
api_router.include_router(inventory_reports.router, prefix="/inventory/reports", tags=["Inventory Reports"])
api_router.include_router(inventory_analytics.router, prefix="/inventory/analytics", tags=["Inventory Analytics"])
api_router.include_router(inventory_search.router, prefix="/inventory/search", tags=["Global Inventory Search"])
api_router.include_router(inventory_import_export.router, prefix="/inventory/import-export", tags=["Inventory Import Export"])

# Procurement Domain Completion Routers
api_router.include_router(suppliers.router, prefix="/procurement/suppliers", tags=["Supplier Master & Ratings"])
api_router.include_router(purchase_requisitions.router, prefix="/procurement/requisitions", tags=["Purchase Requisitions"])
api_router.include_router(rfqs.router, prefix="/procurement/rfqs", tags=["Requests For Quotations (RFQ)"])
api_router.include_router(supplier_quotations.router, prefix="/procurement/quotations", tags=["Supplier Quotations"])
api_router.include_router(purchase_orders.router, prefix="/procurement/orders", tags=["Purchase Orders & Receiving"])
api_router.include_router(purchase_returns.router, prefix="/procurement/returns", tags=["Purchase Returns & Stock Reversals"])
api_router.include_router(procurement_reports.router, prefix="/procurement/reports", tags=["Procurement Reports"])
api_router.include_router(procurement_analytics.router, prefix="/procurement/analytics", tags=["Procurement Analytics"])
api_router.include_router(procurement_search.router, prefix="/procurement/search", tags=["Global Procurement Search"])
api_router.include_router(procurement_import_export.router, prefix="/procurement/import-export", tags=["Procurement Import Export"])

# Sales Domain Completion Routers
api_router.include_router(customers.router, prefix="/sales/customers", tags=["Customer Master"])
api_router.include_router(quotations.router, prefix="/sales/quotations", tags=["Sales Quotations"])
api_router.include_router(sales_orders.router, prefix="/sales/orders", tags=["Sales Orders"])
api_router.include_router(delivery_orders.router, prefix="/sales/deliveries", tags=["Delivery Orders & Dispatches"])
api_router.include_router(sales_returns.router, prefix="/sales/returns", tags=["Sales Returns & Stock Reversals"])
api_router.include_router(pricing.router, prefix="/sales/pricing", tags=["Price Lists & Rules"])
api_router.include_router(discounts.router, prefix="/sales/discounts", tags=["Discount Engine Rules"])
api_router.include_router(sales_reports.router, prefix="/sales/reports", tags=["Sales Reports"])
api_router.include_router(sales_analytics.router, prefix="/sales/analytics", tags=["Sales Analytics"])
api_router.include_router(sales_search.router, prefix="/sales/search", tags=["Global Sales Search"])
api_router.include_router(sales_import_export.router, prefix="/sales/import-export", tags=["Sales Import Export"])

# CRM Domain Completion Routers
api_router.include_router(crm_leads.router, prefix="/crm/leads", tags=["Lead Management & Conversion"])
api_router.include_router(crm_opportunities.router, prefix="/crm/opportunities", tags=["Opportunity Pipeline"])
api_router.include_router(crm_activities.router, prefix="/crm/activities", tags=["Activity Management"])
api_router.include_router(crm_meetings.router, prefix="/crm/meetings", tags=["Calendar & Meetings"])
api_router.include_router(crm_tasks.router, prefix="/crm/tasks", tags=["Task Management & Dependencies"])
api_router.include_router(crm_campaigns.router, prefix="/crm/campaigns", tags=["Marketing Campaign Management"])
api_router.include_router(crm_analytics.router, prefix="/crm/analytics", tags=["CRM Executive Analytics"])
api_router.include_router(crm_search.router, prefix="/crm/search", tags=["Global CRM Search"])
api_router.include_router(crm_import_export.router, prefix="/crm/import-export", tags=["CRM Import Export"])
