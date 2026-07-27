import logging
from typing import Any, Dict, List, Optional
import uuid
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import ApnaERPException
from app.models.leave_balance import LeaveBalance
from app.models.user import User
from app.repositories.employee import employee_repository
from app.repositories.leave_balance import leave_balance_repository
from app.repositories.leave_type import leave_type_repository
from app.schemas.leave_balance import (
    LeaveBalanceAdjustmentRequest,
    LeaveBalanceCreate,
    LeaveBalanceUpdate,
)
from app.tasks.leave_balance_tasks import send_leave_balance_adjustment_notification_task
from app.utils.audit import log_audit
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginatedResult, PaginationParams

logger = logging.getLogger("app.services.leave_balance")

CACHE_DETAIL_PREFIX = "leave_balance:detail"
CACHE_EMP_PREFIX = "leave_balance:employee"


class LeaveBalanceService:
    """
    Service layer implementing Enterprise Leave Balance Management.
    Enforces mathematical derivation of remaining balances, negative balance guards,
    carry-forward validations, Redis caching, audit logging, and background notifications.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = leave_balance_repository
        self.employee_repo = employee_repository
        self.leave_type_repo = leave_type_repository

    async def _invalidate_cache(self, employee_id: uuid.UUID, balance_id: Optional[uuid.UUID] = None):
        """Invalidates Redis leave balance caches for the employee and balance ID."""
        try:
            pattern = f"{CACHE_EMP_PREFIX}:{employee_id}:*"
            await redis_manager.delete_pattern(pattern)
            await redis_manager.delete_pattern("leave_balance:*")
            if balance_id:
                await redis_manager.delete(f"{CACHE_DETAIL_PREFIX}:{balance_id}")
        except Exception as exc:
            logger.warning(f"Failed to clear Redis leave balance cache for employee {employee_id}: {exc}")

    def _validate_negative_balance(self, remaining_days: float, allow_negative_balance: bool) -> None:
        """Enforces negative balance rules based on LeaveType policy."""
        if remaining_days < 0 and not allow_negative_balance:
            raise ApnaERPException(
                message=f"Calculated remaining balance ({remaining_days}) is negative, which is prohibited by this leave policy.",
                status_code=400,
                error_code="NEGATIVE_LEAVE_BALANCE",
            )

    def _validate_carry_forward(self, carried_forward_days: float, leave_type: Any) -> None:
        """Validates carried forward days against LeaveType limits."""
        if not leave_type.carry_forward_allowed and carried_forward_days > 0:
            raise ApnaERPException(
                message=f"Carry-forward is not permitted for leave policy '{leave_type.name}'.",
                status_code=400,
                error_code="INVALID_CARRY_FORWARD",
            )
        if leave_type.carry_forward_allowed and carried_forward_days > leave_type.max_carry_forward:
            raise ApnaERPException(
                message=f"Carried forward days ({carried_forward_days}) exceeds maximum policy cap ({leave_type.max_carry_forward}).",
                status_code=400,
                error_code="INVALID_CARRY_FORWARD",
            )

    async def create_leave_balance(
        self,
        data: LeaveBalanceCreate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> LeaveBalance:
        """Creates a new Leave Balance for an employee with business rule validations."""
        # 1. Verify Employee exists
        employee = await self.employee_repo.get_by_id(self.db, data.employee_id)
        if not employee or employee.is_deleted:
            raise ApnaERPException(
                message=f"Employee with ID '{data.employee_id}' not found.",
                status_code=404,
                error_code="EMPLOYEE_NOT_FOUND",
            )

        # 2. Verify LeaveType exists and is active
        leave_type = await self.leave_type_repo.get_by_id(self.db, data.leave_type_id)
        if not leave_type or leave_type.is_deleted or not leave_type.is_active:
            raise ApnaERPException(
                message=f"Leave type with ID '{data.leave_type_id}' not found or inactive.",
                status_code=404,
                error_code="LEAVE_TYPE_NOT_FOUND",
            )

        # 3. Check Uniqueness constraint (Employee + LeaveType + LeaveYear)
        existing = await self.repository.get_by_employee_type_year(
            self.db,
            employee_id=data.employee_id,
            leave_type_id=data.leave_type_id,
            leave_year=data.leave_year,
            include_deleted=True,
        )
        if existing:
            raise ApnaERPException(
                message=f"Leave balance for employee '{employee.employee_code}', leave type '{leave_type.code}', and year {data.leave_year} already exists.",
                status_code=400,
                error_code="DUPLICATE_LEAVE_BALANCE",
            )

        # 4. Carry forward validation
        self._validate_carry_forward(data.carried_forward_days, leave_type)

        # 5. Derivation & Negative Balance Check
        balance_dict = data.model_dump()
        opening = balance_dict.get("opening_balance", 0.0)
        allocated = balance_dict.get("allocated_days", 0.0)
        earned = balance_dict.get("earned_days", 0.0)
        cf = balance_dict.get("carried_forward_days", 0.0)
        availed = balance_dict.get("availed_days", 0.0)
        encashed = balance_dict.get("encashed_days", 0.0)

        derived_remaining = round(opening + allocated + earned + cf - availed - encashed, 2)
        self._validate_negative_balance(derived_remaining, leave_type.allow_negative_balance)

        balance_dict["remaining_days"] = derived_remaining
        balance_dict["last_updated_by"] = current_user.id if current_user else None

        # 6. Create Entity
        balance = await self.repository.create(self.db, obj_in=balance_dict)

        # 7. Invalidate Cache
        await self._invalidate_cache(balance.employee_id, balance.id)

        # 8. Audit Log
        if current_user:
            await log_audit(
                self.db,
                action="LEAVE_BALANCE_CREATE",
                entity_type="LeaveBalance",
                entity_id=balance.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=None,
                new_data={
                    "employee_id": str(balance.employee_id),
                    "leave_type_id": str(balance.leave_type_id),
                    "leave_year": balance.leave_year,
                    "allocated_days": balance.allocated_days,
                    "remaining_days": balance.remaining_days,
                },
                status_code=201,
            )

        return balance

    async def update_leave_balance(
        self,
        id: uuid.UUID,
        data: LeaveBalanceUpdate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> LeaveBalance:
        """Updates an existing Leave Balance record."""
        balance = await self.repository.get_by_id(self.db, id)
        if not balance or balance.is_deleted:
            raise ApnaERPException(
                message=f"Leave balance with ID '{id}' not found.",
                status_code=404,
                error_code="LEAVE_BALANCE_NOT_FOUND",
            )

        leave_type = await self.leave_type_repo.get_by_id(self.db, balance.leave_type_id)

        prev_data = {
            "opening_balance": balance.opening_balance,
            "allocated_days": balance.allocated_days,
            "earned_days": balance.earned_days,
            "availed_days": balance.availed_days,
            "encashed_days": balance.encashed_days,
            "carried_forward_days": balance.carried_forward_days,
            "remaining_days": balance.remaining_days,
        }

        # Apply updates to temporary values
        opening = data.opening_balance if data.opening_balance is not None else balance.opening_balance
        allocated = data.allocated_days if data.allocated_days is not None else balance.allocated_days
        earned = data.earned_days if data.earned_days is not None else balance.earned_days
        availed = data.availed_days if data.availed_days is not None else balance.availed_days
        encashed = data.encashed_days if data.encashed_days is not None else balance.encashed_days
        cf = data.carried_forward_days if data.carried_forward_days is not None else balance.carried_forward_days

        if data.carried_forward_days is not None and leave_type:
            self._validate_carry_forward(cf, leave_type)

        derived_remaining = round(opening + allocated + earned + cf - availed - encashed, 2)
        if leave_type:
            self._validate_negative_balance(derived_remaining, leave_type.allow_negative_balance)

        update_dict = data.model_dump(exclude_unset=True)
        update_dict["remaining_days"] = derived_remaining
        update_dict["last_updated_by"] = current_user.id if current_user else None

        updated = await self.repository.update(self.db, db_obj=balance, obj_in=update_dict)
        await self._invalidate_cache(updated.employee_id, updated.id)

        if current_user:
            await log_audit(
                self.db,
                action="LEAVE_BALANCE_UPDATE",
                entity_type="LeaveBalance",
                entity_id=updated.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=prev_data,
                new_data={
                    "remaining_days": updated.remaining_days,
                    "allocated_days": updated.allocated_days,
                    "availed_days": updated.availed_days,
                },
                status_code=200,
            )

        return updated

    async def adjust_leave_balance(
        self,
        id: uuid.UUID,
        data: LeaveBalanceAdjustmentRequest,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> LeaveBalance:
        """Manually adjusts a leave balance field and dispatches HR alert notification."""
        balance = await self.repository.get_by_id(self.db, id)
        if not balance or balance.is_deleted:
            raise ApnaERPException(
                message=f"Leave balance with ID '{id}' not found.",
                status_code=404,
                error_code="LEAVE_BALANCE_NOT_FOUND",
            )

        leave_type = await self.leave_type_repo.get_by_id(self.db, balance.leave_type_id)

        allowed_fields = {
            "allocated": "allocated_days",
            "earned": "earned_days",
            "availed": "availed_days",
            "encashed": "encashed_days",
            "opening": "opening_balance",
            "carried_forward": "carried_forward_days",
        }

        if data.adjustment_type not in allowed_fields:
            raise ApnaERPException(
                message=f"Invalid adjustment type '{data.adjustment_type}'. Must be one of {list(allowed_fields.keys())}.",
                status_code=400,
                error_code="INVALID_ADJUSTMENT_TYPE",
            )

        target_attr = allowed_fields[data.adjustment_type]
        current_val = getattr(balance, target_attr, 0.0)
        new_val = round(current_val + data.adjustment_days, 2)

        if new_val < 0:
            raise ApnaERPException(
                message=f"Adjustment would result in negative value ({new_val}) for '{target_attr}'.",
                status_code=400,
                error_code="INVALID_BALANCE_AMOUNT",
            )

        prev_data = {
            target_attr: current_val,
            "remaining_days": balance.remaining_days,
        }

        setattr(balance, target_attr, new_val)
        if target_attr == "carried_forward_days" and leave_type:
            self._validate_carry_forward(new_val, leave_type)

        balance.remaining_days = balance.calculate_remaining_days()
        if leave_type:
            self._validate_negative_balance(balance.remaining_days, leave_type.allow_negative_balance)

        balance.last_updated_by = current_user.id if current_user else None

        await self.db.commit()
        await self.db.refresh(balance)
        await self._invalidate_cache(balance.employee_id, balance.id)

        if current_user:
            await log_audit(
                self.db,
                action="LEAVE_BALANCE_ADJUST",
                entity_type="LeaveBalance",
                entity_id=balance.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=prev_data,
                new_data={
                    target_attr: new_val,
                    "remaining_days": balance.remaining_days,
                    "reason": data.reason,
                },
                status_code=200,
            )

        try:
            send_leave_balance_adjustment_notification_task.delay(
                event_type="ADJUSTED",
                balance_id=str(balance.id),
                employee_id=str(balance.employee_id),
                leave_type_id=str(balance.leave_type_id),
                leave_year=balance.leave_year,
                adjustment_type=data.adjustment_type,
                adjustment_days=data.adjustment_days,
                reason=data.reason,
                new_remaining_days=balance.remaining_days,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for LeaveBalance adjustment: {exc}")

        return balance

    async def delete_leave_balance(
        self,
        id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> bool:
        """Soft-deletes a Leave Balance record."""
        balance = await self.repository.get_by_id(self.db, id)
        if not balance or balance.is_deleted:
            raise ApnaERPException(
                message=f"Leave balance with ID '{id}' not found.",
                status_code=404,
                error_code="LEAVE_BALANCE_NOT_FOUND",
            )

        await self.repository.soft_delete(self.db, id=id)
        await self._invalidate_cache(balance.employee_id, id)

        if current_user:
            await log_audit(
                self.db,
                action="LEAVE_BALANCE_DELETE",
                entity_type="LeaveBalance",
                entity_id=id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"employee_id": str(balance.employee_id), "remaining_days": balance.remaining_days},
                new_data=None,
                status_code=200,
            )

        return True

    async def restore_leave_balance(
        self,
        id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> LeaveBalance:
        """Restores a soft-deleted Leave Balance record."""
        balance = await self.repository.get_by_id(self.db, id, include_deleted=True)
        if not balance:
            raise ApnaERPException(
                message=f"Leave balance with ID '{id}' not found.",
                status_code=404,
                error_code="LEAVE_BALANCE_NOT_FOUND",
            )
        if not balance.is_deleted:
            return balance

        restored = await self.repository.restore(self.db, id=id)
        await self._invalidate_cache(restored.employee_id, id)

        if current_user:
            await log_audit(
                self.db,
                action="LEAVE_BALANCE_RESTORE",
                entity_type="LeaveBalance",
                entity_id=id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"is_deleted": True},
                new_data={"is_deleted": False},
                status_code=200,
            )

        return restored

    async def get_leave_balance_by_id(self, id: uuid.UUID) -> LeaveBalance:
        """Retrieves a single Leave Balance by ID."""
        balance = await self.repository.get_by_id(self.db, id)
        if not balance or balance.is_deleted:
            raise ApnaERPException(
                message=f"Leave balance with ID '{id}' not found.",
                status_code=404,
                error_code="LEAVE_BALANCE_NOT_FOUND",
            )
        return balance

    async def get_employee_leave_balances(
        self,
        employee_id: uuid.UUID,
        leave_year: Optional[int],
        params: PaginationParams,
    ) -> PaginatedResult[LeaveBalance]:
        """Retrieves paginated leave balances for an employee, optionally filtered by leave year."""
        employee = await self.employee_repo.get_by_id(self.db, employee_id)
        if not employee or employee.is_deleted:
            raise ApnaERPException(
                message=f"Employee with ID '{employee_id}' not found.",
                status_code=404,
                error_code="EMPLOYEE_NOT_FOUND",
            )
        return await self.repository.get_employee_balances_paginated(
            self.db, employee_id=employee_id, leave_year=leave_year, params=params
        )

    async def list_leave_balances(
        self,
        params: PaginationParams,
        filters: Optional[List[FilterCriterion]] = None,
    ) -> PaginatedResult[LeaveBalance]:
        """Retrieves paginated list of all Leave Balances."""
        return await self.repository.get_multi_paginated(
            self.db, params=params, filters=filters
        )
