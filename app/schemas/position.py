import datetime
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class EmploymentCategory(str, Enum):
    """Supported position employment contract categories."""
    PERMANENT = "Permanent"
    CONTRACT = "Contract"
    TEMPORARY = "Temporary"
    INTERNSHIP = "Internship"


class PositionBase(BaseModel):
    """Base Pydantic v2 schema for Position fields."""
    code: str = Field(..., max_length=50, description="Unique position code")
    title: str = Field(..., max_length=150, description="Position job title")
    description: Optional[str] = Field(None, description="Position description and responsibilities")
    department_id: uuid.UUID = Field(..., description="Owning Department UUID")
    parent_position_id: Optional[uuid.UUID] = Field(None, description="Parent reporting position UUID")
    employment_category: EmploymentCategory = Field(EmploymentCategory.PERMANENT, description="Employment contract category")
    grade: Optional[str] = Field(None, max_length=50, description="Job grade (e.g. G5)")
    level: Optional[str] = Field(None, max_length=50, description="Job level (e.g. L4)")
    maximum_headcount: int = Field(1, ge=1, description="Maximum headcount capacity")
    is_managerial: bool = Field(False, description="True if position has managerial authority")
    is_active: bool = Field(True, description="Active position flag")


class PositionCreate(PositionBase):
    """Schema for creating a new Position."""
    pass


class PositionUpdate(BaseModel):
    """Schema for updating an existing Position."""
    code: Optional[str] = Field(None, max_length=50)
    title: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    parent_position_id: Optional[uuid.UUID] = None
    employment_category: Optional[EmploymentCategory] = None
    grade: Optional[str] = Field(None, max_length=50)
    level: Optional[str] = Field(None, max_length=50)
    maximum_headcount: Optional[int] = Field(None, ge=1)
    is_managerial: Optional[bool] = None
    is_active: Optional[bool] = None


class PositionSummary(BaseModel):
    """Lightweight summary schema for Position nesting."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    title: str
    department_id: uuid.UUID
    employment_category: str
    maximum_headcount: int
    current_headcount: int
    is_managerial: bool
    is_active: bool


class PositionResponse(PositionBase):
    """Full detailed response schema for Position entity."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    current_headcount: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    is_deleted: bool = False
    deleted_at: Optional[datetime.datetime] = None
    department_name: Optional[str] = None
    parent_position_title: Optional[str] = None


class PositionTreeResponse(BaseModel):
    """Hierarchy tree node representation for Positions."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    title: str
    department_id: uuid.UUID
    department_name: Optional[str] = None
    employment_category: str
    maximum_headcount: int
    current_headcount: int
    is_managerial: bool
    is_active: bool
    children: List["PositionTreeResponse"] = []


class PositionListResponse(BaseModel):
    """Paginated list response wrapper for Position records."""
    items: List[PositionResponse]
    total: int
    page: int
    page_size: int
