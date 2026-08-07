from typing import Any, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integrations import (
    ApiKey,
    BackupMetadata,
    ProviderConfiguration,
    SystemConfiguration,
    WebhookDelivery,
    WebhookSubscription,
)
from app.repositories.base_repository import BaseRepository


class ApiKeyRepository(BaseRepository[ApiKey, Any, Any]):
    def __init__(self):
        super().__init__(ApiKey)

    async def get_by_hash(self, db: AsyncSession, key_hash: str) -> Optional[ApiKey]:
        stmt = select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_deleted == False)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_prefix(self, db: AsyncSession, prefix: str) -> List[ApiKey]:
        stmt = select(ApiKey).where(ApiKey.prefix == prefix, ApiKey.is_deleted == False)
        res = await db.execute(stmt)
        return list(res.scalars().all())


class WebhookSubscriptionRepository(BaseRepository[WebhookSubscription, Any, Any]):
    def __init__(self):
        super().__init__(WebhookSubscription)

    async def get_active_subscriptions_for_event(self, db: AsyncSession, event_type: str) -> List[WebhookSubscription]:
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.is_active == True,
            WebhookSubscription.is_deleted == False,
        )
        res = await db.execute(stmt)
        subs = list(res.scalars().all())
        return [
            sub for sub in subs
            if "*" in sub.event_types or event_type in sub.event_types
        ]


class WebhookDeliveryRepository(BaseRepository[WebhookDelivery, Any, Any]):
    def __init__(self):
        super().__init__(WebhookDelivery)

    async def get_pending_retries(self, db: AsyncSession) -> List[WebhookDelivery]:
        stmt = select(WebhookDelivery).where(WebhookDelivery.status == "Retrying")
        res = await db.execute(stmt)
        return list(res.scalars().all())


class ProviderConfigurationRepository(BaseRepository[ProviderConfiguration, Any, Any]):
    def __init__(self):
        super().__init__(ProviderConfiguration)

    async def get_active_provider(self, db: AsyncSession, provider_type: str) -> Optional[ProviderConfiguration]:
        stmt = select(ProviderConfiguration).where(
            ProviderConfiguration.provider_type == provider_type,
            ProviderConfiguration.is_active == True,
            ProviderConfiguration.is_deleted == False,
        ).order_by(ProviderConfiguration.is_default.desc())
        res = await db.execute(stmt)
        return res.scalars().first()


class BackupMetadataRepository(BaseRepository[BackupMetadata, Any, Any]):
    def __init__(self):
        super().__init__(BackupMetadata)

    async def get_by_name(self, db: AsyncSession, backup_name: str) -> Optional[BackupMetadata]:
        stmt = select(BackupMetadata).where(BackupMetadata.backup_name == backup_name)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()


class SystemConfigurationRepository(BaseRepository[SystemConfiguration, Any, Any]):
    def __init__(self):
        super().__init__(SystemConfiguration)

    async def get_by_key(self, db: AsyncSession, config_key: str) -> Optional[SystemConfiguration]:
        stmt = select(SystemConfiguration).where(SystemConfiguration.config_key == config_key)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()
