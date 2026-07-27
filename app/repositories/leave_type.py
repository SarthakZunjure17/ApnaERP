import logging
from typing import Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leave_type import LeaveType
from app.repositories.base_repository import BaseRepository
from app.schemas.leave_type import LeaveTypeCreate, LeaveTypeUpdate

logger = logging.getLogger("app.repositories.leave_type")


class LeaveTypeRepository(
    BaseRepository[LeaveType, LeaveTypeCreate, LeaveTypeUpdate]
):
    """
    Repository layer for LeaveType entity.
    Provides database queries for code/name unique lookups, soft deletion, and policy restoration.
    """
    def __init__(self):
        super().__init__(LeaveType)

    async def get_by_code(
        self, db: AsyncSession, code: str, include_deleted: bool = False
    ) -> Optional[LeaveType]:
        """
        Retrieves a LeaveType by its unique code.
        """
        query = select(LeaveType).where(LeaveType.code == code)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        return res.scalars().first()

    async def get_by_name(
        self, db: AsyncSession, name: str, include_deleted: bool = False
    ) -> Optional[LeaveType]:
        """
        Retrieves a LeaveType by its unique name.
        """
        query = select(LeaveType).where(LeaveType.name == name)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        return res.scalars().first()

    async def restore(self, db: AsyncSession, id: uuid.UUID) -> Optional[LeaveType]:
        """
        Restores a soft-deleted LeaveType entity.
        """
        obj = await self.get_by_id(db, id=id, include_deleted=True)
        if not obj or not obj.is_deleted:
            return obj

        obj.is_deleted = False
        obj.deleted_at = None
        await db.commit()
        await db.refresh(obj)
        logger.info(f"[LeaveType] Restored soft-deleted leave type record ID '{id}'")
        return obj


leave_type_repository = LeaveTypeRepository()
