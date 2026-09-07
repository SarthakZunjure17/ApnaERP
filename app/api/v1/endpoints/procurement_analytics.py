from datetime import datetime
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.procurement import (
    ProcurementDashboardSummary,
    ProcurementEfficiencyMetricsResponse,
    ProcurementSpendAnalyticsResponse,
)
from app.services.procurement_report_services import (
    procurement_analytics_service,
    procurement_report_service,
)

router = APIRouter()


@router.get("/dashboard-summary", response_model=ProcurementDashboardSummary)
async def get_dashboard_summary(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.analytics.read")),
):
    return await procurement_analytics_service.get_dashboard_summary(db, date_from=date_from, date_to=date_to)


@router.get("/spend", response_model=ProcurementSpendAnalyticsResponse)
async def get_spend_analytics(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    supplier_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.analytics.read")),
):
    return await procurement_report_service.get_spend_analytics(
        db, date_from=date_from, date_to=date_to, supplier_id=supplier_id, warehouse_id=warehouse_id
    )


@router.get("/efficiency", response_model=ProcurementEfficiencyMetricsResponse)
async def get_efficiency_metrics(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.analytics.read")),
):
    return await procurement_report_service.get_efficiency_metrics(db, date_from=date_from, date_to=date_to)
