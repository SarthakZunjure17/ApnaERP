import logging
from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.salary_component import SalaryComponent
from app.repositories.base_repository import BaseRepository
from app.schemas.salary_component import (
    SalaryComponentCreate,
    SalaryComponentUpdate,
)

logger = logging.getLogger("app.repositories.salary_component")


class SalaryComponentRepository(
    BaseRepository[SalaryComponent, SalaryComponentCreate, SalaryComponentUpdate]
):
    """
    Repository layer for SalaryComponent entities.
    Provides lookup by code, name, display_order, and soft-delete restoration.
    """

    def __init__(self):
        super().__init__(SalaryComponent)

    async def get_by_code(
        self, db: AsyncSession, code: str, include_deleted: bool = False
    ) -> Optional[SalaryComponent]:
        """Retrieves a SalaryComponent by its unique component code."""
        query = select(SalaryComponent).where(SalaryComponent.code == code)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def get_by_name(
        self, db: AsyncSession, name: str, include_deleted: bool = False
    ) -> Optional[SalaryComponent]:
        """Retrieves a SalaryComponent by its unique component name."""
        query = select(SalaryComponent).where(SalaryComponent.name == name)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def get_by_display_order(
        self, db: AsyncSession, display_order: int, include_deleted: bool = False
    ) -> Optional[SalaryComponent]:
        """Retrieves a SalaryComponent by its unique display order number."""
        query = select(SalaryComponent).where(SalaryComponent.display_order == display_order)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def get_active_components(self, db: AsyncSession) -> List[SalaryComponent]:
        """Retrieves all active, non-deleted SalaryComponents ordered by display_order."""
        query = (
            select(SalaryComponent)
            .where(SalaryComponent.is_active.is_(True), SalaryComponent.is_deleted.is_(False))
            .order_by(SalaryComponent.display_order)
        )
        res = await db.execute(query)
        return list(res.unique().scalars().all())

    async def restore(self, db: AsyncSession, id: uuid.UUID) -> Optional[SalaryComponent]:
        """Restores a soft-deleted SalaryComponent definition."""
        obj = await self.get_by_id(db, id=id, include_deleted=True)
        if not obj or not obj.is_deleted:
            return obj

        obj.is_deleted = False
        obj.deleted_at = None
        await db.commit()
        await db.refresh(obj)
        logger.info(f"[SalaryComponent] Restored soft-deleted component ID '{id}' (code: '{obj.code}')")
        return obj


salary_component_repository = SalaryComponentRepository()
