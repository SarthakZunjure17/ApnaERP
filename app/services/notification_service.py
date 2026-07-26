import logging
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import ForbiddenException, NotFoundException, ValidationException
from app.models.notification import Notification, NotificationTemplate
from app.models.user import User
from app.repositories.notification import notification_repository, notification_template_repository
from app.repositories.user import user_repository
from app.schemas.notification import NotificationCreate, NotificationSendRequest, NotificationTemplateCreate, NotificationTemplateUpdate
from app.services.base_service import BaseService
from app.services.email_service import email_service
from app.services.template_service import template_service
from app.utils.audit import log_audit
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.sorting import SortCriterion

logger = logging.getLogger("app.services.notification")


class NotificationService(BaseService[notification_repository.__class__]):
    """
    Service layer coordinating In-App and Email notifications, template rendering,
    recipient lookups, read status management, and audit trail logging.
    """
    def __init__(self):
        super().__init__(notification_repository)
        self.template_repo = notification_template_repository

    async def send_notification(
        self,
        db: AsyncSession,
        *,
        request: NotificationSendRequest,
        sender: Optional[User] = None,
    ) -> Notification:
        """
        Dispatches an In-App or Email notification, rendering Jinja2 templates if specified.
        """
        recipient = await user_repository.get_by_id(db, request.user_id)
        if not recipient:
            raise NotFoundException(message=f"Recipient user '{request.user_id}' not found.")

        title = request.title or "System Notification"
        message = request.message or ""

        # Handle Template Rendering if template_name is specified
        if request.template_name:
            template = await self.template_repo.get_by_name(db, request.template_name)
            if not template:
                raise NotFoundException(message=f"Notification template '{request.template_name}' not found.")

            context = request.template_data or {}
            # Inject default context variables if missing
            context.setdefault("user_name", recipient.full_name or recipient.username)
            context.setdefault("email", recipient.email)

            message = template_service.render(template.template_body, context)
            if template.subject:
                title = template_service.render(template.subject, context)

        if not message:
            raise ValidationException(message="Notification message content or template payload must be provided.")

        # Create In-App Notification Record
        notification_in = NotificationCreate(
            user_id=recipient.id,
            title=title,
            message=message,
            notification_type=request.notification_type,
            priority=request.priority,
            is_read=False,
        )
        notification = await self.repository.create(db, obj_in=notification_in)

        # Dispatch Email if channel type is EMAIL
        if request.notification_type.upper() == "EMAIL":
            email_service.send_email(
                recipient_email=recipient.email,
                subject=title,
                body_text=message,
                body_html=f"<h3>{title}</h3><p>{message}</p>",
            )

        # Log Audit Event
        await log_audit(
            db,
            action="NOTIFICATION_SEND",
            entity_type="Notification",
            entity_id=notification.id,
            user_id=sender.id if sender else recipient.id,
            username=sender.username if sender else recipient.username,
            new_data={
                "recipient_id": str(recipient.id),
                "recipient_email": recipient.email,
                "title": title,
                "notification_type": request.notification_type,
            },
            status_code=201,
        )

        return notification

    async def get_user_notifications(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        params: PaginationParams,
        unread_only: bool = False,
        notification_type: Optional[str] = None,
        is_read: Optional[bool] = None,
        search_term: Optional[str] = None,
        sorting: Optional[List[SortCriterion]] = None,
    ) -> PaginatedResult[Notification]:
        return await self.repository.get_user_notifications(
            db,
            user_id=user_id,
            params=params,
            unread_only=unread_only,
            notification_type=notification_type,
            is_read=is_read,
            search_term=search_term,
            sorting=sorting,
        )

    async def mark_as_read(self, db: AsyncSession, *, notification_id: uuid.UUID, current_user: User) -> Notification:
        notification = await self.repository.get_by_id(db, notification_id)
        if not notification:
            raise NotFoundException(message=f"Notification '{notification_id}' not found.")

        if str(notification.user_id) != str(current_user.id):
            raise ForbiddenException(message="Permission denied: You can only manage your own notifications.")

        updated = await self.repository.mark_as_read(db, notification_id=notification_id, user_id=current_user.id)

        await log_audit(
            db,
            action="NOTIFICATION_READ",
            entity_type="Notification",
            entity_id=notification_id,
            user_id=current_user.id,
            username=current_user.username,
            status_code=200,
        )

        return updated or notification

    async def mark_all_as_read(self, db: AsyncSession, *, current_user: User) -> int:
        count = await self.repository.mark_all_as_read(db, user_id=current_user.id)
        await log_audit(
            db,
            action="NOTIFICATION_READ_ALL",
            entity_type="Notification",
            user_id=current_user.id,
            username=current_user.username,
            new_data={"read_count": count},
            status_code=200,
        )
        return count

    async def delete_notification(self, db: AsyncSession, *, notification_id: uuid.UUID, current_user: User) -> None:
        notification = await self.repository.get_by_id(db, notification_id)
        if not notification:
            raise NotFoundException(message=f"Notification '{notification_id}' not found.")

        if not current_user.is_superuser and str(notification.user_id) != str(current_user.id):
            raise ForbiddenException(message="Permission denied: You can only delete your own notifications.")

        await self.repository.delete(db, id=notification_id)

        await log_audit(
            db,
            action="NOTIFICATION_DELETE",
            entity_type="Notification",
            entity_id=notification_id,
            user_id=current_user.id,
            username=current_user.username,
            status_code=200,
        )

    # Notification Template Management
    async def create_template(
        self, db: AsyncSession, *, template_in: NotificationTemplateCreate, current_user: User
    ) -> NotificationTemplate:
        existing = await self.template_repo.get_by_name(db, template_in.name)
        if existing:
            raise ValidationException(message=f"Notification template '{template_in.name}' already exists.")

        template = await self.template_repo.create(db, obj_in=template_in)

        await log_audit(
            db,
            action="TEMPLATE_CREATE",
            entity_type="NotificationTemplate",
            entity_id=template.id,
            user_id=current_user.id,
            username=current_user.username,
            new_data={"name": template.name, "type": template.template_type},
            status_code=201,
        )
        return template

    async def update_template(
        self, db: AsyncSession, *, template_id: uuid.UUID, template_in: NotificationTemplateUpdate, current_user: User
    ) -> NotificationTemplate:
        template = await self.template_repo.get_by_id(db, template_id)
        if not template:
            raise NotFoundException(message=f"Notification template '{template_id}' not found.")

        updated = await self.template_repo.update(db, db_obj=template, obj_in=template_in)

        await log_audit(
            db,
            action="TEMPLATE_UPDATE",
            entity_type="NotificationTemplate",
            entity_id=template_id,
            user_id=current_user.id,
            username=current_user.username,
            status_code=200,
        )
        return updated

    async def delete_template(self, db: AsyncSession, *, template_id: uuid.UUID, current_user: User) -> None:
        template = await self.template_repo.get_by_id(db, template_id)
        if not template:
            raise NotFoundException(message=f"Notification template '{template_id}' not found.")

        await self.template_repo.delete(db, id=template_id)

        await log_audit(
            db,
            action="TEMPLATE_DELETE",
            entity_type="NotificationTemplate",
            entity_id=template_id,
            user_id=current_user.id,
            username=current_user.username,
            status_code=200,
        )


notification_service = NotificationService()
