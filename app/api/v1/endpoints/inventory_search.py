from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.schemas.inventory_advanced import GlobalSearchResponse
from app.services.inventory_search_services import inventory_search_service

router = APIRouter()


@router.get(
    "",
    response_model=GlobalSearchResponse,
    dependencies=[Depends(has_permission("inventory.read"))],
)
async def global_inventory_search(
    query: str = Query(..., min_length=1, description="Search term for SKU, Barcode, Batch, Serial, Lot, Warehouse, Location"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute unified multi-field global inventory search."""
    return await inventory_search_service.global_search(db, query=query, limit=limit)
