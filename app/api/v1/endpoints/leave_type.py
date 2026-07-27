from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.leave_type import LeaveType
from app.models.user import User
from app.schemas.leave_type import (
    LeaveTypeCreate,
    LeaveTypeListResponse,
    LeaveTypeResponse,
    LeaveTypeUpdate,
)
from app.services.leave_type import LeaveTypeService
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginationParams

router = APIRouter()


def _format_leave_type_response(item: LeaveType) -> LeaveTypeResponse:
    """Helper to convert LeaveType ORM instance to LeaveTypeResponse Pydantic schema."""
    return LeaveTypeResponse(
        id=item.id,
        code=item.code,
        name=item.name,
        description=item.description,
        is_paid=item.is_paid,
        requires_approval=item.requires_approval,
        allow_half_day=item.allow_half_day,
        allow_negative_balance=item.allow_negative_balance,
        annual_allocation=item.annual_allocation,
        carry_forward_allowed=item.carry_forward_allowed,
        max_carry_forward=item.max_carry_forward,
        max_consecutive_days=item.max_consecutive_days,
        gender_restriction=item.gender_restriction,
        is_active=item.is_active,
        created_at=item.created_at,
        updated_at=item.updated_at,
        is_deleted=item.is_deleted,
        deleted_at=item.deleted_at,
    )


@router.get(
    "",
    response_model=LeaveTypeListResponse,
    dependencies=[Depends(has_permission("leave_type.read"))],
    summary="List Leave Types",
    description="Retrieves a paginated list of organizational leave types with search and filtering.",
)
async def list_leave_types(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search term across code, name, and description"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_paid: Optional[bool] = Query(None, description="Filter by paid leave status"),
    db: AsyncSession = Depends(get_db),
):
    service = LeaveTypeService(db)
    params = PaginationParams(page=page, page_size=page_size)

    filters = []
    if is_active is not None:
        filters.append(FilterCriterion(field="is_active", value=is_active))
    if is_paid is not None:
        filters.append(FilterCriterion(field="is_paid", value=is_paid))

    paginated = await service.list_leave_types(params=params, search_term=search, filters=filters)
    items = [_format_leave_type_response(item) for item in paginated.items]

    return LeaveTypeListResponse(
        items=items,
        total=paginated.total,
        page=paginated.page,
        page_size=paginated.page_size,
        total_pages=paginated.total_pages,
    )


@router.get(
    "/{id}",
    response_model=LeaveTypeResponse,
    dependencies=[Depends(has_permission("leave_type.read"))],
    summary="Get Leave Type by ID",
    description="Retrieves details for a single Leave Type policy.",
)
async def get_leave_type(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = LeaveTypeService(db)
    item = await service.get_leave_type_by_id(id)
    return _format_leave_type_response(item)


@router.post(
    "",
    response_model=LeaveTypeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("leave_type.create"))],
    summary="Create Leave Type",
    description="Creates a new organizational Leave Type policy.",
)
async def create_leave_type(
    data: LeaveTypeCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LeaveTypeService(db)
    created = await service.create_leave_type(data=data, current_user=current_user, request=request)
    return _format_leave_type_response(created)


@router.put(
    "/{id}",
    response_model=LeaveTypeResponse,
    dependencies=[Depends(has_permission("leave_type.update"))],
    summary="Update Leave Type",
    description="Updates an existing Leave Type policy.",
)
async def update_leave_type(
    id: uuid.UUID,
    data: LeaveTypeUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LeaveTypeService(db)
    updated = await service.update_leave_type(id=id, data=data, current_user=current_user, request=request)
    return _format_leave_type_response(updated)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(has_permission("leave_type.delete"))],
    summary="Delete Leave Type",
    description="Soft-deletes a Leave Type policy.",
)
async def delete_leave_type(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LeaveTypeService(db)
    await service.delete_leave_type(id=id, current_user=current_user, request=request)
    return None


@router.patch(
    "/{id}/restore",
    response_model=LeaveTypeResponse,
    dependencies=[Depends(has_permission("leave_type.restore"))],
    summary="Restore Leave Type",
    description="Restores a soft-deleted Leave Type policy.",
)
async def restore_leave_type(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LeaveTypeService(db)
    restored = await service.restore_leave_type(id=id, current_user=current_user, request=request)
    return _format_leave_type_response(restored)
