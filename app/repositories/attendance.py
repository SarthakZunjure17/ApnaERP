import datetime
from typing import Dict, List, Optional
import uuid
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import Attendance
from app.models.employee import Employee
from app.repositories.base_repository import BaseRepository
from app.schemas.attendance import AttendanceCreate, AttendanceSummary, AttendanceUpdate


class AttendanceRepository(BaseRepository[Attendance, AttendanceCreate, AttendanceUpdate]):
    """
    Repository for Attendance data access.
    Extends BaseRepository with employee-date lookups, monthly historical queries,
    department aggregations, and summary statistics.
    """

    def __init__(self):
        super().__init__(Attendance)

    async def get_by_employee_and_date(
        self,
        db: AsyncSession,
        employee_id: uuid.UUID,
        attendance_date: datetime.date,
        include_deleted: bool = False,
    ) -> Optional[Attendance]:
        """Retrieves an attendance record for a specific employee and date."""
        query = select(Attendance).where(
            Attendance.employee_id == employee_id,
            Attendance.attendance_date == attendance_date,
        )
        if not include_deleted:
            query = query.where(Attendance.is_deleted == False)

        result = await db.execute(query)
        return result.scalars().first()

    async def get_monthly_attendance(
        self,
        db: AsyncSession,
        employee_id: uuid.UUID,
        year: int,
        month: int,
    ) -> List[Attendance]:
        """Retrieves all attendance records for an employee within a given year and month."""
        query = (
            select(Attendance)
            .where(
                Attendance.employee_id == employee_id,
                Attendance.is_deleted == False,
                extract("year", Attendance.attendance_date) == year,
                extract("month", Attendance.attendance_date) == month,
            )
            .order_by(Attendance.attendance_date.asc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_department_attendance(
        self,
        db: AsyncSession,
        department_id: uuid.UUID,
        target_date: datetime.date,
    ) -> List[Attendance]:
        """Retrieves attendance records for all employees in a department on a target date."""
        query = (
            select(Attendance)
            .join(Employee, Attendance.employee_id == Employee.id)
            .where(
                Employee.department_id == department_id,
                Attendance.attendance_date == target_date,
                Attendance.is_deleted == False,
                Employee.is_deleted == False,
            )
            .order_by(Employee.last_name.asc(), Employee.first_name.asc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_summary(
        self,
        db: AsyncSession,
        start_date: datetime.date,
        end_date: datetime.date,
        department_id: Optional[uuid.UUID] = None,
        employee_id: Optional[uuid.UUID] = None,
    ) -> AttendanceSummary:
        """Calculates aggregated attendance summary statistics for a date range."""
        query = select(Attendance).where(
            Attendance.attendance_date >= start_date,
            Attendance.attendance_date <= end_date,
            Attendance.is_deleted == False,
        )

        if employee_id:
            query = query.where(Attendance.employee_id == employee_id)
        elif department_id:
            query = query.join(Employee, Attendance.employee_id == Employee.id).where(
                Employee.department_id == department_id,
                Employee.is_deleted == False,
            )

        result = await db.execute(query)
        records = list(result.scalars().all())

        summary = AttendanceSummary()
        summary.total_days = len(records)

        for rec in records:
            status = rec.attendance_status
            if status == "Present":
                summary.present_days += 1
            elif status == "Late":
                summary.late_days += 1
            elif status == "Half Day":
                summary.half_days += 1
            elif status == "Absent":
                summary.absent_days += 1
            elif status == "Holiday":
                summary.holiday_days += 1
            elif status == "Weekend":
                summary.weekend_days += 1
            elif status == "Missing Check-out":
                summary.missing_checkout_days += 1

            summary.total_worked_hours += round(rec.worked_minutes / 60.0, 2)
            summary.total_expected_hours += round(rec.expected_minutes / 60.0, 2)
            summary.total_late_minutes += rec.late_minutes
            summary.total_early_departure_minutes += rec.early_departure_minutes

        return summary


attendance_repository = AttendanceRepository()
