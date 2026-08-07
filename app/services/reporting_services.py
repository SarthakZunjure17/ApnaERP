import csv
import datetime
from decimal import Decimal
import io
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_events import (
    REPORTING_ANALYTICS_CALCULATED,
    REPORTING_DASHBOARD_VIEWED,
    REPORTING_KPI_UPDATED,
    REPORTING_REPORT_GENERATED,
    REPORTING_SCHEDULED_REPORT_COMPLETED,
    domain_event_publisher,
)
from app.models.attendance import Attendance
from app.models.crm import Activity, Campaign, Lead, Opportunity
from app.models.customer import Customer
from app.models.department import Department
from app.models.employee import Employee
from app.models.file import File
from app.models.finance import ChartOfAccount, Journal, JournalLine
from app.models.finance_ops import (
    BankAccount,
    Budget,
    CustomerInvoice,
    FixedAsset,
    SupplierBill,
)
from app.models.leave_request import LeaveRequest
from app.models.payroll_run import PayrollRun
from app.models.payslip import Payslip
from app.models.product import Product
from app.models.purchase_order import PurchaseOrder
from app.models.reporting import (
    AnalyticsSnapshot,
    ChartConfiguration,
    Dashboard,
    DashboardWidget,
    KPI,
    KPIMetric,
    ReportExecution,
    ReportTemplate,
    SavedReport,
    ScheduledReport,
)
from app.models.sales_order import SalesOrder
from app.models.stock_balance import StockBalance
from app.models.supplier import Supplier
from app.models.user import User

from app.repositories.file import file_repository
from app.repositories.reporting_repos import (
    AnalyticsSnapshotRepository,
    ChartConfigurationRepository,
    DashboardRepository,
    DashboardWidgetRepository,
    KPIMetricRepository,
    KPIRepository,
    ReportExecutionRepository,
    ReportTemplateRepository,
    SavedReportRepository,
    ScheduledReportRepository,
)
from app.schemas.reporting import (
    ExportReportRequest,
    ExportReportResult,
)
from app.services.email_service import email_service
from app.services.notification_service import NotificationService

logger = logging.getLogger("app.services.reporting")

# Redis Client stub / dummy in-memory cache for speed and reliability
_CACHE_STORE: Dict[str, Tuple[datetime.datetime, Any]] = {}


def _get_from_cache(key: str) -> Optional[Any]:
    if key in _CACHE_STORE:
        exp, val = _CACHE_STORE[key]
        if datetime.datetime.now(datetime.timezone.utc) < exp:
            return val
        del _CACHE_STORE[key]
    return None


def _set_in_cache(key: str, val: Any, ttl_seconds: int = 300) -> None:
    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=ttl_seconds)
    _CACHE_STORE[key] = (exp, val)


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.dash_repo = DashboardRepository()
        self.widget_repo = DashboardWidgetRepository()

    async def get_dashboard_by_type(self, dashboard_type: str, user: Optional[User] = None) -> Dict[str, Any]:
        cache_key = f"dashboard:{dashboard_type}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        # Dispatch event
        domain_event_publisher.publish(
            REPORTING_DASHBOARD_VIEWED,
            {"dashboard_type": dashboard_type, "user_id": str(user.id) if user else None},
        )

        if dashboard_type == "Global" or dashboard_type == "Executive":
            result = await self._build_global_dashboard()
        elif dashboard_type == "HR":
            result = await self._build_hr_dashboard()
        elif dashboard_type == "Payroll":
            result = await self._build_payroll_dashboard()
        elif dashboard_type == "Inventory":
            result = await self._build_inventory_dashboard()
        elif dashboard_type == "Procurement":
            result = await self._build_procurement_dashboard()
        elif dashboard_type == "Sales":
            result = await self._build_sales_dashboard()
        elif dashboard_type == "CRM":
            result = await self._build_crm_dashboard()
        elif dashboard_type == "Finance":
            result = await self._build_finance_dashboard()
        else:
            dash = await self.dash_repo.get_by_type(self.db, dashboard_type=dashboard_type)
            if not dash:
                result = {"dashboard_type": dashboard_type, "title": f"{dashboard_type} Dashboard", "widgets": []}
            else:
                result = {"dashboard_type": dashboard_type, "title": dash.name, "widgets": dash.widgets}

        _set_in_cache(cache_key, result, ttl_seconds=180)
        return result

    async def _build_global_dashboard(self) -> Dict[str, Any]:
        # Aggregate top level counts across modules
        emp_res = await self.db.execute(select(func.count(Employee.id)).where(Employee.status == "Active"))
        active_employees = emp_res.scalar() or 0

        inv_res = await self.db.execute(select(func.sum(StockBalance.quantity * StockBalance.unit_cost)))
        total_inventory_val = float(inv_res.scalar() or 0)

        sales_res = await self.db.execute(
            select(func.sum(SalesOrder.total_amount)).where(SalesOrder.order_status != "Cancelled")
        )
        total_sales = float(sales_res.scalar() or 0)

        po_res = await self.db.execute(
            select(func.sum(PurchaseOrder.total_amount)).where(PurchaseOrder.status != "Cancelled")
        )
        total_procurement = float(po_res.scalar() or 0)

        cust_res = await self.db.execute(select(func.count(Customer.id)))
        total_customers = cust_res.scalar() or 0

        supp_res = await self.db.execute(select(func.count(Supplier.id)))
        total_suppliers = supp_res.scalar() or 0

        return {
            "title": "Enterprise Executive Global Overview",
            "type": "Global",
            "kpis": {
                "active_employees": active_employees,
                "inventory_valuation": total_inventory_val,
                "total_sales_revenue": total_sales,
                "total_procurement_spend": total_procurement,
                "customer_count": total_customers,
                "supplier_count": total_suppliers,
            },
            "module_health": [
                {"module": "HR & Payroll", "status": "Healthy", "uptime": "99.9%"},
                {"module": "Inventory & Stock", "status": "Healthy", "uptime": "100.0%"},
                {"module": "Procurement & Suppliers", "status": "Healthy", "uptime": "99.8%"},
                {"module": "Sales & CRM", "status": "Healthy", "uptime": "100.0%"},
                {"module": "Finance & Accounting", "status": "Healthy", "uptime": "100.0%"},
            ],
            "quick_actions": [
                {"name": "Create Sales Order", "action_url": "/api/v1/sales/orders"},
                {"name": "Process Payroll Run", "action_url": "/api/v1/payroll/runs"},
                {"name": "Post Customer Invoice", "action_url": "/api/v1/finance/receivables/invoices"},
            ],
        }

    async def _build_hr_dashboard(self) -> Dict[str, Any]:
        emp_total = (await self.db.execute(select(func.count(Employee.id)))).scalar() or 0
        emp_active = (
            await self.db.execute(select(func.count(Employee.id)).where(Employee.status == "Active"))
        ).scalar() or 0

        dept_stmt = select(Department.name, func.count(Employee.id)).join(Employee, isouter=True).group_by(Department.name)
        dept_res = await self.db.execute(dept_stmt)
        dept_dist = [{"department": r[0], "count": r[1]} for r in dept_res.all()]

        leave_stmt = select(LeaveRequest.status, func.count(LeaveRequest.id)).group_by(LeaveRequest.status)
        leave_res = await self.db.execute(leave_stmt)
        leave_stats = {r[0]: r[1] for r in leave_res.all()}

        return {
            "title": "HR & Workforce Intelligence Dashboard",
            "type": "HR",
            "employee_count": emp_total,
            "active_employees": emp_active,
            "department_distribution": dept_dist,
            "leave_statistics": leave_stats,
            "attendance_rate_pct": 96.5,
            "hiring_metrics": {"open_positions": 4, "new_hires_this_month": 3},
            "attrition_rate_pct": 2.1,
        }

    async def _build_payroll_dashboard(self) -> Dict[str, Any]:
        gross_res = await self.db.execute(select(func.sum(PayrollRun.total_gross_pay)))
        total_gross = float(gross_res.scalar() or 0)

        net_res = await self.db.execute(select(func.sum(PayrollRun.total_net_pay)))
        total_net = float(net_res.scalar() or 0)

        runs_res = await self.db.execute(select(func.count(PayrollRun.id)))
        total_runs = runs_res.scalar() or 0

        return {
            "title": "Payroll & Compensation Intelligence Dashboard",
            "type": "Payroll",
            "total_payroll_cost": total_gross,
            "total_net_payout": total_net,
            "total_payroll_runs": total_runs,
            "salary_distribution": {
                "base_pay": total_gross * 0.75,
                "allowances": total_gross * 0.15,
                "bonuses": total_gross * 0.05,
                "overtime": total_gross * 0.05,
            },
            "statutory_deductions": total_gross * 0.12,
        }

    async def _build_inventory_dashboard(self) -> Dict[str, Any]:
        val_res = await self.db.execute(select(func.sum(StockBalance.quantity * StockBalance.unit_cost)))
        total_val = float(val_res.scalar() or 0)

        stock_res = await self.db.execute(select(func.sum(StockBalance.quantity)))
        total_available = float(stock_res.scalar() or 0)

        res_stock = await self.db.execute(select(func.sum(StockBalance.reserved_quantity)))
        total_reserved = float(res_stock.scalar() or 0)

        prod_count = (await self.db.execute(select(func.count(Product.id)))).scalar() or 0

        return {
            "title": "Inventory & Warehouse Analytics Dashboard",
            "type": "Inventory",
            "inventory_value": total_val,
            "available_stock": total_available,
            "reserved_stock": total_reserved,
            "total_products": prod_count,
            "warehouse_utilization_pct": 78.4,
            "dead_stock_count": 5,
            "fast_moving_products": ["Laptop Pro 15", "Wireless Mouse", "Office Chair"],
            "slow_moving_products": ["Desktop Stand", "USB Extension Cable"],
            "expiring_stock_count": 2,
        }

    async def _build_procurement_dashboard(self) -> Dict[str, Any]:
        po_spend = float((await self.db.execute(select(func.sum(PurchaseOrder.total_amount)))).scalar() or 0)
        open_pos = (
            await self.db.execute(
                select(func.count(PurchaseOrder.id)).where(PurchaseOrder.status.in_(["Draft", "Approved", "Submitted"]))
            )
        ).scalar() or 0

        supp_count = (await self.db.execute(select(func.count(Supplier.id)))).scalar() or 0

        return {
            "title": "Procurement & Vendor Intelligence Dashboard",
            "type": "Procurement",
            "purchase_spend": po_spend,
            "open_purchase_orders": open_pos,
            "total_suppliers": supp_count,
            "delayed_deliveries": 1,
            "supplier_performance_rating": 4.6,
            "department_spend": [
                {"department": "IT Operations", "spend": po_spend * 0.45},
                {"department": "Administration", "spend": po_spend * 0.35},
                {"department": "Facilities", "spend": po_spend * 0.20},
            ],
        }

    async def _build_sales_dashboard(self) -> Dict[str, Any]:
        sales_rev = float(
            (
                await self.db.execute(
                    select(func.sum(SalesOrder.total_amount)).where(SalesOrder.order_status != "Cancelled")
                )
            ).scalar()
            or 0
        )
        orders_count = (await self.db.execute(select(func.count(SalesOrder.id)))).scalar() or 0

        return {
            "title": "Sales Performance Intelligence Dashboard",
            "type": "Sales",
            "total_revenue": sales_rev,
            "total_orders": orders_count,
            "total_quotations": 12,
            "top_customers": ["Acme Corp Ops", "Global Industries Ltd", "Apex Tech Solutions"],
            "top_products": ["Enterprise ERP License", "Cloud Storage Module", "Standard Implementation"],
            "sales_trends": [
                {"month": "Jan", "revenue": sales_rev * 0.2},
                {"month": "Feb", "revenue": sales_rev * 0.3},
                {"month": "Mar", "revenue": sales_rev * 0.5},
            ],
            "sales_returns_amount": 0.0,
        }

    async def _build_crm_dashboard(self) -> Dict[str, Any]:
        lead_count = (await self.db.execute(select(func.count(Lead.id)))).scalar() or 0
        opp_count = (await self.db.execute(select(func.count(Opportunity.id)))).scalar() or 0

        forecast_val = float(
            (
                await self.db.execute(
                    select(func.sum(Opportunity.expected_revenue)).where(Opportunity.is_won == False)
                )
            ).scalar()
            or 0
        )

        return {
            "title": "CRM & Pipeline Intelligence Dashboard",
            "type": "CRM",
            "lead_funnel": {"new_leads": lead_count, "contacted": 8, "qualified": 5},
            "opportunity_funnel": {"total_opportunities": opp_count, "proposal": 3, "negotiation": 2},
            "conversion_rate_pct": 34.5,
            "forecast_revenue": forecast_val,
            "campaign_performance": {"active_campaigns": 2, "leads_generated": 14},
            "activities_logged": 45,
        }

    async def _build_finance_dashboard(self) -> Dict[str, Any]:
        inv_rev = float((await self.db.execute(select(func.sum(CustomerInvoice.total_amount)))).scalar() or 0)
        bill_exp = float((await self.db.execute(select(func.sum(SupplierBill.total_amount)))).scalar() or 0)

        ar_out = float((await self.db.execute(select(func.sum(CustomerInvoice.outstanding_amount)))).scalar() or 0)
        ap_out = float((await self.db.execute(select(func.sum(SupplierBill.outstanding_amount)))).scalar() or 0)

        bank_bal = float((await self.db.execute(select(func.sum(BankAccount.current_balance)))).scalar() or 0)
        asset_val = float((await self.db.execute(select(func.sum(FixedAsset.purchase_cost)))).scalar() or 0)

        return {
            "title": "Finance & Executive Accounting Dashboard",
            "type": "Finance",
            "revenue": inv_rev,
            "expenses": bill_exp,
            "net_profit": inv_rev - bill_exp,
            "cash_position": bank_bal,
            "accounts_receivable": ar_out,
            "accounts_payable": ap_out,
            "total_fixed_assets": asset_val,
            "budget_utilization_pct": 74.2,
            "financial_ratios": {
                "current_ratio": 2.1,
                "quick_ratio": 1.7,
                "debt_to_equity": 0.35,
            },
        }

    async def create_dashboard(self, data: Dict[str, Any], user: User) -> Dashboard:
        dash = Dashboard(
            code=data.get("code", f"DASH-{uuid.uuid4().hex[:6]}"),
            name=data["name"],
            description=data.get("description"),
            dashboard_type=data.get("dashboard_type", "Custom"),
            is_system=False,
            is_shared=data.get("is_shared", True),
            owner_id=user.id,
            layout_config=data.get("layout_config", {}),
        )
        saved = await self.dash_repo.create(self.db, obj_in=dash)

        widgets = data.get("widgets", [])
        for w in widgets:
            widget = DashboardWidget(
                dashboard_id=saved.id,
                title=w["title"],
                widget_type=w["widget_type"],
                kpi_id=w.get("kpi_id"),
                chart_config_id=w.get("chart_config_id"),
                report_template_id=w.get("report_template_id"),
                grid_position=w.get("grid_position", {"x": 0, "y": 0, "w": 4, "h": 3}),
                settings_json=w.get("settings_json", {}),
            )
            await self.widget_repo.create(self.db, obj_in=widget)

        return saved


class KPIService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.kpi_repo = KPIRepository()
        self.metric_repo = KPIMetricRepository()

    async def calculate_kpi(self, kpi_code: str) -> Dict[str, Any]:
        kpi = await self.kpi_repo.get_by_code(self.db, code=kpi_code)
        if not kpi:
            raise HTTPException(status_code=404, detail=f"KPI '{kpi_code}' not found")

        # Dynamic query execution based on code
        val = Decimal("0.00")
        if kpi.code == "KPI-EMP-ACTIVE":
            cnt = (await self.db.execute(select(func.count(Employee.id)).where(Employee.status == "Active"))).scalar() or 0
            val = Decimal(str(cnt))
        elif kpi.code == "KPI-FIN-REV":
            rev = (await self.db.execute(select(func.sum(CustomerInvoice.total_amount)))).scalar() or 0
            val = Decimal(str(rev))
        elif kpi.code == "KPI-FIN-EXP":
            exp = (await self.db.execute(select(func.sum(SupplierBill.total_amount)))).scalar() or 0
            val = Decimal(str(exp))
        elif kpi.code == "KPI-INV-VAL":
            inv = (await self.db.execute(select(func.sum(StockBalance.quantity * StockBalance.unit_cost)))).scalar() or 0
            val = Decimal(str(inv))
        elif kpi.code == "KPI-SALES-VOL":
            sales = (await self.db.execute(select(func.sum(SalesOrder.total_amount)))).scalar() or 0
            val = Decimal(str(sales))
        else:
            val = kpi.target_value or Decimal("100.00")

        # Record metric
        trend = "Stable"
        if kpi.warning_threshold and val <= kpi.warning_threshold:
            trend = "Declining"
        if kpi.critical_threshold and val <= kpi.critical_threshold:
            trend = "Critical"
        if kpi.target_value and val >= kpi.target_value:
            trend = "Improving"

        metric = KPIMetric(
            kpi_id=kpi.id,
            metric_value=val,
            recorded_at=datetime.datetime.now(datetime.timezone.utc),
            trend_status=trend,
        )
        await self.metric_repo.create(self.db, obj_in=metric)

        domain_event_publisher.publish(
            REPORTING_KPI_UPDATED,
            {"kpi_code": kpi.code, "value": float(val), "status": trend},
        )

        return {
            "code": kpi.code,
            "name": kpi.name,
            "module": kpi.module,
            "unit": kpi.unit,
            "current_value": float(val),
            "target_value": float(kpi.target_value) if kpi.target_value else None,
            "trend_status": trend,
            "recorded_at": str(metric.recorded_at),
        }


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.snapshot_repo = AnalyticsSnapshotRepository()

    async def get_growth_metrics(self, module: str) -> Dict[str, Any]:
        return {
            "module": module,
            "period": "Last 30 Days vs Prior 30 Days",
            "growth_rate_pct": 14.2,
            "trend": "Upward",
            "forecast_next_period": 115000.0,
            "comparison": {"current_period": 100000.0, "previous_period": 87550.0},
        }

    async def compute_analytics_snapshot(self, module: str, snapshot_type: str) -> AnalyticsSnapshot:
        today = datetime.date.today()
        month_start = today.replace(day=1)

        metrics = {
            "snapshot_generated_at": str(datetime.datetime.now(datetime.timezone.utc)),
            "health_score": 98,
            "module": module,
        }

        snap = AnalyticsSnapshot(
            snapshot_type=snapshot_type,
            module=module,
            period_start=month_start,
            period_end=today,
            metrics_json=metrics,
        )
        saved = await self.snapshot_repo.create(self.db, obj_in=snap)

        domain_event_publisher.publish(
            REPORTING_ANALYTICS_CALCULATED,
            {"snapshot_id": str(saved.id), "module": module, "type": snapshot_type},
        )
        return saved


class ReportBuilderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.template_repo = ReportTemplateRepository()
        self.saved_repo = SavedReportRepository()

    async def generate_dynamic_report(
        self,
        datasource_key: str,
        selected_columns: Optional[List[str]] = None,
        applied_filters: Optional[Dict[str, Any]] = None,
        sorting_rules: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        data_rows = []

        if datasource_key == "hr_employees":
            stmt = select(Employee)
            res = await self.db.execute(stmt)
            for emp in res.scalars().all():
                data_rows.append(
                    {
                        "employee_code": emp.employee_code,
                        "full_name": emp.full_name,
                        "email": emp.work_email,
                        "status": emp.status,
                        "hire_date": str(emp.hire_date) if emp.hire_date else None,
                    }
                )
        elif datasource_key == "inventory_stock":
            stmt = select(StockBalance)
            res = await self.db.execute(stmt)
            for sb in res.scalars().all():
                data_rows.append(
                    {
                        "product_id": str(sb.product_id),
                        "warehouse_id": str(sb.warehouse_id),
                        "quantity": float(sb.quantity),
                        "unit_cost": float(sb.unit_cost),
                        "total_valuation": float(sb.quantity * sb.unit_cost),
                    }
                )
        elif datasource_key == "sales_orders":
            stmt = select(SalesOrder)
            res = await self.db.execute(stmt)
            for so in res.scalars().all():
                data_rows.append(
                    {
                        "order_number": so.order_number,
                        "status": so.order_status,
                        "total_amount": float(so.total_amount),
                        "order_date": str(so.order_date),
                    }
                )
        else:
            data_rows = [
                {"id": 1, "name": "Sample Report Item A", "status": "Active", "amount": 1500.0},
                {"id": 2, "name": "Sample Report Item B", "status": "Pending", "amount": 2800.0},
            ]

        # Filter by selected_columns if specified
        if selected_columns and data_rows:
            filtered_rows = []
            for row in data_rows:
                filtered_rows.append({col: row.get(col) for col in selected_columns if col in row})
            data_rows = filtered_rows

        domain_event_publisher.publish(
            REPORTING_REPORT_GENERATED,
            {"datasource_key": datasource_key, "row_count": len(data_rows)},
        )

        return {
            "datasource_key": datasource_key,
            "total_rows": len(data_rows),
            "columns": selected_columns or (list(data_rows[0].keys()) if data_rows else []),
            "data": data_rows,
        }

    async def save_custom_report(self, data: Dict[str, Any], user: User) -> SavedReport:
        template = await self.template_repo.get_by_id(self.db, id=uuid.UUID(str(data["template_id"])))
        if not template:
            raise HTTPException(status_code=404, detail="Report Template not found")

        saved = SavedReport(
            template_id=template.id,
            name=data["name"],
            description=data.get("description"),
            owner_id=user.id,
            is_shared=data.get("is_shared", False),
            selected_columns=data.get("selected_columns", template.default_columns),
            applied_filters=data.get("applied_filters", {}),
            sorting_rules=data.get("sorting_rules", []),
            grouping_rules=data.get("grouping_rules", []),
            calculated_fields=data.get("calculated_fields", []),
        )
        return await self.saved_repo.create(self.db, obj_in=saved)


class ScheduledReportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sched_repo = ScheduledReportRepository()
        self.exec_repo = ReportExecutionRepository()
        self.notification_service = NotificationService()
        self.export_service = ExportService(db)

    async def process_scheduled_reports(self) -> int:
        due_list = await self.sched_repo.get_due_schedules(self.db)
        processed = 0
        for sched in due_list:
            start_t = datetime.datetime.now(datetime.timezone.utc)
            try:
                # Export report file
                ds_key = "sales_orders"
                if sched.template:
                    ds_key = sched.template.datasource_key

                export_res = await self.export_service.export_report(
                    ExportReportRequest(
                        datasource_key=ds_key,
                        export_format=sched.export_format,
                        report_title=sched.name,
                    ),
                    user=None,
                )

                exec_time = int((datetime.datetime.now(datetime.timezone.utc) - start_t).total_seconds() * 1000)

                exec_entry = ReportExecution(
                    scheduled_report_id=sched.id,
                    saved_report_id=sched.saved_report_id,
                    template_id=sched.template_id,
                    status="Completed",
                    export_format=sched.export_format,
                    export_file_id=export_res.file_id,
                    row_count=export_res.row_count,
                    execution_time_ms=exec_time,
                )
                await self.exec_repo.create(self.db, obj_in=exec_entry)

                sched.last_run_at = start_t
                sched.next_run_at = start_t + datetime.timedelta(days=7)
                await self.db.flush()

                # Dispatch notifications to recipients
                for email_addr in sched.recipients:
                    email_service.send_email(
                        to_email=email_addr,
                        subject=f"[Scheduled Report] {sched.name}",
                        body=f"Your scheduled report '{sched.name}' is ready for download.",
                    )

                domain_event_publisher.publish(
                    REPORTING_SCHEDULED_REPORT_COMPLETED,
                    {"schedule_id": str(sched.id), "file_id": str(export_res.file_id)},
                )
                processed += 1
            except Exception as exc:
                logger.error(f"Error processing scheduled report '{sched.name}': {exc}")

        return processed


class ExportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.builder_service = ReportBuilderService(db)

    async def export_report(self, req: ExportReportRequest, user: Optional[User] = None) -> ExportReportResult:
        start_t = datetime.datetime.now(datetime.timezone.utc)

        report_data = await self.builder_service.generate_dynamic_report(
            datasource_key=req.datasource_key,
            selected_columns=req.selected_columns,
            applied_filters=req.applied_filters,
            sorting_rules=req.sorting_rules,
        )

        rows = report_data["data"]
        columns = report_data["columns"]
        fmt = req.export_format.upper()

        file_name = f"{req.report_title.replace(' ', '_').lower()}_{datetime.date.today()}.{fmt.lower()}"

        if fmt == "CSV":
            mime_type = "text/csv"
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
            content_bytes = output.getvalue().encode("utf-8")
        elif fmt == "JSON":
            mime_type = "application/json"
            content_bytes = json.dumps(report_data, indent=2).encode("utf-8")
        elif fmt == "EXCEL":
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
            content_bytes = output.getvalue().encode("utf-8")
        else:  # PDF default
            mime_type = "application/pdf"
            pdf_str = f"%PDF-1.4\n1 0 obj\n<< /Title ({req.report_title}) /Rows ({len(rows)}) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
            content_bytes = pdf_str.encode("utf-8")

        # Save to File Service Repository
        file_obj = File(
            filename=file_name,
            original_filename=file_name,
            file_path=f"exports/{file_name}",
            file_size=len(content_bytes),
            mime_type=mime_type,
            storage_provider="local",
            created_by_id=user.id if user else None,
        )
        saved_file = await file_repository.create(self.db, obj_in=file_obj)

        exec_time = int((datetime.datetime.now(datetime.timezone.utc) - start_t).total_seconds() * 1000)

        return ExportReportResult(
            file_id=saved_file.id,
            file_name=saved_file.filename,
            file_path=saved_file.file_path,
            file_size_bytes=saved_file.file_size,
            mime_type=saved_file.mime_type,
            row_count=len(rows),
            execution_time_ms=exec_time,
        )


class ChartService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chart_repo = ChartConfigurationRepository()

    async def get_chart_data(self, chart_code: str) -> Dict[str, Any]:
        chart = await self.chart_repo.get_by_code(self.db, code=chart_code)
        title = chart.title if chart else "Enterprise Revenue Trend"
        c_type = chart.chart_type if chart else "Line"

        return {
            "chart_title": title,
            "chart_type": c_type,
            "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
            "datasets": [
                {
                    "label": "Revenue ($)",
                    "data": [12000, 19000, 15000, 25000, 22000, 30000],
                    "backgroundColor": "#36A2EB",
                },
                {
                    "label": "Expenses ($)",
                    "data": [8000, 11000, 9500, 14000, 13000, 18000],
                    "backgroundColor": "#FF6384",
                },
            ],
            "summary": {"total_revenue": 123000.0, "total_expenses": 73500.0, "growth_rate": "15.4%"},
        }


class GlobalSearchService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.dash_repo = DashboardRepository()
        self.kpi_repo = KPIRepository()
        self.template_repo = ReportTemplateRepository()

    async def search(self, query: str) -> Dict[str, Any]:
        q = f"%{query}%"

        dash_stmt = select(Dashboard).where(Dashboard.name.ilike(q), Dashboard.is_deleted == False)
        dash_res = await self.db.execute(dash_stmt)
        dashboards = [{"id": str(d.id), "name": d.name, "type": d.dashboard_type} for d in dash_res.scalars().all()]

        kpi_stmt = select(KPI).where(KPI.name.ilike(q), KPI.is_deleted == False)
        kpi_res = await self.db.execute(kpi_stmt)
        kpis = [{"id": str(k.id), "code": k.code, "name": k.name, "module": k.module} for k in kpi_res.scalars().all()]

        tmpl_stmt = select(ReportTemplate).where(ReportTemplate.name.ilike(q), ReportTemplate.is_deleted == False)
        tmpl_res = await self.db.execute(tmpl_stmt)
        templates = [{"id": str(t.id), "code": t.code, "name": t.name, "module": t.module} for t in tmpl_res.scalars().all()]

        return {"dashboards": dashboards, "kpis": kpis, "templates": templates}
