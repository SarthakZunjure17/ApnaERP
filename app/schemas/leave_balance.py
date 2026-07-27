import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class LeaveBalanceCreate(BaseModel):
    """
    Schema for initializing/creating a new Leave Balance for an employee.
    """
    employee_id: uuid.UUID = Field(..., description="Target employee ID")
    leave_type_id: uuid.UUID = Field(..., description="Target leave type ID")
    leave_year: int = Field(..., ge=2000, le=2100, description="Leave year (e.g. 2026)")

    opening_balance: float = Field(0.0, ge=0, description="Opening balance at start of year")
    allocated_days: float = Field(0.0, ge=0, description="Annual allocated leave days")
    earned_days: float = Field(0.0, ge=0, description="Accrued/earned leave days")
    availed_days: float = Field(0.0, ge=0, description="Leave days taken/availed")
    encashed_days: float = Field(0.0, ge=0, description="Leave days encashed")
    carried_forward_days: float = Field(0.0, ge=0, description="Carried forward leave days")
    is_active: bool = Field(True, description="Active status")


class LeaveBalanceUpdate(BaseModel):
    """
    Schema for updating an existing Leave Balance record.
    """
    opening_balance: Optional[float] = Field(None, ge=0)
    allocated_days: Optional[float] = Field(None, ge=0)
    earned_days: Optional[float] = Field(None, ge=0)
    availed_days: Optional[float] = Field(None, ge=0)
    encashed_days: Optional[float] = Field(None, ge=0)
    carried_forward_days: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None


class LeaveBalanceAdjustmentRequest(BaseModel):
    """
    Schema for requesting a manual adjustment to a leave balance.
    """
    adjustment_type: str = Field(
        ...,
        description="Type of adjustment: 'allocated', 'earned', 'availed', 'encashed', 'opening', 'carried_forward'",
    )
    adjustment_days: float = Field(
        ...,
        description="Amount of days to adjust (positive to add, negative to deduct)",
    )
    reason: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Mandatory business justification for manual balance adjustment",
    )


class LeaveBalanceResponse(BaseModel):
    """
    Schema for Leave Balance responses.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    leave_type_id: uuid.UUID
    leave_year: int

    opening_balance: float
    allocated_days: float
    earned_days: float
    availed_days: float
    encashed_days: float
    carried_forward_days: float
    remaining_days: float

    last_updated_by: Optional[uuid.UUID] = None
    is_active: bool

    created_at: datetime.datetime
    updated_at: datetime.datetime
    is_deleted: bool = False
    deleted_at: Optional[datetime.datetime] = None

    # Formatted details
    employee_code: Optional[str] = None
    employee_name: Optional[str] = None
    leave_type_code: Optional[str] = None
    leave_type_name: Optional[str] = None


class LeaveBalanceListResponse(BaseModel):
    """
    Paginated list response for Leave Balances.
    """
    items: List[LeaveBalanceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
