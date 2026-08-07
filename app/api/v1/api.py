from fastapi import APIRouter

from app.api.v1.endpoints import (
    approval,
    attendance,
    audit,
    auth,
    bank_export,
    batches,
    brand,
    category,
    country,
    crm_activities,
    crm_analytics,
    crm_campaigns,
    crm_import_export,
    crm_leads,
    crm_meetings,
    crm_opportunities,
    crm_search,
    crm_tasks,
    customers,
    cycle_counts,
    delivery_orders,
    departments,
    discounts,
    employee_compensation,
    employee_documents,
    employee_statutory_profile,
    employees,
    files,
    finance_accounts,
    finance_analytics,
    finance_assets,
    finance_banks,
    finance_budgets,
    finance_cost_centers,
    finance_currencies,
    finance_fiscal,
    finance_journals,
    finance_payables,
    finance_payments,
    finance_posting_rules,
    finance_receivables,
    finance_reconciliation,
    finance_search,
    finance_statements,
    finance_taxes,
    financial_integration,
    goods_issue,
    goods_receipt,
    health,
    holidays,
    hr_configurations,
    inventory_adjustment,
    inventory_analytics,
    inventory_import_export,
    inventory_reports,
    inventory_search,
    inventory_transaction_type,
    leave_balance,
    leave_request,
    leave_type,
    lots,
    notifications,
    opening_stock,
    payroll_adjustment,
    payroll_analytics,
    payroll_closing,
    payroll_engine,
    payroll_report,
    payroll_run,
    payslip,
    positions,
    pricing,
    procurement_analytics,
    procurement_import_export,
    procurement_reports,
    procurement_search,
    product,
    product_attribute,
    product_document,
    purchase_orders,
    purchase_requisitions,
    purchase_returns,
    quotations,
    rbac,
    reporting_analytics,
    reporting_builder,
    reporting_charts,
    reporting_dashboards,
    reporting_exports,
    reporting_kpis,
    reporting_schedules,
    reporting_search,
    api_keys,
    webhooks,
    providers,
    storage,
    import_export,
    monitoring,
    backups,
    system_config,
    rfqs,
    root,
    salary_component,
    salary_structure,
    sales_analytics,
    sales_import_export,
    sales_orders,
    sales_reports,
    sales_returns,
    sales_search,
    serial_numbers,
    shift_assignment,
    shifts,
    statutory_rule,
    stock_balance,
    stock_ledger,
    stock_reservations,
    stock_transfer,
    storage_location,
    supplier_quotations,
    suppliers,
    templates,
    unit_of_measure,
    warehouse,
)

api_router = APIRouter()

api_router.include_router(root.router, tags=["Root"])
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(departments.router, prefix="/departments", tags=["Departments"])
api_router.include_router(employees.router, prefix="/employees", tags=["Employees"])
api_router.include_router(employee_documents.router, prefix="/employee-documents", tags=["Employee Documents"])
api_router.include_router(positions.router, prefix="/positions", tags=["Job Positions"])
api_router.include_router(hr_configurations.router, prefix="/hr-configurations", tags=["HR Configurations"])
api_router.include_router(shifts.router, prefix="/shifts", tags=["Shifts"])
api_router.include_router(holidays.router, prefix="/holidays", tags=["Holidays"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])
api_router.include_router(shift_assignment.router, prefix="/shift-assignments", tags=["Shift Assignments"])
api_router.include_router(leave_type.router, prefix="/leave-types", tags=["Leave Types"])
api_router.include_router(leave_balance.router, prefix="/leave-balances", tags=["Leave Balances"])
api_router.include_router(leave_request.router, prefix="/leave-requests", tags=["Leave Requests"])
api_router.include_router(approval.router, prefix="/approvals", tags=["Approval Workflows"])
api_router.include_router(salary_component.router, prefix="/salary-components", tags=["Salary Components"])
api_router.include_router(salary_structure.router, prefix="/salary-structures", tags=["Salary Structures"])
api_router.include_router(employee_compensation.router, prefix="/employee-compensations", tags=["Employee Compensation"])
api_router.include_router(payroll_engine.router, prefix="/payroll", tags=["Payroll Engine"])
api_router.include_router(payroll_run.router, prefix="/payroll-runs", tags=["Payroll Runs"])
api_router.include_router(payslip.router, prefix="/payslips", tags=["Payslips"])
api_router.include_router(country.router, prefix="/countries", tags=["Countries"])
api_router.include_router(statutory_rule.router, prefix="/statutory-rules", tags=["Statutory Rules"])
api_router.include_router(employee_statutory_profile.router, prefix="/employee-statutory-profiles", tags=["Employee Statutory Profiles"])
api_router.include_router(payroll_adjustment.router, prefix="/payroll-adjustments", tags=["Payroll Adjustments"])
api_router.include_router(payroll_report.router, prefix="/payroll-reports", tags=["Payroll Reports"])
api_router.include_router(payroll_analytics.router, prefix="/payroll-analytics", tags=["Payroll Analytics"])
api_router.include_router(payroll_closing.router, prefix="/payroll-closings", tags=["Payroll Closings"])
api_router.include_router(financial_integration.router, prefix="/financial-integration", tags=["Financial Integration"])
api_router.include_router(bank_export.router, prefix="/bank-exports", tags=["Bank Export Integration"])

# Platform Utilities
api_router.include_router(rbac.router, prefix="/rbac", tags=["RBAC Management"])
api_router.include_router(audit.router, prefix="/audit-logs", tags=["Audit Logs"])
api_router.include_router(files.router, prefix="/files", tags=["File Storage Engine"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notification Engine"])

# Product Master Routers
api_router.include_router(category.router, prefix="/inventory/categories", tags=["Product Categories"])
api_router.include_router(unit_of_measure.router, prefix="/inventory/uoms", tags=["Units of Measure"])
api_router.include_router(brand.router, prefix="/inventory/brands", tags=["Brands"])
api_router.include_router(warehouse.router, prefix="/inventory/warehouses", tags=["Warehouses"])
api_router.include_router(storage_location.router, prefix="/inventory/locations", tags=["Storage Locations"])
api_router.include_router(product.router, prefix="/inventory/products", tags=["Products"])
api_router.include_router(product_attribute.router, prefix="/inventory/attributes", tags=["Product Attributes"])
api_router.include_router(product_document.router, prefix="/inventory/documents", tags=["Product Documents"])

# Stock Engine Routers
api_router.include_router(inventory_transaction_type.router, prefix="/inventory/transaction-types", tags=["Transaction Types"])
api_router.include_router(opening_stock.router, prefix="/inventory/opening-stocks", tags=["Opening Stocks"])
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

# Finance Core Routers
api_router.include_router(finance_accounts.router, prefix="/finance/accounts", tags=["Chart of Accounts & Groups"])
api_router.include_router(finance_fiscal.router, prefix="/finance/fiscal", tags=["Fiscal Years & Periods"])
api_router.include_router(finance_currencies.router, prefix="/finance/currencies", tags=["Currencies & Exchange Rates"])
api_router.include_router(finance_cost_centers.router, prefix="/finance/cost-centers", tags=["Cost Centers & Dimensions"])
api_router.include_router(finance_journals.router, prefix="/finance/journals", tags=["Journal Types & Journal Entries"])
api_router.include_router(finance_posting_rules.router, prefix="/finance/posting-rules", tags=["Posting Rules"])
api_router.include_router(finance_taxes.router, prefix="/finance/taxes", tags=["Tax Categories & Rates"])
api_router.include_router(finance_search.router, prefix="/finance/search", tags=["Global Finance Search"])

# Finance Operations & Financial Reporting Routers
api_router.include_router(finance_receivables.router, prefix="/finance/receivables", tags=["Accounts Receivable"])
api_router.include_router(finance_payables.router, prefix="/finance/payables", tags=["Accounts Payable"])
api_router.include_router(finance_payments.router, prefix="/finance/payments", tags=["Payments & Vouchers"])
api_router.include_router(finance_banks.router, prefix="/finance/banks", tags=["Bank Management"])
api_router.include_router(finance_reconciliation.router, prefix="/finance/reconciliation", tags=["Bank Reconciliation"])
api_router.include_router(finance_assets.router, prefix="/finance/assets", tags=["Fixed Assets & Depreciation"])
api_router.include_router(finance_budgets.router, prefix="/finance/budgets", tags=["Budget Management"])
api_router.include_router(finance_statements.router, prefix="/finance/statements", tags=["Financial Statements"])
api_router.include_router(finance_analytics.router, prefix="/finance/analytics", tags=["Finance Executive Analytics"])

# Enterprise Reporting & Business Intelligence Routers
api_router.include_router(reporting_dashboards.router, prefix="/reporting/dashboards", tags=["Enterprise Dashboards"])
api_router.include_router(reporting_kpis.router, prefix="/reporting/kpis", tags=["KPI Engine"])
api_router.include_router(reporting_analytics.router, prefix="/reporting/analytics", tags=["Enterprise Analytics"])
api_router.include_router(reporting_builder.router, prefix="/reporting/reports", tags=["Dynamic Report Builder"])
api_router.include_router(reporting_schedules.router, prefix="/reporting/schedules", tags=["Scheduled Reports"])
api_router.include_router(reporting_exports.router, prefix="/reporting/exports", tags=["Export Engine"])
api_router.include_router(reporting_charts.router, prefix="/reporting/charts", tags=["Chart Visualization Engine"])
api_router.include_router(reporting_search.router, prefix="/reporting/search", tags=["Global Reporting Search"])

# Infrastructure & Production Readiness Routers
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["API Key Management"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks Engine"])
api_router.include_router(providers.router, prefix="/providers", tags=["Provider Configurations"])
api_router.include_router(storage.router, prefix="/storage", tags=["Pluggable Storage Engine"])
api_router.include_router(import_export.router, prefix="/import-export", tags=["Bulk Import Export Platform"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["Observability & Prometheus Metrics"])
api_router.include_router(backups.router, prefix="/backups", tags=["Backup & Restore Management"])
api_router.include_router(system_config.router, prefix="/system/config", tags=["System Configuration"])


