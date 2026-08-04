from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.procurement import GlobalProcurementSearchResponse
from app.services.procurement_search_services import procurement_search_service

router = APIRouter()


@router.get("", response_model=GlobalProcurementSearchResponse)
async def global_search(
    query: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.read")),
):
    return await procurement_search_service.global_search(db, query=query, limit=limit)
