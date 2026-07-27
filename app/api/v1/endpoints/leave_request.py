from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.leave_request import LeaveRequest
from app.models.user import User
from app.schemas.leave_request import (
    LeaveRequestCancelRequest,
    LeaveRequestCreate,
    LeaveRequestListResponse,
    LeaveRequestResponse,
    LeaveRequestReviewRequest,
)
from app.services.leave_request import LeaveRequestService
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginationParams

router = APIRouter()


def _format_leave_request_response(item: LeaveRequest) -> LeaveRequestResponse:
    """Helper formatting LeaveRequest ORM object to LeaveRequestResponse Pydantic schema."""
    emp_code = item.employee.employee_code if item.employee else None
    emp_name = f"{item.employee.first_name} {item.employee.last_name}".strip() if item.employee else None
    lt_code = item.leave_type.code if item.leave_type else None
    lt_name = item.leave_type.name if item.leave_type else None
    rev_name = item.reviewer.full_name if item.reviewer else None

    return LeaveRequestResponse(
        id=item.id,
        employee_id=item.employee_id,
        leave_type_id=item.leave_type_id,
        start_date=item.start_date,
        end_date=item.end_date,
        total_days=item.total_days,
        is_half_day=item.is_half_day,
        half_day_session=item.half_day_session,
        reason=item.reason,
        status=item.status,
        submitted_at=item.submitted_at,
        reviewed_at=item.reviewed_at,
        reviewed_by=item.reviewed_by,
        reviewer_comments=item.reviewer_comments,
        created_at=item.created_at,
        updated_at=item.updated_at,
        is_deleted=item.is_deleted,
        deleted_at=item.deleted_at,
        employee_code=emp_code,
        employee_name=emp_name,
        leave_type_code=lt_code,
        leave_type_name=lt_name,
        reviewer_name=rev_name,
    )


@router.get(
    "",
    response_model=LeaveRequestListResponse,
    dependencies=[Depends(has_permission("leave_request.read"))],
    summary="List all Leave Requests",
    description="Retrieves a paginated list of leave requests across the organization.",
)
async def list_leave_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (Draft, Pending, Approved, Rejected, Cancelled, Completed)"),
    leave_type_id: Optional[uuid.UUID] = Query(None, description="Filter by leave type ID"),
    employee_id: Optional[uuid.UUID] = Query(None, description="Filter by employee ID"),
    db: AsyncSession = Depends(get_db),
):
    service = LeaveRequestService(db)
    params = PaginationParams(page=page, page_size=page_size)

    filters = []
    if status_filter:
        filters.append(FilterCriterion(field="status", value=status_filter))
    if leave_type_id is not None:
        filters.append(FilterCriterion(field="leave_type_id", value=leave_type_id))
    if employee_id is not None:
        filters.append(FilterCriterion(field="employee_id", value=employee_id))

    paginated = await service.list_leave_requests(params=params, filters=filters)
    items = [_format_leave_request_response(item) for item in paginated.items]

    return LeaveRequestListResponse(
        items=items,
        total=paginated.total,
        page=paginated.page,
        page_size=paginated.page_size,
        total_pages=paginated.total_pages,
    )


@router.get(
    "/employees/{id}/leave-requests",
    response_model=LeaveRequestListResponse,
    dependencies=[Depends(has_permission("leave_request.read"))],
    summary="List Employee Leave Requests",
    description="Retrieves paginated leave requests for a specific employee.",
)
async def list_employee_leave_requests(
    id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status", description="Optional filter by status"),
    db: AsyncSession = Depends(get_db),
):
    service = LeaveRequestService(db)
    params = PaginationParams(page=page, page_size=page_size)
    paginated = await service.get_employee_leave_requests(
        employee_id=id, status=status_filter, params=params
    )
    items = [_format_leave_request_response(item) for item in paginated.items]

    return LeaveRequestListResponse(
        items=items,
        total=paginated.total,
        page=paginated.page,
        page_size=paginated.page_size,
        total_pages=paginated.total_pages,
    )


@router.get(
    "/{id}",
    response_model=LeaveRequestResponse,
    dependencies=[Depends(has_permission("leave_request.read"))],
    summary="Get Leave Request by ID",
    description="Retrieves details for a single Leave Request record.",
)
async def get_leave_request(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = LeaveRequestService(db)
    item = await service.get_leave_request_by_id(id)
    return _format_leave_request_response(item)


@router.post(
    "",
    response_model=LeaveRequestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("leave_request.create"))],
    summary="Create Leave Request",
    description="Creates a new leave request application in 'Draft' status.",
)
async def create_leave_request(
    data: LeaveRequestCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LeaveRequestService(db)
    created = await service.create_leave_request(data=data, current_user=current_user, request=request)
    return _format_leave_request_response(created)


@router.post(
    "/{id}/submit",
    response_model=LeaveRequestResponse,
    dependencies=[Depends(has_permission("leave_request.submit"))],
    summary="Submit Leave Request",
    description="Submits a Draft leave request for approval (transitions Draft -> Pending).",
)
async def submit_leave_request(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LeaveRequestService(db)
    submitted = await service.submit_leave_request(id=id, current_user=current_user, request=request)
    return _format_leave_request_response(submitted)


@router.post(
    "/{id}/approve",
    response_model=LeaveRequestResponse,
    dependencies=[Depends(has_permission("leave_request.approve"))],
    summary="Approve Leave Request",
    description="Approves a Pending leave request (transitions Pending -> Approved) and updates LeaveBalance availed days.",
)
async def approve_leave_request(
    id: uuid.UUID,
    data: LeaveRequestReviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LeaveRequestService(db)
    approved = await service.approve_leave_request(id=id, data=data, current_user=current_user, request=request)
    return _format_leave_request_response(approved)


@router.post(
    "/{id}/reject",
    response_model=LeaveRequestResponse,
    dependencies=[Depends(has_permission("leave_request.reject"))],
    summary="Reject Leave Request",
    description="Rejects a Pending leave request (transitions Pending -> Rejected).",
)
async def reject_leave_request(
    id: uuid.UUID,
    data: LeaveRequestReviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LeaveRequestService(db)
    rejected = await service.reject_leave_request(id=id, data=data, current_user=current_user, request=request)
    return _format_leave_request_response(rejected)


@router.post(
    "/{id}/cancel",
    response_model=LeaveRequestResponse,
    dependencies=[Depends(has_permission("leave_request.cancel"))],
    summary="Cancel Leave Request",
    description="Cancels a leave request. Restores leave balance if previously Approved.",
)
async def cancel_leave_request(
    id: uuid.UUID,
    data: LeaveRequestCancelRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LeaveRequestService(db)
    cancelled = await service.cancel_leave_request(id=id, data=data, current_user=current_user, request=request)
    return _format_leave_request_response(cancelled)
