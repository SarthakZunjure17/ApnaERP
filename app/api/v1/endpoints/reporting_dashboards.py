from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.reporting import DashboardCreate, DashboardResponse
from app.services.reporting_services import DashboardService

router = APIRouter()


@router.get("/type/{dashboard_type}", response_model=Dict[str, Any])
async def get_dashboard_by_type(
    dashboard_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    service = DashboardService(db)
    return await service.get_dashboard_by_type(dashboard_type, user=current_user)


@router.get("/", response_model=List[DashboardResponse])
async def list_user_dashboards(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Any]:
    service = DashboardService(db)
    return await service.dash_repo.get_user_dashboards(db, owner_id=current_user.id)


@router.post("/", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_dashboard(
    dashboard_in: DashboardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = DashboardService(db)
    return await service.create_dashboard(dashboard_in.model_dump(), user=current_user)
