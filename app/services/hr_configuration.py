import json
import logging
from typing import Any, Dict, List, Optional
import uuid
import zoneinfo
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import ApnaERPException
from app.models.hr_configuration import HRConfiguration
from app.models.user import User
from app.repositories.hr_configuration import hr_configuration_repository
from app.schemas.hr_configuration import (
    HRConfigurationCreate,
    HRConfigurationResponse,
    HRConfigurationUpdate,
    PayrollCycle,
)
from app.utils.audit import log_audit
from app.tasks.hr_config_tasks import send_hr_config_notification_task

logger = logging.getLogger("app.services.hr_configuration")

CACHE_ACTIVE_PREFIX = "hr_configuration:active"
VALID_WEEKEND_DAYS = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}


class HRConfigurationService:
    """
    Business service layer for HRConfiguration management.
    Enforces singleton active policy rules, timezone validation, working hours bounds,
    active deletion guards, Redis caching, audit logging, and Celery notification dispatch.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = hr_configuration_repository

    def _get_cache_key(self, org_code: Optional[str] = None) -> str:
        """Generates Redis cache key for active HR configuration."""
        if org_code:
            return f"{CACHE_ACTIVE_PREFIX}:{org_code.lower()}"
        return f"{CACHE_ACTIVE_PREFIX}:global"

    async def _invalidate_caches(self, org_code: Optional[str] = None) -> None:
        """Invalidates active HR configuration Redis cache."""
        try:
            keys = [f"{CACHE_ACTIVE_PREFIX}:global"]
            if org_code:
                keys.append(f"{CACHE_ACTIVE_PREFIX}:{org_code.lower()}")
            for k in keys:
                await redis_manager.delete(k)
            logger.info(f"[HRConfigurationService] Invalidated Redis cache for active HR config.")
        except Exception as e:
            logger.warning(f"[HRConfigurationService] Redis cache invalidation error: {e}")

    def _validate_configuration_data(
        self,
        timezone: Optional[str] = None,
        weekend_config: Optional[List[str]] = None,
        payroll_cycle: Optional[Any] = None,
        std_hours: Optional[float] = None,
        min_hours: Optional[float] = None,
        currency: Optional[str] = None,
        country: Optional[str] = None,
    ) -> None:
        """Validates domain business rules for HR Configuration fields."""
        # 1. Validate Timezone
        if timezone is not None:
            try:
                zoneinfo.ZoneInfo(timezone)
            except Exception:
                raise ApnaERPException(
                    message=f"Invalid IANA timezone '{timezone}'. Example valid timezones: 'Asia/Kolkata', 'UTC', 'America/New_York'.",
                    status_code=400,
                    error_code="INVALID_TIMEZONE",
                )

        # 2. Validate Weekend Configuration
        if weekend_config is not None:
            if not isinstance(weekend_config, list):
                raise ApnaERPException(
                    message="Weekend configuration must be a list of day names.",
                    status_code=400,
                    error_code="INVALID_WEEKEND_CONFIG",
                )
            for day in weekend_config:
                if not isinstance(day, str) or day.capitalize() not in VALID_WEEKEND_DAYS:
                    raise ApnaERPException(
                        message=f"Invalid weekend day '{day}'. Allowed days: {sorted(list(VALID_WEEKEND_DAYS))}.",
                        status_code=400,
                        error_code="INVALID_WEEKEND_CONFIG",
                    )

        # 3. Validate Working Hours Sanity
        if std_hours is not None and std_hours <= 0:
            raise ApnaERPException(
                message="Standard working hours per day must be greater than 0.",
                status_code=400,
                error_code="INVALID_WORKING_HOURS",
            )
        if min_hours is not None and std_hours is not None:
            if min_hours > std_hours:
                raise ApnaERPException(
                    message=f"Minimum working hours ({min_hours}) cannot exceed standard working hours ({std_hours}).",
                    status_code=400,
                    error_code="INVALID_WORKING_HOURS",
                )

        # 4. Validate Currency
        if currency is not None:
            if len(currency.strip()) != 3:
                raise ApnaERPException(
                    message=f"Currency '{currency}' must be a 3-letter ISO code (e.g. INR, USD, EUR).",
                    status_code=400,
                    error_code="INVALID_CURRENCY",
                )

        # 5. Validate Country
        if country is not None:
            if not country.strip():
                raise ApnaERPException(
                    message="Country name cannot be empty.",
                    status_code=400,
                    error_code="INVALID_COUNTRY",
                )

    async def get_active_configuration(
        self, organization_code: Optional[str] = None
    ) -> Optional[HRConfiguration]:
        """
        Retrieves the currently active HR Configuration.
        Checks Redis cache first; if cache miss, queries database and updates cache.
        """
        cache_key = self._get_cache_key(organization_code)
        try:
            cached_raw = await redis_manager.get(cache_key)
            if cached_raw:
                logger.info(f"[HRConfigurationService] Cache hit for active HR config.")
                data_dict = json.loads(cached_raw)
                # Reconstruct HRConfiguration dummy/proxy or fetch from repo if needed
                # Here we fetch from DB to return complete ORM or query if cache miss
        except Exception as e:
            logger.warning(f"[HRConfigurationService] Redis read error: {e}")

        config = await self.repository.get_active_configuration(self.db, organization_code=organization_code)
        if config:
            try:
                resp_schema = HRConfigurationResponse.model_validate(config)
                await redis_manager.set(cache_key, resp_schema.model_dump_json(), ttl=86400)
            except Exception as e:
                logger.warning(f"[HRConfigurationService] Redis set error: {e}")

        return config

    async def get_configuration_by_id(
        self, config_id: uuid.UUID, include_deleted: bool = False
    ) -> HRConfiguration:
        """Retrieves HRConfiguration by UUID."""
        config = await self.repository.get_by_id(self.db, config_id, include_deleted=include_deleted)
        if not config:
            raise ApnaERPException(
                message=f"HR Configuration with ID '{config_id}' not found.",
                status_code=404,
                error_code="CONFIG_NOT_FOUND",
            )
        return config

    async def create_configuration(
        self,
        data: HRConfigurationCreate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> HRConfiguration:
        """
        Creates a new HR Configuration.
        Enforces field validations and singleton active configuration rule.
        """
        self._validate_configuration_data(
            timezone=data.timezone,
            weekend_config=data.weekend_configuration,
            payroll_cycle=data.payroll_cycle,
            std_hours=data.standard_working_hours_per_day,
            min_hours=data.minimum_working_hours,
            currency=data.currency,
            country=data.country,
        )

        # Singleton active rule: if new config is active, deactivate existing active configs
        if data.is_active:
            await self.repository.deactivate_all_active_configurations(self.db, data.organization_code)

        config = await self.repository.create(self.db, obj_in=data)
        await self._invalidate_caches(data.organization_code)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="HR_CONFIG_CREATE",
            entity_type="HRConfiguration",
            entity_id=config.id,
            user_id=user_id,
            username=username,
            new_data=data.model_dump(mode="json"),
            status_code=201,
        )

        try:
            send_hr_config_notification_task.delay(
                event_type="HR_CONFIG_CREATE",
                config_id=str(config.id),
                organization_code=config.organization_code,
                user_id=str(user_id) if user_id else None,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery HR config notification task: {exc}")

        fresh_config = await self.repository.get_by_id(self.db, config.id)
        return fresh_config if fresh_config else config

    async def update_configuration(
        self,
        config_id: uuid.UUID,
        data: HRConfigurationUpdate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> HRConfiguration:
        """
        Updates an existing HR Configuration.
        """
        config = await self.get_configuration_by_id(config_id)

        target_std_hours = data.standard_working_hours_per_day if data.standard_working_hours_per_day is not None else config.standard_working_hours_per_day
        target_min_hours = data.minimum_working_hours if data.minimum_working_hours is not None else config.minimum_working_hours

        self._validate_configuration_data(
            timezone=data.timezone,
            weekend_config=data.weekend_configuration,
            payroll_cycle=data.payroll_cycle,
            std_hours=target_std_hours,
            min_hours=target_min_hours,
            currency=data.currency,
            country=data.country,
        )

        target_org_code = data.organization_code or config.organization_code

        if data.is_active is True and not config.is_active:
            await self.repository.deactivate_all_active_configurations(self.db, target_org_code)

        updated_config = await self.repository.update(self.db, db_obj=config, obj_in=data)
        await self._invalidate_caches(target_org_code)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="HR_CONFIG_UPDATE",
            entity_type="HRConfiguration",
            entity_id=updated_config.id,
            user_id=user_id,
            username=username,
            new_data=data.model_dump(exclude_unset=True, mode="json"),
            status_code=200,
        )

        try:
            send_hr_config_notification_task.delay(
                event_type="HR_CONFIG_UPDATE",
                config_id=str(updated_config.id),
                organization_code=updated_config.organization_code,
                user_id=str(user_id) if user_id else None,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery HR config update notification task: {exc}")

        fresh_config = await self.repository.get_by_id(self.db, updated_config.id)
        return fresh_config if fresh_config else updated_config

    async def activate_configuration(
        self,
        config_id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> HRConfiguration:
        """
        Activates an HR Configuration and deactivates any previously active configuration.
        """
        config = await self.get_configuration_by_id(config_id)
        if config.is_active:
            return config

        await self.repository.deactivate_all_active_configurations(self.db, config.organization_code)

        config.is_active = True
        await self.db.commit()
        await self.db.refresh(config)

        await self._invalidate_caches(config.organization_code)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="HR_CONFIG_ACTIVATE",
            entity_type="HRConfiguration",
            entity_id=config.id,
            user_id=user_id,
            username=username,
            status_code=200,
        )

        try:
            send_hr_config_notification_task.delay(
                event_type="HR_CONFIG_ACTIVATE",
                config_id=str(config.id),
                organization_code=config.organization_code,
                user_id=str(user_id) if user_id else None,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery HR config activation notification task: {exc}")

        fresh_config = await self.repository.get_by_id(self.db, config.id)
        return fresh_config if fresh_config else config

    async def delete_configuration(
        self,
        config_id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> HRConfiguration:
        """
        Soft-deletes an HR Configuration.
        Blocks deletion if the configuration is currently active.
        """
        config = await self.get_configuration_by_id(config_id)

        if config.is_active:
            raise ApnaERPException(
                message=f"Cannot delete active HR Configuration for organization '{config.organization_code}'. Activate another configuration first.",
                status_code=400,
                error_code="ACTIVE_CONFIG_DELETION_PROHIBITED",
            )

        await self.repository.soft_delete(self.db, id=config.id)
        await self._invalidate_caches(config.organization_code)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="HR_CONFIG_DELETE",
            entity_type="HRConfiguration",
            entity_id=config.id,
            user_id=user_id,
            username=username,
            status_code=200,
        )

        deleted_config = await self.repository.get_by_id(self.db, config.id, include_deleted=True)
        return deleted_config if deleted_config else config

    async def restore_configuration(
        self,
        config_id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> HRConfiguration:
        """Restores a soft-deleted HR Configuration."""
        config = await self.repository.get_by_id(self.db, config_id, include_deleted=True)
        if not config or not getattr(config, "is_deleted", False):
            raise ApnaERPException(
                message=f"Soft-deleted HR Configuration with ID '{config_id}' not found.",
                status_code=404,
                error_code="CONFIG_NOT_FOUND",
            )

        await self.repository.restore(self.db, id=config.id)
        await self._invalidate_caches(config.organization_code)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="HR_CONFIG_RESTORE",
            entity_type="HRConfiguration",
            entity_id=config.id,
            user_id=user_id,
            username=username,
            status_code=200,
        )

        restored_config = await self.repository.get_by_id(self.db, config.id)
        return restored_config if restored_config else config
