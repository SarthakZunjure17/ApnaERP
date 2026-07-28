import datetime
import logging
from typing import List, Optional
import uuid
from fastapi import Request
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import ApnaERPException
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.employee_compensation import EmployeeCompensation
from app.models.leave_request import LeaveRequest
from app.models.payroll_period import PayrollPeriod, PayrollRecord, PayrollRecordComponent
from app.models.salary_structure import SalaryStructureComponent
from app.models.user import User
from app.repositories.employee import employee_repository
from app.repositories.employee_compensation import employee_compensation_repository
from app.repositories.payroll_period import (
    payroll_period_repository,
    payroll_record_component_repository,
    payroll_record_repository,
)
from app.schemas.payroll_period import (
    PayrollPeriodCreate,
    PayrollSummaryResponse,
)
from app.tasks.payroll_engine_tasks import send_payroll_notification_task
from app.utils.audit import log_audit
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginatedResult, PaginationParams

logger = logging.getLogger("app.services.payroll_engine")

CACHE_PREFIX = "payroll"


class PayrollEngineService:
    """
    Service layer for the Enterprise Payroll Processing Engine.
    Integrates Employee Compensation, Salary Structures, Attendance logs, and Approved Leave requests
    to calculate proration, earnings, deductions, gross salary, and net salary.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.period_repository = payroll_period_repository
        self.record_repository = payroll_record_repository
        self.record_component_repository = payroll_record_component_repository
        self.employee_repository = employee_repository
        self.compensation_repository = employee_compensation_repository

    async def _invalidate_cache(self, period_id: Optional[uuid.UUID] = None):
        """Clears Payroll Engine Redis caches."""
        try:
            await redis_manager.delete_pattern(f"{CACHE_PREFIX}:*")
            if period_id:
                await redis_manager.delete(
                    f"{CACHE_PREFIX}:period:{period_id}",
                    f"{CACHE_PREFIX}:summary:{period_id}"
                )
        except Exception as exc:
            logger.warning(f"Failed to clear Redis payroll cache: {exc}")

    async def create_payroll_period(
        self,
        data: PayrollPeriodCreate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> PayrollPeriod:
        """Creates a new Payroll Period cycle."""
        existing_code = await self.period_repository.get_by_code(self.db, data.period_code)
        if existing_code:
            raise ApnaERPException(
                message=f"Payroll period with code '{data.period_code}' already exists.",
                status_code=400,
                error_code="DUPLICATE_PERIOD_CODE",
            )

        if data.end_date < data.start_date:
            raise ApnaERPException(
                message="Period end date cannot be earlier than start date.",
                status_code=400,
                error_code="INVALID_DATE_RANGE",
            )

        period_dict = data.model_dump()
        period_dict["status"] = "Draft"

        period = await self.period_repository.create(self.db, obj_in=period_dict)
        await self.db.commit()
        await self.db.refresh(period)
        await self._invalidate_cache(period.id)

        if current_user:
            await log_audit(
                self.db,
                action="PAYROLL_PERIOD_CREATE",
                entity_type="PayrollPeriod",
                entity_id=period.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=None,
                new_data={
                    "period_code": period.period_code,
                    "start_date": str(period.start_date),
                    "end_date": str(period.end_date),
                    "status": "Draft",
                },
                status_code=201,
            )

        return period

    async def generate_payroll(
        self,
        period_id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> List[PayrollRecord]:
        """Generates payroll records for all eligible employees in the specified payroll period."""
        period = await self.period_repository.get_by_id(self.db, period_id)
        if not period:
            raise ApnaERPException(
                message=f"Payroll period with ID '{period_id}' not found.",
                status_code=404,
                error_code="PERIOD_NOT_FOUND",
            )

        if period.status == "Locked":
            raise ApnaERPException(
                message=f"Cannot generate payroll for locked period '{period.period_code}'.",
                status_code=400,
                error_code="PERIOD_LOCKED",
            )

        period.status = "Processing"
        await self.db.commit()

        # Query all active employees
        emp_query = select(Employee).where(Employee.is_deleted.is_(False))
        emp_res = await self.db.execute(emp_query)
        employees = emp_res.unique().scalars().all()

        generated_records: List[PayrollRecord] = []
        working_days = (period.end_date - period.start_date).days + 1

        for emp in employees:
            # 1. Fetch Active Compensation
            comp = await self.compensation_repository.get_active_compensation(self.db, emp.id)
            if not comp or comp.is_deleted:
                logger.info(f"Skipping payroll generation for employee '{emp.employee_code}': No active compensation.")
                continue

            # 2. Fetch Attendance Present Days
            att_query = select(Attendance).where(
                Attendance.employee_id == emp.id,
                Attendance.attendance_date >= period.start_date,
                Attendance.attendance_date <= period.end_date,
                Attendance.is_deleted.is_(False),
            )
            att_res = await self.db.execute(att_query)
            attendance_logs = att_res.unique().scalars().all()

            present_days = 0.0
            for att in attendance_logs:
                if att.status in ["Present", "Late"]:
                    present_days += 1.0
                elif att.status == "Half-Day":
                    present_days += 0.5

            # 3. Fetch Approved Leave Requests
            leave_query = select(LeaveRequest).where(
                LeaveRequest.employee_id == emp.id,
                LeaveRequest.status == "Approved",
                LeaveRequest.start_date <= period.end_date,
                LeaveRequest.end_date >= period.start_date,
                LeaveRequest.is_deleted.is_(False),
            )
            leave_res = await self.db.execute(leave_query)
            leave_requests = leave_res.unique().scalars().all()

            paid_leave_days = 0.0
            unpaid_leave_days = 0.0
            for l_req in leave_requests:
                # Count overlapping leave days
                l_start = max(l_req.start_date, period.start_date)
                l_end = min(l_req.end_date, period.end_date)
                l_days = float(l_req.leave_days or ((l_end - l_start).days + 1))
                if l_req.leave_type and l_req.leave_type.is_paid:
                    paid_leave_days += l_days
                else:
                    unpaid_leave_days += l_days

            leave_days = paid_leave_days + unpaid_leave_days

            # Fallback for initial demo setup: if no attendance recorded yet, assume 100% attendance
            if present_days == 0.0 and paid_leave_days == 0.0 and unpaid_leave_days == 0.0:
                present_days = float(working_days)

            # Proration Ratio Calculation
            proration_ratio = min(1.0, max(0.0, (present_days + paid_leave_days) / float(working_days))) if working_days > 0 else 1.0

            monthly_gross = float(comp.monthly_gross_salary)

            # 4. Fetch Salary Structure Components
            struct = comp.salary_structure
            total_earnings = 0.0
            total_deductions = 0.0
            record_components: List[dict] = []

            if struct and struct.components:
                for struct_comp in struct.components:
                    sal_comp = struct_comp.component
                    if not sal_comp or not sal_comp.is_active or sal_comp.is_deleted:
                        continue

                    # Baseline amount
                    base_val = float(struct_comp.component_value) if struct_comp.component_value > 0 else float(sal_comp.default_value)
                    if base_val == 0.0 and sal_comp.calculation_method == "Percentage" and sal_comp.percentage_value:
                        base_val = round(monthly_gross * (float(sal_comp.percentage_value) / 100.0), 2)
                    elif base_val == 0.0:
                        base_val = monthly_gross

                    calc_amount = round(base_val * proration_ratio, 2)

                    if sal_comp.type == "Earning":
                        total_earnings += calc_amount
                    elif sal_comp.type == "Deduction":
                        total_deductions += calc_amount

                    record_components.append({
                        "salary_component_id": sal_comp.id,
                        "component_name": sal_comp.name,
                        "component_type": sal_comp.type,
                        "amount": calc_amount,
                    })

            # If structure components weren't configured, fallback to gross salary
            if total_earnings == 0.0:
                total_earnings = round(monthly_gross * proration_ratio, 2)

            gross_salary = round(total_earnings, 2)
            net_salary = max(0.0, round(gross_salary - total_deductions, 2))

            # 5. Build Record Components
            rc_list = [
                PayrollRecordComponent(
                    salary_component_id=rc_data["salary_component_id"],
                    component_name=rc_data["component_name"],
                    component_type=rc_data["component_type"],
                    amount=rc_data["amount"],
                )
                for rc_data in record_components
            ]

            # 6. Save or Update PayrollRecord
            existing_record = await self.record_repository.get_by_period_and_employee(self.db, period_id, emp.id)
            if existing_record:
                await self.db.execute(
                    delete(PayrollRecordComponent).where(
                        PayrollRecordComponent.payroll_record_id == existing_record.id
                    )
                )
                existing_record.employee_compensation_id = comp.id
                existing_record.working_days = working_days
                existing_record.present_days = present_days
                existing_record.leave_days = leave_days
                existing_record.paid_leave_days = paid_leave_days
                existing_record.unpaid_leave_days = unpaid_leave_days
                existing_record.gross_salary = gross_salary
                existing_record.total_earnings = total_earnings
                existing_record.total_deductions = total_deductions
                existing_record.net_salary = net_salary
                existing_record.status = "Calculated"
                existing_record.components = rc_list
                rec = existing_record
            else:
                rec = PayrollRecord(
                    payroll_period_id=period_id,
                    employee_id=emp.id,
                    employee_compensation_id=comp.id,
                    working_days=working_days,
                    present_days=present_days,
                    leave_days=leave_days,
                    paid_leave_days=paid_leave_days,
                    unpaid_leave_days=unpaid_leave_days,
                    overtime_hours=0.00,
                    gross_salary=gross_salary,
                    total_earnings=total_earnings,
                    total_deductions=total_deductions,
                    net_salary=net_salary,
                    status="Calculated",
                    components=rc_list,
                )
                self.db.add(rec)

            generated_records.append(rec)

        period.status = "Completed"
        await self.db.commit()
        await self._invalidate_cache(period_id)

        # Re-fetch generated records with eagerly loaded components
        final_records = await self.record_repository.get_records_by_period(self.db, period_id)
        total_net = sum(float(r.net_salary) for r in final_records)

        if current_user:
            await log_audit(
                self.db,
                action="PAYROLL_GENERATE",
                entity_type="PayrollPeriod",
                entity_id=period_id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"status": "Draft"},
                new_data={
                    "period_code": period.period_code,
                    "total_records": len(final_records),
                    "total_net_salary": total_net,
                    "status": "Completed",
                },
                status_code=200,
            )

        try:
            user_id_str = str(current_user.id) if current_user else "system"
            send_payroll_notification_task.delay(
                action="GENERATED",
                period_id=str(period_id),
                period_code=period.period_code,
                total_records=len(final_records),
                total_net_salary=total_net,
                status=period.status,
                performed_by_id=user_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for payroll generate: {exc}")

        return final_records

    async def approve_payroll(
        self,
        period_id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> PayrollPeriod:
        """Approves generated payroll records for a payroll period."""
        period = await self.period_repository.get_by_id(self.db, period_id)
        if not period:
            raise ApnaERPException(
                message=f"Payroll period with ID '{period_id}' not found.",
                status_code=404,
                error_code="PERIOD_NOT_FOUND",
            )

        if period.status == "Locked":
            raise ApnaERPException(
                message=f"Cannot approve locked period '{period.period_code}'.",
                status_code=400,
                error_code="PERIOD_LOCKED",
            )

        records = await self.record_repository.get_records_by_period(self.db, period_id)
        for rec in records:
            rec.status = "Approved"

        await self.db.commit()
        await self.db.refresh(period)
        await self._invalidate_cache(period_id)

        total_net = sum(float(r.net_salary) for r in records)

        if current_user:
            await log_audit(
                self.db,
                action="PAYROLL_APPROVE",
                entity_type="PayrollPeriod",
                entity_id=period_id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"status": period.status},
                new_data={"status": period.status, "records_approved": len(records)},
                status_code=200,
            )

        try:
            user_id_str = str(current_user.id) if current_user else "system"
            send_payroll_notification_task.delay(
                action="APPROVED",
                period_id=str(period_id),
                period_code=period.period_code,
                total_records=len(records),
                total_net_salary=total_net,
                status=period.status,
                performed_by_id=user_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for payroll approve: {exc}")

        return period

    async def lock_payroll_period(
        self,
        period_id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> PayrollPeriod:
        """Locks a payroll period against further modifications."""
        period = await self.period_repository.get_by_id(self.db, period_id)
        if not period:
            raise ApnaERPException(
                message=f"Payroll period with ID '{period_id}' not found.",
                status_code=404,
                error_code="PERIOD_NOT_FOUND",
            )

        prev_status = period.status
        period.status = "Locked"

        records = await self.record_repository.get_records_by_period(self.db, period_id)
        total_net = sum(float(r.net_salary) for r in records)

        await self.db.commit()
        await self.db.refresh(period)
        await self._invalidate_cache(period_id)

        if current_user:
            await log_audit(
                self.db,
                action="PAYROLL_LOCK",
                entity_type="PayrollPeriod",
                entity_id=period_id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data={"status": prev_status},
                new_data={"status": "Locked"},
                status_code=200,
            )

        try:
            user_id_str = str(current_user.id) if current_user else "system"
            send_payroll_notification_task.delay(
                action="LOCKED",
                period_id=str(period_id),
                period_code=period.period_code,
                total_records=len(records),
                total_net_salary=total_net,
                status="Locked",
                performed_by_id=user_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for payroll lock: {exc}")

        return period

    async def get_payroll_summary(self, period_id: uuid.UUID) -> PayrollSummaryResponse:
        """Retrieves summary metrics for a payroll period run."""
        period = await self.period_repository.get_by_id(self.db, period_id)
        if not period:
            raise ApnaERPException(
                message=f"Payroll period with ID '{period_id}' not found.",
                status_code=404,
                error_code="PERIOD_NOT_FOUND",
            )

        records = await self.record_repository.get_records_by_period(self.db, period_id)
        total_gross = sum(float(r.gross_salary) for r in records)
        total_earnings = sum(float(r.total_earnings) for r in records)
        total_deductions = sum(float(r.total_deductions) for r in records)
        total_net = sum(float(r.net_salary) for r in records)

        return PayrollSummaryResponse(
            payroll_period_id=period.id,
            period_code=period.period_code,
            total_employees=len(records),
            total_gross_salary=total_gross,
            total_earnings=total_earnings,
            total_deductions=total_deductions,
            total_net_salary=total_net,
            status=period.status,
        )

    async def get_payroll_record_by_id(self, record_id: uuid.UUID) -> PayrollRecord:
        """Retrieves a single PayrollRecord by ID."""
        record = await self.record_repository.get_by_id(self.db, record_id)
        if not record:
            raise ApnaERPException(
                message=f"Payroll record with ID '{record_id}' not found.",
                status_code=404,
                error_code="RECORD_NOT_FOUND",
            )
        return record

    async def get_employee_payroll_history(self, employee_id: uuid.UUID) -> List[PayrollRecord]:
        """Retrieves full payroll record history for an employee."""
        return await self.record_repository.get_employee_payroll_history(self.db, employee_id)

    async def list_payroll_periods(
        self, params: PaginationParams, filters: Optional[List[FilterCriterion]] = None
    ) -> PaginatedResult[PayrollPeriod]:
        """Retrieves a paginated list of Payroll Periods."""
        return await self.period_repository.get_multi_paginated(
            self.db, params=params, filters=filters
        )

    async def list_payroll_records(
        self, params: PaginationParams, filters: Optional[List[FilterCriterion]] = None
    ) -> PaginatedResult[PayrollRecord]:
        """Retrieves a paginated list of Payroll Records."""
        return await self.record_repository.get_multi_paginated(
            self.db, params=params, filters=filters
        )
