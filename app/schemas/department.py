from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class DepartmentBase(BaseModel):
    """Base Pydantic schema for Department data."""
    code: str = Field(..., min_length=2, max_length=50, description="Unique department code (e.g. HR, IT-DEV)")
    name: str = Field(..., min_length=2, max_length=100, description="Department name")
    description: Optional[str] = Field(None, max_length=500, description="Detailed description")
    parent_id: Optional[uuid.UUID] = Field(None, description="UUID of parent department")
    manager_id: Optional[uuid.UUID] = Field(None, description="UUID of manager user")
    is_active: bool = Field(True, description="Whether department is active")


class DepartmentCreate(DepartmentBase):
    """Schema for creating a new department."""
    pass


class DepartmentUpdate(BaseModel):
    """Schema for updating an existing department."""
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[uuid.UUID] = None
    manager_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None


class DepartmentSummary(BaseModel):
    """Concise department summary schema."""
    id: uuid.UUID
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class DepartmentResponse(DepartmentBase):
    """Full department response schema."""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    is_deleted: bool = False

    model_config = ConfigDict(from_attributes=True)


class DepartmentTreeResponse(DepartmentResponse):
    """Hierarchical department tree node response schema."""
    children: List["DepartmentTreeResponse"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DepartmentListResponse(BaseModel):
    """Paginated list response for departments."""
    total: int
    page: int
    page_size: int
    items: List[DepartmentResponse]

    model_config = ConfigDict(from_attributes=True)


# Rebuild model for recursive DepartmentTreeResponse schema
DepartmentTreeResponse.model_rebuild()
