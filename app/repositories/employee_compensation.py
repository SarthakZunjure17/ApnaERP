import datetime
import logging
from typing import List, Optional
import uuid
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee_compensation import EmployeeCompensation
from app.repositories.base_repository import BaseRepository
from app.schemas.employee_compensation import (
    EmployeeCompensationCreate,
    EmployeeCompensationUpdate,
)

logger = logging.getLogger("app.repositories.employee_compensation")


class EmployeeCompensationRepository(
    BaseRepository[EmployeeCompensation, EmployeeCompensationCreate, EmployeeCompensationUpdate]
):
    """
    Repository layer for EmployeeCompensation entities.
    Provides active compensation lookups, historical policy queries, and overlap validations.
    """

    def __init__(self):
        super().__init__(EmployeeCompensation)

    async def get_active_compensation(
        self, db: AsyncSession, employee_id: uuid.UUID
    ) -> Optional[EmployeeCompensation]:
        """Retrieves the currently Active compensation policy for an employee."""
        query = (
            select(EmployeeCompensation)
            .where(
                EmployeeCompensation.employee_id == employee_id,
                EmployeeCompensation.status == "Active",
                EmployeeCompensation.is_deleted.is_(False),
            )
            .order_by(EmployeeCompensation.effective_from.desc())
        )
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def get_compensation_history(
        self, db: AsyncSession, employee_id: uuid.UUID
    ) -> List[EmployeeCompensation]:
        """Retrieves all historical and current compensation records for an employee ordered by revision_number desc."""
        query = (
            select(EmployeeCompensation)
            .where(
                EmployeeCompensation.employee_id == employee_id,
                EmployeeCompensation.is_deleted.is_(False),
            )
            .order_by(EmployeeCompensation.revision_number.desc())
        )
        res = await db.execute(query)
        return list(res.unique().scalars().all())

    async def get_future_compensation(
        self, db: AsyncSession, employee_id: uuid.UUID
    ) -> List[EmployeeCompensation]:
        """Retrieves future compensation records for an employee whose effective_from is after today."""
        today = datetime.date.today()
        query = (
            select(EmployeeCompensation)
            .where(
                EmployeeCompensation.employee_id == employee_id,
                EmployeeCompensation.effective_from > today,
                EmployeeCompensation.status.in_(["Draft", "Active"]),
                EmployeeCompensation.is_deleted.is_(False),
            )
            .order_by(EmployeeCompensation.effective_from)
        )
        res = await db.execute(query)
        return list(res.unique().scalars().all())

    async def check_overlapping_effective_dates(
        self,
        db: AsyncSession,
        employee_id: uuid.UUID,
        effective_from: datetime.date,
        effective_to: Optional[datetime.date] = None,
        exclude_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """
        Checks if the proposed effective date range overlaps with any active or draft compensation records for the employee.
        Returns True if an overlap exists, False otherwise.
        """
        query = select(EmployeeCompensation).where(
            EmployeeCompensation.employee_id == employee_id,
            EmployeeCompensation.status.in_(["Draft", "Active"]),
            EmployeeCompensation.is_deleted.is_(False),
        )
        if exclude_id:
            query = query.where(EmployeeCompensation.id != exclude_id)

        res = await db.execute(query)
        records = res.unique().scalars().all()

        for rec in records:
            rec_from = rec.effective_from
            rec_to = rec.effective_to

            # Check overlap: (StartA <= EndB) and (EndA >= StartB)
            # If rec_to is None, consider infinity. If effective_to is None, consider infinity.
            if rec_to is None and effective_to is None:
                return True
            elif rec_to is None:
                if effective_to >= rec_from:
                    return True
            elif effective_to is None:
                if effective_from <= rec_to:
                    return True
            else:
                if effective_from <= rec_to and effective_to >= rec_from:
                    return True

        return False

    async def restore(self, db: AsyncSession, id: uuid.UUID) -> Optional[EmployeeCompensation]:
        """Restores a soft-deleted EmployeeCompensation record."""
        obj = await self.get_by_id(db, id=id, include_deleted=True)
        if not obj or not obj.is_deleted:
            return obj

        obj.is_deleted = False
        obj.deleted_at = None
        await db.commit()
        await db.refresh(obj)
        logger.info(f"[EmployeeCompensation] Restored soft-deleted compensation ID '{id}' for employee '{obj.employee_id}'")
        return obj


employee_compensation_repository = EmployeeCompensationRepository()
