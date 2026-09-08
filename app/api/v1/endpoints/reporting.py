from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.user import User
from app.schemas.reporting import (
    AccountBalancesReport,
    BalanceSheetReport,
    ExecutiveDashboardResponse,
    HeadcountSummaryReport,
    LeadReportSummary,
    LowStockSummaryReport,
    OpportunityPipelineReport,
    PayrollSummaryReport,
    ProfitLossReport,
    PurchaseOrderReportSummary,
    PurchasesBySupplierReport,
    ReportTypeEnum,
    SalesByCustomerReport,
    SalesByProductReport,
    SalesOrderReportSummary,
    SalesQuotationReportSummary,
    StockByProductReport,
    StockByWarehouseReport,
    TrialBalanceReportSummary,
)
from app.services.reporting_services import reporting_service

router = APIRouter()


# =========================================================================
# 1. EXECUTIVE MANAGEMENT DASHBOARD
# =========================================================================

@router.get("/dashboard", response_model=ExecutiveDashboardResponse)
async def get_management_dashboard(
    as_of_date: Optional[date] = Query(None, description="Cutoff date for dashboard calculation"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("reports.dashboard.read")),
):
    """
    Consolidated executive management dashboard summarizing operational metrics across all ERP domains.
    """
    return await reporting_service.get_dashboard(db, as_of_date=as_of_date)


# =========================================================================
# 2. FINANCE REPORTS
# =========================================================================

@router.get("/finance/profit-loss", response_model=ProfitLossReport)
async def get_profit_loss_report(
    from_date: Optional[date] = Query(None, description="Start date"),
    to_date: Optional[date] = Query(None, description="End date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("reports.finance.read")),
):
    """
    Profit & Loss statement reporting Revenues, Expenses, and Net Profit.
    """
    return await reporting_service.get_profit_loss(db, from_date=from_date, to_date=to_date)


@router.get("/finance/balance-sheet", response_model=BalanceSheetReport)
async def get_balance_sheet_report(
    as_of_date: Optional[date] = Query(None, description="As of date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("reports.finance.read")),
):
    """
    Balance Sheet reporting Assets, Liabilities, and Equity.
    """
    return await reporting_service.get_balance_sheet(db, as_of_date=as_of_date)


@router.get("/finance/trial-balance", response_model=TrialBalanceReportSummary)
async def get_trial_balance_report(
    as_of_date: Optional[date] = Query(None, description="As of date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("reports.finance.read")),
):
    """
    Trial Balance verifying debit and credit balancing across all active ledger accounts.
    """
    return await reporting_service.get_trial_balance(db, as_of_date=as_of_date)


@router.get("/finance/account-balances", response_model=AccountBalancesReport)
async def get_account_balances_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("reports.finance.read")),
):
    """
    Current account balances across the Chart of Accounts.
    """
    return await reporting_service.get_account_balances(db)


# =========================================================================
# 3. SALES REPORTS
# =========================================================================

@router.get("/sales/summary", response_model=SalesOrderReportSummary)
async def get_sales_order_summary(
    from_date: Optional[date] = Query(None, description="Start date"),
    to_date: Optional[date] = Query(None, description="End date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("reports.sales.read")),
):
    """
    Sales order totals, discounts, taxes, and status breakdown.
    """
    return await reporting_service.get_sales_summary(db, from_date=from_date, to_date=to_date)


@router.get("/sales/by-customer", response_model=SalesByCustomerReport)
async def get_sales_by_customer(
    from_date: Optional[date] = Query(None, description="Start date"),
    to_date: Optional[date] = Query(None, description="End date"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("reports.sales.read")),
):
    """
    Sales performance aggregated by Customer.
    """
    return await reporting_service.get_sales_by_customer(db, from_date=from_date, to_date=to_date, limit=limit)


@router.get("/sales/by-product", response_model=SalesByProductReport)
async def get_sales_by_product(
    from_date: Optional[date] = Query(None, description="Start date"),
    to_date: Optional[date] = Query(None, description="End date"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("reports.sales.read")),
):
    """
    Sales performance aggregated by Product.
    """
    return await reporting_service.get_sales_by_product(db, from_date=from_date, to_date=to_date, limit=limit)


@router.get("/sales/quotations", response_model=SalesQuotationReportSummary)
async def get_sales_quotations_summary(
    from_date: Optional[date] = Query(None, description="Start date"),
    to_date: Optional[date] = Query(None, description="End date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("reports.sales.read")),
):
    """
    Sales quotation pipeline and conversion metrics.
    """
    return await reporting_service.get_sales_quotations(db, from_date=from_date, to_date=to_date)


# =========================================================================
# 4. PROCUREMENT REPORTS
# =========================================================================

@router.get("/procurement/summary", response_model=PurchaseOrderReportSummary)
async def get_purchase_order_summary(
    from_date: Optional[date] = Query(None, description="Start date"),
    to_date: Optional[date] = Query(None, description="End date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("reports.procurement.read")),
):
    """
    Procurement purchase order spend and status distribution.
    """
    return await reporting_service.get_procurement_summary(db, from_date=from_date, to_date=to_date)


@router.get("/procurement/by-supplier", response_model=PurchasesBySupplierReport)
async def get_purchases_by_supplier(
    from_date: Optional[date] = Query(None, description="Start date"),
    to_date: Optional[date] = Query(None, description="End date"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("reports.procurement.read")),
):
    """
    Purchasing and spend breakdown by Supplier.
    """
    return await reporting_service.get_purchases_by_supplier(db, from_date=from_date, to_date=to_date, limit=limit)


# =========================================================================
# 5. INVENTORY REPORTS
# =========================================================================

@router.get("/inventory/by-warehouse", response_model=StockByWarehouseReport)
async def get_stock_by_warehouse(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("reports.inventory.read")),
):
    """
    Inventory quantities and valuations aggregated per Warehouse facility.
    """
    return await reporting_service.get_stock_by_warehouse(db)


@router.get("/inventory/by-product", response_model=StockByProductReport)
async def get_stock_by_product(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("reports.inventory.read")),
):
    """
    Stock levels (on-hand, reserved, available) and valuations per Product.
    """
    return await reporting_service.get_stock_by_product(db, limit=limit)


@router.get("/inventory/low-stock", response_model=LowStockSummaryReport)
async def get_low_stock_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("reports.inventory.read")),
):
    """
    Inventory items currently at or below safety stock / reorder thresholds.
    """
    return await reporting_service.get_low_stock_summary(db)


# =========================================================================
# 6. HR & PAYROLL REPORTS
# =========================================================================

@router.get("/hr/headcount", response_model=HeadcountSummaryReport)
async def get_hr_headcount_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("reports.hr.read")),
):
    """
    Organization headcount summary across Departments, Designations, and Employment Types.
    """
    return await reporting_service.get_hr_headcount(db)


@router.get("/payroll/summary", response_model=PayrollSummaryReport)
async def get_payroll_summary(
    from_date: Optional[date] = Query(None, description="Start date"),
    to_date: Optional[date] = Query(None, description="End date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("reports.payroll.read")),
):
    """
    Payroll summary with gross wages, deductions, net pay, and departmental spend.
    """
    return await reporting_service.get_payroll_summary(db, from_date=from_date, to_date=to_date)


# =========================================================================
# 7. CRM REPORTS
# =========================================================================

@router.get("/crm/leads", response_model=LeadReportSummary)
async def get_crm_leads_summary(
    from_date: Optional[date] = Query(None, description="Start date"),
    to_date: Optional[date] = Query(None, description="End date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("reports.crm.read")),
):
    """
    Lead volume, status transitions, source distribution, and conversion rates.
    """
    return await reporting_service.get_crm_leads(db, from_date=from_date, to_date=to_date)


@router.get("/crm/pipeline", response_model=OpportunityPipelineReport)
async def get_crm_pipeline_report(
    from_date: Optional[date] = Query(None, description="Start date"),
    to_date: Optional[date] = Query(None, description="End date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("reports.crm.read")),
):
    """
    Commercial opportunity pipeline values, stage distributions, and weighted forecasts.
    """
    return await reporting_service.get_crm_pipeline(db, from_date=from_date, to_date=to_date)


# =========================================================================
# 8. MULTI-REPORT CSV EXPORT
# =========================================================================

@router.get("/export")
async def export_report_csv(
    report_type: ReportTypeEnum = Query(..., description="Report type identifier"),
    from_date: Optional[date] = Query(None, description="Start date"),
    to_date: Optional[date] = Query(None, description="End date"),
    as_of_date: Optional[date] = Query(None, description="As of date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("reports.export")),
):
    """
    Export reporting dataset as an RFC 4180 compliant CSV stream.
    """
    csv_content = await reporting_service.export_report(
        db,
        report_type=report_type.value,
        from_date=from_date,
        to_date=to_date,
        as_of_date=as_of_date,
    )
    filename = f"{report_type.value}_{date.today().isoformat()}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
