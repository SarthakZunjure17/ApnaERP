import datetime
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EmploymentType(str, Enum):
    FULL_TIME = "Full Time"
    PART_TIME = "Part Time"
    CONTRACT = "Contract"
    INTERN = "Intern"


class EmploymentStatus(str, Enum):
    ACTIVE = "Active"
    PROBATION = "Probation"
    NOTICE_PERIOD = "Notice Period"
    SUSPENDED = "Suspended"
    RESIGNED = "Resigned"
    TERMINATED = "Terminated"


class EmployeeBase(BaseModel):
    employee_code: str = Field(..., max_length=50, description="Unique employee identifier code")
    first_name: str = Field(..., max_length=100, description="First name")
    middle_name: Optional[str] = Field(None, max_length=100, description="Middle name")
    last_name: str = Field(..., max_length=100, description="Last name")
    preferred_name: Optional[str] = Field(None, max_length=100, description="Preferred display name")

    work_email: EmailStr = Field(..., description="Unique enterprise work email address")
    personal_email: Optional[EmailStr] = Field(None, description="Personal contact email address")
    work_phone: Optional[str] = Field(None, max_length=50, description="Work telephone number")
    personal_phone: Optional[str] = Field(None, max_length=50, description="Personal phone number")

    user_id: Optional[uuid.UUID] = Field(None, description="Linked user account ID")
    department_id: uuid.UUID = Field(..., description="Assigned department ID")
    manager_id: Optional[uuid.UUID] = Field(None, description="Direct manager employee ID")
    position_id: Optional[uuid.UUID] = Field(None, description="Assigned job position ID")

    employment_type: EmploymentType = Field(default=EmploymentType.FULL_TIME, description="Type of employment contract")
    employment_status: EmploymentStatus = Field(default=EmploymentStatus.ACTIVE, description="Current employment lifecycle status")

    joining_date: datetime.date = Field(..., description="Date employee joined the organization")
    confirmation_date: Optional[datetime.date] = Field(None, description="Probation confirmation date")
    exit_date: Optional[datetime.date] = Field(None, description="Exit/Termination date")
    employment_start_date: Optional[datetime.date] = Field(None, description="Contract/Position start date")
    employment_end_date: Optional[datetime.date] = Field(None, description="Contract/Position end date")
    date_of_birth: Optional[datetime.date] = Field(None, description="Date of birth")
    gender: Optional[str] = Field(None, max_length=20, description="Gender identity")

    profile_photo_file_id: Optional[uuid.UUID] = Field(None, description="Linked profile picture file ID")
    is_active: bool = Field(default=True, description="Active status indicator")


class EmployeeCreate(EmployeeBase):
    """Schema for creating a new Employee."""
    pass


class EmployeeUpdate(BaseModel):
    """Schema for updating an existing Employee."""
    employee_code: Optional[str] = Field(None, max_length=50)
    first_name: Optional[str] = Field(None, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    preferred_name: Optional[str] = Field(None, max_length=100)

    work_email: Optional[EmailStr] = None
    personal_email: Optional[EmailStr] = None
    work_phone: Optional[str] = Field(None, max_length=50)
    personal_phone: Optional[str] = Field(None, max_length=50)

    user_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    manager_id: Optional[uuid.UUID] = None
    position_id: Optional[uuid.UUID] = None

    employment_type: Optional[EmploymentType] = None
    employment_status: Optional[EmploymentStatus] = None

    joining_date: Optional[datetime.date] = None
    confirmation_date: Optional[datetime.date] = None
    exit_date: Optional[datetime.date] = None
    employment_start_date: Optional[datetime.date] = None
    employment_end_date: Optional[datetime.date] = None
    date_of_birth: Optional[datetime.date] = None
    gender: Optional[str] = Field(None, max_length=20)

    profile_photo_file_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None


class EmployeeResponse(EmployeeBase):
    """Full Employee details response schema."""
    id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
    deleted_at: Optional[datetime.datetime] = None
    is_deleted: bool = False

    model_config = ConfigDict(from_attributes=True)


class EmployeeSummary(BaseModel):
    """Concise Employee summary response schema."""
    id: uuid.UUID
    employee_code: str
    first_name: str
    last_name: str
    work_email: str
    department_id: uuid.UUID
    manager_id: Optional[uuid.UUID] = None
    position_id: Optional[uuid.UUID] = None
    employment_type: str
    employment_status: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class EmployeeListResponse(BaseModel):
    """Paginated Employee list response wrapper schema."""
    total: int
    page: int
    page_size: int
    items: List[EmployeeResponse]


class EmployeeHierarchyResponse(EmployeeResponse):
    """Recursive manager reporting hierarchy response schema."""
    direct_reports: List["EmployeeHierarchyResponse"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
