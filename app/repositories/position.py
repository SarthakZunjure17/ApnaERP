from typing import List, Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.position import Position
from app.repositories.base_repository import BaseRepository
from app.schemas.position import PositionCreate, PositionUpdate


class PositionRepository(BaseRepository[Position, PositionCreate, PositionUpdate]):
    """
    Repository layer for Position entity.
    Provides database access methods for positions, department queries, and hierarchy trees.
    """
    def __init__(self):
        super().__init__(Position)

    async def get_by_code(
        self, db: AsyncSession, code: str, include_deleted: bool = False
    ) -> Optional[Position]:
        """Retrieves a Position by unique position code."""
        query = select(Position).where(func.lower(Position.code) == code.lower())
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        return res.scalars().first()

    async def get_by_department_and_title(
        self, db: AsyncSession, department_id: uuid.UUID, title: str, include_deleted: bool = False
    ) -> Optional[Position]:
        """Retrieves a Position by Department ID and Position Title (case-insensitive)."""
        query = select(Position).where(
            Position.department_id == department_id,
            func.lower(Position.title) == title.lower(),
        )
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        return res.scalars().first()

    async def get_by_department(
        self, db: AsyncSession, department_id: uuid.UUID, include_deleted: bool = False
    ) -> List[Position]:
        """Retrieves all positions belonging to a specific department."""
        query = select(Position).where(Position.department_id == department_id)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        query = query.order_by(Position.code.asc())
        res = await db.execute(query)
        return list(res.scalars().all())

    async def get_children(
        self, db: AsyncSession, parent_position_id: uuid.UUID, include_deleted: bool = False
    ) -> List[Position]:
        """Retrieves direct child positions reporting to a parent position."""
        query = select(Position).where(Position.parent_position_id == parent_position_id)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        query = query.order_by(Position.title.asc())
        res = await db.execute(query)
        return list(res.scalars().all())

    async def get_tree(
        self, db: AsyncSession, department_id: Optional[uuid.UUID] = None, include_deleted: bool = False
    ) -> List[Position]:
        """Retrieves root positions (parent_position_id IS NULL) to construct hierarchy tree."""
        query = select(Position).where(Position.parent_position_id.is_(None))
        if department_id:
            query = query.where(Position.department_id == department_id)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        query = query.order_by(Position.code.asc())
        res = await db.execute(query)
        return list(res.scalars().all())

    async def exists_by_code(
        self, db: AsyncSession, code: str, include_deleted: bool = False
    ) -> bool:
        """Checks if a position code exists."""
        query = select(func.count()).select_from(Position).where(
            func.lower(Position.code) == code.lower()
        )
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        count = res.scalar_one_or_none() or 0
        return count > 0


position_repository = PositionRepository()
