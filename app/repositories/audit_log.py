import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.repositories.base_repository import BaseRepository
from app.schemas.audit_log import AuditLogCreate
from app.utils.filters import FilterCriterion, apply_filters
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.sorting import SortCriterion, SortOrder, apply_sorting


class AuditLogRepository(BaseRepository[AuditLog, AuditLogCreate, AuditLogCreate]):
    """
    Repository layer for AuditLog entity.
    """
    def __init__(self):
        super().__init__(AuditLog)

    async def get_filtered_logs(
        self,
        db: AsyncSession,
        *,
        params: PaginationParams,
        user_id: Optional[uuid.UUID] = None,
        username: Optional[str] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        status_code: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sorting: Optional[List[SortCriterion]] = None,
    ) -> PaginatedResult[AuditLog]:
        """
        Retrieves paginated audit log entries with filtering across user, action, entity, status code, and date ranges.
        """
        query = select(AuditLog)

        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if username:
            query = query.where(func.lower(AuditLog.username) == username.lower())
        if action:
            query = query.where(func.lower(AuditLog.action) == action.lower())
        if entity_type:
            query = query.where(func.lower(AuditLog.entity_type) == entity_type.lower())
        if entity_id:
            query = query.where(AuditLog.entity_id == entity_id)
        if status_code is not None:
            query = query.where(AuditLog.status_code == status_code)
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar_one_or_none() or 0

        # Apply sorting (default created_at DESC)
        if not sorting:
            sorting = [SortCriterion(field="created_at", order=SortOrder.DESC)]
        
        paginated_query = apply_sorting(query, AuditLog, sorting)
        paginated_query = paginated_query.offset(params.offset).limit(params.page_size)

        result = await db.execute(paginated_query)
        items = list(result.scalars().all())

        return PaginatedResult(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    async def get_by_entity(
        self,
        db: AsyncSession,
        *,
        entity_type: str,
        entity_id: str,
        params: PaginationParams,
    ) -> PaginatedResult[AuditLog]:
        """
        Retrieves complete audit timeline for a specific entity type and entity ID.
        """
        return await self.get_filtered_logs(
            db,
            params=params,
            entity_type=entity_type,
            entity_id=entity_id,
        )


audit_log_repository = AuditLogRepository()
