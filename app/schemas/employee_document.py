import datetime
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class DocumentType(str, Enum):
    AADHAAR = "Aadhaar"
    PAN = "PAN"
    PASSPORT = "Passport"
    DRIVING_LICENSE = "Driving License"
    RESUME = "Resume"
    OFFER_LETTER = "Offer Letter"
    APPOINTMENT_LETTER = "Appointment Letter"
    EXPERIENCE_LETTER = "Experience Letter"
    EDUCATION_CERTIFICATE = "Education Certificate"
    SALARY_SLIP = "Salary Slip"
    CONTRACT = "Contract"
    NDA = "NDA"
    MEDICAL_CERTIFICATE = "Medical Certificate"
    OTHER = "Other"


class VerificationStatus(str, Enum):
    PENDING = "Pending"
    VERIFIED = "Verified"
    REJECTED = "Rejected"


class EmployeeDocumentBase(BaseModel):
    employee_id: uuid.UUID = Field(..., description="Linked employee ID")
    file_id: uuid.UUID = Field(..., description="Linked storage File ID")
    document_type: DocumentType = Field(..., description="Type category of personnel document")
    document_number: Optional[str] = Field(None, max_length=100, description="Document identification number")

    issue_date: Optional[datetime.date] = Field(None, description="Document issuance date")
    expiry_date: Optional[datetime.date] = Field(None, description="Document expiration date")

    notes: Optional[str] = Field(None, description="Additional document notes or comments")
    is_mandatory: bool = Field(default=False, description="Mandatory document indicator")
    is_active: bool = Field(default=True, description="Active document status")


class EmployeeDocumentCreate(EmployeeDocumentBase):
    """Schema for creating/linking an Employee Document."""
    pass


class EmployeeDocumentUpdate(BaseModel):
    """Schema for updating an Employee Document."""
    document_number: Optional[str] = Field(None, max_length=100)
    issue_date: Optional[datetime.date] = None
    expiry_date: Optional[datetime.date] = None
    notes: Optional[str] = None
    is_mandatory: Optional[bool] = None
    is_active: Optional[bool] = None


class DocumentVerifyRequest(BaseModel):
    """Schema for verifying a document."""
    notes: Optional[str] = Field(None, description="Optional verification approval notes")


class DocumentRejectRequest(BaseModel):
    """Schema for rejecting a document."""
    notes: Optional[str] = Field(None, description="Rejection reason or notes")


class EmployeeDocumentResponse(EmployeeDocumentBase):
    """Full Employee Document response schema."""
    id: uuid.UUID
    verification_status: VerificationStatus
    verified_by: Optional[uuid.UUID] = None
    verified_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    deleted_at: Optional[datetime.datetime] = None
    is_deleted: bool = False

    model_config = ConfigDict(from_attributes=True)


class EmployeeDocumentListResponse(BaseModel):
    """Paginated list of Employee Documents."""
    total: int
    page: int
    page_size: int
    items: List[EmployeeDocumentResponse]
