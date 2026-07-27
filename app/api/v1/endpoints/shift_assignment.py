from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.shift_assignment import ShiftAssignment
from app.models.user import User
from app.schemas.shift_assignment import (
    ShiftAssignmentCreate,
    ShiftAssignmentEndRequest,
    ShiftAssignmentListResponse,
    ShiftAssignmentResponse,
    ShiftAssignmentUpdate,
)
from app.services.shift_assignment import ShiftAssignmentService
from app.utils.pagination import PaginationParams

router = APIRouter()


def _format_shift_assignment_response(assignment: ShiftAssignment) -> ShiftAssignmentResponse:
    """Formats ShiftAssignment ORM entity to response schema with expanded employee and shift details."""
    emp_code = assignment.employee.employee_code if assignment.employee else None
    emp_name = (
        f"{assignment.employee.first_name} {assignment.employee.last_name}"
        if assignment.employee
        else None
    )
    s_name = assignment.shift.name if assignment.shift else None
    s_code = assignment.shift.code if assignment.shift else None

    return ShiftAssignmentResponse(
        id=assignment.id,
        employee_id=assignment.employee_id,
        shift_id=assignment.shift_id,
        effective_from=assignment.effective_from,
        effective_to=assignment.effective_to,
        assignment_type=assignment.assignment_type,
        reason=assignment.reason,
        assigned_by=assignment.assigned_by,
        is_active=assignment.is_active,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
        employee_code=emp_code,
        employee_name=emp_name,
        shift_name=s_name,
        shift_code=s_code,
    )


@router.get(
    "",
    response_model=ShiftAssignmentListResponse,
    dependencies=[Depends(has_permission("shift_assignment.read"))],
    summary="List all Shift Assignments",
    description="Retrieves a paginated list of shift assignments across the organization.",
)
async def list_shift_assignments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = ShiftAssignmentService(db)
    params = PaginationParams(page=page, page_size=page_size)
    paginated = await service.get_all_assignments(params)
    items = [_format_shift_assignment_response(item) for item in paginated.items]
    return ShiftAssignmentListResponse(
        items=items,
        total=paginated.total,
        page=paginated.page,
        page_size=paginated.page_size,
        total_pages=paginated.total_pages,
    )


@router.get(
    "/employees/{id}/shift-assignments",
    response_model=ShiftAssignmentListResponse,
    dependencies=[Depends(has_permission("shift_assignment.read"))],
    summary="List Employee Shift Assignments",
    description="Retrieves all historical and active shift assignments for a specific employee.",
)
async def list_employee_shift_assignments(
    id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = ShiftAssignmentService(db)
    params = PaginationParams(page=page, page_size=page_size)
    paginated = await service.get_employee_assignments(employee_id=id, params=params)
    items = [_format_shift_assignment_response(item) for item in paginated.items]
    return ShiftAssignmentListResponse(
        items=items,
        total=paginated.total,
        page=paginated.page,
        page_size=paginated.page_size,
        total_pages=paginated.total_pages,
    )


@router.get(
    "/{id}",
    response_model=ShiftAssignmentResponse,
    dependencies=[Depends(has_permission("shift_assignment.read"))],
    summary="Get Shift Assignment by ID",
    description="Retrieves details for a single shift assignment.",
)
async def get_shift_assignment(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = ShiftAssignmentService(db)
    assignment = await service.get_by_id(id)
    return _format_shift_assignment_response(assignment)


@router.post(
    "",
    response_model=ShiftAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("shift_assignment.create"))],
    summary="Create Shift Assignment",
    description="Assigns a shift to an employee with effective start and end dates.",
)
async def create_shift_assignment(
    data: ShiftAssignmentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ShiftAssignmentService(db)
    assignment = await service.assign_shift(data=data, current_user=current_user, request=request)
    return _format_shift_assignment_response(assignment)


@router.put(
    "/{id}",
    response_model=ShiftAssignmentResponse,
    dependencies=[Depends(has_permission("shift_assignment.update"))],
    summary="Update Shift Assignment",
    description="Updates shift ID, effective dates, assignment type, or active status.",
)
async def update_shift_assignment(
    id: uuid.UUID,
    data: ShiftAssignmentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ShiftAssignmentService(db)
    updated = await service.update_assignment(
        id=id, data=data, current_user=current_user, request=request
    )
    return _format_shift_assignment_response(updated)


@router.patch(
    "/{id}/end",
    response_model=ShiftAssignmentResponse,
    dependencies=[Depends(has_permission("shift_assignment.update"))],
    summary="End Shift Assignment",
    description="Sets the effective_to date for an active shift assignment.",
)
async def end_shift_assignment(
    id: uuid.UUID,
    data: ShiftAssignmentEndRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ShiftAssignmentService(db)
    ended = await service.end_assignment(
        id=id, data=data, current_user=current_user, request=request
    )
    return _format_shift_assignment_response(ended)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(has_permission("shift_assignment.delete"))],
    summary="Delete Shift Assignment",
    description="Soft-deletes a shift assignment if no locked attendance records exist in its date range.",
)
async def delete_shift_assignment(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ShiftAssignmentService(db)
    await service.delete_assignment(id=id, current_user=current_user, request=request)
    return None
