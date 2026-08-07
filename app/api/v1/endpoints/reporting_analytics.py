from typing import Any, Dict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.reporting_services import AnalyticsService

router = APIRouter()


@router.get("/growth", response_model=Dict[str, Any])
async def get_module_growth(
    module: str = Query("Sales", description="Domain module"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    service = AnalyticsService(db)
    return await service.get_growth_metrics(module)


@router.post("/snapshot", response_model=Dict[str, Any])
async def compute_snapshot(
    module: str = Query("Sales"),
    snapshot_type: str = Query("SalesPerformance"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    service = AnalyticsService(db)
    snap = await service.compute_analytics_snapshot(module, snapshot_type)
    return {
        "id": str(snap.id),
        "snapshot_type": snap.snapshot_type,
        "module": snap.module,
        "metrics": snap.metrics_json,
    }
