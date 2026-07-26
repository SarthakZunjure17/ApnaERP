from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.user import User
from app.schemas.position import (
    PositionCreate,
    PositionListResponse,
    PositionResponse,
    PositionTreeResponse,
    PositionUpdate,
)
from app.services.position import PositionService

router = APIRouter()


@router.get(
    "/positions",
    response_model=PositionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Job Positions",
    description="Retrieves a paginated list of job positions with search, filtering, and sorting.",
    dependencies=[Depends(has_permission("position.read"))]
)
async def list_positions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for code, title, grade, or level"),
    department_id: Optional[uuid.UUID] = Query(None, description="Filter by Department UUID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
) -> PositionListResponse:
    """Lists positions with pagination and filtering."""
    service = PositionService(db)
    result = await service.get_positions_list(
        page=page, page_size=page_size, search=search, department_id=department_id, is_active=is_active
    )
    return PositionListResponse(
        items=[PositionResponse.model_validate(item) for item in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get(
    "/positions/tree",
    response_model=List[PositionTreeResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Position Hierarchy Tree",
    description="Retrieves nested position reporting hierarchy tree, cached via Redis.",
    dependencies=[Depends(has_permission("position.read"))]
)
async def get_position_tree(
    department_id: Optional[uuid.UUID] = Query(None, description="Optional department filter"),
    db: AsyncSession = Depends(get_db),
) -> List[PositionTreeResponse]:
    """Retrieves position hierarchy tree."""
    service = PositionService(db)
    return await service.get_position_tree(department_id=department_id)


@router.get(
    "/positions/{id}",
    response_model=PositionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Position Details",
    description="Retrieves detailed position information by UUID.",
    dependencies=[Depends(has_permission("position.read"))]
)
async def get_position_by_id(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PositionResponse:
    """Retrieves position by ID."""
    service = PositionService(db)
    pos = await service.get_position_by_id(id)
    return PositionResponse.model_validate(pos)


@router.get(
    "/departments/{department_id}/positions",
    response_model=List[PositionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Department Positions",
    description="Retrieves all active positions belonging to a specific department.",
    dependencies=[Depends(has_permission("position.read"))]
)
async def get_positions_by_department(
    department_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> List[PositionResponse]:
    """Retrieves positions for a department."""
    service = PositionService(db)
    positions = await service.get_positions_by_department(department_id)
    return [PositionResponse.model_validate(p) for p in positions]


@router.post(
    "/positions",
    response_model=PositionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Job Position",
    description="Defines a new enterprise job position within a department.",
    dependencies=[Depends(has_permission("position.create"))]
)
async def create_position(
    payload: PositionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PositionResponse:
    """Creates a new job position."""
    service = PositionService(db)
    pos = await service.create_position(data=payload, current_user=current_user, request=request)
    return PositionResponse.model_validate(pos)


@router.put(
    "/positions/{id}",
    response_model=PositionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Job Position",
    description="Updates position details, department placement, parent reporting position, or headcount limits.",
    dependencies=[Depends(has_permission("position.update"))]
)
async def update_position(
    id: uuid.UUID,
    payload: PositionUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PositionResponse:
    """Updates an existing position."""
    service = PositionService(db)
    pos = await service.update_position(
        position_id=id, data=payload, current_user=current_user, request=request
    )
    return PositionResponse.model_validate(pos)


@router.delete(
    "/positions/{id}",
    response_model=PositionResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft Delete Job Position",
    description="Soft-deletes a job position definition if no assigned employees or child positions exist.",
    dependencies=[Depends(has_permission("position.delete"))]
)
async def delete_position(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PositionResponse:
    """Soft deletes a position."""
    service = PositionService(db)
    pos = await service.delete_position(
        position_id=id, current_user=current_user, request=request
    )
    return PositionResponse.model_validate(pos)


@router.patch(
    "/positions/{id}/restore",
    response_model=PositionResponse,
    status_code=status.HTTP_200_OK,
    summary="Restore Soft-Deleted Position",
    description="Restores a soft-deleted job position definition.",
    dependencies=[Depends(has_permission("position.restore"))]
)
async def restore_position(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PositionResponse:
    """Restores a soft-deleted position."""
    service = PositionService(db)
    pos = await service.restore_position(
        position_id=id, current_user=current_user, request=request
    )
    return PositionResponse.model_validate(pos)
