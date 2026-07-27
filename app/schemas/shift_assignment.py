import datetime
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.employee import EmployeeResponse
from app.schemas.shift import ShiftResponse


class AssignmentType(str, Enum):
    PERMANENT = "Permanent"
    TEMPORARY = "Temporary"
    ROTATION = "Rotation"


class ShiftAssignmentBase(BaseModel):
    employee_id: uuid.UUID = Field(..., description="Target employee ID")
    shift_id: uuid.UUID = Field(..., description="Target shift ID")
    effective_from: datetime.date = Field(..., description="Effective start date")
    effective_to: Optional[datetime.date] = Field(None, description="Effective end date (NULL for open-ended)")
    assignment_type: AssignmentType = Field(AssignmentType.PERMANENT, description="Schedule assignment type")
    reason: Optional[str] = Field(None, max_length=500, description="Justification/reason")

    @model_validator(mode="after")
    def validate_dates(self) -> "ShiftAssignmentBase":
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to date must be greater than or equal to effective_from date.")
        return self


class ShiftAssignmentCreate(ShiftAssignmentBase):
    pass


class ShiftAssignmentUpdate(BaseModel):
    shift_id: Optional[uuid.UUID] = Field(None, description="Updated shift ID")
    effective_from: Optional[datetime.date] = Field(None, description="Updated effective start date")
    effective_to: Optional[datetime.date] = Field(None, description="Updated effective end date")
    assignment_type: Optional[AssignmentType] = Field(None, description="Updated schedule assignment type")
    reason: Optional[str] = Field(None, max_length=500, description="Updated justification/reason")
    is_active: Optional[bool] = Field(None, description="Updated active status")

    @model_validator(mode="after")
    def validate_dates(self) -> "ShiftAssignmentUpdate":
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to date must be greater than or equal to effective_from date.")
        return self


class ShiftAssignmentEndRequest(BaseModel):
    end_date: datetime.date = Field(..., description="Effective end date for this shift assignment")


class ShiftAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    shift_id: uuid.UUID
    effective_from: datetime.date
    effective_to: Optional[datetime.date] = None
    assignment_type: str
    reason: Optional[str] = None
    assigned_by: Optional[uuid.UUID] = None
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    # Expanded details if available
    employee_code: Optional[str] = None
    employee_name: Optional[str] = None
    shift_name: Optional[str] = None
    shift_code: Optional[str] = None


class ShiftAssignmentListResponse(BaseModel):
    items: List[ShiftAssignmentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
