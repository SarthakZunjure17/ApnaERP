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
api_router.include_router(employee_documents.router, prefix="", tags=["Employee Document Management"])
api_router.include_router(positions.router, prefix="", tags=["Position Management"])
api_router.include_router(hr_configurations.router, prefix="", tags=["HR Configuration & Policies"])
api_router.include_router(shifts.router, prefix="/shifts", tags=["Shift Management"])
api_router.include_router(shift_assignment.router, prefix="/shift-assignments", tags=["Shift Assignment & Scheduling"])
api_router.include_router(holidays.router, prefix="/holidays", tags=["Holiday Calendar"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["Enterprise Attendance Engine"])
api_router.include_router(leave_type.router, prefix="/leave-types", tags=["Enterprise Leave Types & Policies"])
api_router.include_router(leave_balance.router, prefix="/leave-balances", tags=["Enterprise Leave Balance Management"])
api_router.include_router(leave_request.router, prefix="/leave-requests", tags=["Enterprise Leave Request Workflow"])
api_router.include_router(approval.router, prefix="", tags=["Enterprise Approval Engine"])
api_router.include_router(salary_component.router, prefix="", tags=["Enterprise Salary Components"])
api_router.include_router(salary_structure.router, prefix="", tags=["Enterprise Salary Structures"])
api_router.include_router(employee_compensation.router, prefix="", tags=["Employee Compensation Management"])
api_router.include_router(payroll_engine.router, prefix="", tags=["Enterprise Payroll Processing Engine"])
api_router.include_router(payroll_run.router, prefix="/payroll-runs", tags=["Enterprise Payroll Runs"])
api_router.include_router(payslip.router, prefix="", tags=["Enterprise Employee Payslips"])
api_router.include_router(country.router, prefix="", tags=["Country Jurisdiction Management"])
api_router.include_router(statutory_rule.router, prefix="", tags=["Statutory Compliance Rules & Slabs"])
api_router.include_router(employee_statutory_profile.router, prefix="", tags=["Employee Statutory Profiles"])
api_router.include_router(payroll_adjustment.router, prefix="", tags=["Payroll Adjustments"])
api_router.include_router(payroll_report.router, prefix="", tags=["Payroll Reports"])
api_router.include_router(payroll_analytics.router, prefix="", tags=["Payroll Analytics"])
api_router.include_router(bank_export.router, prefix="", tags=["Bank Export"])
api_router.include_router(payroll_closing.router, prefix="", tags=["Payroll Closing"])
api_router.include_router(financial_integration.router, prefix="", tags=["Financial Integration"])

# Inventory Foundation Routers
api_router.include_router(category.router, prefix="/categories", tags=["Product Categories"])
api_router.include_router(unit_of_measure.router, prefix="/units-of-measure", tags=["Units of Measure"])
api_router.include_router(brand.router, prefix="/brands", tags=["Brands"])
api_router.include_router(warehouse.router, prefix="/warehouses", tags=["Warehouses"])
api_router.include_router(storage_location.router, prefix="/storage-locations", tags=["Storage Locations"])
api_router.include_router(product.router, prefix="/products", tags=["Product Master"])
api_router.include_router(product_attribute.router, prefix="/product-attributes", tags=["Product Attributes"])
api_router.include_router(product_document.router, prefix="", tags=["Product Documents"])

# Inventory Stock Engine Routers
api_router.include_router(inventory_transaction_type.router, prefix="/inventory/transaction-types", tags=["Inventory Transaction Types"])
api_router.include_router(stock_ledger.router, prefix="/inventory/ledger", tags=["Stock Ledger"])
api_router.include_router(opening_stock.router, prefix="/inventory/opening-stock", tags=["Opening Stock"])
api_router.include_router(inventory_adjustment.router, prefix="/inventory/adjustments", tags=["Inventory Adjustments"])
api_router.include_router(stock_balance.router, prefix="/inventory/balances", tags=["Stock Balances & Projections"])
