import logging
from typing import Any, List, Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.country import Country
from app.repositories.base_repository import BaseRepository
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.sorting import SortCriterion, SortOrder, apply_sorting

logger = logging.getLogger("app.repositories.country")


class CountryRepository(BaseRepository[Country, Any, Any]):
    """
    Repository layer for Country entity database interactions.
    """

    def __init__(self):
        super().__init__(Country)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[Country]:
        """Retrieves a Country by its ISO code (case-insensitive)."""
        query = select(Country).where(func.upper(Country.code) == code.upper())
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def get_filtered_countries(
        self,
        db: AsyncSession,
        *,
        params: PaginationParams,
        is_active: Optional[bool] = None,
        search_term: Optional[str] = None,
        sorting: Optional[List[SortCriterion]] = None,
    ) -> PaginatedResult[Country]:
        """
        Queries Country records with filtering, pagination, and sorting.
        """
        query = select(Country)

        if is_active is not None:
            query = query.where(Country.is_active == is_active)
        if search_term:
            term = f"%{search_term}%"
            query = query.where(
                Country.code.ilike(term) | Country.name.ilike(term) | Country.currency.ilike(term)
            )

        # Apply sorting
        default_sort = [SortCriterion(field="code", order=SortOrder.ASC)]
        query = apply_sorting(query, Country, sorting if sorting else default_sort)

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


country_repository = CountryRepository()
