import uuid
from typing import Any, List, Optional
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.repositories.base_repository import BaseRepository


class DashboardRepository(BaseRepository[Dashboard, Any, Any]):
    def __init__(self):
        super().__init__(Dashboard)

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[Dashboard]:
        stmt = select(Dashboard).where(Dashboard.code == code, Dashboard.is_deleted == False)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_type(self, db: AsyncSession, *, dashboard_type: str) -> Optional[Dashboard]:
        stmt = select(Dashboard).where(
            Dashboard.dashboard_type == dashboard_type,
            Dashboard.is_system == True,
            Dashboard.is_deleted == False,
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_dashboards(
        self, db: AsyncSession, *, owner_id: Optional[uuid.UUID] = None
    ) -> List[Dashboard]:
        conditions = [Dashboard.is_deleted == False]
        if owner_id:
            conditions.append(or_(Dashboard.owner_id == owner_id, Dashboard.is_shared == True, Dashboard.is_system == True))
        else:
            conditions.append(or_(Dashboard.is_shared == True, Dashboard.is_system == True))
        stmt = select(Dashboard).where(and_(*conditions)).order_by(Dashboard.name.asc())
        res = await db.execute(stmt)
        return list(res.scalars().all())


class DashboardWidgetRepository(BaseRepository[DashboardWidget, Any, Any]):
    def __init__(self):
        super().__init__(DashboardWidget)

    async def get_by_dashboard(self, db: AsyncSession, *, dashboard_id: uuid.UUID) -> List[DashboardWidget]:
        stmt = select(DashboardWidget).where(DashboardWidget.dashboard_id == dashboard_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())


class KPIRepository(BaseRepository[KPI, Any, Any]):
    def __init__(self):
        super().__init__(KPI)

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[KPI]:
        stmt = select(KPI).where(KPI.code == code, KPI.is_deleted == False)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_module(self, db: AsyncSession, *, module: str) -> List[KPI]:
        stmt = select(KPI).where(KPI.module == module, KPI.is_active == True, KPI.is_deleted == False)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_all_active(self, db: AsyncSession) -> List[KPI]:
        stmt = select(KPI).where(KPI.is_active == True, KPI.is_deleted == False)
        res = await db.execute(stmt)
        return list(res.scalars().all())


class KPIMetricRepository(BaseRepository[KPIMetric, Any, Any]):
    def __init__(self):
        super().__init__(KPIMetric)

    async def get_latest_by_kpi(self, db: AsyncSession, *, kpi_id: uuid.UUID) -> Optional[KPIMetric]:
        stmt = select(KPIMetric).where(KPIMetric.kpi_id == kpi_id).order_by(KPIMetric.recorded_at.desc())
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_history(self, db: AsyncSession, *, kpi_id: uuid.UUID, limit: int = 30) -> List[KPIMetric]:
        stmt = select(KPIMetric).where(KPIMetric.kpi_id == kpi_id).order_by(KPIMetric.recorded_at.desc()).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all())


class ReportTemplateRepository(BaseRepository[ReportTemplate, Any, Any]):
    def __init__(self):
        super().__init__(ReportTemplate)

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[ReportTemplate]:
        stmt = select(ReportTemplate).where(ReportTemplate.code == code, ReportTemplate.is_deleted == False)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_module(self, db: AsyncSession, *, module: str) -> List[ReportTemplate]:
        stmt = select(ReportTemplate).where(ReportTemplate.module == module, ReportTemplate.is_deleted == False)
        res = await db.execute(stmt)
        return list(res.scalars().all())


class SavedReportRepository(BaseRepository[SavedReport, Any, Any]):
    def __init__(self):
        super().__init__(SavedReport)

    async def get_user_saved_reports(
        self, db: AsyncSession, *, owner_id: Optional[uuid.UUID] = None
    ) -> List[SavedReport]:
        conditions = [SavedReport.is_deleted == False]
        if owner_id:
            conditions.append(or_(SavedReport.owner_id == owner_id, SavedReport.is_shared == True))
        else:
            conditions.append(SavedReport.is_shared == True)
        stmt = select(SavedReport).where(and_(*conditions)).order_by(SavedReport.name.asc())
        res = await db.execute(stmt)
        return list(res.scalars().all())


class ScheduledReportRepository(BaseRepository[ScheduledReport, Any, Any]):
    def __init__(self):
        super().__init__(ScheduledReport)

    async def get_due_schedules(self, db: AsyncSession) -> List[ScheduledReport]:
        stmt = select(ScheduledReport).where(
            ScheduledReport.is_active == True,
            ScheduledReport.is_deleted == False,
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


class ReportExecutionRepository(BaseRepository[ReportExecution, Any, Any]):
    def __init__(self):
        super().__init__(ReportExecution)

    async def get_recent(self, db: AsyncSession, *, limit: int = 50) -> List[ReportExecution]:
        stmt = select(ReportExecution).order_by(ReportExecution.created_at.desc()).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all())


class AnalyticsSnapshotRepository(BaseRepository[AnalyticsSnapshot, Any, Any]):
    def __init__(self):
        super().__init__(AnalyticsSnapshot)

    async def get_latest_by_type(
        self, db: AsyncSession, *, snapshot_type: str, module: str
    ) -> Optional[AnalyticsSnapshot]:
        stmt = (
            select(AnalyticsSnapshot)
            .where(AnalyticsSnapshot.snapshot_type == snapshot_type, AnalyticsSnapshot.module == module)
            .order_by(AnalyticsSnapshot.created_at.desc())
        )
        res = await db.execute(stmt)
        return res.scalars().first()


class ChartConfigurationRepository(BaseRepository[ChartConfiguration, Any, Any]):
    def __init__(self):
        super().__init__(ChartConfiguration)

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[ChartConfiguration]:
        stmt = select(ChartConfiguration).where(ChartConfiguration.code == code, ChartConfiguration.is_deleted == False)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_module(self, db: AsyncSession, *, module: str) -> List[ChartConfiguration]:
        stmt = select(ChartConfiguration).where(ChartConfiguration.module == module, ChartConfiguration.is_deleted == False)
        res = await db.execute(stmt)
        return list(res.scalars().all())
