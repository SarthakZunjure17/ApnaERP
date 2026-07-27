from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.leave_balance import LeaveBalance
from app.models.user import User
from app.schemas.leave_balance import (
    LeaveBalanceAdjustmentRequest,
    LeaveBalanceCreate,
    LeaveBalanceListResponse,
    LeaveBalanceResponse,
    LeaveBalanceUpdate,
)
from app.services.leave_balance import LeaveBalanceService
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginationParams

router = APIRouter()


def _format_leave_balance_response(item: LeaveBalance) -> LeaveBalanceResponse:
    """Helper formatting LeaveBalance ORM object to LeaveBalanceResponse Pydantic schema."""
    emp_code = item.employee.employee_code if item.employee else None
    emp_name = f"{item.employee.first_name} {item.employee.last_name}".strip() if item.employee else None
    lt_code = item.leave_type.code if item.leave_type else None
    lt_name = item.leave_type.name if item.leave_type else None

    return LeaveBalanceResponse(
        id=item.id,
        employee_id=item.employee_id,
        leave_type_id=item.leave_type_id,
        leave_year=item.leave_year,
        opening_balance=item.opening_balance,
        allocated_days=item.allocated_days,
        earned_days=item.earned_days,
        availed_days=item.availed_days,
        encashed_days=item.encashed_days,
        carried_forward_days=item.carried_forward_days,
        remaining_days=item.remaining_days,
        last_updated_by=item.last_updated_by,
        is_active=item.is_active,
        created_at=item.created_at,
        updated_at=item.updated_at,
        is_deleted=item.is_deleted,
        deleted_at=item.deleted_at,
        employee_code=emp_code,
        employee_name=emp_name,
        leave_type_code=lt_code,
        leave_type_name=lt_name,
    )


@router.get(
    "",
    response_model=LeaveBalanceListResponse,
    dependencies=[Depends(has_permission("leave_balance.read"))],
    summary="List all Leave Balances",
    description="Retrieves a paginated list of leave balances across the organization.",
)
async def list_leave_balances(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    leave_year: Optional[int] = Query(None, description="Filter by leave year"),
    leave_type_id: Optional[uuid.UUID] = Query(None, description="Filter by leave type ID"),
    employee_id: Optional[uuid.UUID] = Query(None, description="Filter by employee ID"),
    db: AsyncSession = Depends(get_db),
):
    service = LeaveBalanceService(db)
    params = PaginationParams(page=page, page_size=page_size)

    filters = []
    if leave_year is not None:
        filters.append(FilterCriterion(field="leave_year", value=leave_year))
    if leave_type_id is not None:
        filters.append(FilterCriterion(field="leave_type_id", value=leave_type_id))
    if employee_id is not None:
        filters.append(FilterCriterion(field="employee_id", value=employee_id))

    paginated = await service.list_leave_balances(params=params, filters=filters)
    items = [_format_leave_balance_response(item) for item in paginated.items]

    return LeaveBalanceListResponse(
        items=items,
        total=paginated.total,
        page=paginated.page,
        page_size=paginated.page_size,
        total_pages=paginated.total_pages,
    )


@router.get(
    "/employees/{id}/leave-balances",
    response_model=LeaveBalanceListResponse,
    dependencies=[Depends(has_permission("leave_balance.read"))],
    summary="List Employee Leave Balances",
    description="Retrieves paginated leave balances for a specific employee.",
)
async def list_employee_leave_balances(
    id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    leave_year: Optional[int] = Query(None, description="Optional filter by leave year"),
    db: AsyncSession = Depends(get_db),
):
    service = LeaveBalanceService(db)
    params = PaginationParams(page=page, page_size=page_size)
    paginated = await service.get_employee_leave_balances(
        employee_id=id, leave_year=leave_year, params=params
    )
    items = [_format_leave_balance_response(item) for item in paginated.items]

    return LeaveBalanceListResponse(
        items=items,
        total=paginated.total,
        page=paginated.page,
        page_size=paginated.page_size,
        total_pages=paginated.total_pages,
    )


@router.get(
    "/{id}",
    response_model=LeaveBalanceResponse,
    dependencies=[Depends(has_permission("leave_balance.read"))],
    summary="Get Leave Balance by ID",
    description="Retrieves details for a single Leave Balance record.",
)
async def get_leave_balance(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = LeaveBalanceService(db)
    item = await service.get_leave_balance_by_id(id)
    return _format_leave_balance_response(item)


@router.post(
    "",
    response_model=LeaveBalanceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("leave_balance.create"))],
    summary="Create Leave Balance",
    description="Initializes a new leave balance record for an employee.",
)
async def create_leave_balance(
    data: LeaveBalanceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LeaveBalanceService(db)
    created = await service.create_leave_balance(data=data, current_user=current_user, request=request)
    return _format_leave_balance_response(created)


@router.put(
    "/{id}",
    response_model=LeaveBalanceResponse,
    dependencies=[Depends(has_permission("leave_balance.update"))],
    summary="Update Leave Balance",
    description="Updates opening, allocated, earned, or carried forward leave balance fields.",
)
async def update_leave_balance(
    id: uuid.UUID,
    data: LeaveBalanceUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LeaveBalanceService(db)
    updated = await service.update_leave_balance(id=id, data=data, current_user=current_user, request=request)
    return _format_leave_balance_response(updated)


@router.patch(
    "/{id}/adjust",
    response_model=LeaveBalanceResponse,
    dependencies=[Depends(has_permission("leave_balance.adjust"))],
    summary="Adjust Leave Balance",
    description="Manually adjusts a leave balance component (e.g. earned, availed, encashed) with business justification.",
)
async def adjust_leave_balance(
    id: uuid.UUID,
    data: LeaveBalanceAdjustmentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LeaveBalanceService(db)
    adjusted = await service.adjust_leave_balance(id=id, data=data, current_user=current_user, request=request)
    return _format_leave_balance_response(adjusted)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(has_permission("leave_balance.delete"))],
    summary="Delete Leave Balance",
    description="Soft-deletes a Leave Balance record.",
)
async def delete_leave_balance(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LeaveBalanceService(db)
    await service.delete_leave_balance(id=id, current_user=current_user, request=request)
    return None


@router.patch(
    "/{id}/restore",
    response_model=LeaveBalanceResponse,
    dependencies=[Depends(has_permission("leave_balance.restore"))],
    summary="Restore Leave Balance",
    description="Restores a soft-deleted Leave Balance record.",
)
async def restore_leave_balance(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LeaveBalanceService(db)
    restored = await service.restore_leave_balance(id=id, current_user=current_user, request=request)
    return _format_leave_balance_response(restored)
