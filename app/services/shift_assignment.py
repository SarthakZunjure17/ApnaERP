import datetime
import logging
from typing import Optional
import uuid
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import ApnaERPException
from app.models.shift import Shift
from app.models.shift_assignment import ShiftAssignment
from app.models.user import User
from app.repositories.employee import employee_repository
from app.repositories.shift import shift_repository
from app.repositories.shift_assignment import shift_assignment_repository
from app.schemas.shift_assignment import (
    ShiftAssignmentCreate,
    ShiftAssignmentEndRequest,
    ShiftAssignmentResponse,
    ShiftAssignmentUpdate,
)
from app.utils.audit import log_audit
from app.core.redis import redis_manager
from app.tasks.shift_assignment_tasks import send_shift_assignment_notification_task
from app.utils.pagination import PaginatedResult, PaginationParams

logger = logging.getLogger("app.services.shift_assignment")


class ShiftAssignmentService:
    """
    Service layer for Shift Assignment management.
    Orchestrates shift assignments, date overlap validations, historical attendance safeguards,
    Redis caching, audit logging, and notifications.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = shift_assignment_repository
        self.employee_repo = employee_repository
        self.shift_repo = shift_repository

    async def _invalidate_cache(self, employee_id: uuid.UUID):
        """Invalidates Redis shift assignment caches for the target employee."""
        try:
            pattern = f"shift_assignment:active:{employee_id}:*"
            await redis_manager.delete_pattern(pattern)
        except Exception as exc:
            logger.warning(f"Failed to clear Redis shift assignment cache for employee {employee_id}: {exc}")

    async def assign_shift(
        self,
        data: ShiftAssignmentCreate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> ShiftAssignment:
        """
        Assigns a shift to an employee with effective start and end dates.
        Validates employee existence, shift existence, date range, overlap, and attendance lock.
        """
        # 1. Validate Employee
        employee = await self.employee_repo.get_by_id(self.db, data.employee_id)
        if not employee or not employee.is_active or employee.is_deleted:
            raise ApnaERPException(
                message=f"Active employee with ID {data.employee_id} not found.",
                status_code=404,
                error_code="EMPLOYEE_NOT_FOUND",
            )

        # 2. Validate Shift
        shift = await self.shift_repo.get_by_id(self.db, data.shift_id)
        if not shift or not shift.is_active or shift.is_deleted:
            raise ApnaERPException(
                message=f"Active shift with ID {data.shift_id} not found.",
                status_code=404,
                error_code="SHIFT_NOT_FOUND",
            )

        # 3. Validate Date Range
        if data.effective_to and data.effective_to < data.effective_from:
            raise ApnaERPException(
                message="Effective end date (effective_to) cannot be earlier than start date (effective_from).",
                status_code=400,
                error_code="INVALID_DATE_RANGE",
            )

        # 4. Check Date Overlap
        has_overlap = await self.repository.check_overlap(
            self.db,
            employee_id=data.employee_id,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
        )
        if has_overlap:
            raise ApnaERPException(
                message="Employee already has an active shift assignment during this date range.",
                status_code=400,
                error_code="OVERLAPPING_SHIFT_ASSIGNMENT",
            )

        # 5. Check Locked Attendance Guard
        is_locked = await self.repository.has_locked_attendance_in_range(
            self.db,
            employee_id=data.employee_id,
            start_date=data.effective_from,
            end_date=data.effective_to,
        )
        if is_locked:
            raise ApnaERPException(
                message="Cannot create shift assignment overlapping locked attendance records.",
                status_code=400,
                error_code="ATTENDANCE_LOCKED",
            )

        # 6. Create Assignment
        assignment_dict = data.model_dump()
        assignment_dict["assigned_by"] = current_user.id if current_user else None
        assignment_dict["is_active"] = True

        assignment = await self.repository.create(self.db, obj_in=assignment_dict)

        # 7. Invalidate Cache
        await self._invalidate_cache(data.employee_id)

        # 8. Audit Log
        if current_user:
            await log_audit(
                self.db,
                action="SHIFT_ASSIGNMENT_CREATE",
                entity_type="ShiftAssignment",
                entity_id=assignment.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=None,
                new_data={
                    "employee_id": str(assignment.employee_id),
                    "shift_id": str(assignment.shift_id),
                    "effective_from": str(assignment.effective_from),
                    "effective_to": str(assignment.effective_to) if assignment.effective_to else None,
                    "assignment_type": assignment.assignment_type,
                },
                status_code=201,
            )

        # 9. Celery Notification
        try:
            send_shift_assignment_notification_task.delay(
                event_type="SHIFT_ASSIGNMENT_CREATED",
                assignment_id=str(assignment.id),
                employee_id=str(assignment.employee_id),
                shift_id=str(assignment.shift_id),
                effective_from=str(assignment.effective_from),
                effective_to=str(assignment.effective_to) if assignment.effective_to else None,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery shift assignment task: {exc}")

        return assignment

    async def update_assignment(
        self,
        id: uuid.UUID,
        data: ShiftAssignmentUpdate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> ShiftAssignment:
        """Updates an existing shift assignment after validating overlap and attendance lock constraints."""
        assignment = await self.repository.get_by_id(self.db, id)
        if not assignment or assignment.is_deleted:
            raise ApnaERPException(
                message=f"Shift assignment with ID {id} not found.",
                status_code=404,
                error_code="SHIFT_ASSIGNMENT_NOT_FOUND",
            )

        new_shift_id = data.shift_id or assignment.shift_id
        new_from = data.effective_from or assignment.effective_from
        new_to = data.effective_to if data.effective_to is not None else assignment.effective_to

        if data.shift_id:
            shift = await self.shift_repo.get_by_id(self.db, data.shift_id)
            if not shift or not shift.is_active or shift.is_deleted:
                raise ApnaERPException(
                    message=f"Active shift with ID {data.shift_id} not found.",
                    status_code=404,
                    error_code="SHIFT_NOT_FOUND",
                )

        if new_to and new_to < new_from:
            raise ApnaERPException(
                message="Effective end date (effective_to) cannot be earlier than start date (effective_from).",
                status_code=400,
                error_code="INVALID_DATE_RANGE",
            )

        # Check locked attendance for existing range & new range
        locked_existing = await self.repository.has_locked_attendance_in_range(
            self.db,
            employee_id=assignment.employee_id,
            start_date=assignment.effective_from,
            end_date=assignment.effective_to,
        )
        if locked_existing:
            raise ApnaERPException(
                message="Cannot update shift assignment because historical attendance records in this range are locked.",
                status_code=400,
                error_code="ATTENDANCE_LOCKED",
            )

        # Check Overlap excluding current assignment
        has_overlap = await self.repository.check_overlap(
            self.db,
            employee_id=assignment.employee_id,
            effective_from=new_from,
            effective_to=new_to,
            exclude_id=assignment.id,
        )
        if has_overlap:
            raise ApnaERPException(
                message="Updated date range overlaps with another active shift assignment for this employee.",
                status_code=400,
                error_code="OVERLAPPING_SHIFT_ASSIGNMENT",
            )

        prev_data = {
            "shift_id": str(assignment.shift_id),
            "effective_from": str(assignment.effective_from),
            "effective_to": str(assignment.effective_to) if assignment.effective_to else None,
            "is_active": assignment.is_active,
        }

        updated = await self.repository.update(self.db, db_obj=assignment, obj_in=data)
        await self._invalidate_cache(updated.employee_id)

        if current_user:
            await log_audit(
                self.db,
                action="SHIFT_ASSIGNMENT_UPDATE",
                entity_type="ShiftAssignment",
                entity_id=updated.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=prev_data,
                new_data={
                    "shift_id": str(updated.shift_id),
                    "effective_from": str(updated.effective_from),
                    "effective_to": str(updated.effective_to) if updated.effective_to else None,
                    "is_active": updated.is_active,
                },
                status_code=200,
            )

        return updated

    async def end_assignment(
        self,
        id: uuid.UUID,
        data: ShiftAssignmentEndRequest,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> ShiftAssignment:
        """Ends a shift assignment by setting effective_to to end_date."""
        assignment = await self.repository.get_by_id(self.db, id)
        if not assignment or assignment.is_deleted:
            raise ApnaERPException(
                message=f"Shift assignment with ID {id} not found.",
                status_code=404,
                error_code="SHIFT_ASSIGNMENT_NOT_FOUND",
            )

        if data.end_date < assignment.effective_from:
            raise ApnaERPException(
                message=f"End date ({data.end_date}) cannot be earlier than start date ({assignment.effective_from}).",
                status_code=400,
                error_code="INVALID_DATE_RANGE",
            )

        # Check locked attendance guard
        locked = await self.repository.has_locked_attendance_in_range(
            self.db,
            employee_id=assignment.employee_id,
            start_date=data.end_date,
            end_date=assignment.effective_to,
        )
        if locked:
            raise ApnaERPException(
                message="Cannot end shift assignment because attendance records in the affected period are locked.",
                status_code=400,
                error_code="ATTENDANCE_LOCKED",
            )

        prev_data = {"effective_to": str(assignment.effective_to) if assignment.effective_to else None}
        assignment.effective_to = data.end_date
        if data.end_date < datetime.date.today():
            assignment.is_active = False

        await self.db.commit()
        await self.db.refresh(assignment)

        await self._invalidate_cache(assignment.employee_id)

        if current_user:
            await log_audit(
                self.db,
                action="SHIFT_ASSIGNMENT_END",
                entity_type="ShiftAssignment",
                entity_id=assignment.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=prev_data,
                new_data={
                    "effective_to": str(assignment.effective_to),
                    "is_active": assignment.is_active,
                },
                status_code=200,
            )

        return assignment

    async def delete_assignment(
        self,
        id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> bool:
        """Soft-deletes a shift assignment if no locked attendance exists in its date range."""
        assignment = await self.repository.get_by_id(self.db, id)
        if not assignment or assignment.is_deleted:
            raise ApnaERPException(
                message=f"Shift assignment with ID {id} not found.",
                status_code=404,
                error_code="SHIFT_ASSIGNMENT_NOT_FOUND",
            )

        locked = await self.repository.has_locked_attendance_in_range(
            self.db,
            employee_id=assignment.employee_id,
            start_date=assignment.effective_from,
            end_date=assignment.effective_to,
        )
        if locked:
            raise ApnaERPException(
                message="Cannot delete shift assignment because attendance records in this period are locked.",
                status_code=400,
                error_code="ATTENDANCE_LOCKED",
            )

        await self.repository.soft_delete(self.db, id=id)
        await self._invalidate_cache(assignment.employee_id)

        if current_user:
            await log_audit(
                self.db,
                action="SHIFT_ASSIGNMENT_DELETE",
                entity_type="ShiftAssignment",
                entity_id=id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"employee_id": str(assignment.employee_id), "shift_id": str(assignment.shift_id)},
                new_data=None,
                status_code=200,
            )

        return True

    async def get_by_id(self, id: uuid.UUID) -> ShiftAssignment:
        """Retrieves a single shift assignment by ID."""
        assignment = await self.repository.get_by_id(self.db, id)
        if not assignment or assignment.is_deleted:
            raise ApnaERPException(
                message=f"Shift assignment with ID {id} not found.",
                status_code=404,
                error_code="SHIFT_ASSIGNMENT_NOT_FOUND",
            )
        return assignment

    async def get_employee_assignments(
        self, employee_id: uuid.UUID, params: PaginationParams
    ) -> PaginatedResult[ShiftAssignment]:
        """Retrieves paginated shift assignments for a specific employee."""
        employee = await self.employee_repo.get_by_id(self.db, employee_id)
        if not employee or employee.is_deleted:
            raise ApnaERPException(
                message=f"Employee with ID {employee_id} not found.",
                status_code=404,
                error_code="EMPLOYEE_NOT_FOUND",
            )
        return await self.repository.get_employee_assignments_paginated(
            self.db, employee_id=employee_id, params=params
        )

    async def get_all_assignments(self, params: PaginationParams) -> PaginatedResult[ShiftAssignment]:
        """Retrieves all shift assignments paginated."""
        return await self.repository.get_multi_paginated(self.db, params=params)

    async def resolve_shift_for_date(
        self, employee_id: uuid.UUID, target_date: datetime.date
    ) -> Optional[Shift]:
        """
        Resolves the effective Shift for an employee on a target date.
        Uses Redis caching (`shift_assignment:active:{emp_id}:{date}`) with fallback to database.
        Falls back to Employee.shift_id if no assignment exists for the target date.
        """
        cache_key = f"shift_assignment:active:{employee_id}:{target_date.isoformat()}"
        try:
            cached_val = await redis_manager.get(cache_key)
            if cached_val == "NONE":
                return None
            elif cached_val:
                shift = await self.shift_repo.get_by_id(self.db, uuid.UUID(cached_val))
                if shift and shift.is_active and not shift.is_deleted:
                    return shift
        except Exception as exc:
            logger.warning(f"Redis lookup failed for shift assignment cache {cache_key}: {exc}")

        # DB Lookup
        assignment = await self.repository.get_active_assignment_for_date(
            self.db, employee_id=employee_id, target_date=target_date
        )

        shift = None
        if assignment and assignment.shift:
            shift = assignment.shift
            try:
                await redis_manager.set(cache_key, str(shift.id), ttl=3600)
            except Exception as exc:
                logger.warning(f"Redis set failed for shift assignment cache {cache_key}: {exc}")
            return shift

        # Fallback to Employee.shift_id for backwards compatibility
        employee = await self.employee_repo.get_by_id(self.db, employee_id)
        if employee and employee.shift_id:
            shift = await self.shift_repo.get_by_id(self.db, employee.shift_id)
            if shift and shift.is_active and not shift.is_deleted:
                try:
                    await redis_manager.set(cache_key, str(shift.id), ttl=3600)
                except Exception as exc:
                    logger.warning(f"Redis set failed for fallback shift cache {cache_key}: {exc}")
                return shift

        try:
            await redis_manager.set(cache_key, "NONE", ttl=3600)
        except Exception as exc:
            logger.warning(f"Redis set failed for NONE shift cache {cache_key}: {exc}")

        return None
