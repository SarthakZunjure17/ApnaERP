from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.user import User
from app.schemas.country import CountryCreate, CountryResponse, CountryUpdate
from app.services.statutory_compliance import StatutoryComplianceService
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.sorting import SortCriterion, parse_sort_query

router = APIRouter()


@router.get(
    "/countries",
    response_model=PaginatedResult[CountryResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("country.read"))],
)
async def list_countries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves a paginated list of Country records.
    """
    service = StatutoryComplianceService(db)
    pagination = PaginationParams(page=page, page_size=page_size)
    sorting = parse_sort_query(sort) if sort else None
    return await service.list_countries(
        params=pagination, is_active=is_active, search_term=search, sorting=sorting
    )


@router.post(
    "/countries",
    response_model=CountryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("country.create"))],
)
async def create_country(
    data: CountryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creates a new Country jurisdiction record.
    """
    service = StatutoryComplianceService(db)
    return await service.create_country(data=data, current_user=current_user)


@router.put(
    "/countries/{id}",
    response_model=CountryResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("country.update"))],
)
async def update_country(
    id: uuid.UUID,
    data: CountryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Updates an existing Country jurisdiction record.
    """
    service = StatutoryComplianceService(db)
    return await service.update_country(id=id, data=data, current_user=current_user)


@router.delete(
    "/countries/{id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("country.delete"))],
)
async def delete_country(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deletes a Country jurisdiction record.
    """
    service = StatutoryComplianceService(db)
    await service.delete_country(id=id, current_user=current_user)
    return {"message": "Country successfully deleted."}
