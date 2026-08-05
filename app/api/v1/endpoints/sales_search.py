from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.sales import SalesSearchResult
from app.services.sales_search_services import sales_search_service

router = APIRouter()


@router.get("", response_model=List[SalesSearchResult])
async def global_sales_search(
    query: str = Query(..., min_length=2, description="Search term for customers, orders, quotations, deliveries, tracking numbers, or products"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.order.read")),
):
    return await sales_search_service.global_sales_search(db, query=query, limit=limit)
