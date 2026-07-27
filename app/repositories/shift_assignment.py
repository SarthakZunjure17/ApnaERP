import datetime
from typing import List, Optional
import uuid
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import Attendance
from app.models.shift_assignment import ShiftAssignment
from app.repositories.base_repository import BaseRepository
from app.schemas.shift_assignment import ShiftAssignmentCreate, ShiftAssignmentUpdate
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginatedResult, PaginationParams


class ShiftAssignmentRepository(
    BaseRepository[ShiftAssignment, ShiftAssignmentCreate, ShiftAssignmentUpdate]
):
    """
    Repository layer for ShiftAssignment entity.
    Provides database queries for active shift lookups, interval overlap detection,
    and attendance locking safeguards.
    """
    def __init__(self):
        super().__init__(ShiftAssignment)

    async def get_active_assignment_for_date(
        self, db: AsyncSession, employee_id: uuid.UUID, target_date: datetime.date
    ) -> Optional[ShiftAssignment]:
        """
        Retrieves the active shift assignment for a specific employee on a given target date.
        """
        query = (
            select(ShiftAssignment)
            .where(
                ShiftAssignment.employee_id == employee_id,
                ShiftAssignment.is_active.is_(True),
                ShiftAssignment.is_deleted.is_(False),
                ShiftAssignment.effective_from <= target_date,
                or_(
                    ShiftAssignment.effective_to.is_(None),
                    ShiftAssignment.effective_to >= target_date,
                ),
            )
            .order_by(ShiftAssignment.effective_from.desc(), ShiftAssignment.created_at.desc())
        )
        res = await db.execute(query)
        return res.scalars().first()

    async def check_overlap(
        self,
        db: AsyncSession,
        employee_id: uuid.UUID,
        effective_from: datetime.date,
        effective_to: Optional[datetime.date],
        exclude_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """
        Checks if the date range [effective_from, effective_to] overlaps with any existing
        active shift assignment for the employee.
        """
        query = select(ShiftAssignment).where(
            ShiftAssignment.employee_id == employee_id,
            ShiftAssignment.is_active.is_(True),
            ShiftAssignment.is_deleted.is_(False),
        )

        if exclude_id:
            query = query.where(ShiftAssignment.id != exclude_id)

        # Overlap logic:
        # Proposed: [P_start, P_end]
        # Existing: [E_start, E_end]
        # Overlap occurs if P_start <= E_end (or E_end is NULL) AND P_end >= E_start (or P_end is NULL)
        conditions = [ShiftAssignment.effective_from <= (effective_to if effective_to else datetime.date(9999, 12, 31))]

        if effective_to is not None:
            conditions.append(
                or_(
                    ShiftAssignment.effective_to.is_(None),
                    ShiftAssignment.effective_to >= effective_from,
                )
            )
        else:
            conditions.append(
                or_(
                    ShiftAssignment.effective_to.is_(None),
                    ShiftAssignment.effective_to >= effective_from,
                )
            )

        query = query.where(and_(*conditions))
        res = await db.execute(query)
        return res.scalars().first() is not None

    async def get_employee_assignments_paginated(
        self,
        db: AsyncSession,
        employee_id: uuid.UUID,
        params: PaginationParams,
        include_deleted: bool = False,
    ) -> PaginatedResult[ShiftAssignment]:
        """
        Retrieves paginated shift assignments for a specific employee.
        """
        filters = [FilterCriterion(field="employee_id", value=employee_id)]
        return await self.get_multi_paginated(
            db, params=params, filters=filters, include_deleted=include_deleted
        )

    async def has_locked_attendance_in_range(
        self,
        db: AsyncSession,
        employee_id: uuid.UUID,
        start_date: datetime.date,
        end_date: Optional[datetime.date] = None,
    ) -> bool:
        """
        Checks if there are any payroll-locked attendance records for the employee within the date range.
        """
        query = select(Attendance).where(
            Attendance.employee_id == employee_id,
            Attendance.is_locked.is_(True),
            Attendance.is_deleted.is_(False),
            Attendance.attendance_date >= start_date,
        )
        if end_date:
            query = query.where(Attendance.attendance_date <= end_date)

        res = await db.execute(query)
        return res.scalars().first() is not None


shift_assignment_repository = ShiftAssignmentRepository()
