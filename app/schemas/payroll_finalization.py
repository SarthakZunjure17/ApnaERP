import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


# Enums
class AdjustmentTypeEnum(str, Enum):
    BONUS = "Bonus"
    INCENTIVE = "Incentive"
    COMMISSION = "Commission"
    OVERTIME = "Overtime"
    ARREAR = "Arrear"
    REIMBURSEMENT = "Reimbursement"
    LOAN_RECOVERY = "Loan Recovery"
    MANUAL_ADDITION = "Manual Addition"
    MANUAL_DEDUCTION = "Manual Deduction"


class AdjustmentStatusEnum(str, Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    APPLIED = "Applied"


class ReportTypeEnum(str, Enum):
    SALARY_REGISTER = "Salary Register"
    DEPARTMENT_WISE_PAYROLL = "Department-wise Payroll"
    EMPLOYEE_SALARY_HISTORY = "Employee Salary History"
    PAYROLL_SUMMARY = "Payroll Summary"
    DEDUCTION_SUMMARY = "Deduction Summary"
    EARNINGS_SUMMARY = "Earnings Summary"
    COST_CENTER_REPORT = "Cost Center Report"
    MONTHLY_PAYROLL_REGISTER = "Monthly Payroll Register"


class ReportFormatEnum(str, Enum):
    PDF = "PDF"
    EXCEL = "EXCEL"
    CSV = "CSV"


class ClosingStatusEnum(str, Enum):
    OPEN = "Open"
    CLOSED = "Closed"
    ARCHIVED = "Archived"


class PostingStatusEnum(str, Enum):
    PENDING = "Pending"
    POSTED = "Posted"
    FAILED = "Failed"


# --- Payroll Adjustment DTOs ---

class PayrollAdjustmentCreate(BaseModel):
    employee_id: uuid.UUID
    payroll_period_id: uuid.UUID
    adjustment_type: AdjustmentTypeEnum
    amount: Decimal = Field(..., gt=0, description="Numerical amount")
    currency: str = Field(default="INR", max_length=10)
    description: Optional[str] = None


class PayrollAdjustmentUpdate(BaseModel):
    amount: Optional[Decimal] = Field(default=None, gt=0)
    currency: Optional[str] = Field(default=None, max_length=10)
    description: Optional[str] = None
    status: Optional[AdjustmentStatusEnum] = None


class PayrollAdjustmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    payroll_period_id: uuid.UUID
    adjustment_type: str
    amount: Decimal
    currency: str
    description: Optional[str] = None
    status: str
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


# --- Payroll Report Snapshots ---

class PayrollReportGenerateRequest(BaseModel):
    payroll_period_id: uuid.UUID
    report_type: ReportTypeEnum
    format: ReportFormatEnum = ReportFormatEnum.PDF
    department_id: Optional[uuid.UUID] = None
    employee_id: Optional[uuid.UUID] = None


class PayrollReportSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payroll_period_id: uuid.UUID
    report_type: str
    format: str
    generated_by: uuid.UUID
    generated_at: datetime.datetime
    file_id: Optional[uuid.UUID] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime.datetime


# --- Analytics ---

class DepartmentPayrollCost(BaseModel):
    department_id: Optional[str] = None
    department_name: str
    employee_count: int
    total_gross_pay: Decimal
    total_net_pay: Decimal


class PayrollTrendItem(BaseModel):
    payroll_period_id: str
    period_name: str
    total_cost: Decimal
    employee_count: int


class PayrollAnalyticsResponse(BaseModel):
    total_payroll_cost: Decimal
    average_salary: Decimal
    total_earnings: Decimal
    total_deductions: Decimal
    employee_count: int
    highest_salary: Decimal
    lowest_salary: Decimal
    department_costs: List[DepartmentPayrollCost]
    payroll_trends: List[PayrollTrendItem]


# --- Bank Export ---

class BankExportRequest(BaseModel):
    payroll_period_id: uuid.UUID
    bank_format: str = Field(default="STANDARD_CSV", description="Bank export format code")


class BankExportResponse(BaseModel):
    payroll_period_id: uuid.UUID
    file_id: uuid.UUID
    file_name: str
    record_count: int
    total_amount: Decimal
    generated_at: datetime.datetime


# --- Payroll Closing ---

class PayrollClosingRequest(BaseModel):
    closing_remarks: Optional[str] = None


class PayrollReopenRequest(BaseModel):
    reopen_reason: str = Field(..., min_length=5, description="Audited reason for reopening closed payroll")


class PayrollClosingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payroll_period_id: uuid.UUID
    closed_by: uuid.UUID
    closed_at: datetime.datetime
    reopened_by: Optional[uuid.UUID] = None
    reopened_at: Optional[datetime.datetime] = None
    closing_remarks: Optional[str] = None
    status: str
    created_at: datetime.datetime


# --- Financial Integration Queue ---

class FinancialPostingQueueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payroll_period_id: uuid.UUID
    posting_status: str
    payload: Dict[str, Any]
    posted_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
