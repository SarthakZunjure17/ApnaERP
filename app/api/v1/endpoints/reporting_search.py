from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.reporting import GlobalSearchResult
from app.services.reporting_services import GlobalSearchService

router = APIRouter()


@router.get("/", response_model=GlobalSearchResult)
async def global_reporting_search(
    q: str = Query(..., min_length=1, description="Search term for dashboards, reports, KPIs"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = GlobalSearchService(db)
    return await service.search(q)
