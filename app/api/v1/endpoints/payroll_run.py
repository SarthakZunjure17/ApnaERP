from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.payroll_run import PayrollRun
from app.models.user import User
from app.schemas.payroll_run import PayrollRunCreate, PayrollRunResponse
from app.schemas.payslip import PayslipResponse
from app.services.payroll_run import PayrollRunService
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortCriterion, SortOrder

router = APIRouter()


def _format_run_response(item: PayrollRun) -> PayrollRunResponse:
    """Helper formatting PayrollRun ORM entity to response schema."""
    return PayrollRunResponse(
        id=item.id,
        payroll_period_id=item.payroll_period_id,
        run_number=item.run_number,
        run_type=item.run_type,
        status=item.status,
        started_by=item.started_by,
        started_at=item.started_at,
        completed_at=item.completed_at,
        locked_at=item.locked_at,
        remarks=item.remarks,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("", response_model=dict, dependencies=[Depends(has_permission("payroll_run.read"))])
async def list_payroll_runs(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    period_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    run_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    order: Optional[str] = Query("desc"),
):
    """
    Lists Payroll Runs with filtering, sorting, and pagination.
    """
    service = PayrollRunService(db)
    pagination = PaginationParams(page=page, page_size=page_size)

    sorting = None
    if sort_by:
        sort_order = SortOrder.DESC if order and order.lower() == "desc" else SortOrder.ASC
        sorting = [SortCriterion(field=sort_by, order=sort_order)]

    result = await service.list_payroll_runs(
        params=pagination,
        period_id=period_id,
        status=status_filter,
        run_type=run_type,
        search_term=search,
        sorting=sorting,
    )

    items = [_format_run_response(item) for item in result.items]
    return {
        "items": items,
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
    }


@router.post("", response_model=PayrollRunResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(has_permission("payroll_run.create"))])
async def create_payroll_run(
    data: PayrollRunCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creates a new Payroll Run batch in Draft state.
    """
    service = PayrollRunService(db)
    run = await service.create_payroll_run(data=data, current_user=current_user)
    return _format_run_response(run)


@router.get("/{id}", response_model=PayrollRunResponse, dependencies=[Depends(has_permission("payroll_run.read"))])
async def get_payroll_run(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves details for a specific Payroll Run by ID.
    """
    service = PayrollRunService(db)
    run = await service.get_run_by_id(id)
    return _format_run_response(run)


@router.post("/{id}/start", response_model=PayrollRunResponse, dependencies=[Depends(has_permission("payroll_run.update"))])
async def start_payroll_run(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Starts a Payroll Run, transitioning it to Processing state.
    """
    service = PayrollRunService(db)
    run = await service.start_payroll_run(run_id=id, current_user=current_user)
    return _format_run_response(run)


@router.post("/{id}/complete", response_model=PayrollRunResponse, dependencies=[Depends(has_permission("payroll_run.update"))])
async def complete_payroll_run(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Marks a Payroll Run as Completed and triggers notification to Payroll Team.
    """
    service = PayrollRunService(db)
    run = await service.complete_payroll_run(run_id=id, current_user=current_user)
    return _format_run_response(run)


@router.post("/{id}/lock", response_model=PayrollRunResponse, dependencies=[Depends(has_permission("payroll_run.lock"))])
async def lock_payroll_run(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Locks a Payroll Run permanently.
    """
    service = PayrollRunService(db)
    run = await service.lock_payroll_run(run_id=id, current_user=current_user)
    return _format_run_response(run)


@router.post("/{id}/generate-payslips", response_model=List[PayslipResponse], dependencies=[Depends(has_permission("payslip.generate"))])
async def generate_payslips_for_run(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates ReportLab PDF Payslip documents for all records in the Payroll Run.
    """
    service = PayrollRunService(db)
    payslips = await service.generate_payslips(run_id=id, current_user=current_user)
    return [
        PayslipResponse(
            id=p.id,
            payroll_record_id=p.payroll_record_id,
            payslip_number=p.payslip_number,
            employee_id=p.employee_id,
            payroll_period_id=p.payroll_period_id,
            gross_salary=float(p.gross_salary),
            total_earnings=float(p.total_earnings),
            total_deductions=float(p.total_deductions),
            net_salary=float(p.net_salary),
            pdf_file_id=p.pdf_file_id,
            generated_at=p.generated_at,
            published_at=p.published_at,
            status=p.status,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in payslips
    ]


@router.post("/{id}/publish-payslips", response_model=List[PayslipResponse], dependencies=[Depends(has_permission("payslip.publish"))])
async def publish_payslips_for_run(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Publishes generated payslips to employees and dispatches notifications.
    """
    service = PayrollRunService(db)
    payslips = await service.publish_payslips(run_id=id, current_user=current_user)
    return [
        PayslipResponse(
            id=p.id,
            payroll_record_id=p.payroll_record_id,
            payslip_number=p.payslip_number,
            employee_id=p.employee_id,
            payroll_period_id=p.payroll_period_id,
            gross_salary=float(p.gross_salary),
            total_earnings=float(p.total_earnings),
            total_deductions=float(p.total_deductions),
            net_salary=float(p.net_salary),
            pdf_file_id=p.pdf_file_id,
            generated_at=p.generated_at,
            published_at=p.published_at,
            status=p.status,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in payslips
    ]
