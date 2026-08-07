from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.reporting import ChartDataResponse
from app.services.reporting_services import ChartService

router = APIRouter()


@router.get("/code/{code}", response_model=ChartDataResponse)
async def get_chart_data(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = ChartService(db)
    return await service.get_chart_data(code)
