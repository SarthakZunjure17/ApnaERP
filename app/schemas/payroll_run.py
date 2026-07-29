import datetime
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.payroll_period import PayrollPeriodResponse


class PayrollRunTypeEnum(str, Enum):
    REGULAR = "Regular"
    OFF_CYCLE = "Off Cycle"
    ADJUSTMENT = "Adjustment"


class PayrollRunStatusEnum(str, Enum):
    DRAFT = "Draft"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    LOCKED = "Locked"


class PayrollRunCreate(BaseModel):
    """
    Schema for creating a new Payroll Run batch.
    """
    payroll_period_id: uuid.UUID = Field(..., description="ID of parent Payroll Period")
    run_type: PayrollRunTypeEnum = Field(PayrollRunTypeEnum.REGULAR, description="Run type: Regular, Off Cycle, Adjustment")
    remarks: Optional[str] = Field(None, max_length=255, description="Optional operational remarks")


class PayrollRunUpdate(BaseModel):
    """
    Schema for updating a Payroll Run in Draft state.
    """
    remarks: Optional[str] = Field(None, max_length=255)


class PayrollRunResponse(BaseModel):
    """
    Response schema for a Payroll Run execution batch.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payroll_period_id: uuid.UUID
    run_number: str
    run_type: str
    status: str
    started_by: Optional[uuid.UUID] = None
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    locked_at: Optional[datetime.datetime] = None
    remarks: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    payroll_period: Optional[PayrollPeriodResponse] = None
