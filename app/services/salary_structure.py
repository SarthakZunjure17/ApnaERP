import logging
from typing import List, Optional
import uuid
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import ApnaERPException
from app.models.salary_structure import SalaryStructure, SalaryStructureComponent
from app.models.user import User
from app.repositories.salary_component import salary_component_repository
from app.repositories.salary_structure import (
    salary_structure_component_repository,
    salary_structure_repository,
)
from app.schemas.salary_structure import (
    SalaryStructureComponentCreate,
    SalaryStructureComponentUpdate,
    SalaryStructureCreate,
    SalaryStructureUpdate,
)
from app.tasks.payroll_structure_tasks import send_payroll_structure_notification_task
from app.utils.audit import log_audit
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginatedResult, PaginationParams

logger = logging.getLogger("app.services.salary_structure")

CACHE_PREFIX = "salary_structure"


class SalaryStructureService:
    """
    Service layer for managing Salary Structure templates and Component mappings.
    Enforces business rules, date validity, component uniqueness, Redis caching, audit trails, and Celery notifications.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = salary_structure_repository
        self.component_repository = salary_structure_component_repository
        self.salary_component_repository = salary_component_repository

    async def _invalidate_cache(self, structure_id: Optional[uuid.UUID] = None):
        """Clears Salary Structure Redis caches."""
        try:
            await redis_manager.delete_pattern(f"{CACHE_PREFIX}:*")
            if structure_id:
                await redis_manager.delete(f"{CACHE_PREFIX}:id:{structure_id}")
        except Exception as exc:
            logger.warning(f"Failed to clear Redis salary structure cache: {exc}")

    async def create_structure(
        self,
        data: SalaryStructureCreate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> SalaryStructure:
        """Creates a new Salary Structure template."""
        # 1. Uniqueness checks
        existing_code = await self.repository.get_by_code(self.db, data.code, include_deleted=True)
        if existing_code:
            raise ApnaERPException(
                message=f"Salary structure with code '{data.code}' already exists.",
                status_code=400,
                error_code="DUPLICATE_STRUCTURE_CODE",
            )

        existing_name = await self.repository.get_by_name(self.db, data.name, include_deleted=True)
        if existing_name:
            raise ApnaERPException(
                message=f"Salary structure with name '{data.name}' already exists.",
                status_code=400,
                error_code="DUPLICATE_STRUCTURE_NAME",
            )

        # 2. Date range validation
        if data.effective_to and data.effective_to < data.effective_from:
            raise ApnaERPException(
                message="Effective end date (effective_to) cannot be earlier than start date (effective_from).",
                status_code=400,
                error_code="INVALID_DATE_RANGE",
            )

        struct_dict = data.model_dump()
        structure = await self.repository.create(self.db, obj_in=struct_dict)
        await self.db.commit()
        await self.db.refresh(structure)
        await self._invalidate_cache(structure.id)

        if current_user:
            await log_audit(
                self.db,
                action="SALARY_STRUCTURE_CREATE",
                entity_type="SalaryStructure",
                entity_id=structure.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=None,
                new_data={
                    "code": structure.code,
                    "name": structure.name,
                    "currency": structure.currency,
                    "effective_from": str(structure.effective_from),
                    "effective_to": str(structure.effective_to) if structure.effective_to else None,
                },
                status_code=201,
            )

        try:
            user_id_str = str(current_user.id) if current_user else "system"
            send_payroll_structure_notification_task.delay(
                action="CREATED",
                structure_id=str(structure.id),
                code=structure.code,
                name=structure.name,
                performed_by_id=user_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for structure create: {exc}")

        return structure

    async def update_structure(
        self,
        id: uuid.UUID,
        data: SalaryStructureUpdate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> SalaryStructure:
        """Updates an existing Salary Structure template."""
        structure = await self.repository.get_by_id(self.db, id)
        if not structure or structure.is_deleted:
            raise ApnaERPException(
                message=f"Salary structure with ID '{id}' not found.",
                status_code=404,
                error_code="STRUCTURE_NOT_FOUND",
            )

        prev_data = {
            "name": structure.name,
            "currency": structure.currency,
            "is_active": structure.is_active,
            "effective_from": str(structure.effective_from),
            "effective_to": str(structure.effective_to) if structure.effective_to else None,
        }

        # 1. Uniqueness check if name changes
        if data.name and data.name != structure.name:
            existing_name = await self.repository.get_by_name(self.db, data.name, include_deleted=True)
            if existing_name and existing_name.id != id:
                raise ApnaERPException(
                    message=f"Salary structure with name '{data.name}' already exists.",
                    status_code=400,
                    error_code="DUPLICATE_STRUCTURE_NAME",
                )

        # 2. Date range validation
        eff_from = data.effective_from or structure.effective_from
        eff_to = data.effective_to if data.effective_to is not None else structure.effective_to
        if eff_to and eff_to < eff_from:
            raise ApnaERPException(
                message="Effective end date (effective_to) cannot be earlier than start date (effective_from).",
                status_code=400,
                error_code="INVALID_DATE_RANGE",
            )

        update_dict = data.model_dump(exclude_unset=True)
        updated = await self.repository.update(self.db, db_obj=structure, obj_in=update_dict)
        await self.db.commit()
        await self.db.refresh(updated)
        await self._invalidate_cache(updated.id)

        if current_user:
            await log_audit(
                self.db,
                action="SALARY_STRUCTURE_UPDATE",
                entity_type="SalaryStructure",
                entity_id=updated.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=prev_data,
                new_data={
                    "name": updated.name,
                    "currency": updated.currency,
                    "is_active": updated.is_active,
                    "effective_from": str(updated.effective_from),
                    "effective_to": str(updated.effective_to) if updated.effective_to else None,
                },
                status_code=200,
            )

        try:
            user_id_str = str(current_user.id) if current_user else "system"
            send_payroll_structure_notification_task.delay(
                action="UPDATED",
                structure_id=str(updated.id),
                code=updated.code,
                name=updated.name,
                performed_by_id=user_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for structure update: {exc}")

        return updated

    async def delete_structure(
        self,
        id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> bool:
        """Soft-deletes a Salary Structure template."""
        structure = await self.repository.get_by_id(self.db, id)
        if not structure or structure.is_deleted:
            raise ApnaERPException(
                message=f"Salary structure with ID '{id}' not found.",
                status_code=404,
                error_code="STRUCTURE_NOT_FOUND",
            )

        code = structure.code
        name = structure.name

        await self.repository.soft_delete(self.db, id=id)
        await self.db.commit()
        await self._invalidate_cache(id)

        if current_user:
            await log_audit(
                self.db,
                action="SALARY_STRUCTURE_DELETE",
                entity_type="SalaryStructure",
                entity_id=id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"code": code, "name": name},
                new_data={"is_deleted": True},
                status_code=200,
            )

        try:
            user_id_str = str(current_user.id) if current_user else "system"
            send_payroll_structure_notification_task.delay(
                action="DELETED",
                structure_id=str(id),
                code=code,
                name=name,
                performed_by_id=user_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for structure delete: {exc}")

        return True

    async def restore_structure(
        self,
        id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> SalaryStructure:
        """Restores a soft-deleted Salary Structure template."""
        restored = await self.repository.restore(self.db, id=id)
        if not restored:
            raise ApnaERPException(
                message=f"Salary structure with ID '{id}' not found.",
                status_code=404,
                error_code="STRUCTURE_NOT_FOUND",
            )

        await self._invalidate_cache(id)

        if current_user:
            await log_audit(
                self.db,
                action="SALARY_STRUCTURE_RESTORE",
                entity_type="SalaryStructure",
                entity_id=id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"is_deleted": True},
                new_data={"is_deleted": False, "code": restored.code},
                status_code=200,
            )

        try:
            user_id_str = str(current_user.id) if current_user else "system"
            send_payroll_structure_notification_task.delay(
                action="RESTORED",
                structure_id=str(id),
                code=restored.code,
                name=restored.name,
                performed_by_id=user_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for structure restore: {exc}")

        return restored

    async def add_component_to_structure(
        self,
        structure_id: uuid.UUID,
        data: SalaryStructureComponentCreate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> SalaryStructureComponent:
        """Adds a Salary Component mapping to a Salary Structure."""
        structure = await self.repository.get_by_id(self.db, structure_id)
        if not structure or structure.is_deleted:
            raise ApnaERPException(
                message=f"Salary structure with ID '{structure_id}' not found.",
                status_code=404,
                error_code="STRUCTURE_NOT_FOUND",
            )

        # 1. Verify component exists
        salary_comp = await self.salary_component_repository.get_by_id(self.db, data.salary_component_id)
        if not salary_comp or salary_comp.is_deleted:
            raise ApnaERPException(
                message=f"Salary component with ID '{data.salary_component_id}' not found.",
                status_code=404,
                error_code="COMPONENT_NOT_FOUND",
            )

        # 2. Check if component is already in this structure
        existing_mapping = await self.component_repository.get_by_structure_and_component(
            self.db, structure_id, data.salary_component_id
        )
        if existing_mapping:
            raise ApnaERPException(
                message=f"Component '{salary_comp.code}' is already added to this salary structure.",
                status_code=400,
                error_code="DUPLICATE_STRUCTURE_COMPONENT",
            )

        comp_dict = data.model_dump()
        comp_dict["salary_structure_id"] = structure_id

        mapping = await self.component_repository.create(self.db, obj_in=comp_dict)
        await self.db.commit()
        await self.db.refresh(mapping)
        await self._invalidate_cache(structure_id)

        if current_user:
            await log_audit(
                self.db,
                action="SALARY_STRUCTURE_COMPONENT_ADD",
                entity_type="SalaryStructureComponent",
                entity_id=mapping.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=None,
                new_data={
                    "structure_id": str(structure_id),
                    "component_id": str(data.salary_component_id),
                    "component_order": mapping.component_order,
                    "component_value": float(mapping.component_value),
                },
                status_code=201,
            )

        return mapping

    async def update_structure_component(
        self,
        structure_id: uuid.UUID,
        component_mapping_id: uuid.UUID,
        data: SalaryStructureComponentUpdate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> SalaryStructureComponent:
        """Updates an existing component mapping within a Salary Structure."""
        mapping = await self.component_repository.get_by_id(self.db, component_mapping_id)
        if not mapping or mapping.salary_structure_id != structure_id:
            raise ApnaERPException(
                message=f"Structure component mapping ID '{component_mapping_id}' not found for structure '{structure_id}'.",
                status_code=404,
                error_code="STRUCTURE_COMPONENT_NOT_FOUND",
            )

        prev_data = {
            "component_order": mapping.component_order,
            "component_value": float(mapping.component_value),
            "is_active": mapping.is_active,
        }

        update_dict = data.model_dump(exclude_unset=True)
        updated = await self.component_repository.update(self.db, db_obj=mapping, obj_in=update_dict)
        await self.db.commit()
        await self.db.refresh(updated)
        await self._invalidate_cache(structure_id)

        if current_user:
            await log_audit(
                self.db,
                action="SALARY_STRUCTURE_COMPONENT_UPDATE",
                entity_type="SalaryStructureComponent",
                entity_id=updated.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=prev_data,
                new_data={
                    "component_order": updated.component_order,
                    "component_value": float(updated.component_value),
                    "is_active": updated.is_active,
                },
                status_code=200,
            )

        return updated

    async def remove_component_from_structure(
        self,
        structure_id: uuid.UUID,
        component_mapping_id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> bool:
        """Removes a component mapping from a Salary Structure."""
        mapping = await self.component_repository.get_by_id(self.db, component_mapping_id)
        if not mapping or mapping.salary_structure_id != structure_id:
            raise ApnaERPException(
                message=f"Structure component mapping ID '{component_mapping_id}' not found for structure '{structure_id}'.",
                status_code=404,
                error_code="STRUCTURE_COMPONENT_NOT_FOUND",
            )

        await self.db.delete(mapping)
        await self.db.commit()
        await self._invalidate_cache(structure_id)

        if current_user:
            await log_audit(
                self.db,
                action="SALARY_STRUCTURE_COMPONENT_REMOVE",
                entity_type="SalaryStructureComponent",
                entity_id=component_mapping_id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"structure_id": str(structure_id)},
                new_data={"removed": True},
                status_code=200,
            )

        return True

    async def get_structure_by_id(self, id: uuid.UUID) -> SalaryStructure:
        """Retrieves a single Salary Structure template by ID."""
        structure = await self.repository.get_by_id(self.db, id)
        if not structure or structure.is_deleted:
            raise ApnaERPException(
                message=f"Salary structure with ID '{id}' not found.",
                status_code=404,
                error_code="STRUCTURE_NOT_FOUND",
            )
        return structure

    async def list_structures(
        self, params: PaginationParams, filters: Optional[List[FilterCriterion]] = None
    ) -> PaginatedResult[SalaryStructure]:
        """Retrieves a paginated list of Salary Structure templates."""
        return await self.repository.get_multi_paginated(
            self.db, params=params, filters=filters
        )
