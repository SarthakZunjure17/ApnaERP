import uuid
from typing import Any, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_db
from app.dependencies.query_params import get_pagination_params, get_search_params, get_sorting_params
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.notification import NotificationTemplateCreate, NotificationTemplateResponse, NotificationTemplateUpdate
from app.schemas.responses import PaginatedResponse, SuccessResponse, create_paginated_response, create_success_response
from app.services.notification_service import notification_service
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortCriterion

router = APIRouter()


@router.get(
    "/templates",
    response_model=PaginatedResponse[NotificationTemplateResponse],
    status_code=status.HTTP_200_OK,
    summary="List Notification Templates",
    description="Retrieves a paginated list of notification templates.",
)
async def list_templates(
    q: Optional[str] = Depends(get_search_params),
    params: PaginationParams = Depends(get_pagination_params),
    sorting: Optional[list[SortCriterion]] = Depends(get_sorting_params),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    paginated_result = await notification_service.template_repo.get_multi_paginated(
        db,
        params=params,
        search_term=q,
        search_fields=["name", "subject", "template_body"],
        sorting=sorting,
    )
    return create_paginated_response(paginated_result, message="Notification templates retrieved successfully.")


@router.post(
    "/templates",
    response_model=SuccessResponse[NotificationTemplateResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Notification Template",
    description="Creates a new reusable Jinja2 notification template. Restricted to Super Admin.",
)
async def create_template(
    template_in: NotificationTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    template = await notification_service.create_template(db, template_in=template_in, current_user=current_user)
    return create_success_response(data=template, message="Notification template created successfully.")


@router.put(
    "/templates/{id}",
    response_model=SuccessResponse[NotificationTemplateResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Notification Template",
    description="Updates an existing Jinja2 notification template. Restricted to Super Admin.",
)
async def update_template(
    id: uuid.UUID,
    template_in: NotificationTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    template = await notification_service.update_template(db, template_id=id, template_in=template_in, current_user=current_user)
    return create_success_response(data=template, message="Notification template updated successfully.")


@router.delete(
    "/templates/{id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Notification Template",
    description="Deletes a notification template. Restricted to Super Admin.",
)
async def delete_template(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    await notification_service.delete_template(db, template_id=id, current_user=current_user)
    return MessageResponse(message=f"Notification template '{id}' deleted successfully.")
