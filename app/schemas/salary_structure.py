import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.salary_component import SalaryComponentResponse


class SalaryStructureComponentCreate(BaseModel):
    """
    Schema for adding a Salary Component mapping to a Salary Structure.
    """
    salary_component_id: uuid.UUID = Field(..., description="ID of the SalaryComponent to map")
    component_order: int = Field(..., ge=1, description="Display and processing sequence order position")
    component_value: float = Field(0.0, ge=0.0, description="Baseline value or default amount for this structure component")
    calculation_method_override: Optional[str] = Field(None, description="Optional calculation method override (Fixed, Percentage, Formula)")
    is_active: bool = Field(True, description="Active status in this structure")


class SalaryStructureComponentUpdate(BaseModel):
    """
    Schema for updating an existing component mapping in a Salary Structure.
    """
    component_order: Optional[int] = Field(None, ge=1)
    component_value: Optional[float] = Field(None, ge=0.0)
    calculation_method_override: Optional[str] = None
    is_active: Optional[bool] = None


class SalaryStructureComponentResponse(BaseModel):
    """
    Response schema for a Salary Structure component mapping.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    salary_structure_id: uuid.UUID
    salary_component_id: uuid.UUID
    component_order: int
    component_value: float
    calculation_method_override: Optional[str] = None
    is_active: bool
    created_at: datetime.datetime
    component: Optional[SalaryComponentResponse] = None


class SalaryStructureCreate(BaseModel):
    """
    Schema for creating a new Salary Structure template.
    """
    code: str = Field(..., min_length=2, max_length=50, description="Unique salary structure code (e.g. EXEC_PAY_V1)")
    name: str = Field(..., min_length=2, max_length=100, description="Unique salary structure name")
    description: Optional[str] = Field(None, max_length=255, description="Detailed structure description")
    currency: str = Field("INR", max_length=10, description="Currency code (default INR)")
    is_active: bool = Field(True, description="Active status for structure template")
    effective_from: datetime.date = Field(..., description="Date when this structure becomes effective")
    effective_to: Optional[datetime.date] = Field(None, description="Optional end date when this structure expires")


class SalaryStructureUpdate(BaseModel):
    """
    Schema for updating an existing Salary Structure template.
    """
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    currency: Optional[str] = Field(None, max_length=10)
    is_active: Optional[bool] = None
    effective_from: Optional[datetime.date] = None
    effective_to: Optional[datetime.date] = None


class SalaryStructureResponse(BaseModel):
    """
    Response schema for a Salary Structure template.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None
    currency: str
    is_active: bool
    effective_from: datetime.date
    effective_to: Optional[datetime.date] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    components: List[SalaryStructureComponentResponse] = []


class SalaryStructureListResponse(BaseModel):
    """
    Paginated response schema for Salary Structures.
    """
    items: List[SalaryStructureResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
