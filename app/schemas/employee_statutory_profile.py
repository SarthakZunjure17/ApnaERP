import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.country import CountryResponse
from app.schemas.employee import EmployeeResponse


class EmployeeStatutoryProfileCreate(BaseModel):
    """
    Schema for creating an Employee Statutory Profile.
    """
    employee_id: uuid.UUID = Field(..., description="ID of Employee")
    country_id: uuid.UUID = Field(..., description="ID of Country jurisdiction")
    pf_enabled: bool = Field(True, description="Enable Provident Fund deduction")
    esi_enabled: bool = Field(True, description="Enable ESI deduction")
    professional_tax_enabled: bool = Field(True, description="Enable Professional Tax deduction")
    income_tax_enabled: bool = Field(False, description="Enable Income Tax deduction")
    tax_identification_number: Optional[str] = Field(None, max_length=50, description="PAN / SSN")
    pf_number: Optional[str] = Field(None, max_length=50, description="UAN / PF Number")
    esi_number: Optional[str] = Field(None, max_length=50, description="ESI Number")
    effective_from: datetime.date = Field(..., description="Effective start date")
    effective_to: Optional[datetime.date] = Field(None, description="Optional effective end date")
    is_active: bool = Field(True, description="Active status flag")


class EmployeeStatutoryProfileUpdate(BaseModel):
    """
    Schema for updating an Employee Statutory Profile.
    """
    pf_enabled: Optional[bool] = None
    esi_enabled: Optional[bool] = None
    professional_tax_enabled: Optional[bool] = None
    income_tax_enabled: Optional[bool] = None
    tax_identification_number: Optional[str] = Field(None, max_length=50)
    pf_number: Optional[str] = Field(None, max_length=50)
    esi_number: Optional[str] = Field(None, max_length=50)
    effective_from: Optional[datetime.date] = None
    effective_to: Optional[datetime.date] = None
    is_active: Optional[bool] = None


class EmployeeStatutoryProfileResponse(BaseModel):
    """
    Response schema for an Employee Statutory Profile.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    country_id: uuid.UUID
    pf_enabled: bool
    esi_enabled: bool
    professional_tax_enabled: bool
    income_tax_enabled: bool
    tax_identification_number: Optional[str] = None
    pf_number: Optional[str] = None
    esi_number: Optional[str] = None
    effective_from: datetime.date
    effective_to: Optional[datetime.date] = None
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
    employee: Optional[EmployeeResponse] = None
    country: Optional[CountryResponse] = None
