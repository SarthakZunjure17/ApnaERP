from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.user import User
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeHierarchyResponse,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdate,
)
from app.services.employee import EmployeeService

router = APIRouter()


@router.get(
    "/hierarchy",
    response_model=List[EmployeeHierarchyResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Employee Reporting Hierarchy",
    description="Retrieves top-level root managers with nested direct reports reporting tree.",
    dependencies=[Depends(has_permission("employee.read"))]
)
async def get_employee_hierarchy(
    db: AsyncSession = Depends(get_db),
) -> List[EmployeeHierarchyResponse]:
    """Retrieves employee reporting hierarchy from cache or database."""
    service = EmployeeService(db)
    return await service.get_employee_hierarchy()


@router.get(
    "/department/{department_id}",
    response_model=List[EmployeeResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Employees by Department",
    description="Retrieves active employees assigned to a specific department.",
    dependencies=[Depends(has_permission("employee.read"))]
)
async def get_employees_by_department(
    department_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> List[EmployeeResponse]:
    """Retrieves active employees by department ID."""
    service = EmployeeService(db)
    employees = await service.get_employees_by_department(department_id)
    return [EmployeeResponse.model_validate(e) for e in employees]


@router.get(
    "",
    response_model=EmployeeListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Employees",
    description="Retrieves a paginated list of employees with search and filtering.",
    dependencies=[Depends(has_permission("employee.read"))]
)
async def list_employees(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for name, employee code, or work email"),
    db: AsyncSession = Depends(get_db),
) -> EmployeeListResponse:
    """Lists employees with pagination and search."""
    service = EmployeeService(db)
    result = await service.get_employees_list(page=page, page_size=page_size, search=search)
    return EmployeeListResponse.model_validate(result)


@router.get(
    "/{id}",
    response_model=EmployeeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Employee Details",
    description="Retrieves employee details by UUID.",
    dependencies=[Depends(has_permission("employee.read"))]
)
async def get_employee_by_id(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> EmployeeResponse:
    """Retrieves single employee by ID."""
    service = EmployeeService(db)
    emp = await service.get_employee_by_id(id)
    return EmployeeResponse.model_validate(emp)


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Employee",
    description="Creates a new employee record in the organization.",
    dependencies=[Depends(has_permission("employee.create"))]
)
async def create_employee(
    payload: EmployeeCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmployeeResponse:
    """Creates a new employee."""
    service = EmployeeService(db)
    emp = await service.create_employee(data=payload, current_user=current_user, request=request)
    return EmployeeResponse.model_validate(emp)


@router.put(
    "/{id}",
    response_model=EmployeeResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Employee",
    description="Updates employee profile, department, manager, or status.",
    dependencies=[Depends(has_permission("employee.update"))]
)
async def update_employee(
    id: uuid.UUID,
    payload: EmployeeUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmployeeResponse:
    """Updates an existing employee."""
    service = EmployeeService(db)
    emp = await service.update_employee(
        employee_id=id, data=payload, current_user=current_user, request=request
    )
    return EmployeeResponse.model_validate(emp)


@router.delete(
    "/{id}",
    response_model=EmployeeResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft Delete Employee",
    description="Soft-deletes an employee record.",
    dependencies=[Depends(has_permission("employee.delete"))]
)
async def delete_employee(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmployeeResponse:
    """Soft deletes an employee."""
    service = EmployeeService(db)
    emp = await service.delete_employee(
        employee_id=id, current_user=current_user, request=request
    )
    return EmployeeResponse.model_validate(emp)


@router.patch(
    "/{id}/restore",
    response_model=EmployeeResponse,
    status_code=status.HTTP_200_OK,
    summary="Restore Soft-Deleted Employee",
    description="Restores a soft-deleted employee record.",
    dependencies=[Depends(has_permission("employee.restore"))]
)
async def restore_employee(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmployeeResponse:
    """Restores a soft-deleted employee."""
    service = EmployeeService(db)
    emp = await service.restore_employee(
        employee_id=id, current_user=current_user, request=request
    )
    return EmployeeResponse.model_validate(emp)
