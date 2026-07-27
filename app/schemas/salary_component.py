import datetime
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ComponentTypeEnum(str, Enum):
    EARNING = "Earning"
    DEDUCTION = "Deduction"


class CalculationMethodEnum(str, Enum):
    FIXED = "Fixed"
    PERCENTAGE = "Percentage"
    FORMULA = "Formula"


class SalaryComponentCreate(BaseModel):
    """
    Schema for creating a new Salary Component definition.
    """
    code: str = Field(..., min_length=2, max_length=50, description="Unique component code (e.g. BASIC, HRA)")
    name: str = Field(..., min_length=2, max_length=100, description="Unique component name")
    description: Optional[str] = Field(None, max_length=255, description="Detailed component description")
    type: ComponentTypeEnum = Field(..., description="Component type: Earning or Deduction")
    calculation_method: CalculationMethodEnum = Field(..., description="Calculation method: Fixed, Percentage, Formula")
    default_value: float = Field(0.0, ge=0.0, description="Default fixed amount value")
    percentage_value: Optional[float] = Field(None, ge=0.0, le=100.0, description="Percentage value (0-100) if Percentage method")
    is_taxable: bool = Field(True, description="Subject to Income Tax")
    is_pf_applicable: bool = Field(True, description="Subject to Provident Fund")
    is_esi_applicable: bool = Field(True, description="Subject to ESI")
    is_active: bool = Field(True, description="Active status for payroll")
    display_order: int = Field(..., ge=1, description="Unique sequential ordering number")


class SalaryComponentUpdate(BaseModel):
    """
    Schema for updating an existing Salary Component definition.
    """
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    type: Optional[ComponentTypeEnum] = None
    calculation_method: Optional[CalculationMethodEnum] = None
    default_value: Optional[float] = Field(None, ge=0.0)
    percentage_value: Optional[float] = Field(None, ge=0.0, le=100.0)
    is_taxable: Optional[bool] = None
    is_pf_applicable: Optional[bool] = None
    is_esi_applicable: Optional[bool] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = Field(None, ge=1)


class SalaryComponentResponse(BaseModel):
    """
    Response schema for a Salary Component definition.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None
    type: str
    calculation_method: str
    default_value: float
    percentage_value: Optional[float] = None
    is_taxable: bool
    is_pf_applicable: bool
    is_esi_applicable: bool
    is_active: bool
    display_order: int
    created_at: datetime.datetime
    updated_at: datetime.datetime


class SalaryComponentListResponse(BaseModel):
    """
    Paginated response schema for Salary Components.
    """
    items: List[SalaryComponentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
