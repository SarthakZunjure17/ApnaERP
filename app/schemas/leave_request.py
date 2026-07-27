import datetime
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator


class LeaveRequestStatusEnum(str, Enum):
    DRAFT = "Draft"
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"
    COMPLETED = "Completed"


class HalfDaySessionEnum(str, Enum):
    FIRST_HALF = "First Half"
    SECOND_HALF = "Second Half"
    MORNING = "Morning"
    AFTERNOON = "Afternoon"


class LeaveRequestCreate(BaseModel):
    """
    Schema for creating a new Leave Request application.
    """
    employee_id: uuid.UUID = Field(..., description="Target employee ID")
    leave_type_id: uuid.UUID = Field(..., description="Target leave policy ID")
    start_date: datetime.date = Field(..., description="Start date (inclusive)")
    end_date: datetime.date = Field(..., description="End date (inclusive)")

    is_half_day: bool = Field(False, description="True if applying for half-day leave")
    half_day_session: Optional[str] = Field(
        None, description="Half day session ('First Half', 'Second Half', 'Morning', 'Afternoon')"
    )

    reason: str = Field(..., min_length=3, max_length=500, description="Business/personal leave justification")

    @model_validator(mode="after")
    def validate_dates_and_half_day(self):
        if self.end_date < self.start_date:
            raise ValueError("End date cannot be prior to start date.")
        if self.is_half_day and self.start_date != self.end_date:
            raise ValueError("Half-day leave requests must have identical start and end dates.")
        return self


class LeaveRequestUpdate(BaseModel):
    """
    Schema for updating an existing Draft Leave Request.
    """
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    is_half_day: Optional[bool] = None
    half_day_session: Optional[str] = None
    reason: Optional[str] = Field(None, min_length=3, max_length=500)


class LeaveRequestReviewRequest(BaseModel):
    """
    Schema for reviewing (approving or rejecting) a Leave Request.
    """
    reviewer_comments: Optional[str] = Field(
        None, max_length=500, description="Comments/justification from reviewer"
    )


class LeaveRequestCancelRequest(BaseModel):
    """
    Schema for cancelling a Leave Request.
    """
    reason: Optional[str] = Field(
        None, max_length=500, description="Reason for cancelling the leave request"
    )


class LeaveRequestResponse(BaseModel):
    """
    Response DTO for Leave Request entity.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    leave_type_id: uuid.UUID

    start_date: datetime.date
    end_date: datetime.date
    total_days: float

    is_half_day: bool
    half_day_session: Optional[str] = None
    reason: str
    status: str

    submitted_at: Optional[datetime.datetime] = None
    reviewed_at: Optional[datetime.datetime] = None
    reviewed_by: Optional[uuid.UUID] = None
    reviewer_comments: Optional[str] = None

    created_at: datetime.datetime
    updated_at: datetime.datetime
    is_deleted: bool = False
    deleted_at: Optional[datetime.datetime] = None

    # Formatted details
    employee_code: Optional[str] = None
    employee_name: Optional[str] = None
    leave_type_code: Optional[str] = None
    leave_type_name: Optional[str] = None
    reviewer_name: Optional[str] = None


class LeaveRequestListResponse(BaseModel):
    """
    Paginated list response for Leave Requests.
    """
    items: List[LeaveRequestResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
