import datetime
import logging
from typing import Any, List, Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.employee_statutory_profile import EmployeeStatutoryProfile
from app.repositories.base_repository import BaseRepository
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.sorting import SortCriterion, SortOrder, apply_sorting

logger = logging.getLogger("app.repositories.employee_statutory_profile")


class EmployeeStatutoryProfileRepository(
    BaseRepository[EmployeeStatutoryProfile, Any, Any]
):
    """
    Repository layer for EmployeeStatutoryProfile entity database interactions.
    """

    def __init__(self):
        super().__init__(EmployeeStatutoryProfile)

    async def get_by_id(
        self, db: AsyncSession, id: uuid.UUID
    ) -> Optional[EmployeeStatutoryProfile]:
        """Retrieves an EmployeeStatutoryProfile by ID with loaded relationships."""
        query = select(EmployeeStatutoryProfile).options(
            selectinload(EmployeeStatutoryProfile.employee),
            selectinload(EmployeeStatutoryProfile.country),
        ).where(EmployeeStatutoryProfile.id == id)
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def get_active_profile_by_employee(
        self,
        db: AsyncSession,
        employee_id: uuid.UUID,
        target_date: Optional[datetime.date] = None,
    ) -> Optional[EmployeeStatutoryProfile]:
        """
        Retrieves the active EmployeeStatutoryProfile for an employee.
        """
        target = target_date or datetime.date.today()
        query = (
            select(EmployeeStatutoryProfile)
            .options(
                selectinload(EmployeeStatutoryProfile.employee),
                selectinload(EmployeeStatutoryProfile.country),
            )
            .where(
                EmployeeStatutoryProfile.employee_id == employee_id,
                EmployeeStatutoryProfile.is_active == True,
                EmployeeStatutoryProfile.effective_from <= target,
                (EmployeeStatutoryProfile.effective_to == None) | (EmployeeStatutoryProfile.effective_to >= target),
            )
            .order_by(EmployeeStatutoryProfile.effective_from.desc())
        )
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def get_all_profiles_by_employee(
        self, db: AsyncSession, employee_id: uuid.UUID
    ) -> List[EmployeeStatutoryProfile]:
        """Retrieves all statutory profile history for an employee ordered by effective_from DESC."""
        query = (
            select(EmployeeStatutoryProfile)
            .options(
                selectinload(EmployeeStatutoryProfile.employee),
                selectinload(EmployeeStatutoryProfile.country),
            )
            .where(EmployeeStatutoryProfile.employee_id == employee_id)
            .order_by(EmployeeStatutoryProfile.effective_from.desc())
        )
        res = await db.execute(query)
        return list(res.unique().scalars().all())

    async def get_filtered_profiles(
        self,
        db: AsyncSession,
        *,
        params: PaginationParams,
        employee_id: Optional[uuid.UUID] = None,
        country_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
        sorting: Optional[List[SortCriterion]] = None,
    ) -> PaginatedResult[EmployeeStatutoryProfile]:
        """
        Queries EmployeeStatutoryProfile records with filtering, pagination, and sorting.
        """
        query = select(EmployeeStatutoryProfile).options(
            selectinload(EmployeeStatutoryProfile.employee),
            selectinload(EmployeeStatutoryProfile.country),
        )

        if employee_id:
            query = query.where(EmployeeStatutoryProfile.employee_id == employee_id)
        if country_id:
            query = query.where(EmployeeStatutoryProfile.country_id == country_id)
        if is_active is not None:
            query = query.where(EmployeeStatutoryProfile.is_active == is_active)

        # Apply sorting
        default_sort = [SortCriterion(field="effective_from", order=SortOrder.DESC)]
        query = apply_sorting(query, EmployeeStatutoryProfile, sorting if sorting else default_sort)

        # Count total records
        count_query = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_query)
        total = total_res.scalar_one()

        # Apply pagination
        query = query.offset((params.page - 1) * params.page_size).limit(params.page_size)
        results = await db.execute(query)
        items = list(results.unique().scalars().all())

        return PaginatedResult(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
        )


employee_statutory_profile_repository = EmployeeStatutoryProfileRepository()
