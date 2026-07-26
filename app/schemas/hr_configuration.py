import datetime
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class PayrollCycle(str, Enum):
    MONTHLY = "Monthly"
    BIWEEKLY = "Biweekly"
    WEEKLY = "Weekly"


class HRConfigurationBase(BaseModel):
    """Base schema for HR Configuration attributes."""
    organization_name: str = Field(..., min_length=2, max_length=150, description="Organization name")
    organization_code: str = Field(..., min_length=2, max_length=50, description="Unique organization code")

    timezone: str = Field(default="UTC", max_length=50, description="IANA timezone name")
    country: str = Field(default="India", max_length=50, description="Country name")
    currency: str = Field(default="INR", min_length=3, max_length=10, description="ISO Currency code")

    standard_working_hours_per_day: float = Field(default=8.0, gt=0, le=24, description="Standard working hours per day")
    standard_working_days_per_week: int = Field(default=5, ge=1, le=7, description="Standard working days per week")
    weekend_configuration: List[str] = Field(default=["Saturday", "Sunday"], description="List of weekend days")

    default_shift_name: str = Field(default="General Shift", max_length=100, description="Default shift name")
    grace_period_minutes: int = Field(default=15, ge=0, le=240, description="Grace period in minutes")
    minimum_working_hours: float = Field(default=4.0, ge=0, le=24, description="Minimum working hours for half day credit")

    default_probation_period_days: int = Field(default=90, ge=0, le=365, description="Probation period in days")
    leave_year_start_month: int = Field(default=1, ge=1, le=12, description="Leave year start month (1-12)")
    payroll_cycle: PayrollCycle = Field(default=PayrollCycle.MONTHLY, description="Payroll cycle frequency")
    fiscal_year_start_month: int = Field(default=4, ge=1, le=12, description="Fiscal year start month (1-12)")

    is_active: bool = Field(default=True, description="Active configuration flag")


class HRConfigurationCreate(HRConfigurationBase):
    """Schema for creating a new HR Configuration."""
    pass


class HRConfigurationUpdate(BaseModel):
    """Schema for updating an existing HR Configuration."""
    organization_name: Optional[str] = Field(None, min_length=2, max_length=150)
    organization_code: Optional[str] = Field(None, min_length=2, max_length=50)

    timezone: Optional[str] = Field(None, max_length=50)
    country: Optional[str] = Field(None, max_length=50)
    currency: Optional[str] = Field(None, min_length=3, max_length=10)

    standard_working_hours_per_day: Optional[float] = Field(None, gt=0, le=24)
    standard_working_days_per_week: Optional[int] = Field(None, ge=1, le=7)
    weekend_configuration: Optional[List[str]] = None

    default_shift_name: Optional[str] = Field(None, max_length=100)
    grace_period_minutes: Optional[int] = Field(None, ge=0, le=240)
    minimum_working_hours: Optional[float] = Field(None, ge=0, le=24)

    default_probation_period_days: Optional[int] = Field(None, ge=0, le=365)
    leave_year_start_month: Optional[int] = Field(None, ge=1, le=12)
    payroll_cycle: Optional[PayrollCycle] = None
    fiscal_year_start_month: Optional[int] = Field(None, ge=1, le=12)

    is_active: Optional[bool] = None


class HRConfigurationResponse(HRConfigurationBase):
    """Schema for returning HR Configuration responses."""
    id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
    is_deleted: bool = False
    deleted_at: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True)


class HRConfigurationListResponse(BaseModel):
    """Schema for paginated HR Configuration list response."""
    items: List[HRConfigurationResponse]
    total: int
    page: int
    page_size: int

    model_config = ConfigDict(from_attributes=True)
