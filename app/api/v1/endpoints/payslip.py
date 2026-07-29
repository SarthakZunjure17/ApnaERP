from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.exceptions.base import ForbiddenException
from app.models.payslip import Payslip
from app.models.user import User
from app.repositories.employee import employee_repository
from app.schemas.payslip import PayslipResponse
from app.services.payroll_run import PayrollRunService
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortCriterion, SortOrder

router = APIRouter()


def _format_payslip_response(item: Payslip) -> PayslipResponse:
    """Helper formatting Payslip ORM entity to response schema."""
    return PayslipResponse(
        id=item.id,
        payroll_record_id=item.payroll_record_id,
        payslip_number=item.payslip_number,
        employee_id=item.employee_id,
        payroll_period_id=item.payroll_period_id,
        gross_salary=float(item.gross_salary),
        total_earnings=float(item.total_earnings),
        total_deductions=float(item.total_deductions),
        net_salary=float(item.net_salary),
        pdf_file_id=item.pdf_file_id,
        generated_at=item.generated_at,
        published_at=item.published_at,
        status=item.status,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("/payslips", response_model=dict, dependencies=[Depends(has_permission("payslip.read"))])
async def list_payslips(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    employee_id: Optional[uuid.UUID] = Query(None),
    period_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    order: Optional[str] = Query("desc"),
):
    """
    Lists Payslips with pagination, filtering, and sorting.
    """
    service = PayrollRunService(db)
    pagination = PaginationParams(page=page, page_size=page_size)

    sorting = None
    if sort_by:
        sort_order = SortOrder.DESC if order and order.lower() == "desc" else SortOrder.ASC
        sorting = [SortCriterion(field=sort_by, order=sort_order)]

    result = await service.list_payslips(
        params=pagination,
        employee_id=employee_id,
        period_id=period_id,
        status=status_filter,
        search_term=search,
        sorting=sorting,
    )

    items = [_format_payslip_response(item) for item in result.items]
    return {
        "items": items,
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
    }


@router.get("/payslips/{id}", response_model=PayslipResponse)
async def get_payslip(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves details for a specific Payslip by ID.
    Allows HR/Payroll Manager with 'payslip.read' permission or employee owner.
    """
    service = PayrollRunService(db)
    payslip = await service.get_payslip_by_id(id)

    # Check ownership or permission
    emp = await employee_repository.get_by_user_id(db, current_user.id)
    is_owner = emp and str(emp.id) == str(payslip.employee_id)

    if not current_user.is_superuser and not is_owner:
        # Verify permission
        has_perm = False
        if hasattr(current_user, "roles"):
            for role in current_user.roles:
                for perm in getattr(role, "permissions", []):
                    if perm.code == "payslip.read":
                        has_perm = True
                        break
        if not has_perm:
            raise ForbiddenException(message="Permission denied: You do not have permission to view this payslip.")

    return _format_payslip_response(payslip)


@router.get("/employees/{id}/payslips", response_model=List[PayslipResponse])
async def list_employee_payslips(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves all payslips for an employee.
    """
    service = PayrollRunService(db)

    # Check ownership or permission
    emp = await employee_repository.get_by_user_id(db, current_user.id)
    is_owner = emp and str(emp.id) == str(id)

    if not current_user.is_superuser and not is_owner:
        has_perm = False
        if hasattr(current_user, "roles"):
            for role in current_user.roles:
                for perm in getattr(role, "permissions", []):
                    if perm.code == "payslip.read":
                        has_perm = True
                        break
        if not has_perm:
            raise ForbiddenException(message="Permission denied: You do not have permission to view employee payslips.")

    payslips = await service.get_employee_payslips(employee_id=id)
    return [_format_payslip_response(p) for p in payslips]


@router.get("/payslips/{id}/download")
async def download_payslip_pdf(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Downloads the PDF Payslip document binary file stream.
    """
    service = PayrollRunService(db)
    payslip, file_record, file_bytes = await service.download_payslip_pdf(payslip_id=id, current_user=current_user)

    filename = file_record.original_filename or f"{payslip.payslip_number}.pdf"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }

    return Response(
        content=file_bytes,
        media_type="application/pdf",
        headers=headers,
    )
