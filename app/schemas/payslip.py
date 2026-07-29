import datetime
from enum import Enum
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.employee import EmployeeResponse
from app.schemas.file import FileResponse
from app.schemas.payroll_period import PayrollPeriodResponse


class PayslipStatusEnum(str, Enum):
    DRAFT = "Draft"
    GENERATED = "Generated"
    PUBLISHED = "Published"


class PayslipResponse(BaseModel):
    """
    Response schema for an employee Payslip document.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payroll_record_id: uuid.UUID
    payslip_number: str
    employee_id: uuid.UUID
    payroll_period_id: uuid.UUID
    gross_salary: float
    total_earnings: float
    total_deductions: float
    net_salary: float
    pdf_file_id: Optional[uuid.UUID] = None
    generated_at: Optional[datetime.datetime] = None
    published_at: Optional[datetime.datetime] = None
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    employee: Optional[EmployeeResponse] = None
    payroll_period: Optional[PayrollPeriodResponse] = None
    pdf_file: Optional[FileResponse] = None
