from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.api.v1.endpoints.salary_structure import _format_structure_response
from app.models.employee_compensation import EmployeeCompensation
from app.models.user import User
from app.schemas.employee_compensation import (
    EmployeeCompensationCreate,
    EmployeeCompensationListResponse,
    EmployeeCompensationResponse,
    EmployeeCompensationRevise,
    EmployeeCompensationUpdate,
)
from app.services.employee_compensation import EmployeeCompensationService
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginationParams

router = APIRouter()


def _format_compensation_response(item: EmployeeCompensation) -> EmployeeCompensationResponse:
    """Helper formatting EmployeeCompensation ORM entity to response schema."""
    struct_resp = _format_structure_response(item.salary_structure) if hasattr(item, "salary_structure") and item.salary_structure else None
    return EmployeeCompensationResponse(
        id=item.id,
        employee_id=item.employee_id,
        salary_structure_id=item.salary_structure_id,
        effective_from=item.effective_from,
        effective_to=item.effective_to,
        annual_ctc=float(item.annual_ctc),
        monthly_gross_salary=float(item.monthly_gross_salary),
        monthly_net_salary=float(item.monthly_net_salary) if item.monthly_net_salary is not None else None,
        status=item.status,
        revision_number=item.revision_number,
        previous_compensation_id=item.previous_compensation_id,
        remarks=item.remarks,
        approved_by=item.approved_by,
        approved_at=item.approved_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
        salary_structure=struct_resp,
    )


@router.get(
    "/employee-compensations",
    response_model=EmployeeCompensationListResponse,
    dependencies=[Depends(has_permission("compensation.read"))],
    summary="List Employee Compensations",
    description="Retrieves a paginated list of employee compensation records.",
)
async def list_employee_compensations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (Draft, Active, Expired, Cancelled)"),
    employee_id: Optional[uuid.UUID] = Query(None, description="Filter by employee ID"),
    db: AsyncSession = Depends(get_db),
):
    service = EmployeeCompensationService(db)
    params = PaginationParams(page=page, page_size=page_size)

    filters = []
    if status_filter:
        filters.append(FilterCriterion(field="status", value=status_filter))
    if employee_id:
        filters.append(FilterCriterion(field="employee_id", value=employee_id))

    paginated = await service.list_compensations(params=params, filters=filters)
    items = [_format_compensation_response(item) for item in paginated.items]

    return EmployeeCompensationListResponse(
        items=items,
        total=paginated.total,
        page=paginated.page,
        page_size=paginated.page_size,
        total_pages=paginated.total_pages,
    )


@router.get(
    "/employee-compensations/{id}",
    response_model=EmployeeCompensationResponse,
    dependencies=[Depends(has_permission("compensation.read"))],
    summary="Get Employee Compensation by ID",
    description="Retrieves details for a specific employee compensation policy.",
)
async def get_employee_compensation(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = EmployeeCompensationService(db)
    item = await service.get_compensation_by_id(id)
    return _format_compensation_response(item)


@router.get(
    "/employees/{id}/compensation",
    response_model=EmployeeCompensationResponse,
    dependencies=[Depends(has_permission("compensation.read"))],
    summary="Get Current Active Compensation for Employee",
    description="Retrieves the currently Active compensation policy for a given employee.",
)
async def get_current_employee_compensation(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = EmployeeCompensationService(db)
    item = await service.get_current_compensation(id)
    return _format_compensation_response(item)


@router.get(
    "/employees/{id}/compensation/history",
    response_model=List[EmployeeCompensationResponse],
    dependencies=[Depends(has_permission("compensation.read"))],
    summary="Get Employee Compensation History",
    description="Retrieves the full compensation revision history for an employee.",
)
async def get_employee_compensation_history(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = EmployeeCompensationService(db)
    history = await service.get_compensation_history(id)
    return [_format_compensation_response(item) for item in history]


@router.post(
    "/employee-compensations",
    response_model=EmployeeCompensationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("compensation.create"))],
    summary="Assign Compensation",
    description="Assigns a new Salary Structure / Compensation policy to an Employee in Draft status.",
)
async def create_employee_compensation(
    data: EmployeeCompensationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EmployeeCompensationService(db)
    created = await service.assign_compensation(data=data, current_user=current_user, request=request)
    return _format_compensation_response(created)


@router.post(
    "/employee-compensations/{id}/revise",
    response_model=EmployeeCompensationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("compensation.create"))],
    summary="Revise Employee Compensation",
    description="Creates a new compensation revision linked to a previous compensation policy.",
)
async def revise_employee_compensation(
    id: uuid.UUID,
    data: EmployeeCompensationRevise,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EmployeeCompensationService(db)
    revised = await service.revise_compensation(previous_id=id, data=data, current_user=current_user, request=request)
    return _format_compensation_response(revised)


@router.put(
    "/employee-compensations/{id}",
    response_model=EmployeeCompensationResponse,
    dependencies=[Depends(has_permission("compensation.update"))],
    summary="Update Employee Compensation Draft",
    description="Updates details of an existing employee compensation draft.",
)
async def update_employee_compensation(
    id: uuid.UUID,
    data: EmployeeCompensationUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EmployeeCompensationService(db)
    updated = await service.update_compensation(id=id, data=data, current_user=current_user, request=request)
    return _format_compensation_response(updated)


@router.post(
    "/employee-compensations/{id}/activate",
    response_model=EmployeeCompensationResponse,
    dependencies=[Depends(has_permission("compensation.activate"))],
    summary="Activate Employee Compensation",
    description="Activates a compensation policy, automatically expiring any currently active policy for the employee.",
)
async def activate_employee_compensation(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EmployeeCompensationService(db)
    activated = await service.activate_compensation(id=id, current_user=current_user, request=request)
    return _format_compensation_response(activated)


@router.post(
    "/employee-compensations/{id}/cancel",
    response_model=EmployeeCompensationResponse,
    dependencies=[Depends(has_permission("compensation.cancel"))],
    summary="Cancel Employee Compensation",
    description="Cancels an employee compensation policy.",
)
async def cancel_employee_compensation(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EmployeeCompensationService(db)
    cancelled = await service.cancel_compensation(id=id, current_user=current_user, request=request)
    return _format_compensation_response(cancelled)


@router.delete(
    "/employee-compensations/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(has_permission("compensation.delete"))],
    summary="Delete Employee Compensation",
    description="Soft-deletes an employee compensation policy record.",
)
async def delete_employee_compensation(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EmployeeCompensationService(db)
    await service.delete_compensation(id=id, current_user=current_user, request=request)
    return None


@router.patch(
    "/employee-compensations/{id}/restore",
    response_model=EmployeeCompensationResponse,
    dependencies=[Depends(has_permission("compensation.create"))],
    summary="Restore Employee Compensation",
    description="Restores a soft-deleted employee compensation record.",
)
async def restore_employee_compensation(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EmployeeCompensationService(db)
    restored = await service.restore_compensation(id=id, current_user=current_user, request=request)
    return _format_compensation_response(restored)
