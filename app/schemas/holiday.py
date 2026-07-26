import datetime
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class HolidayType(str, Enum):
    NATIONAL = "National"
    REGIONAL = "Regional"
    COMPANY = "Company"
    OPTIONAL = "Optional"


class HolidayBase(BaseModel):
    """Base schema for Holiday attributes."""
    code: str = Field(..., min_length=2, max_length=50, description="Unique holiday code (e.g. HOL-2026-IND-DAY)")
    name: str = Field(..., min_length=2, max_length=100, description="Official holiday name")
    description: Optional[str] = Field(None, description="Detailed holiday description")

    holiday_date: datetime.date = Field(..., description="Date of the holiday")
    holiday_type: HolidayType = Field(default=HolidayType.COMPANY, description="Holiday classification type")

    country: str = Field(default="India", max_length=100, description="Target country")
    state_region: Optional[str] = Field(None, max_length=100, description="Target state/region for regional holidays")

    is_half_day: bool = Field(default=False, description="Flag for half-day holiday observation")
    is_recurring_annually: bool = Field(default=False, description="Flag for annually recurring holiday")
    is_active: bool = Field(default=True, description="Active holiday status flag")


class HolidayCreate(HolidayBase):
    """Schema for creating a new Holiday."""
    pass


class HolidayUpdate(BaseModel):
    """Schema for updating an existing Holiday."""
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None

    holiday_date: Optional[datetime.date] = None
    holiday_type: Optional[HolidayType] = None

    country: Optional[str] = Field(None, max_length=100)
    state_region: Optional[str] = Field(None, max_length=100)

    is_half_day: Optional[bool] = None
    is_recurring_annually: Optional[bool] = None
    is_active: Optional[bool] = None


class HolidayResponse(HolidayBase):
    """Schema for returning full Holiday details."""
    id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
    is_deleted: bool = False
    deleted_at: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True)


class HolidaySummary(BaseModel):
    """Lightweight schema for Holiday summary in listings."""
    id: uuid.UUID
    code: str
    name: str
    holiday_date: datetime.date
    holiday_type: str
    country: str
    state_region: Optional[str] = None
    is_half_day: bool
    is_recurring_annually: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class HolidayListResponse(BaseModel):
    """Paginated list response for Holidays."""
    items: List[HolidayResponse]
    total: int
    page: int
    page_size: int

    model_config = ConfigDict(from_attributes=True)
