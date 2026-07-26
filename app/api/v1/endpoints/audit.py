import uuid
from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_db, has_role
from app.dependencies.query_params import get_pagination_params, get_sorting_params
from app.models.user import User
from app.schemas.audit_log import AuditLogResponse
from app.schemas.responses import PaginatedResponse, SuccessResponse, create_paginated_response, create_success_response
from app.services.audit_log import audit_log_service
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortCriterion, SortOrder

router = APIRouter()


@router.get(
    "/audit/logs",
    response_model=PaginatedResponse[AuditLogResponse],
    status_code=status.HTTP_200_OK,
    summary="List Audit Logs",
    description="Retrieves paginated audit log entries with filtering across user, action, entity, status code, and date ranges. Requires Super Admin privilege.",
)
async def get_audit_logs(
    user_id: Optional[uuid.UUID] = Query(default=None, description="Filter by User UUID"),
    username: Optional[str] = Query(default=None, description="Filter by Username"),
    action: Optional[str] = Query(default=None, description="Filter by Action code (e.g. LOGIN, CREATE, ROLE_ASSIGN)"),
    entity_type: Optional[str] = Query(default=None, description="Filter by Target Entity Type (e.g. User, Role)"),
    entity_id: Optional[str] = Query(default=None, description="Filter by Target Entity ID"),
    status_code: Optional[int] = Query(default=None, description="Filter by HTTP status code"),
    start_date: Optional[datetime] = Query(default=None, description="Filter records created on or after UTC timestamp"),
    end_date: Optional[datetime] = Query(default=None, description="Filter records created on or before UTC timestamp"),
    params: PaginationParams = Depends(get_pagination_params),
    sorting: Optional[list[SortCriterion]] = Depends(get_sorting_params),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_role("Super Admin")),
) -> Any:
    paginated_result = await audit_log_service.get_filtered_logs(
        db,
        params=params,
        user_id=user_id,
        username=username,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        status_code=status_code,
        start_date=start_date,
        end_date=end_date,
        sorting=sorting,
    )
    return create_paginated_response(paginated_result, message="Audit logs retrieved successfully.")


@router.get(
    "/audit/logs/{id}",
    response_model=SuccessResponse[AuditLogResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Audit Log by ID",
    description="Retrieves a specific audit log record by Primary Key ID. Requires Super Admin privilege.",
)
async def get_audit_log_by_id(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_role("Super Admin")),
) -> Any:
    log_entry = await audit_log_service.get_by_id(db, id)
    return create_success_response(data=log_entry, message="Audit log record retrieved successfully.")


@router.get(
    "/audit/entity/{entity}/{id}",
    response_model=PaginatedResponse[AuditLogResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Entity Audit History",
    description="Retrieves complete audit modification history for a specific entity type and entity ID. Requires Super Admin privilege.",
)
async def get_entity_audit_history(
    entity: str,
    id: str,
    params: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_role("Super Admin")),
) -> Any:
    paginated_result = await audit_log_service.get_entity_history(
        db,
        entity_type=entity,
        entity_id=id,
        params=params,
    )
    return create_paginated_response(paginated_result, message=f"Audit history for '{entity}' ID '{id}' retrieved successfully.")
