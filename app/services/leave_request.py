import datetime
import logging
from typing import Any, Dict, List, Optional
import uuid
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import ApnaERPException
from app.models.holiday import Holiday
from app.models.leave_request import LeaveRequest
from app.models.user import User
from app.repositories.employee import employee_repository
from app.repositories.leave_balance import leave_balance_repository
from app.repositories.leave_request import leave_request_repository
from app.repositories.leave_type import leave_type_repository
from app.schemas.leave_request import (
    LeaveRequestCancelRequest,
    LeaveRequestCreate,
    LeaveRequestReviewRequest,
    LeaveRequestUpdate,
)
from app.tasks.leave_request_tasks import send_leave_request_notification_task
from app.utils.audit import log_audit
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginatedResult, PaginationParams

logger = logging.getLogger("app.services.leave_request")

CACHE_DETAIL_PREFIX = "leave_request:detail"
CACHE_EMP_PREFIX = "leave_request:employee"


class LeaveRequestService:
    """
    Service layer implementing Enterprise Leave Request Workflow.
    Handles state machine transitions, working day calculations (excluding weekends & holidays),
    policy checks, overlap prevention, leave balance updating, audit logging, and Celery notifications.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = leave_request_repository
        self.employee_repo = employee_repository
        self.leave_type_repo = leave_type_repository
        self.balance_repo = leave_balance_repository

    async def _invalidate_cache(self, employee_id: uuid.UUID, request_id: Optional[uuid.UUID] = None):
        """Invalidates Redis leave request caches."""
        try:
            pattern = f"{CACHE_EMP_PREFIX}:{employee_id}:*"
            await redis_manager.delete_pattern(pattern)
            await redis_manager.delete_pattern("leave_request:*")
            if request_id:
                await redis_manager.delete(f"{CACHE_DETAIL_PREFIX}:{request_id}")
        except Exception as exc:
            logger.warning(f"Failed to clear Redis leave request cache for employee {employee_id}: {exc}")

    async def calculate_working_days(
        self, start_date: datetime.date, end_date: datetime.date, is_half_day: bool = False
    ) -> float:
        """
        Calculates net working days between start_date and end_date inclusive.
        Excludes Saturdays (weekday 5), Sundays (weekday 6), and active organization Holidays.
        """
        if is_half_day:
            return 0.5

        # Fetch active holidays in date range
        holiday_query = select(Holiday.holiday_date).where(
            Holiday.holiday_date >= start_date,
            Holiday.holiday_date <= end_date,
            Holiday.is_active.is_(True),
            Holiday.is_deleted.is_(False),
        )
        res = await self.db.execute(holiday_query)
        holiday_dates = set(res.scalars().all())

        working_days = 0
        curr = start_date
        one_day = datetime.timedelta(days=1)

        while curr <= end_date:
            # Check weekend (5=Saturday, 6=Sunday) and Holiday table
            if curr.weekday() not in (5, 6) and curr not in holiday_dates:
                working_days += 1
            curr += one_day

        return float(working_days)

    async def _validate_leave_policies(
        self,
        employee: Any,
        leave_type: Any,
        start_date: datetime.date,
        end_date: datetime.date,
        total_days: float,
        is_half_day: bool,
        exclude_request_id: Optional[uuid.UUID] = None,
    ):
        """Validates all policy constraints for a leave request."""
        # 1. Dates order
        if end_date < start_date:
            raise ApnaERPException(
                message="End date cannot be prior to start date.",
                status_code=400,
                error_code="INVALID_LEAVE_DATES",
            )

        # 2. Net Working Days check
        if total_days <= 0:
            raise ApnaERPException(
                message="The requested date range consists entirely of weekends or holidays.",
                status_code=400,
                error_code="INVALID_LEAVE_DATES",
            )

        # 3. Half-day policy check
        if is_half_day and not leave_type.allow_half_day:
            raise ApnaERPException(
                message=f"Half-day leave is not permitted for leave policy '{leave_type.name}'.",
                status_code=400,
                error_code="HALF_DAY_NOT_PERMITTED",
            )

        # 4. Max consecutive days check
        if total_days > leave_type.max_consecutive_days:
            raise ApnaERPException(
                message=f"Requested duration ({total_days} days) exceeds maximum consecutive days allowed ({leave_type.max_consecutive_days} days).",
                status_code=400,
                error_code="EXCEEDS_MAX_CONSECUTIVE_DAYS",
            )

        # 5. Gender restriction check
        if leave_type.gender_restriction and leave_type.gender_restriction != "All":
            emp_gender = (employee.gender or "").strip()
            if emp_gender and emp_gender.lower() != leave_type.gender_restriction.lower():
                raise ApnaERPException(
                    message=f"Leave policy '{leave_type.name}' is restricted to '{leave_type.gender_restriction}' employees.",
                    status_code=400,
                    error_code="GENDER_RESTRICTION_MISMATCH",
                )

        # 6. Overlap detection
        overlapping = await self.repository.get_overlapping_requests(
            self.db,
            employee_id=employee.id,
            start_date=start_date,
            end_date=end_date,
            exclude_id=exclude_request_id,
        )
        if overlapping:
            raise ApnaERPException(
                message=f"An active leave request already exists overlapping dates {start_date} to {end_date}.",
                status_code=400,
                error_code="OVERLAPPING_LEAVE_REQUEST",
            )

        # 7. Leave Balance Check
        balance = await self.balance_repo.get_by_employee_type_year(
            self.db,
            employee_id=employee.id,
            leave_type_id=leave_type.id,
            leave_year=start_date.year,
        )
        if not balance and not leave_type.allow_negative_balance:
            raise ApnaERPException(
                message=f"No leave balance record found for employee '{employee.employee_code}' for leave year {start_date.year}.",
                status_code=400,
                error_code="INSUFFICIENT_LEAVE_BALANCE",
            )
        if balance and balance.remaining_days < total_days and not leave_type.allow_negative_balance:
            raise ApnaERPException(
                message=f"Insufficient leave balance ({balance.remaining_days} days available, {total_days} days requested).",
                status_code=400,
                error_code="INSUFFICIENT_LEAVE_BALANCE",
            )

    async def create_leave_request(
        self,
        data: LeaveRequestCreate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> LeaveRequest:
        """Creates a new Leave Request in 'Draft' status."""
        employee = await self.employee_repo.get_by_id(self.db, data.employee_id)
        if not employee or employee.is_deleted:
            raise ApnaERPException(
                message=f"Employee with ID '{data.employee_id}' not found.",
                status_code=404,
                error_code="EMPLOYEE_NOT_FOUND",
            )

        leave_type = await self.leave_type_repo.get_by_id(self.db, data.leave_type_id)
        if not leave_type or leave_type.is_deleted or not leave_type.is_active:
            raise ApnaERPException(
                message=f"Leave type with ID '{data.leave_type_id}' not found or inactive.",
                status_code=404,
                error_code="LEAVE_TYPE_NOT_FOUND",
            )

        total_days = await self.calculate_working_days(
            data.start_date, data.end_date, is_half_day=data.is_half_day
        )
        await self._validate_leave_policies(
            employee=employee,
            leave_type=leave_type,
            start_date=data.start_date,
            end_date=data.end_date,
            total_days=total_days,
            is_half_day=data.is_half_day,
        )

        req_dict = data.model_dump()
        req_dict["total_days"] = total_days
        req_dict["status"] = "Draft"

        created = await self.repository.create(self.db, obj_in=req_dict)
        await self._invalidate_cache(created.employee_id, created.id)

        if current_user:
            await log_audit(
                self.db,
                action="LEAVE_REQUEST_CREATE",
                entity_type="LeaveRequest",
                entity_id=created.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=None,
                new_data={
                    "employee_id": str(created.employee_id),
                    "leave_type_id": str(created.leave_type_id),
                    "start_date": str(created.start_date),
                    "end_date": str(created.end_date),
                    "total_days": created.total_days,
                    "status": created.status,
                },
                status_code=201,
            )

        return created

    async def update_leave_request(
        self,
        id: uuid.UUID,
        data: LeaveRequestUpdate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> LeaveRequest:
        """Updates a Leave Request record (Draft status only)."""
        req_obj = await self.repository.get_by_id(self.db, id)
        if not req_obj or req_obj.is_deleted:
            raise ApnaERPException(
                message=f"Leave request with ID '{id}' not found.",
                status_code=404,
                error_code="LEAVE_REQUEST_NOT_FOUND",
            )

        if req_obj.status != "Draft":
            raise ApnaERPException(
                message=f"Leave request in '{req_obj.status}' status cannot be modified. Only 'Draft' requests can be edited.",
                status_code=400,
                error_code="CANNOT_EDIT_NON_DRAFT_REQUEST",
            )

        employee = await self.employee_repo.get_by_id(self.db, req_obj.employee_id)
        leave_type = await self.leave_type_repo.get_by_id(self.db, req_obj.leave_type_id)

        start_date = data.start_date if data.start_date is not None else req_obj.start_date
        end_date = data.end_date if data.end_date is not None else req_obj.end_date
        is_half_day = data.is_half_day if data.is_half_day is not None else req_obj.is_half_day

        total_days = await self.calculate_working_days(start_date, end_date, is_half_day=is_half_day)
        await self._validate_leave_policies(
            employee=employee,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            is_half_day=is_half_day,
            exclude_request_id=req_obj.id,
        )

        update_dict = data.model_dump(exclude_unset=True)
        update_dict["total_days"] = total_days

        updated = await self.repository.update(self.db, db_obj=req_obj, obj_in=update_dict)
        await self._invalidate_cache(updated.employee_id, updated.id)

        if current_user:
            await log_audit(
                self.db,
                action="LEAVE_REQUEST_UPDATE",
                entity_type="LeaveRequest",
                entity_id=updated.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"status": "Draft"},
                new_data={"start_date": str(updated.start_date), "end_date": str(updated.end_date), "total_days": updated.total_days},
                status_code=200,
            )

        return updated

    async def submit_leave_request(
        self,
        id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> LeaveRequest:
        """Transitions Leave Request from 'Draft' -> 'Pending' and triggers manager alert."""
        req_obj = await self.repository.get_by_id(self.db, id)
        if not req_obj or req_obj.is_deleted:
            raise ApnaERPException(
                message=f"Leave request with ID '{id}' not found.",
                status_code=404,
                error_code="LEAVE_REQUEST_NOT_FOUND",
            )

        if req_obj.status != "Draft":
            raise ApnaERPException(
                message=f"Cannot submit leave request in '{req_obj.status}' status. Must be 'Draft'.",
                status_code=400,
                error_code="INVALID_WORKFLOW_TRANSITION",
            )

        # Re-validate policies upon submission
        employee = await self.employee_repo.get_by_id(self.db, req_obj.employee_id)
        leave_type = await self.leave_type_repo.get_by_id(self.db, req_obj.leave_type_id)
        await self._validate_leave_policies(
            employee=employee,
            leave_type=leave_type,
            start_date=req_obj.start_date,
            end_date=req_obj.end_date,
            total_days=req_obj.total_days,
            is_half_day=req_obj.is_half_day,
            exclude_request_id=req_obj.id,
        )

        req_obj.status = "Pending"
        req_obj.submitted_at = datetime.datetime.now(datetime.timezone.utc)

        await self.db.commit()
        await self.db.refresh(req_obj)
        await self._invalidate_cache(req_obj.employee_id, req_obj.id)

        if current_user:
            await log_audit(
                self.db,
                action="LEAVE_REQUEST_SUBMIT",
                entity_type="LeaveRequest",
                entity_id=req_obj.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"status": "Draft"},
                new_data={"status": "Pending", "submitted_at": req_obj.submitted_at.isoformat()},
                status_code=200,
            )

        try:
            send_leave_request_notification_task.delay(
                event_type="SUBMITTED",
                request_id=str(req_obj.id),
                employee_id=str(req_obj.employee_id),
                leave_type_id=str(req_obj.leave_type_id),
                start_date=str(req_obj.start_date),
                end_date=str(req_obj.end_date),
                total_days=req_obj.total_days,
                status="Pending",
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for LeaveRequest submit: {exc}")

        return req_obj

    async def approve_leave_request(
        self,
        id: uuid.UUID,
        data: LeaveRequestReviewRequest,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> LeaveRequest:
        """Transitions Leave Request from 'Pending' -> 'Approved' and updates LeaveBalance."""
        req_obj = await self.repository.get_by_id(self.db, id)
        if not req_obj or req_obj.is_deleted:
            raise ApnaERPException(
                message=f"Leave request with ID '{id}' not found.",
                status_code=404,
                error_code="LEAVE_REQUEST_NOT_FOUND",
            )

        if req_obj.status != "Pending":
            raise ApnaERPException(
                message=f"Cannot approve leave request in '{req_obj.status}' status. Must be 'Pending'.",
                status_code=400,
                error_code="INVALID_WORKFLOW_TRANSITION",
            )

        leave_type = await self.leave_type_repo.get_by_id(self.db, req_obj.leave_type_id)
        balance = await self.balance_repo.get_by_employee_type_year(
            self.db,
            employee_id=req_obj.employee_id,
            leave_type_id=req_obj.leave_type_id,
            leave_year=req_obj.start_date.year,
        )

        if not balance and not leave_type.allow_negative_balance:
            raise ApnaERPException(
                message=f"No leave balance record found for year {req_obj.start_date.year}.",
                status_code=400,
                error_code="INSUFFICIENT_LEAVE_BALANCE",
            )

        if balance:
            if balance.remaining_days < req_obj.total_days and not leave_type.allow_negative_balance:
                raise ApnaERPException(
                    message=f"Insufficient leave balance ({balance.remaining_days} days available, {req_obj.total_days} days required).",
                    status_code=400,
                    error_code="INSUFFICIENT_LEAVE_BALANCE",
                )
            # Reserve & update balance availed days
            balance.availed_days = round(balance.availed_days + req_obj.total_days, 2)
            balance.remaining_days = balance.calculate_remaining_days()

        now = datetime.datetime.now(datetime.timezone.utc)
        req_obj.status = "Approved"
        req_obj.reviewed_at = now
        req_obj.reviewed_by = current_user.id if current_user else None
        req_obj.reviewer_comments = data.reviewer_comments

        await self.db.commit()
        await self.db.refresh(req_obj)
        await self._invalidate_cache(req_obj.employee_id, req_obj.id)

        if current_user:
            await log_audit(
                self.db,
                action="LEAVE_REQUEST_APPROVE",
                entity_type="LeaveRequest",
                entity_id=req_obj.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"status": "Pending"},
                new_data={
                    "status": "Approved",
                    "reviewed_by": str(current_user.id),
                    "reviewer_comments": data.reviewer_comments,
                },
                status_code=200,
            )

        try:
            send_leave_request_notification_task.delay(
                event_type="APPROVED",
                request_id=str(req_obj.id),
                employee_id=str(req_obj.employee_id),
                leave_type_id=str(req_obj.leave_type_id),
                start_date=str(req_obj.start_date),
                end_date=str(req_obj.end_date),
                total_days=req_obj.total_days,
                status="Approved",
                reviewer_id=str(current_user.id) if current_user else None,
                comments=data.reviewer_comments,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for LeaveRequest approve: {exc}")

        return req_obj

    async def reject_leave_request(
        self,
        id: uuid.UUID,
        data: LeaveRequestReviewRequest,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> LeaveRequest:
        """Transitions Leave Request from 'Pending' -> 'Rejected' (Terminal state)."""
        req_obj = await self.repository.get_by_id(self.db, id)
        if not req_obj or req_obj.is_deleted:
            raise ApnaERPException(
                message=f"Leave request with ID '{id}' not found.",
                status_code=404,
                error_code="LEAVE_REQUEST_NOT_FOUND",
            )

        if req_obj.status != "Pending":
            raise ApnaERPException(
                message=f"Cannot reject leave request in '{req_obj.status}' status. Must be 'Pending'.",
                status_code=400,
                error_code="INVALID_WORKFLOW_TRANSITION",
            )

        now = datetime.datetime.now(datetime.timezone.utc)
        req_obj.status = "Rejected"
        req_obj.reviewed_at = now
        req_obj.reviewed_by = current_user.id if current_user else None
        req_obj.reviewer_comments = data.reviewer_comments

        await self.db.commit()
        await self.db.refresh(req_obj)
        await self._invalidate_cache(req_obj.employee_id, req_obj.id)

        if current_user:
            await log_audit(
                self.db,
                action="LEAVE_REQUEST_REJECT",
                entity_type="LeaveRequest",
                entity_id=req_obj.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"status": "Pending"},
                new_data={
                    "status": "Rejected",
                    "reviewed_by": str(current_user.id),
                    "reviewer_comments": data.reviewer_comments,
                },
                status_code=200,
            )

        try:
            send_leave_request_notification_task.delay(
                event_type="REJECTED",
                request_id=str(req_obj.id),
                employee_id=str(req_obj.employee_id),
                leave_type_id=str(req_obj.leave_type_id),
                start_date=str(req_obj.start_date),
                end_date=str(req_obj.end_date),
                total_days=req_obj.total_days,
                status="Rejected",
                reviewer_id=str(current_user.id) if current_user else None,
                comments=data.reviewer_comments,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for LeaveRequest reject: {exc}")

        return req_obj

    async def cancel_leave_request(
        self,
        id: uuid.UUID,
        data: LeaveRequestCancelRequest,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> LeaveRequest:
        """Transitions Leave Request -> 'Cancelled'. Restores leave balance if previously Approved."""
        req_obj = await self.repository.get_by_id(self.db, id)
        if not req_obj or req_obj.is_deleted:
            raise ApnaERPException(
                message=f"Leave request with ID '{id}' not found.",
                status_code=404,
                error_code="LEAVE_REQUEST_NOT_FOUND",
            )

        if req_obj.status in ("Rejected", "Cancelled", "Completed"):
            raise ApnaERPException(
                message=f"Cannot cancel leave request in terminal '{req_obj.status}' status.",
                status_code=400,
                error_code="INVALID_WORKFLOW_TRANSITION",
            )

        today = datetime.date.today()
        if req_obj.status == "Approved" and today >= req_obj.start_date:
            raise ApnaERPException(
                message=f"Approved leave requests can only be cancelled prior to the start date ({req_obj.start_date}).",
                status_code=400,
                error_code="CANNOT_CANCEL_STARTED_LEAVE",
            )

        prev_status = req_obj.status
        # If cancelling an Approved leave, restore leave balance
        if prev_status == "Approved":
            balance = await self.balance_repo.get_by_employee_type_year(
                self.db,
                employee_id=req_obj.employee_id,
                leave_type_id=req_obj.leave_type_id,
                leave_year=req_obj.start_date.year,
            )
            if balance:
                balance.availed_days = max(0.0, round(balance.availed_days - req_obj.total_days, 2))
                balance.remaining_days = balance.calculate_remaining_days()

        req_obj.status = "Cancelled"
        if data.reason:
            req_obj.reviewer_comments = f"Cancelled: {data.reason}"

        await self.db.commit()
        await self.db.refresh(req_obj)
        await self._invalidate_cache(req_obj.employee_id, req_obj.id)

        if current_user:
            await log_audit(
                self.db,
                action="LEAVE_REQUEST_CANCEL",
                entity_type="LeaveRequest",
                entity_id=req_obj.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"status": prev_status},
                new_data={"status": "Cancelled", "reason": data.reason},
                status_code=200,
            )

        try:
            send_leave_request_notification_task.delay(
                event_type="CANCELLED",
                request_id=str(req_obj.id),
                employee_id=str(req_obj.employee_id),
                leave_type_id=str(req_obj.leave_type_id),
                start_date=str(req_obj.start_date),
                end_date=str(req_obj.end_date),
                total_days=req_obj.total_days,
                status="Cancelled",
                comments=data.reason,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for LeaveRequest cancel: {exc}")

        return req_obj

    async def get_leave_request_by_id(self, id: uuid.UUID) -> LeaveRequest:
        """Retrieves a single Leave Request by ID."""
        req_obj = await self.repository.get_by_id(self.db, id)
        if not req_obj or req_obj.is_deleted:
            raise ApnaERPException(
                message=f"Leave request with ID '{id}' not found.",
                status_code=404,
                error_code="LEAVE_REQUEST_NOT_FOUND",
            )
        return req_obj

    async def get_employee_leave_requests(
        self,
        employee_id: uuid.UUID,
        status: Optional[str],
        params: PaginationParams,
    ) -> PaginatedResult[LeaveRequest]:
        """Retrieves paginated leave requests for a specific employee."""
        employee = await self.employee_repo.get_by_id(self.db, employee_id)
        if not employee or employee.is_deleted:
            raise ApnaERPException(
                message=f"Employee with ID '{employee_id}' not found.",
                status_code=404,
                error_code="EMPLOYEE_NOT_FOUND",
            )
        return await self.repository.get_employee_requests_paginated(
            self.db, employee_id=employee_id, status=status, params=params
        )

    async def list_leave_requests(
        self,
        params: PaginationParams,
        filters: Optional[List[FilterCriterion]] = None,
    ) -> PaginatedResult[LeaveRequest]:
        """Retrieves paginated list of all Leave Requests."""
        return await self.repository.get_multi_paginated(
            self.db, params=params, filters=filters
        )
