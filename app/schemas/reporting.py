import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# =========================================================================
# 1. EXECUTIVE MANAGEMENT DASHBOARD SCHEMAS
# =========================================================================

class DashboardHRMetrics(BaseModel):
    total_employees: int = 0
    active_employees: int = 0
    total_departments: int = 0


class DashboardCRMMetrics(BaseModel):
    open_leads: int = 0
    total_leads: int = 0
    active_opportunities: int = 0
    pipeline_value: Decimal = Decimal("0.00")
    weighted_forecast_value: Decimal = Decimal("0.00")


class DashboardSalesMetrics(BaseModel):
    total_orders_count: int = 0
    total_sales_revenue: Decimal = Decimal("0.00")
    pending_orders_count: int = 0
    average_order_value: Decimal = Decimal("0.00")


class DashboardProcurementMetrics(BaseModel):
    total_pos_count: int = 0
    total_spend: Decimal = Decimal("0.00")
    pending_pos_count: int = 0


class DashboardInventoryMetrics(BaseModel):
    total_products_count: int = 0
    total_warehouses_count: int = 0
    total_on_hand_quantity: Decimal = Decimal("0.00")
    total_inventory_valuation: Decimal = Decimal("0.00")
    low_stock_items_count: int = 0


class DashboardFinanceMetrics(BaseModel):
    total_revenue: Decimal = Decimal("0.00")
    total_expenses: Decimal = Decimal("0.00")
    net_operating_income: Decimal = Decimal("0.00")
    posted_journals_count: int = 0


class DashboardPayrollMetrics(BaseModel):
    total_payroll_runs_count: int = 0
    total_payroll_cost: Decimal = Decimal("0.00")
    total_net_disbursed: Decimal = Decimal("0.00")


class ExecutiveDashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    as_of_date: date
    hr: DashboardHRMetrics
    crm: DashboardCRMMetrics
    sales: DashboardSalesMetrics
    procurement: DashboardProcurementMetrics
    inventory: DashboardInventoryMetrics
    finance: DashboardFinanceMetrics
    payroll: DashboardPayrollMetrics


# =========================================================================
# 2. FINANCE REPORT SCHEMAS
# =========================================================================

class ProfitLossAccountLine(BaseModel):
    account_id: uuid.UUID
    account_code: str
    account_name: str
    account_group_name: Optional[str] = None
    account_type: str
    amount: Decimal


class ProfitLossReport(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_revenue: Decimal = Decimal("0.00")
    total_expenses: Decimal = Decimal("0.00")
    net_profit: Decimal = Decimal("0.00")
    revenue_lines: List[ProfitLossAccountLine] = []
    expense_lines: List[ProfitLossAccountLine] = []


class BalanceSheetAccountLine(BaseModel):
    account_id: uuid.UUID
    account_code: str
    account_name: str
    account_group_name: Optional[str] = None
    account_type: str
    balance: Decimal


class BalanceSheetReport(BaseModel):
    as_of_date: date
    total_assets: Decimal = Decimal("0.00")
    total_liabilities: Decimal = Decimal("0.00")
    total_equity: Decimal = Decimal("0.00")
    total_liabilities_and_equity: Decimal = Decimal("0.00")
    is_balanced: bool = True
    asset_lines: List[BalanceSheetAccountLine] = []
    liability_lines: List[BalanceSheetAccountLine] = []
    equity_lines: List[BalanceSheetAccountLine] = []


class TrialBalanceSummaryItem(BaseModel):
    account_id: uuid.UUID
    account_code: str
    account_name: str
    account_type: str
    opening_balance: Decimal
    period_debit: Decimal
    period_credit: Decimal
    debit_balance: Decimal
    credit_balance: Decimal


class TrialBalanceReportSummary(BaseModel):
    as_of_date: date
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool
    accounts_count: int
    lines: List[TrialBalanceSummaryItem] = []


class AccountBalanceItem(BaseModel):
    account_id: uuid.UUID
    account_code: str
    account_name: str
    account_type: str
    currency_code: str
    current_balance: Decimal
    is_active: bool


class AccountBalancesReport(BaseModel):
    as_of_date: date
    total_accounts: int
    total_debit_balance: Decimal
    total_credit_balance: Decimal
    accounts: List[AccountBalanceItem] = []


# =========================================================================
# 3. SALES REPORT SCHEMAS
# =========================================================================

class SalesOrderStatusItem(BaseModel):
    status: str
    order_count: int
    total_amount: Decimal


class SalesOrderReportSummary(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_orders: int = 0
    total_gross_amount: Decimal = Decimal("0.00")
    total_discount_amount: Decimal = Decimal("0.00")
    total_tax_amount: Decimal = Decimal("0.00")
    total_net_amount: Decimal = Decimal("0.00")
    average_order_value: Decimal = Decimal("0.00")
    status_breakdown: List[SalesOrderStatusItem] = []


class SalesByCustomerItem(BaseModel):
    customer_id: uuid.UUID
    customer_code: str
    customer_name: str
    order_count: int
    total_spent: Decimal
    average_order_value: Decimal
    outstanding_balance: Decimal = Decimal("0.00")


class SalesByCustomerReport(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_customers: int
    total_revenue: Decimal
    customers: List[SalesByCustomerItem] = []


class SalesByProductItem(BaseModel):
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    units_sold: Decimal
    total_revenue: Decimal
    average_price: Decimal


class SalesByProductReport(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_products: int
    total_units_sold: Decimal
    total_revenue: Decimal
    products: List[SalesByProductItem] = []


class SalesQuotationReportSummary(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_quotations: int = 0
    total_quotation_value: Decimal = Decimal("0.00")
    converted_quotations_count: int = 0
    conversion_rate: float = 0.0
    status_breakdown: Dict[str, int] = {}


# =========================================================================
# 4. PROCUREMENT REPORT SCHEMAS
# =========================================================================

class PurchaseOrderStatusItem(BaseModel):
    status: str
    po_count: int
    total_amount: Decimal


class PurchaseOrderReportSummary(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_purchase_orders: int = 0
    total_spend: Decimal = Decimal("0.00")
    average_po_value: Decimal = Decimal("0.00")
    status_breakdown: List[PurchaseOrderStatusItem] = []


class PurchasesBySupplierItem(BaseModel):
    supplier_id: uuid.UUID
    supplier_code: str
    supplier_name: str
    po_count: int
    total_purchases: Decimal
    average_po_value: Decimal


class PurchasesBySupplierReport(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_suppliers: int
    total_spend: Decimal
    suppliers: List[PurchasesBySupplierItem] = []


class ProcurementSpendItem(BaseModel):
    period: str
    spend_amount: Decimal
    po_count: int


class ProcurementSpendReport(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_spend: Decimal
    spend_by_period: List[ProcurementSpendItem] = []


class GoodsReceiptSummaryItem(BaseModel):
    receipt_id: uuid.UUID
    receipt_number: str
    po_id: Optional[uuid.UUID] = None
    po_number: Optional[str] = None
    supplier_name: Optional[str] = None
    receipt_date: date
    status: str
    total_lines: int


class GoodsReceiptReport(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_receipts: int
    receipts: List[GoodsReceiptSummaryItem] = []


class PurchaseReturnSummaryItem(BaseModel):
    return_id: uuid.UUID
    return_number: str
    supplier_name: Optional[str] = None
    return_date: date
    status: str
    total_amount: Decimal


class PurchaseReturnReport(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_returns: int
    total_return_amount: Decimal
    returns: List[PurchaseReturnSummaryItem] = []


# =========================================================================
# 5. INVENTORY REPORT SCHEMAS
# =========================================================================

class StockByWarehouseItem(BaseModel):
    warehouse_id: uuid.UUID
    warehouse_code: str
    warehouse_name: str
    products_count: int
    total_quantity: Decimal
    total_valuation: Decimal


class StockByWarehouseReport(BaseModel):
    total_warehouses: int
    total_inventory_quantity: Decimal
    total_inventory_valuation: Decimal
    warehouses: List[StockByWarehouseItem] = []


class StockByProductItem(BaseModel):
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    category_name: Optional[str] = None
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    quantity_available: Decimal
    valuation: Decimal


class StockByProductReport(BaseModel):
    total_products: int
    total_quantity: Decimal
    total_valuation: Decimal
    products: List[StockByProductItem] = []


class StockMovementSummaryItem(BaseModel):
    movement_type: str
    movement_count: int
    total_quantity_moved: Decimal


class StockMovementsReport(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_movements: int
    total_quantity_moved: Decimal
    movements_by_type: List[StockMovementSummaryItem] = []


class LowStockReportItem(BaseModel):
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    warehouse_name: Optional[str] = None
    current_stock: Decimal
    reorder_level: Decimal
    minimum_stock: Decimal
    shortage_quantity: Decimal


class LowStockSummaryReport(BaseModel):
    total_low_stock_items: int
    items: List[LowStockReportItem] = []


class BatchExpirySummaryItem(BaseModel):
    batch_id: uuid.UUID
    batch_number: str
    product_sku: str
    product_name: str
    quantity: Decimal
    expiry_date: Optional[date] = None
    is_expired: bool = False
    days_to_expiry: Optional[int] = None


class BatchExpirySummaryReport(BaseModel):
    total_batches: int
    expired_batches_count: int
    expiring_soon_count: int
    batches: List[BatchExpirySummaryItem] = []


class StockReservationSummaryItem(BaseModel):
    reservation_id: uuid.UUID
    product_sku: str
    product_name: str
    warehouse_name: str
    reserved_quantity: Decimal
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    status: str
    created_at: datetime


class StockReservationSummaryReport(BaseModel):
    total_active_reservations: int
    total_reserved_quantity: Decimal
    reservations: List[StockReservationSummaryItem] = []


# =========================================================================
# 6. HR & PAYROLL REPORT SCHEMAS
# =========================================================================

class DepartmentHeadcountItem(BaseModel):
    department_id: Optional[uuid.UUID] = None
    department_name: str
    active_count: int
    inactive_count: int
    total_count: int


class DesignationHeadcountItem(BaseModel):
    designation_name: str
    employee_count: int


class EmploymentTypeHeadcountItem(BaseModel):
    employment_type: str
    employee_count: int


class HeadcountSummaryReport(BaseModel):
    total_employees: int
    total_active_employees: int
    total_departments: int
    by_department: List[DepartmentHeadcountItem] = []
    by_designation: List[DesignationHeadcountItem] = []
    by_employment_type: List[EmploymentTypeHeadcountItem] = []


class DepartmentAttendanceItem(BaseModel):
    department_name: str
    total_records: int
    present_count: int
    absent_count: int
    late_count: int
    leave_count: int
    attendance_rate: float


class AttendanceSummaryReport(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_attendance_records: int
    present_records: int
    absent_records: int
    late_records: int
    leave_records: int
    overall_attendance_rate: float
    by_department: List[DepartmentAttendanceItem] = []


class LeaveTypeUsageItem(BaseModel):
    leave_type_name: str
    requests_count: int
    total_days_approved: float


class LeaveSummaryReport(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_leave_requests: int
    approved_requests_count: int
    pending_requests_count: int
    rejected_requests_count: int
    total_leave_days_taken: float
    by_leave_type: List[LeaveTypeUsageItem] = []


class PayrollCostByDepartmentItem(BaseModel):
    department_name: str
    employees_count: int
    total_gross_pay: Decimal
    total_deductions: Decimal
    total_net_pay: Decimal
    total_employer_cost: Decimal


class PayrollSummaryReport(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_payroll_runs: int
    total_payslips: int
    total_gross_pay: Decimal
    total_deductions: Decimal
    total_net_pay: Decimal
    total_employer_cost: Decimal
    by_department: List[PayrollCostByDepartmentItem] = []


# =========================================================================
# 7. CRM REPORT SCHEMAS
# =========================================================================

class LeadByStatusItem(BaseModel):
    status: str
    count: int
    percentage: float


class LeadBySourceItem(BaseModel):
    source_name: str
    count: int
    percentage: float


class LeadReportSummary(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_leads: int
    converted_leads_count: int
    conversion_rate: float
    average_lead_score: float
    by_status: List[LeadByStatusItem] = []
    by_source: List[LeadBySourceItem] = []


class OpportunityStageItem(BaseModel):
    stage_name: str
    stage_code: str
    opportunity_count: int
    total_value: Decimal
    weighted_value: Decimal


class OpportunityPipelineReport(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_opportunities: int
    total_pipeline_value: Decimal
    total_weighted_forecast: Decimal
    average_deal_size: Decimal
    by_stage: List[OpportunityStageItem] = []


class OpportunityWinLossSummary(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_closed_deals: int
    won_count: int
    lost_count: int
    win_rate: float
    total_won_revenue: Decimal
    total_lost_revenue: Decimal


class ActivityTypeBreakdownItem(BaseModel):
    activity_type: str
    total_count: int
    completed_count: int
    pending_count: int


class CRMActivitySummary(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_activities: int
    total_completed: int
    total_pending: int
    completion_rate: float
    by_type: List[ActivityTypeBreakdownItem] = []


# =========================================================================
# 8. EXPORT SCHEMA
# =========================================================================

class ReportTypeEnum(str, Enum):
    DASHBOARD = "dashboard"
    FINANCE_PROFIT_LOSS = "finance_profit_loss"
    FINANCE_BALANCE_SHEET = "finance_balance_sheet"
    FINANCE_TRIAL_BALANCE = "finance_trial_balance"
    SALES_SUMMARY = "sales_summary"
    SALES_BY_CUSTOMER = "sales_by_customer"
    SALES_BY_PRODUCT = "sales_by_product"
    PROCUREMENT_SUMMARY = "procurement_summary"
    PROCUREMENT_BY_SUPPLIER = "procurement_by_supplier"
    INVENTORY_SUMMARY = "inventory_summary"
    INVENTORY_BY_WAREHOUSE = "inventory_by_warehouse"
    INVENTORY_LOW_STOCK = "inventory_low_stock"
    HR_HEADCOUNT = "hr_headcount"
    HR_ATTENDANCE = "hr_attendance"
    HR_LEAVE = "hr_leave"
    PAYROLL_SUMMARY = "payroll_summary"
    CRM_LEADS = "crm_leads"
    CRM_PIPELINE = "crm_pipeline"


# =========================================================================
# 9. DYNAMIC REPORTING & BI SCHEMAS (LEGACY / EXTENSION COMPATIBILITY)
# =========================================================================

class DashboardWidgetBase(BaseModel):
    widget_type: str = Field(..., max_length=50, description="Chart, KPI, Table, Metric")
    title: str = Field(..., max_length=150)
    config_json: Optional[Dict[str, Any]] = None
    row_pos: int = 0
    col_pos: int = 0
    width: int = 4
    height: int = 3
    kpi_id: Optional[uuid.UUID] = None
    chart_config_id: Optional[uuid.UUID] = None
    saved_report_id: Optional[uuid.UUID] = None


class DashboardWidgetCreate(DashboardWidgetBase):
    pass


class DashboardWidgetUpdate(BaseModel):
    widget_type: Optional[str] = None
    title: Optional[str] = None
    config_json: Optional[Dict[str, Any]] = None
    row_pos: Optional[int] = None
    col_pos: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    kpi_id: Optional[uuid.UUID] = None
    chart_config_id: Optional[uuid.UUID] = None
    saved_report_id: Optional[uuid.UUID] = None


class DashboardWidgetResponse(DashboardWidgetBase):
    id: uuid.UUID
    dashboard_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=150)
    description: Optional[str] = None
    dashboard_type: str = Field("Executive", max_length=50)
    is_shared: bool = False
    layout_config: Optional[Dict[str, Any]] = None


class DashboardCreate(DashboardBase):
    widgets: Optional[List[DashboardWidgetCreate]] = None


class DashboardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    dashboard_type: Optional[str] = None
    is_shared: Optional[bool] = None
    layout_config: Optional[Dict[str, Any]] = None


class DashboardResponse(DashboardBase):
    id: uuid.UUID
    is_system: bool
    owner_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    widgets: List[DashboardWidgetResponse] = []

    model_config = ConfigDict(from_attributes=True)


class KPIMetricBase(BaseModel):
    metric_value: Decimal
    dimensions_json: Optional[Dict[str, Any]] = None
    trend_status: Optional[str] = None


class KPIMetricCreate(KPIMetricBase):
    kpi_id: uuid.UUID
    recorded_at: Optional[datetime] = None


class KPIMetricResponse(KPIMetricBase):
    id: uuid.UUID
    kpi_id: uuid.UUID
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KPIBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=150)
    module: str = Field(..., max_length=50)
    calculation_type: str = "SystemQuery"
    formula: Optional[str] = None
    unit: str = "Count"
    target_value: Optional[Decimal] = None
    warning_threshold: Optional[Decimal] = None
    critical_threshold: Optional[Decimal] = None
    refresh_interval_minutes: int = 60
    is_active: bool = True


class KPICreate(KPIBase):
    pass


class KPIUpdate(BaseModel):
    name: Optional[str] = None
    target_value: Optional[Decimal] = None
    warning_threshold: Optional[Decimal] = None
    critical_threshold: Optional[Decimal] = None
    refresh_interval_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class KPIResponse(KPIBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    current_value: Optional[Decimal] = None
    trend_status: Optional[str] = None
    metrics: List[KPIMetricResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ReportTemplateBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=150)
    module: str = Field(..., max_length=50)
    description: Optional[str] = None
    datasource_key: str = Field(..., max_length=100)
    default_columns: List[str] = Field(default_factory=list)
    default_filters: Optional[Dict[str, Any]] = None
    default_sorting: Optional[List[Dict[str, Any]]] = None
    is_system: bool = True


class ReportTemplateCreate(ReportTemplateBase):
    pass


class ReportTemplateResponse(ReportTemplateBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SavedReportBase(BaseModel):
    template_id: uuid.UUID
    name: str = Field(..., max_length=150)
    description: Optional[str] = None
    is_shared: bool = False
    selected_columns: List[str] = Field(default_factory=list)
    applied_filters: Optional[Dict[str, Any]] = None
    sorting_rules: Optional[List[Dict[str, Any]]] = None
    grouping_rules: Optional[List[str]] = None
    calculated_fields: Optional[List[Dict[str, Any]]] = None


class SavedReportCreate(SavedReportBase):
    pass


class SavedReportUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_shared: Optional[bool] = None
    selected_columns: Optional[List[str]] = None
    applied_filters: Optional[Dict[str, Any]] = None
    sorting_rules: Optional[List[Dict[str, Any]]] = None
    grouping_rules: Optional[List[str]] = None
    calculated_fields: Optional[List[Dict[str, Any]]] = None


class SavedReportResponse(SavedReportBase):
    id: uuid.UUID
    owner_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    template: Optional[ReportTemplateResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ScheduledReportBase(BaseModel):
    name: str = Field(..., max_length=150)
    saved_report_id: Optional[uuid.UUID] = None
    template_id: Optional[uuid.UUID] = None
    frequency: str = Field("Weekly", max_length=30)
    cron_expression: Optional[str] = None
    export_format: str = Field("PDF", max_length=20)
    recipients: List[str] = Field(default_factory=list)
    is_active: bool = True


class ScheduledReportCreate(ScheduledReportBase):
    pass


class ScheduledReportUpdate(BaseModel):
    name: Optional[str] = None
    frequency: Optional[str] = None
    cron_expression: Optional[str] = None
    export_format: Optional[str] = None
    recipients: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ScheduledReportResponse(ScheduledReportBase):
    id: uuid.UUID
    owner_id: Optional[uuid.UUID] = None
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportExecutionResponse(BaseModel):
    id: uuid.UUID
    scheduled_report_id: Optional[uuid.UUID] = None
    saved_report_id: Optional[uuid.UUID] = None
    template_id: Optional[uuid.UUID] = None
    executed_by_id: Optional[uuid.UUID] = None
    status: str
    export_format: str
    export_file_id: Optional[uuid.UUID] = None
    row_count: int
    execution_time_ms: int
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExportReportRequest(BaseModel):
    datasource_key: str
    export_format: str = Field("PDF", description="PDF, Excel, CSV, JSON")
    selected_columns: Optional[List[str]] = None
    applied_filters: Optional[Dict[str, Any]] = None
    sorting_rules: Optional[List[Dict[str, Any]]] = None
    grouping_rules: Optional[List[str]] = None
    report_title: Optional[str] = "ERP Enterprise Report"


class ExportReportResult(BaseModel):
    file_id: uuid.UUID
    file_name: str
    file_path: str
    file_size_bytes: int
    mime_type: str
    row_count: int
    execution_time_ms: int


class ChartConfigurationBase(BaseModel):
    code: str = Field(..., max_length=50)
    title: str = Field(..., max_length=150)
    chart_type: str = Field(..., max_length=50, description="Line, Bar, Area, Pie, Donut, StackedBar, Heatmap, Trend")
    module: str = Field(..., max_length=50)
    x_axis_field: str = Field(..., max_length=100)
    y_axis_fields: List[str] = Field(default_factory=list)
    series_config: Optional[Dict[str, Any]] = None
    color_palette: Optional[List[str]] = None


class ChartConfigurationCreate(ChartConfigurationBase):
    pass


class ChartConfigurationResponse(ChartConfigurationBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChartDataResponse(BaseModel):
    chart_title: str
    chart_type: str
    labels: List[str]
    datasets: List[Dict[str, Any]]
    summary: Optional[Dict[str, Any]] = None


class AnalyticsSnapshotResponse(BaseModel):
    id: uuid.UUID
    snapshot_type: str
    module: str
    period_start: date
    period_end: date
    metrics_json: Dict[str, Any]
    dimensions_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GlobalSearchResult(BaseModel):
    dashboards: List[Dict[str, Any]] = []
    reports: List[Dict[str, Any]] = []
    kpis: List[Dict[str, Any]] = []
    templates: List[Dict[str, Any]] = []

