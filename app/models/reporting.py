import datetime
from decimal import Decimal
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class Dashboard(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Dashboard ORM Model.
    Represents system or user-customized dashboards.
    """
    __tablename__ = "dashboards"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dashboard_type: Mapped[str] = mapped_column(
        String(50),
        default="Custom",
        nullable=False,
        index=True,
        comment="Global, HR, Payroll, Inventory, Procurement, Sales, CRM, Finance, Executive, Custom",
    )
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    layout_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict, nullable=True)

    # Relationships
    widgets: Mapped[List["DashboardWidget"]] = relationship(
        "DashboardWidget", back_populates="dashboard", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Dashboard(code='{self.code}', name='{self.name}', type='{self.dashboard_type}')>"


class DashboardWidget(Base, UUIDMixin, TimestampMixin):
    """
    DashboardWidget ORM Model.
    Represents layout widgets configured on a Dashboard.
    """
    __tablename__ = "dashboard_widgets"

    dashboard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dashboards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    widget_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="KPI, Chart, Report, Table, QuickAction, MetricCard",
    )
    kpi_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kpis.id", ondelete="SET NULL"),
        nullable=True,
    )
    chart_config_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chart_configurations.id", ondelete="SET NULL"),
        nullable=True,
    )
    report_template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    grid_position: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, default=lambda: {"x": 0, "y": 0, "w": 4, "h": 3}, nullable=False
    )
    settings_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict, nullable=True)

    # Relationships
    dashboard: Mapped["Dashboard"] = relationship("Dashboard", back_populates="widgets")
    kpi: Mapped[Optional["KPI"]] = relationship("KPI", lazy="selectin")
    chart_config: Mapped[Optional["ChartConfiguration"]] = relationship("ChartConfiguration", lazy="selectin")
    report_template: Mapped[Optional["ReportTemplate"]] = relationship("ReportTemplate", lazy="selectin")

    def __repr__(self) -> str:
        return f"<DashboardWidget(title='{self.title}', type='{self.widget_type}')>"


class KPI(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    KPI ORM Model.
    Master Key Performance Indicator definition.
    """
    __tablename__ = "kpis"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    module: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Platform, HR, Payroll, Inventory, Procurement, Sales, CRM, Finance, CrossModule",
    )
    calculation_type: Mapped[str] = mapped_column(
        String(50),
        default="SystemQuery",
        nullable=False,
        comment="SystemQuery, Expression, Aggregation",
    )
    formula: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit: Mapped[str] = mapped_column(String(30), default="Count", nullable=False)
    target_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    warning_threshold: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    critical_threshold: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    refresh_interval_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    metrics: Mapped[List["KPIMetric"]] = relationship(
        "KPIMetric", back_populates="kpi", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<KPI(code='{self.code}', name='{self.name}', module='{self.module}')>"


class KPIMetric(Base, UUIDMixin, TimestampMixin):
    """
    KPIMetric ORM Model.
    Historical recorded metric value points for a KPI.
    """
    __tablename__ = "kpi_metrics"

    kpi_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kpis.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    recorded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False, index=True
    )
    dimensions_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict, nullable=True)
    trend_status: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment="Improving, Stable, Declining, Critical"
    )

    # Relationships
    kpi: Mapped["KPI"] = relationship("KPI", back_populates="metrics")

    def __repr__(self) -> str:
        return f"<KPIMetric(value={self.metric_value}, status='{self.trend_status}')>"


class ReportTemplate(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    ReportTemplate ORM Model.
    Pre-defined system report templates across domain modules.
    """
    __tablename__ = "report_templates"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    module: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="HR, Payroll, Inventory, Procurement, Sales, CRM, Finance, Executive",
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    datasource_key: Mapped[str] = mapped_column(String(100), nullable=False, comment="Query handler identifier")
    default_columns: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    default_filters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict, nullable=True)
    default_sorting: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, default=list, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    saved_reports: Mapped[List["SavedReport"]] = relationship("SavedReport", back_populates="template")

    def __repr__(self) -> str:
        return f"<ReportTemplate(code='{self.code}', name='{self.name}', module='{self.module}')>"


class SavedReport(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    SavedReport ORM Model.
    Custom user-created reports based on ReportTemplates.
    """
    __tablename__ = "saved_reports"

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    selected_columns: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    applied_filters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict, nullable=True)
    sorting_rules: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, default=list, nullable=True)
    grouping_rules: Mapped[Optional[List[str]]] = mapped_column(JSONB, default=list, nullable=True)
    calculated_fields: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, default=list, nullable=True)

    # Relationships
    template: Mapped["ReportTemplate"] = relationship("ReportTemplate", back_populates="saved_reports")
    schedules: Mapped[List["ScheduledReport"]] = relationship("ScheduledReport", back_populates="saved_report")

    def __repr__(self) -> str:
        return f"<SavedReport(name='{self.name}', shared={self.is_shared})>"


class ScheduledReport(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    ScheduledReport ORM Model.
    Automated recurring report generation and notification configuration.
    """
    __tablename__ = "scheduled_reports"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    saved_report_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("saved_reports.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    frequency: Mapped[str] = mapped_column(
        String(30),
        default="Weekly",
        nullable=False,
        comment="Daily, Weekly, Monthly, Quarterly, Yearly, CustomCron",
    )
    cron_expression: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    export_format: Mapped[str] = mapped_column(
        String(20), default="PDF", nullable=False, comment="PDF, Excel, CSV, JSON"
    )
    recipients: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False, comment="Email list")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    last_run_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    saved_report: Mapped[Optional["SavedReport"]] = relationship("SavedReport", back_populates="schedules")
    template: Mapped[Optional["ReportTemplate"]] = relationship("ReportTemplate")
    executions: Mapped[List["ReportExecution"]] = relationship("ReportExecution", back_populates="schedule")

    def __repr__(self) -> str:
        return f"<ScheduledReport(name='{self.name}', frequency='{self.frequency}', active={self.is_active})>"


class ReportExecution(Base, UUIDMixin, TimestampMixin):
    """
    ReportExecution ORM Model.
    Audit log of report generation runs and export files.
    """
    __tablename__ = "report_executions"

    scheduled_report_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scheduled_reports.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    saved_report_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("saved_reports.id", ondelete="SET NULL"),
        nullable=True,
    )
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    executed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(30), default="Completed", nullable=False, index=True, comment="Pending, InProgress, Completed, Failed"
    )
    export_format: Mapped[str] = mapped_column(String(20), default="PDF", nullable=False)
    export_file_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    execution_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    schedule: Mapped[Optional["ScheduledReport"]] = relationship("ScheduledReport", back_populates="executions")

    def __repr__(self) -> str:
        return f"<ReportExecution(status='{self.status}', rows={self.row_count}, format='{self.export_format}')>"


class AnalyticsSnapshot(Base, UUIDMixin, TimestampMixin):
    """
    AnalyticsSnapshot ORM Model.
    Periodic aggregated domain snapshots for fast business intelligence trend analysis.
    """
    __tablename__ = "analytics_snapshots"

    snapshot_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="ExecutiveSummary, HRMetrics, PayrollCosts, InventoryValuation, ProcurementSpend, SalesPerformance, CRMFunnel, FinanceHealth",
    )
    module: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    period_start: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    period_end: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    metrics_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    dimensions_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict, nullable=True)

    def __repr__(self) -> str:
        return f"<AnalyticsSnapshot(type='{self.snapshot_type}', module='{self.module}', period='{self.period_start} to {self.period_end}')>"


class ChartConfiguration(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    ChartConfiguration ORM Model.
    Reusable chart layout and visualization definitions.
    """
    __tablename__ = "chart_configurations"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    chart_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Line, Bar, Area, Pie, Donut, StackedBar, Heatmap, Trend",
    )
    module: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    x_axis_field: Mapped[str] = mapped_column(String(100), nullable=False)
    y_axis_fields: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    series_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict, nullable=True)
    color_palette: Mapped[Optional[List[str]]] = mapped_column(JSONB, default=list, nullable=True)

    def __repr__(self) -> str:
        return f"<ChartConfiguration(title='{self.title}', type='{self.chart_type}', module='{self.module}')>"
