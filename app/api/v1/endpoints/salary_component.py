from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.salary_component import SalaryComponent
from app.models.user import User
from app.schemas.salary_component import (
    SalaryComponentCreate,
    SalaryComponentListResponse,
    SalaryComponentResponse,
    SalaryComponentUpdate,
)
from app.services.salary_component import SalaryComponentService
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginationParams

router = APIRouter()


def _format_component_response(item: SalaryComponent) -> SalaryComponentResponse:
    """Helper formatting SalaryComponent ORM entity to response schema."""
    return SalaryComponentResponse(
        id=item.id,
        code=item.code,
        name=item.name,
        description=item.description,
        type=item.type,
        calculation_method=item.calculation_method,
        default_value=float(item.default_value),
        percentage_value=float(item.percentage_value) if item.percentage_value is not None else None,
        is_taxable=item.is_taxable,
        is_pf_applicable=item.is_pf_applicable,
        is_esi_applicable=item.is_esi_applicable,
        is_active=item.is_active,
        display_order=item.display_order,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get(
    "/salary-components",
    response_model=SalaryComponentListResponse,
    dependencies=[Depends(has_permission("salary_component.read"))],
    summary="List Salary Components",
    description="Retrieves a paginated list of organization-wide salary components.",
)
async def list_salary_components(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type_filter: Optional[str] = Query(None, alias="type", description="Filter by type (Earning, Deduction)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
):
    service = SalaryComponentService(db)
    params = PaginationParams(page=page, page_size=page_size)

    filters = []
    if type_filter:
        filters.append(FilterCriterion(field="type", value=type_filter))
    if is_active is not None:
        filters.append(FilterCriterion(field="is_active", value=is_active))

    paginated = await service.list_components(params=params, filters=filters)
    items = [_format_component_response(item) for item in paginated.items]

    return SalaryComponentListResponse(
        items=items,
        total=paginated.total,
        page=paginated.page,
        page_size=paginated.page_size,
        total_pages=paginated.total_pages,
    )


@router.get(
    "/salary-components/{id}",
    response_model=SalaryComponentResponse,
    dependencies=[Depends(has_permission("salary_component.read"))],
    summary="Get Salary Component by ID",
    description="Retrieves details for a specific salary component definition.",
)
async def get_salary_component(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = SalaryComponentService(db)
    item = await service.get_component_by_id(id)
    return _format_component_response(item)


@router.post(
    "/salary-components",
    response_model=SalaryComponentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("salary_component.create"))],
    summary="Create Salary Component",
    description="Creates a new organization-wide salary component definition.",
)
async def create_salary_component(
    data: SalaryComponentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SalaryComponentService(db)
    created = await service.create_component(data=data, current_user=current_user, request=request)
    return _format_component_response(created)


@router.put(
    "/salary-components/{id}",
    response_model=SalaryComponentResponse,
    dependencies=[Depends(has_permission("salary_component.update"))],
    summary="Update Salary Component",
    description="Updates an existing salary component definition.",
)
async def update_salary_component(
    id: uuid.UUID,
    data: SalaryComponentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SalaryComponentService(db)
    updated = await service.update_component(id=id, data=data, current_user=current_user, request=request)
    return _format_component_response(updated)


@router.delete(
    "/salary-components/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(has_permission("salary_component.delete"))],
    summary="Delete Salary Component",
    description="Soft-deletes a salary component definition.",
)
async def delete_salary_component(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SalaryComponentService(db)
    await service.delete_component(id=id, current_user=current_user, request=request)
    return None


@router.patch(
    "/salary-components/{id}/restore",
    response_model=SalaryComponentResponse,
    dependencies=[Depends(has_permission("salary_component.restore"))],
    summary="Restore Salary Component",
    description="Restores a soft-deleted salary component definition.",
)
async def restore_salary_component(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SalaryComponentService(db)
    restored = await service.restore_component(id=id, current_user=current_user, request=request)
    return _format_component_response(restored)
