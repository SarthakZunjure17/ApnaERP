import datetime
import json
import logging
from typing import Any, Dict, List, Optional
import uuid
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import ApnaERPException
from app.models.shift import Shift
from app.models.user import User
from app.repositories.shift import shift_repository
from app.schemas.shift import ShiftCreate, ShiftResponse, ShiftUpdate
from app.utils.audit import log_audit
from app.tasks.shift_tasks import send_shift_notification_task

logger = logging.getLogger("app.services.shift")

CACHE_LIST_KEY = "shift:list"
CACHE_DETAIL_PREFIX = "shift:detail"


class ShiftService:
    """
    Business service layer for Shift management.
    Handles reusable shift schedules, overnight transition calculations,
    working hour validations, active employee assignment guards, Redis caching,
    audit logging, and Celery notifications.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = shift_repository

    async def _invalidate_caches(self, shift_id: Optional[uuid.UUID] = None) -> None:
        """Invalidates Shift list and detail Redis caches."""
        try:
            await redis_manager.delete(CACHE_LIST_KEY)
            if shift_id:
                await redis_manager.delete(f"{CACHE_DETAIL_PREFIX}:{shift_id}")
            logger.info("[ShiftService] Invalidated Redis caches.")
        except Exception as e:
            logger.warning(f"[ShiftService] Redis cache invalidation error: {e}")

    def _calculate_duration_hours(
        self, start_time: datetime.time, end_time: datetime.time
    ) -> float:
        """Calculates total shift duration in hours (accounting for overnight shifts)."""
        start_secs = start_time.hour * 3600 + start_time.minute * 60 + start_time.second
        end_secs = end_time.hour * 3600 + end_time.minute * 60 + end_time.second

        if end_secs >= start_secs:
            diff_secs = end_secs - start_secs
        else:
            diff_secs = (24 * 3600 - start_secs) + end_secs

        return round(diff_secs / 3600.0, 2)

    def _validate_shift_rules(
        self,
        start_time: datetime.time,
        end_time: datetime.time,
        break_duration_minutes: int,
        grace_period_minutes: int,
        minimum_working_hours: float,
        maximum_working_hours: float,
    ) -> bool:
        """Validates duration, break, grace period, and working hour bounds."""
        duration_hours = self._calculate_duration_hours(start_time, end_time)

        # 1. Break duration sanity check
        break_hours = break_duration_minutes / 60.0
        if break_hours >= duration_hours:
            raise ApnaERPException(
                message=f"Break duration ({break_duration_minutes} mins / {break_hours:.2f} hrs) cannot equal or exceed total shift duration ({duration_hours:.2f} hrs).",
                status_code=400,
                error_code="INVALID_BREAK_DURATION",
            )

        # 2. Grace period sanity check
        grace_hours = grace_period_minutes / 60.0
        if grace_hours >= duration_hours:
            raise ApnaERPException(
                message=f"Grace period ({grace_period_minutes} mins / {grace_hours:.2f} hrs) cannot equal or exceed total shift duration ({duration_hours:.2f} hrs).",
                status_code=400,
                error_code="INVALID_GRACE_PERIOD",
            )

        # 3. Working hours bounds check
        if minimum_working_hours > maximum_working_hours:
            raise ApnaERPException(
                message=f"Minimum working hours ({minimum_working_hours}) cannot exceed maximum working hours ({maximum_working_hours}).",
                status_code=400,
                error_code="INVALID_WORKING_HOURS",
            )

        # Auto-detect overnight shift if end_time <= start_time
        return end_time <= start_time

    async def get_shift_by_id(
        self, shift_id: uuid.UUID, include_deleted: bool = False
    ) -> Shift:
        """Retrieves a Shift by UUID."""
        shift = await self.repository.get_by_id(self.db, shift_id, include_deleted=include_deleted)
        if not shift:
            raise ApnaERPException(
                message=f"Shift with ID '{shift_id}' not found.",
                status_code=404,
                error_code="SHIFT_NOT_FOUND",
            )
        return shift

    async def get_shifts(
        self,
        page: int = 1,
        page_size: int = 100,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ):
        """Retrieves paginated list of shifts with search and filtering."""
        from app.utils.pagination import PaginationParams
        from app.utils.filters import FilterCriterion, FilterOperator

        params = PaginationParams(page=page, page_size=page_size)
        filters = []
        if is_active is not None:
            filters.append(FilterCriterion(field="is_active", operator=FilterOperator.EQ, value=is_active))

        return await self.repository.get_multi_paginated(
            self.db,
            params=params,
            filters=filters,
            search_term=search,
            search_fields=["code", "name", "description"],
        )

    async def create_shift(
        self,
        data: ShiftCreate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> Shift:
        """Creates a new Shift schedule record."""
        # 1. Unique code check
        if await self.repository.exists_by_code(self.db, data.code):
            raise ApnaERPException(
                message=f"Shift with code '{data.code}' already exists.",
                status_code=400,
                error_code="DUPLICATE_SHIFT_CODE",
            )

        # 2. Unique name check
        if await self.repository.exists_by_name(self.db, data.name):
            raise ApnaERPException(
                message=f"Shift with name '{data.name}' already exists.",
                status_code=400,
                error_code="DUPLICATE_SHIFT_NAME",
            )

        # 3. Shift rules and overnight validation
        is_overnight = self._validate_shift_rules(
            start_time=data.start_time,
            end_time=data.end_time,
            break_duration_minutes=data.break_duration_minutes,
            grace_period_minutes=data.grace_period_minutes,
            minimum_working_hours=data.minimum_working_hours,
            maximum_working_hours=data.maximum_working_hours,
        )

        # If overnight shift detected, ensure is_night_shift is set to True
        if is_overnight and not data.is_night_shift:
            data.is_night_shift = True

        shift = await self.repository.create(self.db, obj_in=data)
        await self._invalidate_caches()

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="SHIFT_CREATE",
            entity_type="Shift",
            entity_id=shift.id,
            user_id=user_id,
            username=username,
            new_data=data.model_dump(mode="json"),
            status_code=201,
        )

        try:
            send_shift_notification_task.delay(
                event_type="SHIFT_CREATE",
                shift_id=str(shift.id),
                shift_code=shift.code,
                shift_name=shift.name,
                user_id=str(user_id) if user_id else None,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery shift notification task: {exc}")

        fresh_shift = await self.repository.get_by_id(self.db, shift.id)
        return fresh_shift if fresh_shift else shift

    async def update_shift(
        self,
        shift_id: uuid.UUID,
        data: ShiftUpdate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> Shift:
        """Updates an existing Shift schedule record."""
        shift = await self.get_shift_by_id(shift_id)

        # Unique code check if changed
        if data.code and data.code.lower() != shift.code.lower():
            if await self.repository.exists_by_code(self.db, data.code):
                raise ApnaERPException(
                    message=f"Shift with code '{data.code}' already exists.",
                    status_code=400,
                    error_code="DUPLICATE_SHIFT_CODE",
                )

        # Unique name check if changed
        if data.name and data.name.lower() != shift.name.lower():
            if await self.repository.exists_by_name(self.db, data.name):
                raise ApnaERPException(
                    message=f"Shift with name '{data.name}' already exists.",
                    status_code=400,
                    error_code="DUPLICATE_SHIFT_NAME",
                )

        start_t = data.start_time if data.start_time is not None else shift.start_time
        end_t = data.end_time if data.end_time is not None else shift.end_time
        break_m = data.break_duration_minutes if data.break_duration_minutes is not None else shift.break_duration_minutes
        grace_m = data.grace_period_minutes if data.grace_period_minutes is not None else shift.grace_period_minutes
        min_h = data.minimum_working_hours if data.minimum_working_hours is not None else shift.minimum_working_hours
        max_h = data.maximum_working_hours if data.maximum_working_hours is not None else shift.maximum_working_hours

        is_overnight = self._validate_shift_rules(
            start_time=start_t,
            end_time=end_t,
            break_duration_minutes=break_m,
            grace_period_minutes=grace_m,
            minimum_working_hours=min_h,
            maximum_working_hours=max_h,
        )

        if is_overnight and data.is_night_shift is None:
            data.is_night_shift = True

        updated_shift = await self.repository.update(self.db, db_obj=shift, obj_in=data)
        await self._invalidate_caches(shift_id)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="SHIFT_UPDATE",
            entity_type="Shift",
            entity_id=updated_shift.id,
            user_id=user_id,
            username=username,
            new_data=data.model_dump(exclude_unset=True, mode="json"),
            status_code=200,
        )

        try:
            send_shift_notification_task.delay(
                event_type="SHIFT_UPDATE",
                shift_id=str(updated_shift.id),
                shift_code=updated_shift.code,
                shift_name=updated_shift.name,
                user_id=str(user_id) if user_id else None,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery shift update notification task: {exc}")

        fresh_shift = await self.repository.get_by_id(self.db, updated_shift.id)
        return fresh_shift if fresh_shift else updated_shift

    async def delete_shift(
        self,
        shift_id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> Shift:
        """
        Soft-deletes a Shift schedule record.
        Blocks deletion if active employees are currently assigned to this shift.
        """
        shift = await self.get_shift_by_id(shift_id)

        assigned_count = await self.repository.get_assigned_employee_count(self.db, shift.id)
        if assigned_count > 0:
            raise ApnaERPException(
                message=f"Cannot delete shift '{shift.name}' because {assigned_count} active employees are assigned to it.",
                status_code=400,
                error_code="ASSIGNED_EMPLOYEES_EXIST",
            )

        await self.repository.soft_delete(self.db, id=shift.id)
        await self._invalidate_caches(shift.id)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="SHIFT_DELETE",
            entity_type="Shift",
            entity_id=shift.id,
            user_id=user_id,
            username=username,
            status_code=200,
        )

        try:
            send_shift_notification_task.delay(
                event_type="SHIFT_DELETE",
                shift_id=str(shift.id),
                shift_code=shift.code,
                shift_name=shift.name,
                user_id=str(user_id) if user_id else None,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery shift deletion notification task: {exc}")

        deleted_shift = await self.repository.get_by_id(self.db, shift.id, include_deleted=True)
        return deleted_shift if deleted_shift else shift

    async def restore_shift(
        self,
        shift_id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> Shift:
        """Restores a soft-deleted Shift record."""
        shift = await self.repository.get_by_id(self.db, shift_id, include_deleted=True)
        if not shift or not getattr(shift, "is_deleted", False):
            raise ApnaERPException(
                message=f"Soft-deleted Shift with ID '{shift_id}' not found.",
                status_code=404,
                error_code="SHIFT_NOT_FOUND",
            )

        await self.repository.restore(self.db, id=shift.id)
        await self._invalidate_caches(shift.id)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="SHIFT_RESTORE",
            entity_type="Shift",
            entity_id=shift.id,
            user_id=user_id,
            username=username,
            status_code=200,
        )

        restored_shift = await self.repository.get_by_id(self.db, shift.id)
        return restored_shift if restored_shift else shift
