import datetime
from decimal import Decimal
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------
# Dashboard Schemas
# ---------------------------------------------------------
class DashboardWidgetBase(BaseModel):
    title: str = Field(..., max_length=150)
    widget_type: str = Field(..., max_length=50, description="KPI, Chart, Report, Table, QuickAction, MetricCard")
    kpi_id: Optional[uuid.UUID] = None
    chart_config_id: Optional[uuid.UUID] = None
    report_template_id: Optional[uuid.UUID] = None
    grid_position: Dict[str, Any] = Field(default_factory=lambda: {"x": 0, "y": 0, "w": 4, "h": 3})
    settings_json: Optional[Dict[str, Any]] = None


class DashboardWidgetCreate(DashboardWidgetBase):
    pass


class DashboardWidgetResponse(DashboardWidgetBase):
    id: uuid.UUID
    dashboard_id: uuid.UUID
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=150)
    description: Optional[str] = None
    dashboard_type: str = Field("Custom", max_length=50)
    is_shared: bool = True
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
    created_at: datetime.datetime
    updated_at: datetime.datetime
    widgets: List[DashboardWidgetResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# KPI & Metric Schemas
# ---------------------------------------------------------
class KPIMetricBase(BaseModel):
    metric_value: Decimal
    dimensions_json: Optional[Dict[str, Any]] = None
    trend_status: Optional[str] = None


class KPIMetricCreate(KPIMetricBase):
    kpi_id: uuid.UUID
    recorded_at: Optional[datetime.datetime] = None


class KPIMetricResponse(KPIMetricBase):
    id: uuid.UUID
    kpi_id: uuid.UUID
    recorded_at: datetime.datetime

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
    created_at: datetime.datetime
    updated_at: datetime.datetime
    current_value: Optional[Decimal] = None
    trend_status: Optional[str] = None
    metrics: List[KPIMetricResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# Report Template & Saved Report Schemas
# ---------------------------------------------------------
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
    created_at: datetime.datetime

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
    created_at: datetime.datetime
    updated_at: datetime.datetime
    template: Optional[ReportTemplateResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# Scheduled Report Schemas
# ---------------------------------------------------------
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
    last_run_at: Optional[datetime.datetime] = None
    next_run_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# Report Execution & Export Schemas
# ---------------------------------------------------------
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
    created_at: datetime.datetime

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


# ---------------------------------------------------------
# Analytics & Chart Schemas
# ---------------------------------------------------------
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
    created_at: datetime.datetime

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
    period_start: datetime.date
    period_end: datetime.date
    metrics_json: Dict[str, Any]
    dimensions_json: Optional[Dict[str, Any]] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class GlobalSearchResult(BaseModel):
    dashboards: List[Dict[str, Any]] = []
    reports: List[Dict[str, Any]] = []
    kpis: List[Dict[str, Any]] = []
    templates: List[Dict[str, Any]] = []
