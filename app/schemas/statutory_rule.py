import datetime
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class RuleTypeEnum(str, Enum):
    PROVIDENT_FUND = "Provident Fund"
    ESI = "ESI"
    PROFESSIONAL_TAX = "Professional Tax"
    INCOME_TAX = "Income Tax"
    OTHER = "Other"


class CalculationMethodEnum(str, Enum):
    FIXED = "Fixed"
    PERCENTAGE = "Percentage"
    SLAB = "Slab"


class StatutoryRuleSlabCreate(BaseModel):
    """
    Schema for creating a Statutory Rule Slab.
    """
    min_amount: float = Field(..., ge=0, description="Minimum salary boundary (inclusive)")
    max_amount: Optional[float] = Field(None, ge=0, description="Maximum salary boundary (inclusive, None for infinity)")
    percentage: float = Field(0.00, ge=0, le=100, description="Percentage rate")
    fixed_amount: float = Field(0.00, ge=0, description="Fixed amount applied")
    sequence: int = Field(1, ge=1, description="Sequence order index")


class StatutoryRuleSlabUpdate(BaseModel):
    """
    Schema for updating a Statutory Rule Slab.
    """
    min_amount: Optional[float] = Field(None, ge=0)
    max_amount: Optional[float] = Field(None, ge=0)
    percentage: Optional[float] = Field(None, ge=0, le=100)
    fixed_amount: Optional[float] = Field(None, ge=0)
    sequence: Optional[int] = Field(None, ge=1)


class StatutoryRuleSlabResponse(BaseModel):
    """
    Response schema for a Statutory Rule Slab.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    statutory_rule_id: uuid.UUID
    min_amount: float
    max_amount: Optional[float] = None
    percentage: float
    fixed_amount: float
    sequence: int
    created_at: datetime.datetime
    updated_at: datetime.datetime


class StatutoryRuleCreate(BaseModel):
    """
    Schema for creating a Statutory Rule.
    """
    rule_code: str = Field(..., max_length=50, description="Unique rule code (e.g. IND_PF_STANDARD, IND_PT_MH)")
    rule_name: str = Field(..., max_length=100, description="Human-readable rule name")
    country_id: uuid.UUID = Field(..., description="ID of applicable Country")
    rule_type: RuleTypeEnum = Field(..., description="Rule Type")
    calculation_method: CalculationMethodEnum = Field(..., description="Calculation Method")
    effective_from: datetime.date = Field(..., description="Effective start date")
    effective_to: Optional[datetime.date] = Field(None, description="Optional effective end date")
    is_active: bool = Field(True, description="Active status flag")
    priority: int = Field(1, ge=1, description="Priority evaluation order")
    description: Optional[str] = Field(None, description="Rule description")
    slabs: Optional[List[StatutoryRuleSlabCreate]] = Field(None, description="Optional list of initial slabs")


class StatutoryRuleUpdate(BaseModel):
    """
    Schema for updating a Statutory Rule.
    """
    rule_name: Optional[str] = Field(None, max_length=100)
    effective_from: Optional[datetime.date] = None
    effective_to: Optional[datetime.date] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None


class StatutoryRuleResponse(BaseModel):
    """
    Response schema for a Statutory Rule.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rule_code: str
    rule_name: str
    country_id: uuid.UUID
    rule_type: str
    calculation_method: str
    effective_from: datetime.date
    effective_to: Optional[datetime.date] = None
    is_active: bool
    priority: int
    description: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    slabs: List[StatutoryRuleSlabResponse] = []


class StatutoryCalculationRequest(BaseModel):
    """
    Request schema for calculating statutory deductions for an employee.
    """
    employee_id: uuid.UUID = Field(..., description="ID of Employee")
    gross_salary: float = Field(..., ge=0, description="Monthly gross salary or eligible base for statutory calculation")
    calculation_date: Optional[datetime.date] = Field(None, description="Target calculation date (defaults to current date)")


class StatutoryDeductionResult(BaseModel):
    """
    Result item for a single statutory deduction rule evaluation.
    """
    rule_code: str
    rule_name: str
    rule_type: str
    calculation_method: str
    amount: float


class StatutoryCalculationResponse(BaseModel):
    """
    Response schema for statutory deduction calculation.
    """
    employee_id: uuid.UUID
    country_code: str
    gross_salary: float
    calculation_date: datetime.date
    total_statutory_deductions: float
    deductions: List[StatutoryDeductionResult]
