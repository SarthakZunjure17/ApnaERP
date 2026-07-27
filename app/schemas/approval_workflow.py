import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ApprovalStepCreate(BaseModel):
    """
    Schema for defining a single step within an Approval Workflow.
    """
    step_number: int = Field(..., ge=1, description="Sequential step number (1, 2, 3...)")
    approver_role_id: uuid.UUID = Field(..., description="Role ID authorized to approve this step")
    required_approvals: int = Field(1, ge=1, description="Number of required approvals at this step")
    auto_approve: bool = Field(False, description="True if step is auto-approved under business rules")
    is_active: bool = Field(True, description="True if step is active")


class ApprovalStepResponse(BaseModel):
    """
    Response schema for an Approval Step.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_id: uuid.UUID
    step_number: int
    approver_role_id: uuid.UUID
    approver_role_name: Optional[str] = None
    required_approvals: int
    auto_approve: bool
    is_active: bool


class ApprovalWorkflowCreate(BaseModel):
    """
    Schema for creating a new Approval Workflow definition.
    """
    code: str = Field(..., min_length=2, max_length=50, description="Unique workflow code (e.g. WF_LEAVE_STD)")
    name: str = Field(..., min_length=2, max_length=100, description="Human readable workflow name")
    description: Optional[str] = Field(None, max_length=255, description="Workflow description")
    module_name: str = Field(..., min_length=2, max_length=50, description="Associated module name (e.g. leave, expense)")
    is_active: bool = Field(True, description="Active status")
    steps: List[ApprovalStepCreate] = Field(default_factory=list, description="Ordered approval steps")


class ApprovalWorkflowUpdate(BaseModel):
    """
    Schema for updating an existing Approval Workflow definition.
    """
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    module_name: Optional[str] = Field(None, min_length=2, max_length=50)
    is_active: Optional[bool] = None
    steps: Optional[List[ApprovalStepCreate]] = None


class ApprovalWorkflowResponse(BaseModel):
    """
    Response schema for an Approval Workflow definition.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None
    module_name: str
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
    steps: List[ApprovalStepResponse] = []


class ApprovalWorkflowListResponse(BaseModel):
    """
    Paginated response schema for Approval Workflows.
    """
    items: List[ApprovalWorkflowResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ApprovalRequestCreate(BaseModel):
    """
    Schema for initiating a new Approval Request for a target domain entity.
    """
    workflow_code: str = Field(..., description="Target workflow definition code")
    entity_type: str = Field(..., description="Target domain entity type (e.g. LeaveRequest, ExpenseClaim)")
    entity_id: str = Field(..., description="Target domain entity ID/UUID")
    comments: Optional[str] = Field(None, max_length=500, description="Submission comments")


class ApprovalActionRequest(BaseModel):
    """
    Schema for approving, rejecting, or cancelling an Approval Request.
    """
    comments: Optional[str] = Field(None, max_length=500, description="Action comments/justification")


class ApprovalHistoryResponse(BaseModel):
    """
    Response schema for an immutable Approval History record.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    approval_request_id: uuid.UUID
    step_number: int
    action: str
    comments: Optional[str] = None
    performed_by: uuid.UUID
    performer_name: Optional[str] = None
    action_time: datetime.datetime


class ApprovalRequestResponse(BaseModel):
    """
    Response schema for an Approval Request execution instance.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_id: uuid.UUID
    entity_type: str
    entity_id: str
    current_step_number: int
    status: str
    submitted_by: uuid.UUID
    submitted_at: datetime.datetime
    completed_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    workflow_code: Optional[str] = None
    workflow_name: Optional[str] = None
    submitter_name: Optional[str] = None
    history: List[ApprovalHistoryResponse] = []


class ApprovalRequestListResponse(BaseModel):
    """
    Paginated response schema for Approval Requests.
    """
    items: List[ApprovalRequestResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
