import json
import logging
from typing import Any, Dict, List, Optional
import uuid
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import ApnaERPException
from app.models.leave_type import LeaveType
from app.models.user import User
from app.repositories.leave_type import leave_type_repository
from app.schemas.leave_type import LeaveTypeCreate, LeaveTypeUpdate
from app.tasks.leave_type_tasks import send_leave_policy_change_notification_task
from app.utils.audit import log_audit
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginatedResult, PaginationParams

logger = logging.getLogger("app.services.leave_type")

CACHE_LIST_KEY = "leave_type:list"
CACHE_DETAIL_PREFIX = "leave_type:detail"


class LeaveTypeService:
    """
    Service layer implementing Enterprise Leave Types & Policies.
    Enforces organizational policy validation, carry-forward constraints,
    Redis caching, audit logging, and background notifications.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = leave_type_repository

    async def _invalidate_cache(self, leave_type_id: Optional[uuid.UUID] = None):
        """Invalidates Redis leave type caches."""
        try:
            await redis_manager.delete_pattern("leave_type:*")
            if leave_type_id:
                await redis_manager.delete(f"{CACHE_DETAIL_PREFIX}:{leave_type_id}")
        except Exception as exc:
            logger.warning(f"Failed to invalidate Redis cache for leave type {leave_type_id}: {exc}")

    def _validate_carry_forward_rules(
        self,
        annual_allocation: float,
        carry_forward_allowed: bool,
        max_carry_forward: float,
    ) -> None:
        """Validates business rules for leave carry forward limits."""
        if not carry_forward_allowed and max_carry_forward > 0:
            raise ApnaERPException(
                message="Maximum carry forward must be 0 when carry forward is not allowed.",
                status_code=400,
                error_code="INVALID_CARRY_FORWARD",
            )
        if carry_forward_allowed and max_carry_forward > annual_allocation:
            raise ApnaERPException(
                message=f"Maximum carry forward ({max_carry_forward}) cannot exceed annual allocation ({annual_allocation}).",
                status_code=400,
                error_code="INVALID_CARRY_FORWARD",
            )

    async def create_leave_type(
        self,
        data: LeaveTypeCreate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> LeaveType:
        """Creates a new Leave Type with code/name uniqueness and policy validations."""
        # 1. Check code uniqueness
        existing_code = await self.repository.get_by_code(self.db, code=data.code, include_deleted=True)
        if existing_code:
            raise ApnaERPException(
                message=f"Leave type with code '{data.code}' already exists.",
                status_code=400,
                error_code="DUPLICATE_LEAVE_CODE",
            )

        # 2. Check name uniqueness
        existing_name = await self.repository.get_by_name(self.db, name=data.name, include_deleted=True)
        if existing_name:
            raise ApnaERPException(
                message=f"Leave type with name '{data.name}' already exists.",
                status_code=400,
                error_code="DUPLICATE_LEAVE_NAME",
            )

        # 3. Carry forward policy validation
        self._validate_carry_forward_rules(
            annual_allocation=data.annual_allocation,
            carry_forward_allowed=data.carry_forward_allowed,
            max_carry_forward=data.max_carry_forward,
        )

        # 4. Create Entity
        leave_type = await self.repository.create(self.db, obj_in=data)

        # 5. Invalidate Cache
        await self._invalidate_cache(leave_type.id)

        # 6. Audit Log
        if current_user:
            await log_audit(
                self.db,
                action="LEAVE_TYPE_CREATE",
                entity_type="LeaveType",
                entity_id=leave_type.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=None,
                new_data={
                    "code": leave_type.code,
                    "name": leave_type.name,
                    "annual_allocation": leave_type.annual_allocation,
                    "carry_forward_allowed": leave_type.carry_forward_allowed,
                    "max_carry_forward": leave_type.max_carry_forward,
                },
                status_code=201,
            )

        # 7. Background Celery Task
        try:
            send_leave_policy_change_notification_task.delay(
                event_type="CREATED",
                leave_type_id=str(leave_type.id),
                leave_code=leave_type.code,
                leave_name=leave_type.name,
                details={"annual_allocation": leave_type.annual_allocation},
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for LeaveType creation: {exc}")

        return leave_type

    async def update_leave_type(
        self,
        id: uuid.UUID,
        data: LeaveTypeUpdate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> LeaveType:
        """Updates an existing Leave Type policy with business rule validation."""
        leave_type = await self.repository.get_by_id(self.db, id)
        if not leave_type or leave_type.is_deleted:
            raise ApnaERPException(
                message=f"Leave type with ID '{id}' not found.",
                status_code=404,
                error_code="LEAVE_TYPE_NOT_FOUND",
            )

        # Unique code check if changed
        if data.code is not None and data.code != leave_type.code:
            existing_code = await self.repository.get_by_code(self.db, code=data.code, include_deleted=True)
            if existing_code and existing_code.id != id:
                raise ApnaERPException(
                    message=f"Leave type with code '{data.code}' already exists.",
                    status_code=400,
                    error_code="DUPLICATE_LEAVE_CODE",
                )

        # Unique name check if changed
        if data.name is not None and data.name != leave_type.name:
            existing_name = await self.repository.get_by_name(self.db, name=data.name, include_deleted=True)
            if existing_name and existing_name.id != id:
                raise ApnaERPException(
                    message=f"Leave type with name '{data.name}' already exists.",
                    status_code=400,
                    error_code="DUPLICATE_LEAVE_NAME",
                )

        # Validate carry forward rules using merged parameters
        merged_annual = data.annual_allocation if data.annual_allocation is not None else leave_type.annual_allocation
        merged_allowed = data.carry_forward_allowed if data.carry_forward_allowed is not None else leave_type.carry_forward_allowed
        merged_max_cf = data.max_carry_forward if data.max_carry_forward is not None else leave_type.max_carry_forward

        self._validate_carry_forward_rules(
            annual_allocation=merged_annual,
            carry_forward_allowed=merged_allowed,
            max_carry_forward=merged_max_cf,
        )

        prev_data = {
            "code": leave_type.code,
            "name": leave_type.name,
            "annual_allocation": leave_type.annual_allocation,
            "carry_forward_allowed": leave_type.carry_forward_allowed,
            "max_carry_forward": leave_type.max_carry_forward,
            "is_active": leave_type.is_active,
        }

        updated = await self.repository.update(self.db, db_obj=leave_type, obj_in=data)
        await self._invalidate_cache(updated.id)

        if current_user:
            await log_audit(
                self.db,
                action="LEAVE_TYPE_UPDATE",
                entity_type="LeaveType",
                entity_id=updated.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=prev_data,
                new_data={
                    "code": updated.code,
                    "name": updated.name,
                    "annual_allocation": updated.annual_allocation,
                    "carry_forward_allowed": updated.carry_forward_allowed,
                    "max_carry_forward": updated.max_carry_forward,
                    "is_active": updated.is_active,
                },
                status_code=200,
            )

        try:
            send_leave_policy_change_notification_task.delay(
                event_type="UPDATED",
                leave_type_id=str(updated.id),
                leave_code=updated.code,
                leave_name=updated.name,
                details={"updated_fields": list(data.model_dump(exclude_unset=True).keys())},
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for LeaveType update: {exc}")

        return updated

    async def delete_leave_type(
        self,
        id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> bool:
        """Soft-deletes a Leave Type policy."""
        leave_type = await self.repository.get_by_id(self.db, id)
        if not leave_type or leave_type.is_deleted:
            raise ApnaERPException(
                message=f"Leave type with ID '{id}' not found.",
                status_code=404,
                error_code="LEAVE_TYPE_NOT_FOUND",
            )

        await self.repository.soft_delete(self.db, id=id)
        await self._invalidate_cache(id)

        if current_user:
            await log_audit(
                self.db,
                action="LEAVE_TYPE_DELETE",
                entity_type="LeaveType",
                entity_id=id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"code": leave_type.code, "name": leave_type.name},
                new_data=None,
                status_code=200,
            )

        try:
            send_leave_policy_change_notification_task.delay(
                event_type="DELETED",
                leave_type_id=str(id),
                leave_code=leave_type.code,
                leave_name=leave_type.name,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for LeaveType deletion: {exc}")

        return True

    async def restore_leave_type(
        self,
        id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> LeaveType:
        """Restores a soft-deleted Leave Type policy."""
        leave_type = await self.repository.get_by_id(self.db, id, include_deleted=True)
        if not leave_type:
            raise ApnaERPException(
                message=f"Leave type with ID '{id}' not found.",
                status_code=404,
                error_code="LEAVE_TYPE_NOT_FOUND",
            )
        if not leave_type.is_deleted:
            return leave_type

        restored = await self.repository.restore(self.db, id=id)
        await self._invalidate_cache(id)

        if current_user:
            await log_audit(
                self.db,
                action="LEAVE_TYPE_RESTORE",
                entity_type="LeaveType",
                entity_id=id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"is_deleted": True},
                new_data={"is_deleted": False},
                status_code=200,
            )

        try:
            send_leave_policy_change_notification_task.delay(
                event_type="RESTORED",
                leave_type_id=str(id),
                leave_code=restored.code,
                leave_name=restored.name,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for LeaveType restore: {exc}")

        return restored

    async def get_leave_type_by_id(self, id: uuid.UUID) -> LeaveType:
        """Retrieves a single Leave Type by ID using Redis caching."""
        cache_key = f"{CACHE_DETAIL_PREFIX}:{id}"
        try:
            cached_raw = await redis_manager.get(cache_key)
            if cached_raw:
                # Validate DB record still exists
                obj = await self.repository.get_by_id(self.db, id)
                if obj and not obj.is_deleted:
                    return obj
        except Exception as exc:
            logger.warning(f"Redis cache lookup failed for leave type {id}: {exc}")

        leave_type = await self.repository.get_by_id(self.db, id)
        if not leave_type or leave_type.is_deleted:
            raise ApnaERPException(
                message=f"Leave type with ID '{id}' not found.",
                status_code=404,
                error_code="LEAVE_TYPE_NOT_FOUND",
            )

        try:
            await redis_manager.set(cache_key, str(leave_type.id), ttl=3600)
        except Exception as exc:
            logger.warning(f"Redis set failed for leave type cache {id}: {exc}")

        return leave_type

    async def list_leave_types(
        self,
        params: PaginationParams,
        search_term: Optional[str] = None,
        filters: Optional[List[FilterCriterion]] = None,
    ) -> PaginatedResult[LeaveType]:
        """Retrieves paginated list of Leave Types with dynamic search and filtering."""
        search_fields = ["code", "name", "description"]
        return await self.repository.get_multi_paginated(
            self.db,
            params=params,
            search_term=search_term,
            search_fields=search_fields,
            filters=filters,
        )
