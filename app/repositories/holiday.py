import datetime
from typing import List, Optional
import uuid
from sqlalchemy import extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.holiday import Holiday
from app.repositories.base_repository import BaseRepository
from app.schemas.holiday import HolidayCreate, HolidayUpdate


class HolidayRepository(BaseRepository[Holiday, HolidayCreate, HolidayUpdate]):
    """
    Repository layer for Holiday entity.
    Provides database access methods for holiday calendar schedules, code/date/region lookups,
    and annual recurring holiday queries.
    """
    def __init__(self):
        super().__init__(Holiday)

    async def get_by_code(
        self, db: AsyncSession, code: str, include_deleted: bool = False
    ) -> Optional[Holiday]:
        """Retrieves a Holiday by unique code."""
        query = select(Holiday).where(func.lower(Holiday.code) == code.lower())
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        return res.scalars().first()

    async def exists_by_code(
        self, db: AsyncSession, code: str, include_deleted: bool = False
    ) -> bool:
        """Checks if a holiday code exists."""
        query = select(func.count()).select_from(Holiday).where(func.lower(Holiday.code) == code.lower())
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        count = res.scalar_one_or_none() or 0
        return count > 0

    async def get_by_date_and_region(
        self,
        db: AsyncSession,
        holiday_date: datetime.date,
        country: str,
        state_region: Optional[str] = None,
        include_deleted: bool = False,
    ) -> Optional[Holiday]:
        """Retrieves a Holiday matching specific date, country, and state_region."""
        query = select(Holiday).where(
            Holiday.holiday_date == holiday_date,
            func.lower(Holiday.country) == country.lower(),
        )
        if state_region:
            query = query.where(func.lower(Holiday.state_region) == state_region.lower())
        else:
            query = query.where(Holiday.state_region.is_(None))

        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        return res.scalars().first()

    async def get_holidays_by_year(
        self,
        db: AsyncSession,
        year: int,
        country: Optional[str] = None,
        state_region: Optional[str] = None,
    ) -> List[Holiday]:
        """
        Retrieves all active holidays for a specific calendar year.
        Includes non-recurring holidays occurring in `year` AND recurring annual holidays from any year.
        """
        query = select(Holiday).where(
            Holiday.is_active.is_(True),
            or_(
                extract("year", Holiday.holiday_date) == year,
                Holiday.is_recurring_annually.is_(True),
            )
        )
        if country:
            query = query.where(func.lower(Holiday.country) == country.lower())
        if state_region:
            query = query.where(
                or_(
                    Holiday.state_region.is_(None),
                    func.lower(Holiday.state_region) == state_region.lower(),
                )
            )

        query = self._apply_soft_delete_filter(query, include_deleted=False)
        query = query.order_by(Holiday.holiday_date.asc())
        res = await db.execute(query)
        raw_holidays = list(res.scalars().all())

        # Project recurring annual holidays onto target year
        result_holidays = []
        for h in raw_holidays:
            if h.is_recurring_annually and h.holiday_date.year != year:
                try:
                    projected_date = datetime.date(year, h.holiday_date.month, h.holiday_date.day)
                except ValueError:
                    # Handle Feb 29 in non-leap year -> Feb 28
                    projected_date = datetime.date(year, h.holiday_date.month, 28)

                # Create transient copy with projected date
                h_copy = Holiday(
                    id=h.id,
                    code=h.code,
                    name=h.name,
                    description=h.description,
                    holiday_date=projected_date,
                    holiday_type=h.holiday_type,
                    country=h.country,
                    state_region=h.state_region,
                    is_half_day=h.is_half_day,
                    is_recurring_annually=h.is_recurring_annually,
                    is_active=h.is_active,
                    created_at=h.created_at,
                    updated_at=h.updated_at,
                    is_deleted=h.is_deleted,
                    deleted_at=h.deleted_at,
                )
                result_holidays.append(h_copy)
            else:
                result_holidays.append(h)

        result_holidays.sort(key=lambda x: x.holiday_date)
        return result_holidays

    async def get_holidays_by_date(
        self,
        db: AsyncSession,
        target_date: datetime.date,
        country: Optional[str] = None,
        state_region: Optional[str] = None,
    ) -> List[Holiday]:
        """
        Retrieves active holidays falling on a specific date (including annual recurring holidays).
        """
        query = select(Holiday).where(
            Holiday.is_active.is_(True),
            or_(
                Holiday.holiday_date == target_date,
                (
                    Holiday.is_recurring_annually.is_(True)
                    & (extract("month", Holiday.holiday_date) == target_date.month)
                    & (extract("day", Holiday.holiday_date) == target_date.day)
                ),
            )
        )
        if country:
            query = query.where(func.lower(Holiday.country) == country.lower())
        if state_region:
            query = query.where(
                or_(
                    Holiday.state_region.is_(None),
                    func.lower(Holiday.state_region) == state_region.lower(),
                )
            )

        query = self._apply_soft_delete_filter(query, include_deleted=False)
        res = await db.execute(query)
        return list(res.scalars().all())


holiday_repository = HolidayRepository()
