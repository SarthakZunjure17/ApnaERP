import datetime
from dataclasses import dataclass
import logging
from typing import List, Optional, Union

from app.models.hr_configuration import HRConfiguration
from app.models.shift import Shift
from app.schemas.attendance import AttendanceStatus

logger = logging.getLogger("app.services.attendance_engine")


@dataclass
class AttendanceCalculationResult:
    attendance_status: str
    worked_minutes: int
    expected_minutes: int
    late_minutes: int
    early_departure_minutes: int


class AttendanceEngine:
    """
    Domain Business Rules Engine for Attendance Calculations.
    Pure, deterministic domain service operating independently from API controllers.
    Calculates expected time, worked time, tardiness, early departure, and attendance status
    by synthesizing Employee, Shift, Holiday Calendar, and HR Configuration rules.
    """

    @staticmethod
    def calculate_attendance(
        attendance_date: datetime.date,
        check_in_time: Optional[datetime.datetime] = None,
        check_out_time: Optional[datetime.datetime] = None,
        break_minutes: int = 0,
        shift: Optional[Shift] = None,
        hr_config: Optional[HRConfiguration] = None,
        is_holiday: bool = False,
        is_on_leave: bool = False,
    ) -> AttendanceCalculationResult:
        """
        Calculates attendance metrics and status.
        """
        # 1. Determine Weekend
        day_name = attendance_date.strftime("%A")  # e.g., "Saturday", "Sunday"
        weekend_days: List[str] = []
        if hr_config and hr_config.weekend_configuration:
            weekend_days = [w.strip().lower() for w in hr_config.weekend_configuration]

        is_weekend = day_name.lower() in weekend_days

        # 2. Extract Shift or Fallback HR Config parameters
        standard_hours = (
            hr_config.standard_working_hours_per_day
            if hr_config
            else 8.0
        )
        grace_period_mins = (
            shift.grace_period_minutes
            if shift
            else (hr_config.grace_period_minutes if hr_config else 15)
        )
        min_working_hours = (
            shift.minimum_working_hours
            if shift
            else (hr_config.minimum_working_hours if hr_config else 4.0)
        )

        # 3. Expected Minutes Calculation
        if is_weekend or is_holiday:
            expected_minutes = 0
        elif shift:
            # Shift duration in minutes minus shift break duration
            total_shift_mins = int(shift.duration_hours * 60)
            expected_minutes = max(0, total_shift_mins - shift.break_duration_minutes)
        else:
            expected_minutes = int(standard_hours * 60)

        # 4. Construct Shift Reference Window (Start & End Timestamps)
        if shift:
            shift_start_time = shift.start_time
            shift_end_time = shift.end_time
        else:
            shift_start_time = datetime.time(9, 0)
            shift_end_time = datetime.time(17, 0)

        # Create timezone-naive reference datetimes or preserve tzinfo
        ref_tz = None
        if check_in_time and check_in_time.tzinfo:
            ref_tz = check_in_time.tzinfo
        elif check_out_time and check_out_time.tzinfo:
            ref_tz = check_out_time.tzinfo

        if ref_tz:
            shift_start_dt = datetime.datetime.combine(attendance_date, shift_start_time, tzinfo=ref_tz)
        else:
            shift_start_dt = datetime.datetime.combine(attendance_date, shift_start_time)

        # Overnight shift handling (end_time <= start_time)
        is_overnight = shift_end_time <= shift_start_time
        if is_overnight:
            next_date = attendance_date + datetime.timedelta(days=1)
            if ref_tz:
                shift_end_dt = datetime.datetime.combine(next_date, shift_end_time, tzinfo=ref_tz)
            else:
                shift_end_dt = datetime.datetime.combine(next_date, shift_end_time)
        else:
            if ref_tz:
                shift_end_dt = datetime.datetime.combine(attendance_date, shift_end_time, tzinfo=ref_tz)
            else:
                shift_end_dt = datetime.datetime.combine(attendance_date, shift_end_time)

        # Normalize timestamps for comparison (strip tzinfo if one side is naive)
        calc_check_in = check_in_time
        calc_check_out = check_out_time

        if calc_check_in and shift_start_dt and (calc_check_in.tzinfo != shift_start_dt.tzinfo):
            calc_check_in = calc_check_in.replace(tzinfo=None)
            shift_start_dt = shift_start_dt.replace(tzinfo=None)

        if calc_check_out and shift_end_dt and (calc_check_out.tzinfo != shift_end_dt.tzinfo):
            calc_check_out = calc_check_out.replace(tzinfo=None)
            shift_end_dt = shift_end_dt.replace(tzinfo=None)

        # 5. Worked Minutes Calculation
        if calc_check_in and calc_check_out:
            raw_seconds = (calc_check_out - calc_check_in).total_seconds()
            raw_minutes = max(0, int(raw_seconds // 60))
            worked_minutes = max(0, raw_minutes - break_minutes)
        else:
            worked_minutes = 0

        # 6. Late Minutes Calculation
        if calc_check_in:
            late_threshold = shift_start_dt + datetime.timedelta(minutes=grace_period_mins)
            if calc_check_in > late_threshold:
                late_minutes = int((calc_check_in - shift_start_dt).total_seconds() // 60)
            else:
                late_minutes = 0
        else:
            late_minutes = 0

        # 7. Early Departure Minutes Calculation
        if calc_check_out:
            if calc_check_out < shift_end_dt:
                early_departure_minutes = int((shift_end_dt - calc_check_out).total_seconds() // 60)
            else:
                early_departure_minutes = 0
        else:
            early_departure_minutes = 0

        # 8. Status Decision Matrix
        if not calc_check_in and not calc_check_out:
            if is_on_leave:
                status = AttendanceStatus.ON_LEAVE.value
            elif is_holiday:
                status = AttendanceStatus.HOLIDAY.value
            elif is_weekend:
                status = AttendanceStatus.WEEKEND.value
            else:
                status = AttendanceStatus.ABSENT.value
        elif calc_check_in and not calc_check_out:
            status = AttendanceStatus.MISSING_CHECK_OUT.value
        elif not calc_check_in and calc_check_out:
            status = AttendanceStatus.MISSING_CHECK_IN.value
        else:
            # Both check-in and check-out present
            min_working_mins = int(min_working_hours * 60)
            if worked_minutes < min_working_mins:
                status = AttendanceStatus.HALF_DAY.value
            elif late_minutes > 0:
                status = AttendanceStatus.LATE.value
            else:
                status = AttendanceStatus.PRESENT.value

        return AttendanceCalculationResult(
            attendance_status=status,
            worked_minutes=worked_minutes,
            expected_minutes=expected_minutes,
            late_minutes=late_minutes,
            early_departure_minutes=early_departure_minutes,
        )
