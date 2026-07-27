import logging
from typing import List, Optional
import uuid
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import ApnaERPException
from app.models.salary_component import SalaryComponent
from app.models.user import User
from app.repositories.salary_component import salary_component_repository
from app.schemas.salary_component import (
    SalaryComponentCreate,
    SalaryComponentUpdate,
)
from app.tasks.payroll_component_tasks import send_payroll_component_notification_task
from app.utils.audit import log_audit
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginatedResult, PaginationParams

logger = logging.getLogger("app.services.salary_component")

CACHE_PREFIX = "salary_component"


class SalaryComponentService:
    """
    Service layer for managing organization-wide Salary Components.
    Enforces business rules, calculation method validity, display ordering,
    Redis caching, audit trails, and Celery notifications.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = salary_component_repository

    async def _invalidate_cache(self, component_id: Optional[uuid.UUID] = None):
        """Clears Salary Component Redis caches."""
        try:
            await redis_manager.delete_pattern(f"{CACHE_PREFIX}:*")
            if component_id:
                await redis_manager.delete(f"{CACHE_PREFIX}:id:{component_id}")
        except Exception as exc:
            logger.warning(f"Failed to clear Redis salary component cache: {exc}")

    def _validate_calculation_rules(
        self, method: str, default_value: Optional[float], percentage_value: Optional[float]
    ):
        """Enforces calculation method configuration rules."""
        if method == "Percentage":
            if percentage_value is None or percentage_value <= 0.0 or percentage_value > 100.0:
                raise ApnaERPException(
                    message="Percentage calculation method requires a valid percentage_value between 0.01 and 100.0.",
                    status_code=400,
                    error_code="INVALID_CALCULATION_METHOD_CONFIG",
                )
        elif method == "Fixed":
            if default_value is not None and default_value < 0.0:
                raise ApnaERPException(
                    message="Fixed calculation method default_value cannot be negative.",
                    status_code=400,
                    error_code="INVALID_CALCULATION_METHOD_CONFIG",
                )

    async def create_component(
        self,
        data: SalaryComponentCreate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> SalaryComponent:
        """Creates a new organization-wide Salary Component definition."""
        # 1. Uniqueness checks
        existing_code = await self.repository.get_by_code(self.db, data.code, include_deleted=True)
        if existing_code:
            raise ApnaERPException(
                message=f"Salary component with code '{data.code}' already exists.",
                status_code=400,
                error_code="DUPLICATE_COMPONENT_CODE",
            )

        existing_name = await self.repository.get_by_name(self.db, data.name, include_deleted=True)
        if existing_name:
            raise ApnaERPException(
                message=f"Salary component with name '{data.name}' already exists.",
                status_code=400,
                error_code="DUPLICATE_COMPONENT_NAME",
            )

        existing_order = await self.repository.get_by_display_order(
            self.db, data.display_order, include_deleted=True
        )
        if existing_order:
            raise ApnaERPException(
                message=f"Salary component display order {data.display_order} is already in use.",
                status_code=400,
                error_code="DUPLICATE_DISPLAY_ORDER",
            )

        # 2. Calculation method rule validation
        self._validate_calculation_rules(
            method=data.calculation_method.value,
            default_value=data.default_value,
            percentage_value=data.percentage_value,
        )

        comp_dict = data.model_dump()
        comp_dict["type"] = data.type.value
        comp_dict["calculation_method"] = data.calculation_method.value

        component = await self.repository.create(self.db, obj_in=comp_dict)
        await self.db.commit()
        await self.db.refresh(component)
        await self._invalidate_cache(component.id)

        # 3. Audit Log
        if current_user:
            await log_audit(
                self.db,
                action="SALARY_COMPONENT_CREATE",
                entity_type="SalaryComponent",
                entity_id=component.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=None,
                new_data={
                    "code": component.code,
                    "name": component.name,
                    "type": component.type,
                    "calculation_method": component.calculation_method,
                    "display_order": component.display_order,
                },
                status_code=201,
            )

        # 4. Celery notification
        try:
            user_id_str = str(current_user.id) if current_user else "system"
            send_payroll_component_notification_task.delay(
                action="CREATED",
                component_id=str(component.id),
                code=component.code,
                name=component.name,
                component_type=component.type,
                calculation_method=component.calculation_method,
                performed_by_id=user_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for component create: {exc}")

        return component

    async def update_component(
        self,
        id: uuid.UUID,
        data: SalaryComponentUpdate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> SalaryComponent:
        """Updates an existing Salary Component definition."""
        component = await self.repository.get_by_id(self.db, id)
        if not component or component.is_deleted:
            raise ApnaERPException(
                message=f"Salary component with ID '{id}' not found.",
                status_code=404,
                error_code="COMPONENT_NOT_FOUND",
            )

        prev_data = {
            "name": component.name,
            "type": component.type,
            "calculation_method": component.calculation_method,
            "default_value": float(component.default_value),
            "percentage_value": float(component.percentage_value) if component.percentage_value else None,
            "display_order": component.display_order,
            "is_active": component.is_active,
        }

        # 1. Uniqueness checks if updating name or display_order
        if data.name and data.name != component.name:
            existing_name = await self.repository.get_by_name(self.db, data.name, include_deleted=True)
            if existing_name and existing_name.id != id:
                raise ApnaERPException(
                    message=f"Salary component with name '{data.name}' already exists.",
                    status_code=400,
                    error_code="DUPLICATE_COMPONENT_NAME",
                )

        if data.display_order and data.display_order != component.display_order:
            existing_order = await self.repository.get_by_display_order(
                self.db, data.display_order, include_deleted=True
            )
            if existing_order and existing_order.id != id:
                raise ApnaERPException(
                    message=f"Salary component display order {data.display_order} is already in use.",
                    status_code=400,
                    error_code="DUPLICATE_DISPLAY_ORDER",
                )

        # 2. Calculation method rule validation
        eff_method = data.calculation_method.value if data.calculation_method else component.calculation_method
        eff_default = data.default_value if data.default_value is not None else float(component.default_value)
        eff_perc = data.percentage_value if data.percentage_value is not None else (float(component.percentage_value) if component.percentage_value else None)

        self._validate_calculation_rules(
            method=eff_method,
            default_value=eff_default,
            percentage_value=eff_perc,
        )

        update_dict = data.model_dump(exclude_unset=True)
        if "type" in update_dict and data.type:
            update_dict["type"] = data.type.value
        if "calculation_method" in update_dict and data.calculation_method:
            update_dict["calculation_method"] = data.calculation_method.value

        updated = await self.repository.update(self.db, db_obj=component, obj_in=update_dict)
        await self.db.commit()
        await self.db.refresh(updated)
        await self._invalidate_cache(updated.id)

        # 3. Audit Log
        if current_user:
            await log_audit(
                self.db,
                action="SALARY_COMPONENT_UPDATE",
                entity_type="SalaryComponent",
                entity_id=updated.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=prev_data,
                new_data={
                    "name": updated.name,
                    "type": updated.type,
                    "calculation_method": updated.calculation_method,
                    "display_order": updated.display_order,
                    "is_active": updated.is_active,
                },
                status_code=200,
            )

        # 4. Celery notification
        try:
            user_id_str = str(current_user.id) if current_user else "system"
            send_payroll_component_notification_task.delay(
                action="UPDATED",
                component_id=str(updated.id),
                code=updated.code,
                name=updated.name,
                component_type=updated.type,
                calculation_method=updated.calculation_method,
                performed_by_id=user_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for component update: {exc}")

        return updated

    async def delete_component(
        self,
        id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> bool:
        """Soft-deletes a Salary Component definition."""
        component = await self.repository.get_by_id(self.db, id)
        if not component or component.is_deleted:
            raise ApnaERPException(
                message=f"Salary component with ID '{id}' not found.",
                status_code=404,
                error_code="COMPONENT_NOT_FOUND",
            )

        prev_code = component.code
        prev_name = component.name
        prev_type = component.type
        prev_method = component.calculation_method

        await self.repository.soft_delete(self.db, id=id)
        await self.db.commit()
        await self._invalidate_cache(id)

        if current_user:
            await log_audit(
                self.db,
                action="SALARY_COMPONENT_DELETE",
                entity_type="SalaryComponent",
                entity_id=id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"code": prev_code, "name": prev_name},
                new_data={"is_deleted": True},
                status_code=200,
            )

        try:
            user_id_str = str(current_user.id) if current_user else "system"
            send_payroll_component_notification_task.delay(
                action="DELETED",
                component_id=str(id),
                code=prev_code,
                name=prev_name,
                component_type=prev_type,
                calculation_method=prev_method,
                performed_by_id=user_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for component delete: {exc}")

        return True

    async def restore_component(
        self,
        id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> SalaryComponent:
        """Restores a soft-deleted Salary Component definition."""
        restored = await self.repository.restore(self.db, id=id)
        if not restored:
            raise ApnaERPException(
                message=f"Salary component with ID '{id}' not found.",
                status_code=404,
                error_code="COMPONENT_NOT_FOUND",
            )

        await self._invalidate_cache(id)

        if current_user:
            await log_audit(
                self.db,
                action="SALARY_COMPONENT_RESTORE",
                entity_type="SalaryComponent",
                entity_id=id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"is_deleted": True},
                new_data={"is_deleted": False, "code": restored.code},
                status_code=200,
            )

        try:
            user_id_str = str(current_user.id) if current_user else "system"
            send_payroll_component_notification_task.delay(
                action="RESTORED",
                component_id=str(id),
                code=restored.code,
                name=restored.name,
                component_type=restored.type,
                calculation_method=restored.calculation_method,
                performed_by_id=user_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for component restore: {exc}")

        return restored

    async def get_component_by_id(self, id: uuid.UUID) -> SalaryComponent:
        """Retrieves a single Salary Component definition by ID."""
        component = await self.repository.get_by_id(self.db, id)
        if not component or component.is_deleted:
            raise ApnaERPException(
                message=f"Salary component with ID '{id}' not found.",
                status_code=404,
                error_code="COMPONENT_NOT_FOUND",
            )
        return component

    async def list_components(
        self, params: PaginationParams, filters: Optional[List[FilterCriterion]] = None
    ) -> PaginatedResult[SalaryComponent]:
        """Retrieves a paginated list of Salary Components."""
        return await self.repository.get_multi_paginated(
            self.db, params=params, filters=filters
        )
