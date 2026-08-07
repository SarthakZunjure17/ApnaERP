import datetime
from decimal import Decimal
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.employee import Employee
from app.models.product import Product
from app.models.reporting import (
    ChartConfiguration,
    Dashboard,
    KPI,
    ReportTemplate,
    SavedReport,
    ScheduledReport,
)
from app.models.sales_order import SalesOrder
from app.models.stock_balance import StockBalance
from app.models.user import User
from app.schemas.reporting import ExportReportRequest
from app.services.reporting_services import (
    AnalyticsService,
    ChartService,
    DashboardService,
    ExportService,
    GlobalSearchService,
    KPIService,
    ReportBuilderService,
    ScheduledReportService,
)


async def helper_get_user(session: AsyncSession) -> User:
    user = User(
        username=f"testbi_{uuid.uuid4().hex[:6]}",
        email=f"testbi_{uuid.uuid4().hex[:6]}@example.com",
        full_name="BI Test Analyst",
        password_hash="hashedpassword123",
        is_active=True,
        is_superuser=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_enterprise_and_module_dashboards():
    async with AsyncSessionLocal() as db_session:
        user = await helper_get_user(db_session)
        service = DashboardService(db_session)

        # Test System Dashboards
        global_dash = await service.get_dashboard_by_type("Global", user=user)
        assert global_dash["type"] == "Global"
        assert "kpis" in global_dash

        hr_dash = await service.get_dashboard_by_type("HR", user=user)
        assert hr_dash["type"] == "HR"
        assert "employee_count" in hr_dash

        fin_dash = await service.get_dashboard_by_type("Finance", user=user)
        assert fin_dash["type"] == "Finance"
        assert "revenue" in fin_dash

        # Create Custom Dashboard
        custom_in = {
            "code": f"DASH-BI-{uuid.uuid4().hex[:4]}",
            "name": "Custom Executive Monitor",
            "dashboard_type": "Custom",
            "is_shared": True,
            "widgets": [
                {
                    "title": "Revenue Chart",
                    "widget_type": "Chart",
                    "grid_position": {"x": 0, "y": 0, "w": 6, "h": 4},
                }
            ],
        }
        saved_dash = await service.create_dashboard(custom_in, user=user)
        assert saved_dash.name == "Custom Executive Monitor"
        assert len(saved_dash.widgets) == 1


@pytest.mark.asyncio
async def test_kpi_engine_and_metric_recording():
    async with AsyncSessionLocal() as db_session:
        service = KPIService(db_session)

        kpi_code = f"KPI-TEST-{uuid.uuid4().hex[:4]}"
        kpi = KPI(
            code=kpi_code,
            name="Active Workforce Count Test",
            module="HR",
            calculation_type="SystemQuery",
            unit="Headcount",
            target_value=Decimal("50.00"),
            warning_threshold=Decimal("10.00"),
            critical_threshold=Decimal("5.00"),
        )
        db_session.add(kpi)
        await db_session.commit()

        res = await service.calculate_kpi(kpi_code)
        assert res["code"] == kpi_code
        assert "current_value" in res
        assert res["trend_status"] in ["Improving", "Stable", "Declining", "Critical"]


@pytest.mark.asyncio
async def test_report_builder_and_saved_reports():
    async with AsyncSessionLocal() as db_session:
        user = await helper_get_user(db_session)
        builder = ReportBuilderService(db_session)

        # Dynamic Report Generation
        rep_data = await builder.generate_dynamic_report(datasource_key="hr_employees")
        assert rep_data["datasource_key"] == "hr_employees"
        assert "total_rows" in rep_data

        # Create Template & Saved Report
        tmpl = ReportTemplate(
            code=f"TMPL-{uuid.uuid4().hex[:4]}",
            name="Sales Performance Template",
            module="Sales",
            datasource_key="sales_orders",
            default_columns=["order_number", "total_amount", "order_date"],
        )
        db_session.add(tmpl)
        await db_session.commit()

        saved_in = {
            "template_id": str(tmpl.id),
            "name": "My Quarterly Sales Report",
            "description": "Custom saved sales report",
            "selected_columns": ["order_number", "total_amount"],
        }
        saved_rep = await builder.save_custom_report(saved_in, user=user)
        assert saved_rep.name == "My Quarterly Sales Report"
        assert saved_rep.template_id == tmpl.id


@pytest.mark.asyncio
async def test_scheduled_reports_and_processing():
    async with AsyncSessionLocal() as db_session:
        user = await helper_get_user(db_session)
        tmpl = ReportTemplate(
            code=f"TMPL-SCHED-{uuid.uuid4().hex[:4]}",
            name="Scheduled Sales Summary",
            module="Sales",
            datasource_key="sales_orders",
            default_columns=["order_number", "total_amount"],
        )
        db_session.add(tmpl)
        await db_session.commit()

        sched = ScheduledReport(
            name="Weekly Sales Digest",
            template_id=tmpl.id,
            owner_id=user.id,
            frequency="Weekly",
            export_format="PDF",
            recipients=["executives@example.com"],
            is_active=True,
        )
        db_session.add(sched)
        await db_session.commit()

        service = ScheduledReportService(db_session)
        count = await service.process_scheduled_reports()
        assert count >= 1


@pytest.mark.asyncio
async def test_export_engine_multi_format():
    async with AsyncSessionLocal() as db_session:
        user = await helper_get_user(db_session)
        export_service = ExportService(db_session)

        # Test PDF Export
        pdf_req = ExportReportRequest(
            datasource_key="hr_employees", export_format="PDF", report_title="Employee Directory"
        )
        pdf_res = await export_service.export_report(pdf_req, user=user)
        assert pdf_res.mime_type == "application/pdf"
        assert pdf_res.file_size_bytes > 0

        # Test CSV Export
        csv_req = ExportReportRequest(
            datasource_key="inventory_stock", export_format="CSV", report_title="Stock Valuation"
        )
        csv_res = await export_service.export_report(csv_req, user=user)
        assert csv_res.mime_type == "text/csv"
        assert csv_res.file_size_bytes > 0

        # Test JSON Export
        json_req = ExportReportRequest(
            datasource_key="sales_orders", export_format="JSON", report_title="Sales Export"
        )
        json_res = await export_service.export_report(json_req, user=user)
        assert json_res.mime_type == "application/json"
        assert json_res.file_size_bytes > 0


@pytest.mark.asyncio
async def test_analytics_charts_and_global_search():
    async with AsyncSessionLocal() as db_session:
        analytics = AnalyticsService(db_session)
        chart_service = ChartService(db_session)
        search_service = GlobalSearchService(db_session)

        # Analytics Growth
        growth = await analytics.get_growth_metrics("Sales")
        assert growth["module"] == "Sales"
        assert "growth_rate_pct" in growth

        # Analytics Snapshot
        snap = await analytics.compute_analytics_snapshot("Finance", "FinanceHealth")
        assert snap.snapshot_type == "FinanceHealth"

        # Chart Payload
        chart = await chart_service.get_chart_data("CHART-REV-TREND")
        assert chart["chart_type"] in ["Line", "Bar", "Area", "Pie", "Donut", "StackedBar", "Heatmap", "Trend"]
        assert len(chart["labels"]) > 0

        # Global Search
        search_res = await search_service.search("Executive")
        assert "dashboards" in search_res
        assert "kpis" in search_res
        assert "templates" in search_res
