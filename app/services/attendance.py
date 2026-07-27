import datetime
import logging
from typing import Any, List, Optional
import uuid
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import ApnaERPException
from app.models.attendance import Attendance
from app.models.user import User
from app.repositories.attendance import attendance_repository
from app.repositories.employee import employee_repository
from app.repositories.holiday import holiday_repository
from app.repositories.hr_configuration import hr_configuration_repository
from app.repositories.shift import shift_repository
from app.schemas.attendance import (
    AttendanceCorrectionRequest,
    AttendanceLockRequest,
    AttendanceResponse,
    AttendanceSummary,
    CheckInRequest,
    CheckOutRequest,
)
from app.services.attendance_engine import AttendanceEngine
from app.tasks.attendance_tasks import send_attendance_notification_task
from app.utils.audit import log_audit
from app.utils.filters import FilterCriterion, FilterOperator
from app.utils.pagination import PaginatedResult, PaginationParams

logger = logging.getLogger("app.services.attendance")

CACHE_TODAY_KEY = "attendance:today"


class AttendanceService:
    """
    Service Layer for Enterprise Attendance Operations.
    Coordinates database repositories, AttendanceEngine calculation rules, Redis caching,
    audit logging, and Celery notification tasks.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = attendance_repository
        self.employee_repo = employee_repository
        self.shift_repo = shift_repository
        self.holiday_repo = holiday_repository
        self.hr_config_repo = hr_configuration_repository
        self.engine = AttendanceEngine()

    async def _invalidate_caches(self, employee_id: Optional[uuid.UUID] = None) -> None:
        """Invalidates Redis attendance caches."""
        try:
            await redis_manager.delete(CACHE_TODAY_KEY)
            if employee_id:
                # Pattern invalidation for monthly employee caches if needed
                pass
            logger.info("[AttendanceService] Invalidated Redis caches.")
        except Exception as e:
            logger.warning(f"[AttendanceService] Redis cache invalidation error: {e}")

    async def get_attendance_by_id(
        self, attendance_id: uuid.UUID, include_deleted: bool = False
    ) -> Attendance:
        """Retrieves attendance record by UUID."""
        attendance = await self.repository.get_by_id(self.db, attendance_id, include_deleted=include_deleted)
        if not attendance:
            raise ApnaERPException(
                message=f"Attendance record with ID '{attendance_id}' not found.",
                status_code=404,
                error_code="ATTENDANCE_NOT_FOUND",
            )
        return attendance

    async def get_attendances(
        self,
        page: int = 1,
        page_size: int = 100,
        search: Optional[str] = None,
        employee_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
        attendance_status: Optional[str] = None,
        is_locked: Optional[bool] = None,
    ) -> PaginatedResult[Attendance]:
        """Retrieves paginated attendance records with search and filters."""
        params = PaginationParams(page=page, page_size=page_size)
        filters = []

        if employee_id:
            filters.append(FilterCriterion(field="employee_id", operator=FilterOperator.EQ, value=employee_id))
        if start_date:
            filters.append(FilterCriterion(field="attendance_date", operator=FilterOperator.GTE, value=start_date))
        if end_date:
            filters.append(FilterCriterion(field="attendance_date", operator=FilterOperator.LTE, value=end_date))
        if attendance_status:
            filters.append(FilterCriterion(field="attendance_status", operator=FilterOperator.EQ, value=attendance_status))
        if is_locked is not None:
            filters.append(FilterCriterion(field="is_locked", operator=FilterOperator.EQ, value=is_locked))

        return await self.repository.get_multi_paginated(
            self.db,
            params=params,
            filters=filters,
            search_term=search,
            search_fields=["attendance_status", "correction_notes"],
        )

    async def get_employee_monthly_attendance(
        self, employee_id: uuid.UUID, year: int, month: int
    ) -> List[Attendance]:
        """Retrieves monthly attendance records for an employee."""
        employee = await self.employee_repo.get_by_id(self.db, employee_id)
        if not employee:
            raise ApnaERPException(
                message=f"Employee with ID '{employee_id}' not found.",
                status_code=404,
                error_code="EMPLOYEE_NOT_FOUND",
            )
        return await self.repository.get_monthly_attendance(self.db, employee_id, year, month)

    async def get_summary(
        self,
        start_date: datetime.date,
        end_date: datetime.date,
        department_id: Optional[uuid.UUID] = None,
        employee_id: Optional[uuid.UUID] = None,
    ) -> AttendanceSummary:
        """Calculates attendance summary metrics."""
        return await self.repository.get_summary(
            self.db, start_date=start_date, end_date=end_date, department_id=department_id, employee_id=employee_id
        )

    async def process_check_in(
        self,
        data: CheckInRequest,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> Attendance:
        """Processes employee check-in."""
        # 1. Employee Validation
        employee = await self.employee_repo.get_by_id(self.db, data.employee_id)
        if not employee or employee.is_deleted:
            raise ApnaERPException(
                message=f"Employee with ID '{data.employee_id}' not found.",
                status_code=404,
                error_code="EMPLOYEE_NOT_FOUND",
            )
        if not employee.is_active:
            raise ApnaERPException(
                message=f"Employee '{employee.first_name} {employee.last_name}' is inactive.",
                status_code=400,
                error_code="EMPLOYEE_INACTIVE",
            )

        # 2. Check-in Timestamp & Target Date
        check_in_dt = data.check_in_time or datetime.datetime.now(datetime.timezone.utc)
        target_date = check_in_dt.date()

        # 3. Shift & Policy Lookups
        shift = None
        shift_id_to_use = data.shift_id or employee.shift_id
        if shift_id_to_use:
            shift = await self.shift_repo.get_by_id(self.db, shift_id_to_use)

        hr_config = await self.hr_config_repo.get_active_configuration(self.db)
        holidays = await self.holiday_repo.get_holidays_by_date(
            self.db, target_date=target_date, country=getattr(employee, "country", "India")
        )
        is_holiday = len(holidays) > 0

        # 4. Check for Existing Attendance Record on target_date
        existing = await self.repository.get_by_employee_and_date(self.db, employee.id, target_date)
        if existing:
            if existing.is_locked:
                raise ApnaERPException(
                    message=f"Attendance record for {target_date} is locked for payroll.",
                    status_code=400,
                    error_code="ATTENDANCE_LOCKED",
                )
            # Update check-in time and re-evaluate
            existing.check_in_time = check_in_dt
            if shift:
                existing.shift_id = shift.id

            calc = self.engine.calculate_attendance(
                attendance_date=target_date,
                check_in_time=existing.check_in_time,
                check_out_time=existing.check_out_time,
                break_minutes=existing.break_minutes,
                shift=shift,
                hr_config=hr_config,
                is_holiday=is_holiday,
            )

            existing.attendance_status = calc.attendance_status
            existing.worked_minutes = calc.worked_minutes
            existing.expected_minutes = calc.expected_minutes
            existing.late_minutes = calc.late_minutes
            existing.early_departure_minutes = calc.early_departure_minutes

            attendance_obj = await self.repository.update(self.db, db_obj=existing, obj_in={})
        else:
            # Calculate new attendance
            calc = self.engine.calculate_attendance(
                attendance_date=target_date,
                check_in_time=check_in_dt,
                check_out_time=None,
                break_minutes=0,
                shift=shift,
                hr_config=hr_config,
                is_holiday=is_holiday,
            )

            new_attendance = Attendance(
                employee_id=employee.id,
                attendance_date=target_date,
                shift_id=shift.id if shift else None,
                check_in_time=check_in_dt,
                check_out_time=None,
                break_minutes=0,
                worked_minutes=calc.worked_minutes,
                expected_minutes=calc.expected_minutes,
                late_minutes=calc.late_minutes,
                early_departure_minutes=calc.early_departure_minutes,
                attendance_status=calc.attendance_status,
                is_locked=False,
            )

            self.db.add(new_attendance)
            await self.db.commit()
            await self.db.refresh(new_attendance)
            attendance_obj = new_attendance

        await self._invalidate_caches(employee.id)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="ATTENDANCE_CHECKIN",
            entity_type="Attendance",
            entity_id=attendance_obj.id,
            user_id=user_id,
            username=username,
            new_data={
                "employee_id": str(employee.id),
                "attendance_date": str(target_date),
                "check_in_time": check_in_dt.isoformat(),
                "attendance_status": attendance_obj.attendance_status,
                "late_minutes": attendance_obj.late_minutes,
            },
            status_code=200,
        )

        if attendance_obj.attendance_status == "Late":
            try:
                send_attendance_notification_task.delay(
                    event_type="LATE_ARRIVAL",
                    attendance_id=str(attendance_obj.id),
                    employee_id=str(employee.id),
                    attendance_date=str(target_date),
                    attendance_status=attendance_obj.attendance_status,
                    details={"late_minutes": attendance_obj.late_minutes},
                )
            except Exception as exc:
                logger.warning(f"Failed to dispatch Celery attendance notification task: {exc}")

        fresh = await self.repository.get_by_id(self.db, attendance_obj.id)
        return fresh if fresh else attendance_obj

    async def process_check_out(
        self,
        data: CheckOutRequest,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> Attendance:
        """Processes employee check-out."""
        # 1. Employee Validation
        employee = await self.employee_repo.get_by_id(self.db, data.employee_id)
        if not employee or employee.is_deleted:
            raise ApnaERPException(
                message=f"Employee with ID '{data.employee_id}' not found.",
                status_code=404,
                error_code="EMPLOYEE_NOT_FOUND",
            )

        # 2. Check-out Timestamp & Target Date
        check_out_dt = data.check_out_time or datetime.datetime.now(datetime.timezone.utc)
        target_date = check_out_dt.date()

        # Look for existing record on target_date or open check-in record
        existing = await self.repository.get_by_employee_and_date(self.db, employee.id, target_date)
        if not existing:
            # Check previous date for overnight shifts
            prev_date = target_date - datetime.timedelta(days=1)
            prev_existing = await self.repository.get_by_employee_and_date(self.db, employee.id, prev_date)
            if prev_existing and prev_existing.check_in_time and not prev_existing.check_out_time:
                existing = prev_existing

        if not existing:
            raise ApnaERPException(
                message=f"No open check-in record found for employee '{employee.first_name} {employee.last_name}'.",
                status_code=404,
                error_code="ATTENDANCE_NOT_FOUND",
            )

        if existing.is_locked:
            raise ApnaERPException(
                message=f"Attendance record for {existing.attendance_date} is locked for payroll.",
                status_code=400,
                error_code="ATTENDANCE_LOCKED",
            )

        # 3. Shift & Policy Lookups
        shift = None
        shift_id_to_use = existing.shift_id or employee.shift_id
        if shift_id_to_use:
            shift = await self.shift_repo.get_by_id(self.db, shift_id_to_use)

        hr_config = await self.hr_config_repo.get_active_configuration(self.db)
        holidays = await self.holiday_repo.get_holidays_by_date(
            self.db, target_date=existing.attendance_date, country=getattr(employee, "country", "India")
        )
        is_holiday = len(holidays) > 0

        # 4. Engine Evaluation
        existing.check_out_time = check_out_dt
        existing.break_minutes = data.break_minutes

        calc = self.engine.calculate_attendance(
            attendance_date=existing.attendance_date,
            check_in_time=existing.check_in_time,
            check_out_time=existing.check_out_time,
            break_minutes=existing.break_minutes,
            shift=shift,
            hr_config=hr_config,
            is_holiday=is_holiday,
        )

        existing.attendance_status = calc.attendance_status
        existing.worked_minutes = calc.worked_minutes
        existing.expected_minutes = calc.expected_minutes
        existing.late_minutes = calc.late_minutes
        existing.early_departure_minutes = calc.early_departure_minutes

        attendance_obj = await self.repository.update(self.db, db_obj=existing, obj_in={})
        await self._invalidate_caches(employee.id)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="ATTENDANCE_CHECKOUT",
            entity_type="Attendance",
            entity_id=attendance_obj.id,
            user_id=user_id,
            username=username,
            new_data={
                "employee_id": str(employee.id),
                "attendance_date": str(existing.attendance_date),
                "check_out_time": check_out_dt.isoformat(),
                "attendance_status": attendance_obj.attendance_status,
                "worked_minutes": attendance_obj.worked_minutes,
            },
            status_code=200,
        )

        fresh = await self.repository.get_by_id(self.db, attendance_obj.id)
        return fresh if fresh else attendance_obj

    async def correct_attendance(
        self,
        data: AttendanceCorrectionRequest,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> Attendance:
        """Manually corrects an attendance record."""
        attendance = await self.get_attendance_by_id(data.attendance_id)
        if attendance.is_locked:
            raise ApnaERPException(
                message=f"Attendance record for {attendance.attendance_date} is locked for payroll.",
                status_code=400,
                error_code="ATTENDANCE_LOCKED",
            )

        employee = await self.employee_repo.get_by_id(self.db, attendance.employee_id)
        shift = None
        if attendance.shift_id:
            shift = await self.shift_repo.get_by_id(self.db, attendance.shift_id)

        hr_config = await self.hr_config_repo.get_active_configuration(self.db)
        holidays = await self.holiday_repo.get_holidays_by_date(
            self.db, target_date=attendance.attendance_date, country=getattr(employee, "country", "India") if employee else "India"
        )
        is_holiday = len(holidays) > 0

        # Apply corrections
        if data.check_in_time is not None:
            attendance.check_in_time = data.check_in_time
        if data.check_out_time is not None:
            attendance.check_out_time = data.check_out_time
        if data.break_minutes is not None:
            attendance.break_minutes = data.break_minutes

        calc = self.engine.calculate_attendance(
            attendance_date=attendance.attendance_date,
            check_in_time=attendance.check_in_time,
            check_out_time=attendance.check_out_time,
            break_minutes=attendance.break_minutes,
            shift=shift,
            hr_config=hr_config,
            is_holiday=is_holiday,
        )

        attendance.worked_minutes = calc.worked_minutes
        attendance.expected_minutes = calc.expected_minutes
        attendance.late_minutes = calc.late_minutes
        attendance.early_departure_minutes = calc.early_departure_minutes

        if data.attendance_status:
            attendance.attendance_status = data.attendance_status.value
        else:
            attendance.attendance_status = calc.attendance_status

        attendance.is_manual_correction = True
        attendance.corrected_by_user_id = current_user.id if current_user else None
        attendance.correction_notes = data.correction_notes

        updated_attendance = await self.repository.update(self.db, db_obj=attendance, obj_in={})
        await self._invalidate_caches(attendance.employee_id)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="ATTENDANCE_CORRECT",
            entity_type="Attendance",
            entity_id=updated_attendance.id,
            user_id=user_id,
            username=username,
            new_data={
                "correction_notes": data.correction_notes,
                "attendance_status": updated_attendance.attendance_status,
                "worked_minutes": updated_attendance.worked_minutes,
            },
            status_code=200,
        )

        try:
            send_attendance_notification_task.delay(
                event_type="ATTENDANCE_CORRECTED",
                attendance_id=str(updated_attendance.id),
                employee_id=str(updated_attendance.employee_id),
                attendance_date=str(updated_attendance.attendance_date),
                attendance_status=updated_attendance.attendance_status,
                details={"correction_notes": data.correction_notes},
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery attendance notification task: {exc}")

        fresh = await self.repository.get_by_id(self.db, updated_attendance.id)
        return fresh if fresh else updated_attendance

    async def lock_attendance(
        self,
        data: AttendanceLockRequest,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> List[Attendance]:
        """Locks attendance records for payroll processing."""
        records_to_lock: List[Attendance] = []

        if data.attendance_ids:
            for att_id in data.attendance_ids:
                rec = await self.repository.get_by_id(self.db, att_id)
                if rec:
                    records_to_lock.append(rec)
        elif data.start_date and data.end_date:
            summary_query = await self.repository.get_multi_paginated(
                self.db,
                params=PaginationParams(page=1, page_size=10000),
                filters=[
                    FilterCriterion(field="attendance_date", operator=FilterOperator.GTE, value=data.start_date),
                    FilterCriterion(field="attendance_date", operator=FilterOperator.LTE, value=data.end_date),
                ],
            )
            records_to_lock = summary_query.items

        locked_records = []
        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        for rec in records_to_lock:
            if not rec.is_locked:
                rec.is_locked = True
                updated = await self.repository.update(self.db, db_obj=rec, obj_in={})
                locked_records.append(updated)

                await log_audit(
                    self.db,
                    action="ATTENDANCE_LOCK",
                    entity_type="Attendance",
                    entity_id=updated.id,
                    user_id=user_id,
                    username=username,
                    status_code=200,
                )

        await self._invalidate_caches()
        return locked_records
