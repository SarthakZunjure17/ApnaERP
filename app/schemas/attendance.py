import datetime
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AttendanceStatus(str, Enum):
    PRESENT = "Present"
    LATE = "Late"
    HALF_DAY = "Half Day"
    ABSENT = "Absent"
    HOLIDAY = "Holiday"
    WEEKEND = "Weekend"
    ON_LEAVE = "On Leave"
    MISSING_CHECK_IN = "Missing Check-in"
    MISSING_CHECK_OUT = "Missing Check-out"


class AttendanceCreate(BaseModel):
    employee_id: uuid.UUID
    attendance_date: datetime.date
    shift_id: Optional[uuid.UUID] = None
    check_in_time: Optional[datetime.datetime] = None
    check_out_time: Optional[datetime.datetime] = None
    break_minutes: int = 0
    worked_minutes: int = 0
    expected_minutes: int = 0
    late_minutes: int = 0
    early_departure_minutes: int = 0
    attendance_status: str = "Absent"
    is_manual_correction: bool = False
    corrected_by_user_id: Optional[uuid.UUID] = None
    correction_notes: Optional[str] = None
    is_locked: bool = False


class AttendanceUpdate(BaseModel):
    shift_id: Optional[uuid.UUID] = None
    check_in_time: Optional[datetime.datetime] = None
    check_out_time: Optional[datetime.datetime] = None
    break_minutes: Optional[int] = None
    worked_minutes: Optional[int] = None
    expected_minutes: Optional[int] = None
    late_minutes: Optional[int] = None
    early_departure_minutes: Optional[int] = None
    attendance_status: Optional[str] = None
    is_manual_correction: Optional[bool] = None
    corrected_by_user_id: Optional[uuid.UUID] = None
    correction_notes: Optional[str] = None
    is_locked: Optional[bool] = None


class CheckInRequest(BaseModel):
    employee_id: uuid.UUID = Field(..., description="Employee UUID checking in")
    check_in_time: Optional[datetime.datetime] = Field(
        None, description="Check-in timestamp in UTC (defaults to current time if omitted)"
    )
    shift_id: Optional[uuid.UUID] = Field(
        None, description="Optional override shift UUID (defaults to employee assigned shift)"
    )


class CheckOutRequest(BaseModel):
    employee_id: uuid.UUID = Field(..., description="Employee UUID checking out")
    check_out_time: Optional[datetime.datetime] = Field(
        None, description="Check-out timestamp in UTC (defaults to current time if omitted)"
    )
    break_minutes: int = Field(
        default=0, ge=0, description="Total break time taken during shift in minutes"
    )


class AttendanceCorrectionRequest(BaseModel):
    attendance_id: uuid.UUID = Field(..., description="Attendance record UUID to correct")
    check_in_time: Optional[datetime.datetime] = Field(None, description="Corrected check-in timestamp in UTC")
    check_out_time: Optional[datetime.datetime] = Field(None, description="Corrected check-out timestamp in UTC")
    break_minutes: Optional[int] = Field(None, ge=0, description="Corrected break time in minutes")
    attendance_status: Optional[AttendanceStatus] = Field(
        None, description="Manual override status (optional, engine re-evaluates if omitted)"
    )
    correction_notes: str = Field(
        ..., min_length=3, max_length=1000, description="Mandatory audit justification for manual correction"
    )

    @model_validator(mode="after")
    def validate_timestamps(self) -> "AttendanceCorrectionRequest":
        if self.check_in_time and self.check_out_time:
            if self.check_out_time < self.check_in_time:
                raise ValueError("Check-out time cannot be earlier than check-in time.")
        return self


class AttendanceLockRequest(BaseModel):
    attendance_ids: Optional[List[uuid.UUID]] = Field(
        None, description="Specific attendance UUIDs to lock"
    )
    start_date: Optional[datetime.date] = Field(
        None, description="Start date for range locking"
    )
    end_date: Optional[datetime.date] = Field(
        None, description="End date for range locking"
    )
    employee_id: Optional[uuid.UUID] = Field(
        None, description="Optional target employee for range locking"
    )

    @model_validator(mode="after")
    def validate_lock_params(self) -> "AttendanceLockRequest":
        if not self.attendance_ids and not (self.start_date and self.end_date):
            raise ValueError("Either attendance_ids or a valid date range (start_date and end_date) must be provided.")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be earlier than start_date.")
        return self


class AttendanceResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: Optional[str] = None
    attendance_date: datetime.date
    shift_id: Optional[uuid.UUID] = None
    shift_name: Optional[str] = None
    check_in_time: Optional[datetime.datetime] = None
    check_out_time: Optional[datetime.datetime] = None
    break_minutes: int
    worked_minutes: int
    expected_minutes: int
    late_minutes: int
    early_departure_minutes: int
    attendance_status: str
    is_manual_correction: bool
    corrected_by_user_id: Optional[uuid.UUID] = None
    correction_notes: Optional[str] = None
    is_locked: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class AttendanceSummary(BaseModel):
    total_days: int = 0
    present_days: int = 0
    late_days: int = 0
    half_days: int = 0
    absent_days: int = 0
    holiday_days: int = 0
    weekend_days: int = 0
    missing_checkout_days: int = 0
    total_worked_hours: float = 0.0
    total_expected_hours: float = 0.0
    total_late_minutes: int = 0
    total_early_departure_minutes: int = 0


class AttendanceListResponse(BaseModel):
    items: List[AttendanceResponse]
    total: int
    page: int
    page_size: int
