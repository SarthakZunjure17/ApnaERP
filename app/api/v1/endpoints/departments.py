from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.user import User
from app.schemas.department import (
    DepartmentCreate,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentTreeResponse,
    DepartmentUpdate,
)
from app.services.department import DepartmentService

router = APIRouter()


@router.get(
    "/tree",
    response_model=List[DepartmentTreeResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Department Hierarchy Tree",
    description="Retrieves top-level root departments with nested child sub-departments.",
    dependencies=[Depends(has_permission("department.read"))]
)
async def get_departments_tree(
    db: AsyncSession = Depends(get_db),
) -> List[DepartmentTreeResponse]:
    """Retrieves department hierarchy tree from cache or database."""
    service = DepartmentService(db)
    return await service.get_departments_tree()


@router.get(
    "",
    response_model=DepartmentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Departments",
    description="Retrieves a paginated list of departments with optional search filtering.",
    dependencies=[Depends(has_permission("department.read"))]
)
async def list_departments(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for department name"),
    db: AsyncSession = Depends(get_db),
) -> DepartmentListResponse:
    """Lists departments with pagination and search."""
    service = DepartmentService(db)
    result = await service.get_departments_list(page=page, page_size=page_size, search=search)
    return DepartmentListResponse.model_validate(result)


@router.get(
    "/{department_id}",
    response_model=DepartmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Department Details",
    description="Retrieves department details by UUID.",
    dependencies=[Depends(has_permission("department.read"))]
)
async def get_department_by_id(
    department_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DepartmentResponse:
    """Retrieves a single department by ID."""
    service = DepartmentService(db)
    dept = await service.get_department_by_id(department_id)
    return DepartmentResponse.model_validate(dept)


@router.post(
    "",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Department",
    description="Creates a new department entity in the hierarchy.",
    dependencies=[Depends(has_permission("department.create"))]
)
async def create_department(
    payload: DepartmentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DepartmentResponse:
    """Creates a new department."""
    service = DepartmentService(db)
    dept = await service.create_department(data=payload, current_user=current_user, request=request)
    return DepartmentResponse.model_validate(dept)


@router.put(
    "/{department_id}",
    response_model=DepartmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Department",
    description="Updates department attributes, parent link, or manager assignment.",
    dependencies=[Depends(has_permission("department.update"))]
)
async def update_department(
    department_id: uuid.UUID,
    payload: DepartmentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DepartmentResponse:
    """Updates an existing department."""
    service = DepartmentService(db)
    dept = await service.update_department(
        department_id=department_id, data=payload, current_user=current_user, request=request
    )
    return DepartmentResponse.model_validate(dept)


@router.delete(
    "/{department_id}",
    response_model=DepartmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft Delete Department",
    description="Soft-deletes a department after verifying no active child departments exist.",
    dependencies=[Depends(has_permission("department.delete"))]
)
async def delete_department(
    department_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DepartmentResponse:
    """Soft deletes a department."""
    service = DepartmentService(db)
    dept = await service.delete_department(
        department_id=department_id, current_user=current_user, request=request
    )
    return DepartmentResponse.model_validate(dept)


@router.patch(
    "/{department_id}/restore",
    response_model=DepartmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Restore Soft-Deleted Department",
    description="Restores a previously soft-deleted department entity.",
    dependencies=[Depends(has_permission("department.restore"))]
)
async def restore_department(
    department_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DepartmentResponse:
    """Restores a soft-deleted department."""
    service = DepartmentService(db)
    dept = await service.restore_department(
        department_id=department_id, current_user=current_user, request=request
    )
    return DepartmentResponse.model_validate(dept)
