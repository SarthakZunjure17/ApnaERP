import uuid
from typing import Any, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.dependencies.query_params import get_pagination_params, get_search_params, get_sorting_params
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.notification import NotificationResponse, NotificationSendRequest
from app.schemas.responses import PaginatedResponse, SuccessResponse, create_paginated_response, create_success_response
from app.services.notification_service import notification_service
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortCriterion

router = APIRouter()


@router.get(
    "/notifications",
    response_model=PaginatedResponse[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Authenticated User Notifications",
    description="Retrieves a paginated list of notifications belonging exclusively to the authenticated user.",
)
async def list_notifications(
    notification_type: Optional[str] = Query(default=None, description="Filter by type (IN_APP, EMAIL, SYSTEM, ALERT)"),
    is_read: Optional[bool] = Query(default=None, description="Filter by read status"),
    q: Optional[str] = Depends(get_search_params),
    params: PaginationParams = Depends(get_pagination_params),
    sorting: Optional[list[SortCriterion]] = Depends(get_sorting_params),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    paginated_result = await notification_service.get_user_notifications(
        db,
        user_id=current_user.id,
        params=params,
        unread_only=False,
        notification_type=notification_type,
        is_read=is_read,
        search_term=q,
        sorting=sorting,
    )
    return create_paginated_response(paginated_result, message="Notifications retrieved successfully.")


@router.get(
    "/notifications/unread",
    response_model=PaginatedResponse[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Authenticated User Unread Notifications",
    description="Retrieves a paginated list of unread notifications belonging to the authenticated user.",
)
async def list_unread_notifications(
    params: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    paginated_result = await notification_service.get_user_notifications(
        db,
        user_id=current_user.id,
        params=params,
        unread_only=True,
    )
    return create_paginated_response(paginated_result, message="Unread notifications retrieved successfully.")


@router.post(
    "/notifications/send",
    response_model=SuccessResponse[NotificationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Send Notification",
    description="Dispatches an In-App or Email notification to a target user, rendering templates if specified.",
)
async def send_notification(
    request: NotificationSendRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    notification = await notification_service.send_notification(db, request=request, sender=current_user)
    return create_success_response(data=notification, message="Notification dispatched successfully.")


@router.put(
    "/notifications/read/{id}",
    response_model=SuccessResponse[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="Mark Notification as Read",
    description="Marks a specific notification as read for the authenticated user.",
)
async def mark_notification_read(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    notification = await notification_service.mark_as_read(db, notification_id=id, current_user=current_user)
    return create_success_response(data=notification, message="Notification marked as read.")


@router.put(
    "/notifications/read-all",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark All Notifications as Read",
    description="Marks all unread notifications as read for the authenticated user.",
)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    count = await notification_service.mark_all_as_read(db, current_user=current_user)
    return MessageResponse(message=f"Marked {count} notifications as read.")


@router.delete(
    "/notifications/{id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Notification",
    description="Deletes a notification belonging to the authenticated user.",
)
async def delete_notification(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    await notification_service.delete_notification(db, notification_id=id, current_user=current_user)
    return MessageResponse(message=f"Notification '{id}' deleted successfully.")
