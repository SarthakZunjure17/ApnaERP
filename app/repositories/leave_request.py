import datetime
import logging
from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leave_request import LeaveRequest
from app.repositories.base_repository import BaseRepository
from app.schemas.leave_request import LeaveRequestCreate, LeaveRequestUpdate
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginatedResult, PaginationParams

logger = logging.getLogger("app.repositories.leave_request")


class LeaveRequestRepository(
    BaseRepository[LeaveRequest, LeaveRequestCreate, LeaveRequestUpdate]
):
    """
    Repository layer for LeaveRequest entity.
    Provides employee request queries, overlap detection, pending approvals queries, and pagination.
    """

    def __init__(self):
        super().__init__(LeaveRequest)

    async def get_employee_requests_paginated(
        self,
        db: AsyncSession,
        employee_id: uuid.UUID,
        status: Optional[str] = None,
        params: Optional[PaginationParams] = None,
        include_deleted: bool = False,
    ) -> PaginatedResult[LeaveRequest]:
        """Retrieves paginated leave requests for a specific employee."""
        filters = [FilterCriterion(field="employee_id", value=employee_id)]
        if status:
            filters.append(FilterCriterion(field="status", value=status))

        params = params or PaginationParams(page=1, page_size=20)
        return await self.get_multi_paginated(
            db, params=params, filters=filters, include_deleted=include_deleted
        )

    async def get_overlapping_requests(
        self,
        db: AsyncSession,
        employee_id: uuid.UUID,
        start_date: datetime.date,
        end_date: datetime.date,
        exclude_id: Optional[uuid.UUID] = None,
    ) -> List[LeaveRequest]:
        """
        Retrieves existing active (Pending or Approved) leave requests for an employee
        that overlap with the specified date range.
        Overlap condition: (req.start_date <= end_date) AND (req.end_date >= start_date)
        """
        query = select(LeaveRequest).where(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status.in_(["Pending", "Approved"]),
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date,
            LeaveRequest.is_deleted.is_(False),
        )
        if exclude_id:
            query = query.where(LeaveRequest.id != exclude_id)

        res = await db.execute(query)
        return list(res.scalars().all())

    async def get_pending_requests_paginated(
        self,
        db: AsyncSession,
        params: Optional[PaginationParams] = None,
        include_deleted: bool = False,
    ) -> PaginatedResult[LeaveRequest]:
        """Retrieves paginated pending leave requests awaiting approval."""
        filters = [FilterCriterion(field="status", value="Pending")]
        params = params or PaginationParams(page=1, page_size=20)
        return await self.get_multi_paginated(
            db, params=params, filters=filters, include_deleted=include_deleted
        )

    async def restore(self, db: AsyncSession, id: uuid.UUID) -> Optional[LeaveRequest]:
        """Restores a soft-deleted LeaveRequest entity."""
        obj = await self.get_by_id(db, id=id, include_deleted=True)
        if not obj or not obj.is_deleted:
            return obj

        obj.is_deleted = False
        obj.deleted_at = None
        await db.commit()
        await db.refresh(obj)
        logger.info(f"[LeaveRequest] Restored soft-deleted leave request ID '{id}'")
        return obj


leave_request_repository = LeaveRequestRepository()
