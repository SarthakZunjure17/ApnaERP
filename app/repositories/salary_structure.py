import logging
from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.salary_structure import SalaryStructure, SalaryStructureComponent
from app.repositories.base_repository import BaseRepository
from app.schemas.salary_structure import (
    SalaryStructureComponentCreate,
    SalaryStructureComponentUpdate,
    SalaryStructureCreate,
    SalaryStructureUpdate,
)

logger = logging.getLogger("app.repositories.salary_structure")


class SalaryStructureRepository(
    BaseRepository[SalaryStructure, SalaryStructureCreate, SalaryStructureUpdate]
):
    """
    Repository layer for SalaryStructure entities.
    Provides lookup by code, name, and soft-delete restoration.
    """

    def __init__(self):
        super().__init__(SalaryStructure)

    async def get_by_code(
        self, db: AsyncSession, code: str, include_deleted: bool = False
    ) -> Optional[SalaryStructure]:
        """Retrieves a SalaryStructure by its unique structure code."""
        query = select(SalaryStructure).where(SalaryStructure.code == code)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def get_by_name(
        self, db: AsyncSession, name: str, include_deleted: bool = False
    ) -> Optional[SalaryStructure]:
        """Retrieves a SalaryStructure by its unique structure name."""
        query = select(SalaryStructure).where(SalaryStructure.name == name)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def restore(self, db: AsyncSession, id: uuid.UUID) -> Optional[SalaryStructure]:
        """Restores a soft-deleted SalaryStructure definition."""
        obj = await self.get_by_id(db, id=id, include_deleted=True)
        if not obj or not obj.is_deleted:
            return obj

        obj.is_deleted = False
        obj.deleted_at = None
        await db.commit()
        await db.refresh(obj)
        logger.info(f"[SalaryStructure] Restored soft-deleted structure ID '{id}' (code: '{obj.code}')")
        return obj


class SalaryStructureComponentRepository(
    BaseRepository[SalaryStructureComponent, SalaryStructureComponentCreate, SalaryStructureComponentUpdate]
):
    """
    Repository layer for SalaryStructureComponent mapping entities.
    """

    def __init__(self):
        super().__init__(SalaryStructureComponent)

    async def get_by_structure_and_component(
        self, db: AsyncSession, structure_id: uuid.UUID, component_id: uuid.UUID
    ) -> Optional[SalaryStructureComponent]:
        """Retrieves a structure component mapping by structure_id and component_id."""
        query = select(SalaryStructureComponent).where(
            SalaryStructureComponent.salary_structure_id == structure_id,
            SalaryStructureComponent.salary_component_id == component_id,
        )
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def get_components_by_structure(
        self, db: AsyncSession, structure_id: uuid.UUID
    ) -> List[SalaryStructureComponent]:
        """Retrieves all component mappings for a given structure ordered by component_order."""
        query = (
            select(SalaryStructureComponent)
            .where(SalaryStructureComponent.salary_structure_id == structure_id)
            .order_by(SalaryStructureComponent.component_order)
        )
        res = await db.execute(query)
        return list(res.unique().scalars().all())


salary_structure_repository = SalaryStructureRepository()
salary_structure_component_repository = SalaryStructureComponentRepository()
