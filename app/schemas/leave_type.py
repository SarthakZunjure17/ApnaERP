import datetime
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class GenderRestrictionEnum(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    ALL = "All"


class LeaveTypeCreate(BaseModel):
    """
    Schema for creating a new Leave Type / Policy.
    """
    code: str = Field(..., min_length=2, max_length=50, description="Unique leave code (e.g. ANNUAL, SICK)")
    name: str = Field(..., min_length=2, max_length=100, description="Unique leave name (e.g. Annual Leave)")
    description: Optional[str] = Field(None, description="Detailed leave policy description")

    is_paid: bool = Field(True, description="True if leave is paid")
    requires_approval: bool = Field(True, description="True if leave requires manager/HR approval")
    allow_half_day: bool = Field(True, description="True if half-day leave is allowed")
    allow_negative_balance: bool = Field(False, description="True if leave balance can go negative")

    annual_allocation: float = Field(0.0, ge=0, description="Default annual leave allocation (days)")
    carry_forward_allowed: bool = Field(False, description="True if carry-forward to next year is permitted")
    max_carry_forward: float = Field(0.0, ge=0, description="Maximum carry-forward days allowed")
    max_consecutive_days: Optional[int] = Field(30, gt=0, description="Maximum consecutive leave days allowed")

    gender_restriction: Optional[str] = Field(None, description="Gender restriction if applicable (Male, Female, All)")
    is_active: bool = Field(True, description="Active status")


class LeaveTypeUpdate(BaseModel):
    """
    Schema for updating an existing Leave Type.
    """
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None

    is_paid: Optional[bool] = None
    requires_approval: Optional[bool] = None
    allow_half_day: Optional[bool] = None
    allow_negative_balance: Optional[bool] = None

    annual_allocation: Optional[float] = Field(None, ge=0)
    carry_forward_allowed: Optional[bool] = None
    max_carry_forward: Optional[float] = Field(None, ge=0)
    max_consecutive_days: Optional[int] = Field(None, gt=0)

    gender_restriction: Optional[str] = None
    is_active: Optional[bool] = None


class LeaveTypeResponse(BaseModel):
    """
    Schema for Leave Type responses.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None

    is_paid: bool
    requires_approval: bool
    allow_half_day: bool
    allow_negative_balance: bool

    annual_allocation: float
    carry_forward_allowed: bool
    max_carry_forward: float
    max_consecutive_days: Optional[int] = None
    gender_restriction: Optional[str] = None

    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
    is_deleted: bool = False
    deleted_at: Optional[datetime.datetime] = None


class LeaveTypeListResponse(BaseModel):
    """
    Paginated list response for Leave Types.
    """
    items: List[LeaveTypeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
