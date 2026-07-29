from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.exceptions.base import ForbiddenException
from app.models.user import User
from app.repositories.employee import employee_repository
from app.schemas.employee_statutory_profile import (
    EmployeeStatutoryProfileCreate,
    EmployeeStatutoryProfileResponse,
    EmployeeStatutoryProfileUpdate,
)
from app.services.statutory_compliance import StatutoryComplianceService
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.sorting import parse_sort_query

router = APIRouter()


@router.get(
    "/employee-statutory-profiles",
    response_model=PaginatedResult[EmployeeStatutoryProfileResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("statutory_profile.read"))],
)
async def list_employee_statutory_profiles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    employee_id: Optional[uuid.UUID] = Query(None),
    country_id: Optional[uuid.UUID] = Query(None),
    is_active: Optional[bool] = Query(None),
    sort: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves a paginated list of Employee Statutory Profiles.
    """
    service = StatutoryComplianceService(db)
    pagination = PaginationParams(page=page, page_size=page_size)
    sorting = parse_sort_query(sort) if sort else None
    return await service.list_employee_profiles(
        params=pagination,
        employee_id=employee_id,
        country_id=country_id,
        is_active=is_active,
        sorting=sorting,
    )


@router.get(
    "/employees/{id}/statutory-profile",
    response_model=EmployeeStatutoryProfileResponse,
    status_code=status.HTTP_200_OK,
)
async def get_employee_statutory_profile(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves the active statutory profile for an employee.
    Requires statutory_profile.read permission or self-ownership.
    """
    service = StatutoryComplianceService(db)
    emp = await employee_repository.get_by_user_id(db, current_user.id)
    is_owner = emp and str(emp.id) == str(id)

    if not current_user.is_superuser and not is_owner:
        has_perm = False
        if hasattr(current_user, "roles"):
            for role in current_user.roles:
                for perm in getattr(role, "permissions", []):
                    if perm.code == "statutory_profile.read":
                        has_perm = True
                        break
        if not has_perm:
            raise ForbiddenException(message="Permission denied: You do not have permission to view this employee statutory profile.")

    return await service.get_active_profile_by_employee(employee_id=id)


@router.post(
    "/employee-statutory-profiles",
    response_model=EmployeeStatutoryProfileResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("statutory_profile.create"))],
)
async def assign_employee_statutory_profile(
    data: EmployeeStatutoryProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Assigns or creates an Employee Statutory Profile.
    """
    service = StatutoryComplianceService(db)
    return await service.assign_employee_profile(data=data, current_user=current_user)


@router.put(
    "/employee-statutory-profiles/{id}",
    response_model=EmployeeStatutoryProfileResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("statutory_profile.update"))],
)
async def update_employee_statutory_profile(
    id: uuid.UUID,
    data: EmployeeStatutoryProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Updates an Employee Statutory Profile.
    """
    service = StatutoryComplianceService(db)
    return await service.update_employee_profile(id=id, data=data, current_user=current_user)
