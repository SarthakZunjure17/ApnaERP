from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.payroll_period import PayrollPeriod, PayrollRecord, PayrollRecordComponent
from app.models.user import User
from app.schemas.payroll_period import (
    PayrollPeriodCreate,
    PayrollPeriodListResponse,
    PayrollPeriodResponse,
    PayrollRecordComponentResponse,
    PayrollRecordListResponse,
    PayrollRecordResponse,
    PayrollSummaryResponse,
)
from app.services.payroll_engine import PayrollEngineService
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginationParams

router = APIRouter()


def _format_period_response(item: PayrollPeriod) -> PayrollPeriodResponse:
    """Helper formatting PayrollPeriod ORM entity to response schema."""
    return PayrollPeriodResponse(
        id=item.id,
        period_code=item.period_code,
        start_date=item.start_date,
        end_date=item.end_date,
        status=item.status,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _format_record_component_response(item: PayrollRecordComponent) -> PayrollRecordComponentResponse:
    """Helper formatting PayrollRecordComponent ORM entity to response schema."""
    return PayrollRecordComponentResponse(
        id=item.id,
        payroll_record_id=item.payroll_record_id,
        salary_component_id=item.salary_component_id,
        component_name=item.component_name,
        component_type=item.component_type,
        amount=float(item.amount),
    )


def _format_record_response(item: PayrollRecord) -> PayrollRecordResponse:
    """Helper formatting PayrollRecord ORM entity to response schema."""
    components = [
        _format_record_component_response(c)
        for c in (item.components or [])
    ]
    return PayrollRecordResponse(
        id=item.id,
        payroll_period_id=item.payroll_period_id,
        employee_id=item.employee_id,
        employee_compensation_id=item.employee_compensation_id,
        working_days=item.working_days,
        present_days=float(item.present_days),
        leave_days=float(item.leave_days),
        paid_leave_days=float(item.paid_leave_days),
        unpaid_leave_days=float(item.unpaid_leave_days),
        overtime_hours=float(item.overtime_hours),
        gross_salary=float(item.gross_salary),
        total_earnings=float(item.total_earnings),
        total_deductions=float(item.total_deductions),
        net_salary=float(item.net_salary),
        status=item.status,
        created_at=item.created_at,
        updated_at=item.updated_at,
        components=components,
    )


@router.get(
    "/payroll-periods",
    response_model=PayrollPeriodListResponse,
    dependencies=[Depends(has_permission("payroll.read"))],
    summary="List Payroll Periods",
    description="Retrieves a paginated list of payroll processing periods.",
)
async def list_payroll_periods(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (Draft, Processing, Completed, Locked)"),
    db: AsyncSession = Depends(get_db),
):
    service = PayrollEngineService(db)
    params = PaginationParams(page=page, page_size=page_size)

    filters = []
    if status_filter:
        filters.append(FilterCriterion(field="status", value=status_filter))

    paginated = await service.list_payroll_periods(params=params, filters=filters)
    items = [_format_period_response(item) for item in paginated.items]

    return PayrollPeriodListResponse(
        items=items,
        total=paginated.total,
        page=paginated.page,
        page_size=paginated.page_size,
        total_pages=paginated.total_pages,
    )


@router.post(
    "/payroll-periods",
    response_model=PayrollPeriodResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("payroll.generate"))],
    summary="Create Payroll Period",
    description="Creates a new payroll processing period cycle.",
)
async def create_payroll_period(
    data: PayrollPeriodCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PayrollEngineService(db)
    created = await service.create_payroll_period(data=data, current_user=current_user, request=request)
    return _format_period_response(created)


@router.get(
    "/payroll-periods/{id}",
    response_model=PayrollPeriodResponse,
    dependencies=[Depends(has_permission("payroll.read"))],
    summary="Get Payroll Period by ID",
    description="Retrieves details for a specific payroll period.",
)
async def get_payroll_period(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = PayrollEngineService(db)
    item = await service.period_repository.get_by_id(db, id)
    if not item:
        from app.exceptions.base import ApnaERPException
        raise ApnaERPException(message=f"Payroll period '{id}' not found.", status_code=404, error_code="PERIOD_NOT_FOUND")
    return _format_period_response(item)


@router.post(
    "/payroll-periods/{id}/generate",
    response_model=List[PayrollRecordResponse],
    dependencies=[Depends(has_permission("payroll.generate"))],
    summary="Generate Payroll for Period",
    description="Generates employee payroll records for the specified payroll period based on compensation, attendance, and leave.",
)
async def generate_payroll_for_period(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PayrollEngineService(db)
    records = await service.generate_payroll(period_id=id, current_user=current_user, request=request)
    return [_format_record_response(rec) for rec in records]


@router.post(
    "/payroll-periods/{id}/approve",
    response_model=PayrollPeriodResponse,
    dependencies=[Depends(has_permission("payroll.approve"))],
    summary="Approve Payroll Period Records",
    description="Approves all calculated payroll records for a payroll period.",
)
async def approve_payroll_for_period(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PayrollEngineService(db)
    approved = await service.approve_payroll(period_id=id, current_user=current_user, request=request)
    return _format_period_response(approved)


@router.post(
    "/payroll-periods/{id}/lock",
    response_model=PayrollPeriodResponse,
    dependencies=[Depends(has_permission("payroll.lock"))],
    summary="Lock Payroll Period",
    description="Locks a payroll period against further generation or recalculation.",
)
async def lock_payroll_period(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PayrollEngineService(db)
    locked = await service.lock_payroll_period(period_id=id, current_user=current_user, request=request)
    return _format_period_response(locked)


@router.get(
    "/payroll-records",
    response_model=PayrollRecordListResponse,
    dependencies=[Depends(has_permission("payroll.read"))],
    summary="List Payroll Records",
    description="Retrieves a paginated list of generated employee payroll records.",
)
async def list_payroll_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    period_id: Optional[uuid.UUID] = Query(None, description="Filter by payroll period ID"),
    employee_id: Optional[uuid.UUID] = Query(None, description="Filter by employee ID"),
    db: AsyncSession = Depends(get_db),
):
    service = PayrollEngineService(db)
    params = PaginationParams(page=page, page_size=page_size)

    filters = []
    if period_id:
        filters.append(FilterCriterion(field="payroll_period_id", value=period_id))
    if employee_id:
        filters.append(FilterCriterion(field="employee_id", value=employee_id))

    paginated = await service.list_payroll_records(params=params, filters=filters)
    items = [_format_record_response(item) for item in paginated.items]

    return PayrollRecordListResponse(
        items=items,
        total=paginated.total,
        page=paginated.page,
        page_size=paginated.page_size,
        total_pages=paginated.total_pages,
    )


@router.get(
    "/payroll-records/{id}",
    response_model=PayrollRecordResponse,
    dependencies=[Depends(has_permission("payroll.read"))],
    summary="Get Payroll Record by ID",
    description="Retrieves details for a specific generated payroll record.",
)
async def get_payroll_record(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = PayrollEngineService(db)
    item = await service.get_payroll_record_by_id(id)
    return _format_record_response(item)


@router.get(
    "/employees/{id}/payroll",
    response_model=List[PayrollRecordResponse],
    dependencies=[Depends(has_permission("payroll.read"))],
    summary="Get Employee Payroll History",
    description="Retrieves full payroll record history for an employee.",
)
async def get_employee_payroll_history(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = PayrollEngineService(db)
    history = await service.get_employee_payroll_history(id)
    return [_format_record_response(rec) for rec in history]
