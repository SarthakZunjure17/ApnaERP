import datetime
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.salary_structure import SalaryStructureResponse


class CompensationStatusEnum(str, Enum):
    DRAFT = "Draft"
    ACTIVE = "Active"
    EXPIRED = "Expired"
    CANCELLED = "Cancelled"


class EmployeeCompensationCreate(BaseModel):
    """
    Schema for assigning a new Salary Structure / Compensation policy to an Employee.
    """
    employee_id: uuid.UUID = Field(..., description="ID of the Employee receiving compensation assignment")
    salary_structure_id: uuid.UUID = Field(..., description="ID of the SalaryStructure template")
    effective_from: datetime.date = Field(..., description="Date when this compensation policy takes effect")
    effective_to: Optional[datetime.date] = Field(None, description="Optional end date when this policy expires")
    annual_ctc: float = Field(..., ge=0.0, description="Annual Cost to Company (CTC)")
    monthly_gross_salary: float = Field(..., ge=0.0, description="Monthly gross salary amount")
    monthly_net_salary: Optional[float] = Field(None, ge=0.0, description="Optional monthly net salary estimate")
    remarks: Optional[str] = Field(None, max_length=255, description="Justification or remarks")


class EmployeeCompensationRevise(BaseModel):
    """
    Schema for revising an existing Employee Compensation policy.
    """
    salary_structure_id: uuid.UUID = Field(..., description="ID of the updated SalaryStructure template")
    effective_from: datetime.date = Field(..., description="Start date of the revised compensation policy")
    effective_to: Optional[datetime.date] = Field(None, description="Optional end date of the revised policy")
    annual_ctc: float = Field(..., ge=0.0, description="Revised annual Cost to Company (CTC)")
    monthly_gross_salary: float = Field(..., ge=0.0, description="Revised monthly gross salary amount")
    monthly_net_salary: Optional[float] = Field(None, ge=0.0, description="Optional revised monthly net salary estimate")
    remarks: Optional[str] = Field(None, max_length=255, description="Revision justification remarks")


class EmployeeCompensationUpdate(BaseModel):
    """
    Schema for updating an existing Employee Compensation draft.
    """
    effective_from: Optional[datetime.date] = None
    effective_to: Optional[datetime.date] = None
    annual_ctc: Optional[float] = Field(None, ge=0.0)
    monthly_gross_salary: Optional[float] = Field(None, ge=0.0)
    monthly_net_salary: Optional[float] = Field(None, ge=0.0)
    remarks: Optional[str] = Field(None, max_length=255)


class EmployeeCompensationResponse(BaseModel):
    """
    Response schema for Employee Compensation policy details.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    salary_structure_id: uuid.UUID
    effective_from: datetime.date
    effective_to: Optional[datetime.date] = None
    annual_ctc: float
    monthly_gross_salary: float
    monthly_net_salary: Optional[float] = None
    status: str
    revision_number: int
    previous_compensation_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = None
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    salary_structure: Optional[SalaryStructureResponse] = None


class EmployeeCompensationListResponse(BaseModel):
    """
    Paginated response schema for Employee Compensation records.
    """
    items: List[EmployeeCompensationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
