from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.crm import CRMSearchResult
from app.services.crm_services import CRMSearchService

router = APIRouter()
search_service = CRMSearchService()


@router.get("", response_model=CRMSearchResult)
async def search_crm(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Global search across Leads, Opportunities, and Tasks."""
    return await search_service.search_crm(db, query=q)
