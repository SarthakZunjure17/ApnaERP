import logging
from typing import Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leave_balance import LeaveBalance
from app.repositories.base_repository import BaseRepository
from app.schemas.leave_balance import LeaveBalanceCreate, LeaveBalanceUpdate
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginatedResult, PaginationParams

logger = logging.getLogger("app.repositories.leave_balance")


class LeaveBalanceRepository(
    BaseRepository[LeaveBalance, LeaveBalanceCreate, LeaveBalanceUpdate]
):
    """
    Repository layer for LeaveBalance entity.
    Provides queries for employee leave balance lookups by employee/leave_type/year,
    paginated employee balance histories, and soft-delete restoration.
    """

    def __init__(self):
        super().__init__(LeaveBalance)

    async def get_by_employee_type_year(
        self,
        db: AsyncSession,
        employee_id: uuid.UUID,
        leave_type_id: uuid.UUID,
        leave_year: int,
        include_deleted: bool = False,
    ) -> Optional[LeaveBalance]:
        """
        Retrieves a LeaveBalance record for a specific employee, leave type, and leave year.
        """
        query = select(LeaveBalance).where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type_id == leave_type_id,
            LeaveBalance.leave_year == leave_year,
        )
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        return res.scalars().first()

    async def get_employee_balances_paginated(
        self,
        db: AsyncSession,
        employee_id: uuid.UUID,
        leave_year: Optional[int],
        params: PaginationParams,
        include_deleted: bool = False,
    ) -> PaginatedResult[LeaveBalance]:
        """
        Retrieves paginated leave balances for a specific employee, optionally filtered by leave year.
        """
        filters = [FilterCriterion(field="employee_id", value=employee_id)]
        if leave_year is not None:
            filters.append(FilterCriterion(field="leave_year", value=leave_year))

        return await self.get_multi_paginated(
            db, params=params, filters=filters, include_deleted=include_deleted
        )

    async def restore(self, db: AsyncSession, id: uuid.UUID) -> Optional[LeaveBalance]:
        """
        Restores a soft-deleted LeaveBalance entity.
        """
        obj = await self.get_by_id(db, id=id, include_deleted=True)
        if not obj or not obj.is_deleted:
            return obj

        obj.is_deleted = False
        obj.deleted_at = None
        await db.commit()
        await db.refresh(obj)
        logger.info(f"[LeaveBalance] Restored soft-deleted leave balance ID '{id}'")
        return obj


leave_balance_repository = LeaveBalanceRepository()
