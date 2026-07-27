import datetime
import logging
from typing import List, Optional
import uuid
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import ApnaERPException
from app.models.employee_compensation import EmployeeCompensation
from app.models.user import User
from app.repositories.employee import employee_repository
from app.repositories.employee_compensation import employee_compensation_repository
from app.repositories.salary_structure import salary_structure_repository
from app.schemas.employee_compensation import (
    EmployeeCompensationCreate,
    EmployeeCompensationRevise,
    EmployeeCompensationUpdate,
)
from app.tasks.compensation_tasks import send_compensation_notification_task
from app.utils.audit import log_audit
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginatedResult, PaginationParams

logger = logging.getLogger("app.services.employee_compensation")

CACHE_PREFIX = "employee_compensation"


class EmployeeCompensationService:
    """
    Service layer for managing Employee Compensation policies, revisions, activations, and history.
    Enforces single active policy constraints, non-overlapping effective dates, revision numbering,
    Redis caching, audit logging, and Celery notifications.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = employee_compensation_repository
        self.employee_repository = employee_repository
        self.salary_structure_repository = salary_structure_repository

    async def _invalidate_cache(self, employee_id: Optional[uuid.UUID] = None):
        """Clears Employee Compensation Redis caches."""
        try:
            await redis_manager.delete_pattern(f"{CACHE_PREFIX}:*")
            if employee_id:
                await redis_manager.delete(f"{CACHE_PREFIX}:current:{employee_id}")
                await redis_manager.delete(f"{CACHE_PREFIX}:history:{employee_id}")
        except Exception as exc:
            logger.warning(f"Failed to clear Redis employee compensation cache: {exc}")

    async def assign_compensation(
        self,
        data: EmployeeCompensationCreate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> EmployeeCompensation:
        """Assigns a new Salary Structure / Compensation policy to an Employee in Draft status."""
        # 1. Verify Employee exists
        emp = await self.employee_repository.get_by_id(self.db, data.employee_id)
        if not emp or emp.is_deleted:
            raise ApnaERPException(
                message=f"Employee with ID '{data.employee_id}' not found.",
                status_code=404,
                error_code="EMPLOYEE_NOT_FOUND",
            )

        # 2. Verify Salary Structure exists
        struct = await self.salary_structure_repository.get_by_id(self.db, data.salary_structure_id)
        if not struct or struct.is_deleted:
            raise ApnaERPException(
                message=f"Salary structure with ID '{data.salary_structure_id}' not found.",
                status_code=404,
                error_code="STRUCTURE_NOT_FOUND",
            )

        # 3. Date range validation
        if data.effective_to and data.effective_to < data.effective_from:
            raise ApnaERPException(
                message="Effective end date (effective_to) cannot be earlier than start date (effective_from).",
                status_code=400,
                error_code="INVALID_DATE_RANGE",
            )

        # 4. Overlapping date check
        has_overlap = await self.repository.check_overlapping_effective_dates(
            self.db,
            employee_id=data.employee_id,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
        )
        if has_overlap:
            raise ApnaERPException(
                message="Compensation effective date range overlaps with an existing policy for this employee.",
                status_code=400,
                error_code="OVERLAPPING_COMPENSATION_DATES",
            )

        comp_dict = data.model_dump()
        comp_dict["status"] = "Draft"
        comp_dict["revision_number"] = 1

        comp = await self.repository.create(self.db, obj_in=comp_dict)
        await self.db.commit()
        await self.db.refresh(comp)
        await self._invalidate_cache(data.employee_id)

        if current_user:
            await log_audit(
                self.db,
                action="COMPENSATION_ASSIGN",
                entity_type="EmployeeCompensation",
                entity_id=comp.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=None,
                new_data={
                    "employee_id": str(data.employee_id),
                    "structure_id": str(data.salary_structure_id),
                    "annual_ctc": data.annual_ctc,
                    "status": "Draft",
                    "revision_number": 1,
                },
                status_code=201,
            )

        try:
            user_id_str = str(current_user.id) if current_user else "system"
            send_compensation_notification_task.delay(
                action="ASSIGNED",
                compensation_id=str(comp.id),
                employee_id=str(comp.employee_id),
                salary_structure_id=str(comp.salary_structure_id),
                annual_ctc=float(comp.annual_ctc),
                status=comp.status,
                performed_by_id=user_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for compensation assign: {exc}")

        return comp

    async def revise_compensation(
        self,
        previous_id: uuid.UUID,
        data: EmployeeCompensationRevise,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> EmployeeCompensation:
        """Revises an existing compensation policy, incrementing revision number and linking previous compensation."""
        prev_comp = await self.repository.get_by_id(self.db, previous_id)
        if not prev_comp or prev_comp.is_deleted:
            raise ApnaERPException(
                message=f"Previous compensation record with ID '{previous_id}' not found.",
                status_code=404,
                error_code="COMPENSATION_NOT_FOUND",
            )

        # Verify Structure exists
        struct = await self.salary_structure_repository.get_by_id(self.db, data.salary_structure_id)
        if not struct or struct.is_deleted:
            raise ApnaERPException(
                message=f"Salary structure with ID '{data.salary_structure_id}' not found.",
                status_code=404,
                error_code="STRUCTURE_NOT_FOUND",
            )

        # Date range validation
        if data.effective_to and data.effective_to < data.effective_from:
            raise ApnaERPException(
                message="Effective end date (effective_to) cannot be earlier than start date (effective_from).",
                status_code=400,
                error_code="INVALID_DATE_RANGE",
            )

        # Overlapping date check
        has_overlap = await self.repository.check_overlapping_effective_dates(
            self.db,
            employee_id=prev_comp.employee_id,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            exclude_id=previous_id,
        )
        if has_overlap:
            raise ApnaERPException(
                message="Revised compensation effective date range overlaps with an existing policy for this employee.",
                status_code=400,
                error_code="OVERLAPPING_COMPENSATION_DATES",
            )

        new_revision_number = prev_comp.revision_number + 1

        comp_dict = data.model_dump()
        comp_dict["employee_id"] = prev_comp.employee_id
        comp_dict["previous_compensation_id"] = previous_id
        comp_dict["status"] = "Draft"
        comp_dict["revision_number"] = new_revision_number

        revised = await self.repository.create(self.db, obj_in=comp_dict)
        await self.db.commit()
        await self.db.refresh(revised)
        await self._invalidate_cache(prev_comp.employee_id)

        if current_user:
            await log_audit(
                self.db,
                action="COMPENSATION_REVISE",
                entity_type="EmployeeCompensation",
                entity_id=revised.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"previous_compensation_id": str(previous_id), "revision_number": prev_comp.revision_number},
                new_data={
                    "employee_id": str(prev_comp.employee_id),
                    "structure_id": str(data.salary_structure_id),
                    "annual_ctc": data.annual_ctc,
                    "status": "Draft",
                    "revision_number": new_revision_number,
                },
                status_code=201,
            )

        try:
            user_id_str = str(current_user.id) if current_user else "system"
            send_compensation_notification_task.delay(
                action="REVISED",
                compensation_id=str(revised.id),
                employee_id=str(revised.employee_id),
                salary_structure_id=str(revised.salary_structure_id),
                annual_ctc=float(revised.annual_ctc),
                status=revised.status,
                performed_by_id=user_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for compensation revise: {exc}")

        return revised

    async def activate_compensation(
        self,
        id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> EmployeeCompensation:
        """Activates a Draft compensation policy, automatically expiring any currently active policy for the employee."""
        comp = await self.repository.get_by_id(self.db, id)
        if not comp or comp.is_deleted:
            raise ApnaERPException(
                message=f"Employee compensation with ID '{id}' not found.",
                status_code=404,
                error_code="COMPENSATION_NOT_FOUND",
            )

        if comp.status == "Active":
            return comp
        if comp.status in ["Cancelled", "Expired"]:
            raise ApnaERPException(
                message=f"Cannot activate compensation with status '{comp.status}'.",
                status_code=400,
                error_code="INVALID_COMPENSATION_STATUS",
            )

        # 1. Expire currently active compensation for this employee if exists
        currently_active = await self.repository.get_active_compensation(self.db, comp.employee_id)
        if currently_active and currently_active.id != id:
            currently_active.status = "Expired"
            # Adjust effective_to of old active policy
            expire_to = comp.effective_from - datetime.timedelta(days=1)
            if expire_to < currently_active.effective_from:
                expire_to = currently_active.effective_from
            currently_active.effective_to = expire_to

        # 2. Activate current compensation
        comp.status = "Active"
        if current_user:
            comp.approved_by = current_user.id
        comp.approved_at = datetime.datetime.now(datetime.timezone.utc)

        await self.db.commit()
        await self.db.refresh(comp)
        await self._invalidate_cache(comp.employee_id)

        if current_user:
            await log_audit(
                self.db,
                action="COMPENSATION_ACTIVATE",
                entity_type="EmployeeCompensation",
                entity_id=comp.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"status": "Draft"},
                new_data={"status": "Active", "approved_by": str(comp.approved_by)},
                status_code=200,
            )

        try:
            user_id_str = str(current_user.id) if current_user else "system"
            send_compensation_notification_task.delay(
                action="ACTIVATED",
                compensation_id=str(comp.id),
                employee_id=str(comp.employee_id),
                salary_structure_id=str(comp.salary_structure_id),
                annual_ctc=float(comp.annual_ctc),
                status=comp.status,
                performed_by_id=user_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for compensation activate: {exc}")

        return comp

    async def cancel_compensation(
        self,
        id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> EmployeeCompensation:
        """Cancels a compensation policy."""
        comp = await self.repository.get_by_id(self.db, id)
        if not comp or comp.is_deleted:
            raise ApnaERPException(
                message=f"Employee compensation with ID '{id}' not found.",
                status_code=404,
                error_code="COMPENSATION_NOT_FOUND",
            )

        prev_status = comp.status
        comp.status = "Cancelled"

        await self.db.commit()
        await self.db.refresh(comp)
        await self._invalidate_cache(comp.employee_id)

        if current_user:
            await log_audit(
                self.db,
                action="COMPENSATION_CANCEL",
                entity_type="EmployeeCompensation",
                entity_id=comp.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"status": prev_status},
                new_data={"status": "Cancelled"},
                status_code=200,
            )

        try:
            user_id_str = str(current_user.id) if current_user else "system"
            send_compensation_notification_task.delay(
                action="CANCELLED",
                compensation_id=str(comp.id),
                employee_id=str(comp.employee_id),
                salary_structure_id=str(comp.salary_structure_id),
                annual_ctc=float(comp.annual_ctc),
                status=comp.status,
                performed_by_id=user_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for compensation cancel: {exc}")

        return comp

    async def update_compensation(
        self,
        id: uuid.UUID,
        data: EmployeeCompensationUpdate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> EmployeeCompensation:
        """Updates an existing compensation policy draft."""
        comp = await self.repository.get_by_id(self.db, id)
        if not comp or comp.is_deleted:
            raise ApnaERPException(
                message=f"Employee compensation with ID '{id}' not found.",
                status_code=404,
                error_code="COMPENSATION_NOT_FOUND",
            )

        if comp.status in ["Expired", "Cancelled"]:
            raise ApnaERPException(
                message=f"Cannot update compensation with status '{comp.status}'.",
                status_code=400,
                error_code="INVALID_COMPENSATION_STATUS",
            )

        prev_data = {
            "annual_ctc": float(comp.annual_ctc),
            "effective_from": str(comp.effective_from),
            "effective_to": str(comp.effective_to) if comp.effective_to else None,
        }

        # Date range validation
        eff_from = data.effective_from or comp.effective_from
        eff_to = data.effective_to if data.effective_to is not None else comp.effective_to
        if eff_to and eff_to < eff_from:
            raise ApnaERPException(
                message="Effective end date (effective_to) cannot be earlier than start date (effective_from).",
                status_code=400,
                error_code="INVALID_DATE_RANGE",
            )

        update_dict = data.model_dump(exclude_unset=True)
        updated = await self.repository.update(self.db, db_obj=comp, obj_in=update_dict)
        await self.db.commit()
        await self.db.refresh(updated)
        await self._invalidate_cache(updated.employee_id)

        if current_user:
            await log_audit(
                self.db,
                action="COMPENSATION_UPDATE",
                entity_type="EmployeeCompensation",
                entity_id=updated.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=prev_data,
                new_data={
                    "annual_ctc": float(updated.annual_ctc),
                    "effective_from": str(updated.effective_from),
                    "effective_to": str(updated.effective_to) if updated.effective_to else None,
                },
                status_code=200,
            )

        return updated

    async def delete_compensation(
        self,
        id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> bool:
        """Soft-deletes an Employee Compensation record."""
        comp = await self.repository.get_by_id(self.db, id)
        if not comp or comp.is_deleted:
            raise ApnaERPException(
                message=f"Employee compensation with ID '{id}' not found.",
                status_code=404,
                error_code="COMPENSATION_NOT_FOUND",
            )

        emp_id = comp.employee_id
        await self.repository.soft_delete(self.db, id=id)
        await self.db.commit()
        await self._invalidate_cache(emp_id)

        if current_user:
            await log_audit(
                self.db,
                action="COMPENSATION_DELETE",
                entity_type="EmployeeCompensation",
                entity_id=id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"employee_id": str(emp_id)},
                new_data={"is_deleted": True},
                status_code=200,
            )

        return True

    async def restore_compensation(
        self,
        id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> EmployeeCompensation:
        """Restores a soft-deleted Employee Compensation record."""
        restored = await self.repository.restore(self.db, id=id)
        if not restored:
            raise ApnaERPException(
                message=f"Employee compensation with ID '{id}' not found.",
                status_code=404,
                error_code="COMPENSATION_NOT_FOUND",
            )

        await self._invalidate_cache(restored.employee_id)

        if current_user:
            await log_audit(
                self.db,
                action="COMPENSATION_RESTORE",
                entity_type="EmployeeCompensation",
                entity_id=id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"is_deleted": True},
                new_data={"is_deleted": False},
                status_code=200,
            )

        return restored

    async def get_current_compensation(self, employee_id: uuid.UUID) -> EmployeeCompensation:
        """Retrieves the currently Active compensation policy for an employee."""
        comp = await self.repository.get_active_compensation(self.db, employee_id)
        if not comp:
            raise ApnaERPException(
                message=f"Active compensation policy for employee ID '{employee_id}' not found.",
                status_code=404,
                error_code="ACTIVE_COMPENSATION_NOT_FOUND",
            )
        return comp

    async def get_compensation_history(self, employee_id: uuid.UUID) -> List[EmployeeCompensation]:
        """Retrieves the full compensation policy history for an employee."""
        return await self.repository.get_compensation_history(self.db, employee_id)

    async def get_compensation_by_id(self, id: uuid.UUID) -> EmployeeCompensation:
        """Retrieves a single Employee Compensation record by ID."""
        comp = await self.repository.get_by_id(self.db, id)
        if not comp or comp.is_deleted:
            raise ApnaERPException(
                message=f"Employee compensation with ID '{id}' not found.",
                status_code=404,
                error_code="COMPENSATION_NOT_FOUND",
            )
        return comp

    async def list_compensations(
        self, params: PaginationParams, filters: Optional[List[FilterCriterion]] = None
    ) -> PaginatedResult[EmployeeCompensation]:
        """Retrieves a paginated list of Employee Compensation records."""
        return await self.repository.get_multi_paginated(
            self.db, params=params, filters=filters
        )
