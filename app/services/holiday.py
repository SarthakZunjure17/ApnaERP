import datetime
import logging
from typing import Any, List, Optional
import uuid
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import ApnaERPException
from app.models.holiday import Holiday
from app.models.user import User
from app.repositories.holiday import holiday_repository
from app.schemas.holiday import HolidayCreate, HolidayResponse, HolidayType, HolidayUpdate
from app.utils.audit import log_audit
from app.tasks.holiday_tasks import send_holiday_notification_task
from app.utils.filters import FilterCriterion, FilterOperator
from app.utils.pagination import PaginatedResult, PaginationParams

logger = logging.getLogger("app.services.holiday")

CACHE_LIST_KEY = "holiday:list"
CACHE_PREFIX = "holiday"


class HolidayService:
    """
    Business service layer for Holiday management.
    Handles official holiday schedules, annual recurring projections, duplicate region checks,
    Redis caching, audit logging, and Celery notification tasks.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = holiday_repository

    async def _invalidate_caches(self) -> None:
        """Invalidates Holiday Redis caches."""
        try:
            await redis_manager.delete(CACHE_LIST_KEY)
            # Invalidate pattern matched keys if supported, or primary list
            logger.info("[HolidayService] Invalidated Redis caches.")
        except Exception as e:
            logger.warning(f"[HolidayService] Redis cache invalidation error: {e}")

    async def get_holiday_by_id(
        self, holiday_id: uuid.UUID, include_deleted: bool = False
    ) -> Holiday:
        """Retrieves a Holiday by UUID."""
        holiday = await self.repository.get_by_id(self.db, holiday_id, include_deleted=include_deleted)
        if not holiday:
            raise ApnaERPException(
                message=f"Holiday with ID '{holiday_id}' not found.",
                status_code=404,
                error_code="HOLIDAY_NOT_FOUND",
            )
        return holiday

    async def get_holidays(
        self,
        page: int = 1,
        page_size: int = 100,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        holiday_type: Optional[str] = None,
        country: Optional[str] = None,
        state_region: Optional[str] = None,
    ) -> PaginatedResult[Holiday]:
        """Retrieves paginated list of holidays with search and multi-field filtering."""
        params = PaginationParams(page=page, page_size=page_size)
        filters = []
        if is_active is not None:
            filters.append(FilterCriterion(field="is_active", operator=FilterOperator.EQ, value=is_active))
        if holiday_type:
            filters.append(FilterCriterion(field="holiday_type", operator=FilterOperator.EQ, value=holiday_type))
        if country:
            filters.append(FilterCriterion(field="country", operator=FilterOperator.EQ, value=country))
        if state_region:
            filters.append(FilterCriterion(field="state_region", operator=FilterOperator.EQ, value=state_region))

        return await self.repository.get_multi_paginated(
            self.db,
            params=params,
            filters=filters,
            search_term=search,
            search_fields=["code", "name", "description", "country", "state_region"],
        )

    async def get_holidays_by_year(
        self,
        year: int,
        country: Optional[str] = None,
        state_region: Optional[str] = None,
    ) -> List[Holiday]:
        """Retrieves holidays occurring in a specific calendar year (including annual recurring ones)."""
        if year < 1900 or year > 2100:
            raise ApnaERPException(
                message=f"Invalid year '{year}'. Must be between 1900 and 2100.",
                status_code=400,
                error_code="INVALID_YEAR",
            )
        return await self.repository.get_holidays_by_year(
            self.db, year=year, country=country, state_region=state_region
        )

    async def get_holidays_by_date(
        self,
        target_date: datetime.date,
        country: Optional[str] = None,
        state_region: Optional[str] = None,
    ) -> List[Holiday]:
        """Retrieves holidays falling on a specific date."""
        return await self.repository.get_holidays_by_date(
            self.db, target_date=target_date, country=country, state_region=state_region
        )

    async def create_holiday(
        self,
        data: HolidayCreate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> Holiday:
        """Creates a new Holiday entry."""
        # 1. Unique code check
        if await self.repository.exists_by_code(self.db, data.code):
            raise ApnaERPException(
                message=f"Holiday with code '{data.code}' already exists.",
                status_code=400,
                error_code="DUPLICATE_HOLIDAY_CODE",
            )

        # 2. Duplicate holiday on same date and region check
        existing = await self.repository.get_by_date_and_region(
            self.db,
            holiday_date=data.holiday_date,
            country=data.country,
            state_region=data.state_region,
        )
        if existing:
            raise ApnaERPException(
                message=f"Holiday '{existing.name}' already exists on {data.holiday_date} for region '{data.country}{'/' + data.state_region if data.state_region else ''}'.",
                status_code=400,
                error_code="DUPLICATE_HOLIDAY",
            )

        holiday = await self.repository.create(self.db, obj_in=data)
        await self._invalidate_caches()

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="HOLIDAY_CREATE",
            entity_type="Holiday",
            entity_id=holiday.id,
            user_id=user_id,
            username=username,
            new_data=data.model_dump(mode="json"),
            status_code=201,
        )

        try:
            send_holiday_notification_task.delay(
                event_type="HOLIDAY_CREATE",
                holiday_id=str(holiday.id),
                holiday_code=holiday.code,
                holiday_name=holiday.name,
                user_id=str(user_id) if user_id else None,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery holiday notification task: {exc}")

        fresh_holiday = await self.repository.get_by_id(self.db, holiday.id)
        return fresh_holiday if fresh_holiday else holiday

    async def update_holiday(
        self,
        holiday_id: uuid.UUID,
        data: HolidayUpdate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> Holiday:
        """Updates an existing Holiday entry."""
        holiday = await self.get_holiday_by_id(holiday_id)

        # Unique code check if changed
        if data.code and data.code.lower() != holiday.code.lower():
            if await self.repository.exists_by_code(self.db, data.code):
                raise ApnaERPException(
                    message=f"Holiday with code '{data.code}' already exists.",
                    status_code=400,
                    error_code="DUPLICATE_HOLIDAY_CODE",
                )

        # Duplicate date & region check if date, country, or region changed
        target_date = data.holiday_date if data.holiday_date is not None else holiday.holiday_date
        target_country = data.country if data.country is not None else holiday.country
        target_region = data.state_region if data.state_region is not None else holiday.state_region

        if (
            target_date != holiday.holiday_date
            or target_country.lower() != holiday.country.lower()
            or (target_region or "").lower() != (holiday.state_region or "").lower()
        ):
            existing = await self.repository.get_by_date_and_region(
                self.db,
                holiday_date=target_date,
                country=target_country,
                state_region=target_region,
            )
            if existing and existing.id != holiday.id:
                raise ApnaERPException(
                    message=f"Holiday '{existing.name}' already exists on {target_date} for region '{target_country}{'/' + target_region if target_region else ''}'.",
                    status_code=400,
                    error_code="DUPLICATE_HOLIDAY",
                )

        updated_holiday = await self.repository.update(self.db, db_obj=holiday, obj_in=data)
        await self._invalidate_caches()

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="HOLIDAY_UPDATE",
            entity_type="Holiday",
            entity_id=updated_holiday.id,
            user_id=user_id,
            username=username,
            new_data=data.model_dump(exclude_unset=True, mode="json"),
            status_code=200,
        )

        try:
            send_holiday_notification_task.delay(
                event_type="HOLIDAY_UPDATE",
                holiday_id=str(updated_holiday.id),
                holiday_code=updated_holiday.code,
                holiday_name=updated_holiday.name,
                user_id=str(user_id) if user_id else None,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery holiday notification task: {exc}")

        fresh_holiday = await self.repository.get_by_id(self.db, updated_holiday.id)
        return fresh_holiday if fresh_holiday else updated_holiday

    async def delete_holiday(
        self,
        holiday_id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> Holiday:
        """Soft-deletes a Holiday record."""
        holiday = await self.get_holiday_by_id(holiday_id)

        await self.repository.soft_delete(self.db, id=holiday.id)
        await self._invalidate_caches()

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="HOLIDAY_DELETE",
            entity_type="Holiday",
            entity_id=holiday.id,
            user_id=user_id,
            username=username,
            status_code=200,
        )

        try:
            send_holiday_notification_task.delay(
                event_type="HOLIDAY_DELETE",
                holiday_id=str(holiday.id),
                holiday_code=holiday.code,
                holiday_name=holiday.name,
                user_id=str(user_id) if user_id else None,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery holiday deletion task: {exc}")

        deleted_holiday = await self.repository.get_by_id(self.db, holiday.id, include_deleted=True)
        return deleted_holiday if deleted_holiday else holiday

    async def restore_holiday(
        self,
        holiday_id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> Holiday:
        """Restores a soft-deleted Holiday record."""
        holiday = await self.repository.get_by_id(self.db, holiday_id, include_deleted=True)
        if not holiday or not getattr(holiday, "is_deleted", False):
            raise ApnaERPException(
                message=f"Soft-deleted Holiday with ID '{holiday_id}' not found.",
                status_code=404,
                error_code="HOLIDAY_NOT_FOUND",
            )

        await self.repository.restore(self.db, id=holiday.id)
        await self._invalidate_caches()

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="HOLIDAY_RESTORE",
            entity_type="Holiday",
            entity_id=holiday.id,
            user_id=user_id,
            username=username,
            status_code=200,
        )

        restored_holiday = await self.repository.get_by_id(self.db, holiday.id)
        return restored_holiday if restored_holiday else holiday
