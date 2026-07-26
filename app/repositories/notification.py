import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationTemplate
from app.repositories.base_repository import BaseRepository
from app.schemas.notification import NotificationCreate, NotificationTemplateCreate, NotificationTemplateUpdate
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.search import apply_search
from app.utils.sorting import SortCriterion, SortOrder, apply_sorting


class NotificationRepository(BaseRepository[Notification, NotificationCreate, NotificationCreate]):
    """
    Repository layer for Notification entity.
    """
    def __init__(self):
        super().__init__(Notification)

    async def get_user_notifications(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        params: PaginationParams,
        unread_only: bool = False,
        notification_type: Optional[str] = None,
        is_read: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search_term: Optional[str] = None,
        sorting: Optional[List[SortCriterion]] = None,
    ) -> PaginatedResult[Notification]:
        """
        Retrieves paginated notifications for a specific user with filtering and searching.
        """
        query = select(Notification).where(Notification.user_id == user_id)

        if unread_only or is_read is False:
            query = query.where(Notification.is_read == False)
        elif is_read is True:
            query = query.where(Notification.is_read == True)

        if notification_type:
            query = query.where(func.lower(Notification.notification_type) == notification_type.lower())

        if start_date:
            query = query.where(Notification.created_at >= start_date)
        if end_date:
            query = query.where(Notification.created_at <= end_date)

        query = apply_search(query, Notification, search_term, search_fields=["title", "message"])

        count_query = select(func.count()).select_from(query.subquery())
        count_res = await db.execute(count_query)
        total = count_res.scalar_one_or_none() or 0

        if not sorting:
            sorting = [SortCriterion(field="created_at", order=SortOrder.DESC)]

        paginated_query = apply_sorting(query, Notification, sorting)
        paginated_query = paginated_query.offset(params.offset).limit(params.page_size)

        result = await db.execute(paginated_query)
        items = list(result.scalars().all())

        return PaginatedResult(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    async def mark_as_read(self, db: AsyncSession, *, notification_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Notification]:
        """
        Marks a specific notification as read for a given user.
        """
        notification = await self.get_by_id(db, notification_id)
        if not notification or notification.user_id != user_id:
            return None

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            db.add(notification)
            await db.commit()
            await db.refresh(notification)

        return notification

    async def mark_all_as_read(self, db: AsyncSession, *, user_id: uuid.UUID) -> int:
        """
        Marks all unread notifications as read for a given user.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True, read_at=now)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount or 0


class NotificationTemplateRepository(BaseRepository[NotificationTemplate, NotificationTemplateCreate, NotificationTemplateUpdate]):
    """
    Repository layer for NotificationTemplate entity.
    """
    def __init__(self):
        super().__init__(NotificationTemplate)

    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[NotificationTemplate]:
        """
        Retrieves a NotificationTemplate by unique name.
        """
        result = await db.execute(select(NotificationTemplate).where(func.lower(NotificationTemplate.name) == name.lower()))
        return result.scalars().first()


notification_repository = NotificationRepository()
notification_template_repository = NotificationTemplateRepository()
