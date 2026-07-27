from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.api.v1.endpoints.salary_component import _format_component_response
from app.models.salary_structure import SalaryStructure, SalaryStructureComponent
from app.models.user import User
from app.schemas.salary_structure import (
    SalaryStructureComponentCreate,
    SalaryStructureComponentResponse,
    SalaryStructureComponentUpdate,
    SalaryStructureCreate,
    SalaryStructureListResponse,
    SalaryStructureResponse,
    SalaryStructureUpdate,
)
from app.services.salary_structure import SalaryStructureService
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginationParams

router = APIRouter()


def _format_structure_component_response(item: SalaryStructureComponent) -> SalaryStructureComponentResponse:
    """Helper formatting SalaryStructureComponent ORM entity to response schema."""
    comp_resp = _format_component_response(item.component) if hasattr(item, "component") and item.component else None
    return SalaryStructureComponentResponse(
        id=item.id,
        salary_structure_id=item.salary_structure_id,
        salary_component_id=item.salary_component_id,
        component_order=item.component_order,
        component_value=float(item.component_value),
        calculation_method_override=item.calculation_method_override,
        is_active=item.is_active,
        created_at=item.created_at,
        component=comp_resp,
    )


def _format_structure_response(item: SalaryStructure) -> SalaryStructureResponse:
    """Helper formatting SalaryStructure ORM entity to response schema."""
    components = [
        _format_structure_component_response(c)
        for c in (item.components or [])
    ]
    return SalaryStructureResponse(
        id=item.id,
        code=item.code,
        name=item.name,
        description=item.description,
        currency=item.currency,
        is_active=item.is_active,
        effective_from=item.effective_from,
        effective_to=item.effective_to,
        created_at=item.created_at,
        updated_at=item.updated_at,
        components=components,
    )


@router.get(
    "/salary-structures",
    response_model=SalaryStructureListResponse,
    dependencies=[Depends(has_permission("salary_structure.read"))],
    summary="List Salary Structures",
    description="Retrieves a paginated list of organization-wide salary structure templates.",
)
async def list_salary_structures(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
):
    service = SalaryStructureService(db)
    params = PaginationParams(page=page, page_size=page_size)

    filters = []
    if is_active is not None:
        filters.append(FilterCriterion(field="is_active", value=is_active))

    paginated = await service.list_structures(params=params, filters=filters)
    items = [_format_structure_response(item) for item in paginated.items]

    return SalaryStructureListResponse(
        items=items,
        total=paginated.total,
        page=paginated.page,
        page_size=paginated.page_size,
        total_pages=paginated.total_pages,
    )


@router.get(
    "/salary-structures/{id}",
    response_model=SalaryStructureResponse,
    dependencies=[Depends(has_permission("salary_structure.read"))],
    summary="Get Salary Structure by ID",
    description="Retrieves details for a specific salary structure template.",
)
async def get_salary_structure(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = SalaryStructureService(db)
    item = await service.get_structure_by_id(id)
    return _format_structure_response(item)


@router.post(
    "/salary-structures",
    response_model=SalaryStructureResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("salary_structure.create"))],
    summary="Create Salary Structure",
    description="Creates a new organization-wide salary structure template.",
)
async def create_salary_structure(
    data: SalaryStructureCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SalaryStructureService(db)
    created = await service.create_structure(data=data, current_user=current_user, request=request)
    return _format_structure_response(created)


@router.put(
    "/salary-structures/{id}",
    response_model=SalaryStructureResponse,
    dependencies=[Depends(has_permission("salary_structure.update"))],
    summary="Update Salary Structure",
    description="Updates an existing salary structure template.",
)
async def update_salary_structure(
    id: uuid.UUID,
    data: SalaryStructureUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SalaryStructureService(db)
    updated = await service.update_structure(id=id, data=data, current_user=current_user, request=request)
    return _format_structure_response(updated)


@router.delete(
    "/salary-structures/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(has_permission("salary_structure.delete"))],
    summary="Delete Salary Structure",
    description="Soft-deletes a salary structure template.",
)
async def delete_salary_structure(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SalaryStructureService(db)
    await service.delete_structure(id=id, current_user=current_user, request=request)
    return None


@router.patch(
    "/salary-structures/{id}/restore",
    response_model=SalaryStructureResponse,
    dependencies=[Depends(has_permission("salary_structure.restore"))],
    summary="Restore Salary Structure",
    description="Restores a soft-deleted salary structure template.",
)
async def restore_salary_structure(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SalaryStructureService(db)
    restored = await service.restore_structure(id=id, current_user=current_user, request=request)
    return _format_structure_response(restored)


@router.post(
    "/salary-structures/{id}/components",
    response_model=SalaryStructureComponentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("salary_structure.update"))],
    summary="Add Component to Salary Structure",
    description="Maps a salary component into a salary structure template.",
)
async def add_component_to_salary_structure(
    id: uuid.UUID,
    data: SalaryStructureComponentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SalaryStructureService(db)
    mapping = await service.add_component_to_structure(
        structure_id=id, data=data, current_user=current_user, request=request
    )
    return _format_structure_component_response(mapping)


@router.put(
    "/salary-structures/{id}/components/{componentId}",
    response_model=SalaryStructureComponentResponse,
    dependencies=[Depends(has_permission("salary_structure.update"))],
    summary="Update Salary Structure Component Mapping",
    description="Updates order or baseline value of a component mapped in a salary structure.",
)
async def update_salary_structure_component(
    id: uuid.UUID,
    componentId: uuid.UUID,
    data: SalaryStructureComponentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SalaryStructureService(db)
    updated = await service.update_structure_component(
        structure_id=id, component_mapping_id=componentId, data=data, current_user=current_user, request=request
    )
    return _format_structure_component_response(updated)


@router.delete(
    "/salary-structures/{id}/components/{componentId}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(has_permission("salary_structure.update"))],
    summary="Remove Component from Salary Structure",
    description="Removes a mapped component from a salary structure template.",
)
async def remove_component_from_salary_structure(
    id: uuid.UUID,
    componentId: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SalaryStructureService(db)
    await service.remove_component_from_structure(
        structure_id=id, component_mapping_id=componentId, current_user=current_user, request=request
    )
    return None
