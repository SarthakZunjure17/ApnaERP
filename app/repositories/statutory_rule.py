import datetime
import logging
from typing import Any, List, Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.statutory_rule import StatutoryRule, StatutoryRuleSlab
from app.repositories.base_repository import BaseRepository
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.sorting import SortCriterion, SortOrder, apply_sorting

logger = logging.getLogger("app.repositories.statutory_rule")


class StatutoryRuleRepository(BaseRepository[StatutoryRule, Any, Any]):
    """
    Repository layer for StatutoryRule entity database interactions.
    """

    def __init__(self):
        super().__init__(StatutoryRule)

    async def get_by_code(
        self, db: AsyncSession, rule_code: str, include_deleted: bool = False
    ) -> Optional[StatutoryRule]:
        """Retrieves a StatutoryRule by its unique rule_code."""
        query = select(StatutoryRule).options(
            selectinload(StatutoryRule.country),
            selectinload(StatutoryRule.slabs),
        ).where(func.upper(StatutoryRule.rule_code) == rule_code.upper())
        if not include_deleted:
            query = query.where(StatutoryRule.is_deleted == False)
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def get_by_id(
        self, db: AsyncSession, id: uuid.UUID, include_deleted: bool = False
    ) -> Optional[StatutoryRule]:
        """Retrieves a StatutoryRule by ID with loaded relationships."""
        query = select(StatutoryRule).options(
            selectinload(StatutoryRule.country),
            selectinload(StatutoryRule.slabs),
        ).where(StatutoryRule.id == id)
        if not include_deleted:
            query = query.where(StatutoryRule.is_deleted == False)
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def get_applicable_rules(
        self,
        db: AsyncSession,
        *,
        country_id: uuid.UUID,
        target_date: datetime.date,
        rule_type: Optional[str] = None,
    ) -> List[StatutoryRule]:
        """
        Retrieves active statutory rules for a country effective on target_date, ordered by priority ASC.
        """
        query = (
            select(StatutoryRule)
            .options(
                selectinload(StatutoryRule.country),
                selectinload(StatutoryRule.slabs),
            )
            .where(
                StatutoryRule.country_id == country_id,
                StatutoryRule.is_active == True,
                StatutoryRule.is_deleted == False,
                StatutoryRule.effective_from <= target_date,
                (StatutoryRule.effective_to == None) | (StatutoryRule.effective_to >= target_date),
            )
        )
        if rule_type:
            query = query.where(StatutoryRule.rule_type == rule_type)

        query = query.order_by(StatutoryRule.priority.asc(), StatutoryRule.created_at.asc())
        res = await db.execute(query)
        return list(res.unique().scalars().all())

    async def get_filtered_rules(
        self,
        db: AsyncSession,
        *,
        params: PaginationParams,
        country_id: Optional[uuid.UUID] = None,
        rule_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        search_term: Optional[str] = None,
        sorting: Optional[List[SortCriterion]] = None,
    ) -> PaginatedResult[StatutoryRule]:
        """
        Queries StatutoryRule records with filtering, pagination, sorting, and relationship loading.
        """
        query = select(StatutoryRule).options(
            selectinload(StatutoryRule.country),
            selectinload(StatutoryRule.slabs),
        ).where(StatutoryRule.is_deleted == False)

        if country_id:
            query = query.where(StatutoryRule.country_id == country_id)
        if rule_type:
            query = query.where(StatutoryRule.rule_type == rule_type)
        if is_active is not None:
            query = query.where(StatutoryRule.is_active == is_active)
        if search_term:
            term = f"%{search_term}%"
            query = query.where(
                StatutoryRule.rule_code.ilike(term)
                | StatutoryRule.rule_name.ilike(term)
                | StatutoryRule.description.ilike(term)
            )

        # Apply sorting
        default_sort = [SortCriterion(field="priority", order=SortOrder.ASC)]
        query = apply_sorting(query, StatutoryRule, sorting if sorting else default_sort)

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


class StatutoryRuleSlabRepository(BaseRepository[StatutoryRuleSlab, Any, Any]):
    """
    Repository layer for StatutoryRuleSlab entity database interactions.
    """

    def __init__(self):
        super().__init__(StatutoryRuleSlab)

    async def get_slabs_by_rule_id(
        self, db: AsyncSession, rule_id: uuid.UUID
    ) -> List[StatutoryRuleSlab]:
        """Retrieves all slabs for a rule ordered by sequence ASC."""
        query = (
            select(StatutoryRuleSlab)
            .where(StatutoryRuleSlab.statutory_rule_id == rule_id)
            .order_by(StatutoryRuleSlab.sequence.asc())
        )
        res = await db.execute(query)
        return list(res.unique().scalars().all())


statutory_rule_repository = StatutoryRuleRepository()
statutory_rule_slab_repository = StatutoryRuleSlabRepository()
