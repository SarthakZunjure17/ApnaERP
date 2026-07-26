from typing import List, Optional
import uuid
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hr_configuration import HRConfiguration
from app.repositories.base_repository import BaseRepository
from app.schemas.hr_configuration import HRConfigurationCreate, HRConfigurationUpdate


class HRConfigurationRepository(BaseRepository[HRConfiguration, HRConfigurationCreate, HRConfigurationUpdate]):
    """
    Repository layer for HRConfiguration entity.
    Provides database access methods for organization policies and singleton active configurations.
    """
    def __init__(self):
        super().__init__(HRConfiguration)

    async def get_active_configuration(
        self, db: AsyncSession, organization_code: Optional[str] = None
    ) -> Optional[HRConfiguration]:
        """Retrieves the currently active HR Configuration."""
        query = select(HRConfiguration).where(
            HRConfiguration.is_active.is_(True),
            HRConfiguration.is_deleted.is_(False),
        )
        if organization_code:
            query = query.where(func.lower(HRConfiguration.organization_code) == organization_code.lower())
        
        query = query.order_by(HRConfiguration.updated_at.desc())
        res = await db.execute(query)
        return res.scalars().first()

    async def get_by_organization_code(
        self, db: AsyncSession, organization_code: str, include_deleted: bool = False
    ) -> List[HRConfiguration]:
        """Retrieves all configurations for a given organization code."""
        query = select(HRConfiguration).where(
            func.lower(HRConfiguration.organization_code) == organization_code.lower()
        )
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        query = query.order_by(HRConfiguration.created_at.desc())
        res = await db.execute(query)
        return list(res.scalars().all())

    async def deactivate_all_active_configurations(
        self, db: AsyncSession, organization_code: Optional[str] = None
    ) -> None:
        """Deactivates all active configurations for an organization to enforce singleton active rule."""
        stmt = update(HRConfiguration).where(
            HRConfiguration.is_active.is_(True),
            HRConfiguration.is_deleted.is_(False),
        )
        if organization_code:
            stmt = stmt.where(func.lower(HRConfiguration.organization_code) == organization_code.lower())
        
        stmt = stmt.values(is_active=False)
        await db.execute(stmt)
        await db.commit()


hr_configuration_repository = HRConfigurationRepository()
