import datetime
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class PayrollPeriodStatusEnum(str, Enum):
    DRAFT = "Draft"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    LOCKED = "Locked"


class PayrollRecordStatusEnum(str, Enum):
    DRAFT = "Draft"
    CALCULATED = "Calculated"
    APPROVED = "Approved"
    PAID = "Paid"


class PayrollPeriodCreate(BaseModel):
    """
    Schema for creating a new Payroll Period cycle.
    """
    period_code: str = Field(..., min_length=2, max_length=50, description="Unique period code (e.g. 2026-01, PAY_2026_01)")
    start_date: datetime.date = Field(..., description="Start date of payroll period")
    end_date: datetime.date = Field(..., description="End date of payroll period")


class PayrollPeriodResponse(BaseModel):
    """
    Response schema for a Payroll Period.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    period_code: str
    start_date: datetime.date
    end_date: datetime.date
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


class PayrollPeriodListResponse(BaseModel):
    """
    Paginated response schema for Payroll Periods.
    """
    items: List[PayrollPeriodResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PayrollRecordComponentResponse(BaseModel):
    """
    Response schema for line-item components in a generated payroll record.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payroll_record_id: uuid.UUID
    salary_component_id: uuid.UUID
    component_name: str
    component_type: str
    amount: float


class PayrollRecordResponse(BaseModel):
    """
    Response schema for a generated employee payroll record.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payroll_period_id: uuid.UUID
    employee_id: uuid.UUID
    employee_compensation_id: uuid.UUID
    working_days: int
    present_days: float
    leave_days: float
    paid_leave_days: float
    unpaid_leave_days: float
    overtime_hours: float
    gross_salary: float
    total_earnings: float
    total_deductions: float
    net_salary: float
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    components: List[PayrollRecordComponentResponse] = []


class PayrollRecordListResponse(BaseModel):
    """
    Paginated response schema for Employee Payroll Records.
    """
    items: List[PayrollRecordResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PayrollSummaryResponse(BaseModel):
    """
    Summary response schema for a Payroll Period run.
    """
    payroll_period_id: uuid.UUID
    period_code: str
    total_employees: int
    total_gross_salary: float
    total_earnings: float
    total_deductions: float
    total_net_salary: float
    status: str
