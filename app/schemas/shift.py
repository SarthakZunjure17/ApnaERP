import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ShiftBase(BaseModel):
    """Base schema for Shift attributes."""
    code: str = Field(..., min_length=2, max_length=50, description="Unique shift code (e.g. SHIFT-DAY-01)")
    name: str = Field(..., min_length=2, max_length=100, description="Unique shift name (e.g. Morning Shift)")
    description: Optional[str] = Field(None, description="Shift schedule description")

    start_time: datetime.time = Field(..., description="Shift start time (e.g. 09:00:00)")
    end_time: datetime.time = Field(..., description="Shift end time (e.g. 17:00:00)")

    break_duration_minutes: int = Field(default=60, ge=0, le=480, description="Break duration in minutes")
    grace_period_minutes: int = Field(default=15, ge=0, le=180, description="Arrival grace period in minutes")

    minimum_working_hours: float = Field(default=4.0, ge=0, le=24, description="Minimum working hours for half-day")
    maximum_working_hours: float = Field(default=12.0, ge=0, le=24, description="Maximum allowed working hours")

    is_night_shift: bool = Field(default=False, description="Flag for overnight shift across midnight")
    is_flexible_shift: bool = Field(default=False, description="Flag for flexible timing support")
    is_active: bool = Field(default=True, description="Active shift flag")


class ShiftCreate(ShiftBase):
    """Schema for creating a new Shift."""
    pass


class ShiftUpdate(BaseModel):
    """Schema for updating an existing Shift."""
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None

    start_time: Optional[datetime.time] = None
    end_time: Optional[datetime.time] = None

    break_duration_minutes: Optional[int] = Field(None, ge=0, le=480)
    grace_period_minutes: Optional[int] = Field(None, ge=0, le=180)

    minimum_working_hours: Optional[float] = Field(None, ge=0, le=24)
    maximum_working_hours: Optional[float] = Field(None, ge=0, le=24)

    is_night_shift: Optional[bool] = None
    is_flexible_shift: Optional[bool] = None
    is_active: Optional[bool] = None


class ShiftResponse(ShiftBase):
    """Schema for returning full Shift details."""
    id: uuid.UUID
    duration_hours: float = Field(..., description="Calculated total shift duration in hours")
    created_at: datetime.datetime
    updated_at: datetime.datetime
    is_deleted: bool = False
    deleted_at: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ShiftSummary(BaseModel):
    """Lightweight schema for Shift summary in listings."""
    id: uuid.UUID
    code: str
    name: str
    start_time: datetime.time
    end_time: datetime.time
    duration_hours: float
    is_night_shift: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ShiftListResponse(BaseModel):
    """Paginated list response for Shifts."""
    items: List[ShiftResponse]
    total: int
    page: int
    page_size: int

    model_config = ConfigDict(from_attributes=True)
