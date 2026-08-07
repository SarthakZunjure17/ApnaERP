from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.reporting import KPICreate, KPIResponse
from app.services.reporting_services import KPIService

router = APIRouter()


@router.get("/", response_model=List[KPIResponse])
async def list_active_kpis(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = KPIService(db)
    return await service.kpi_repo.get_all_active(db)


@router.get("/code/{code}/calculate", response_model=Dict[str, Any])
async def calculate_kpi(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    service = KPIService(db)
    return await service.calculate_kpi(code)


@router.post("/", response_model=KPIResponse, status_code=status.HTTP_201_CREATED)
async def create_kpi(
    kpi_in: KPICreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = KPIService(db)
    return await service.kpi_repo.create(db, obj_in=kpi_in.model_dump())
