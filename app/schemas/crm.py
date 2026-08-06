from datetime import datetime
from decimal import Decimal
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Lead Source Schemas ---
class LeadSourceBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    is_active: bool = True


class LeadSourceCreate(LeadSourceBase):
    pass


class LeadSourceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class LeadSourceResponse(LeadSourceBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Lead Tag Schemas ---
class LeadTagCreate(BaseModel):
    name: str = Field(..., max_length=50)
    color: Optional[str] = "#3B82F6"


class LeadTagResponse(BaseModel):
    id: uuid.UUID
    name: str
    color: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Lead Note Schemas ---
class LeadNoteCreate(BaseModel):
    content: str
    is_private: bool = False
    is_pinned: bool = False


class LeadNoteResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    author_id: Optional[uuid.UUID]
    content: str
    is_private: bool
    is_pinned: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Lead Schemas ---
class LeadBase(BaseModel):
    first_name: str = Field(..., max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    company: Optional[str] = Field(None, max_length=255)
    title: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    status: str = Field("New", max_length=50)
    source_id: Optional[uuid.UUID] = None
    assigned_to_id: Optional[uuid.UUID] = None
    estimated_value: Decimal = Field(Decimal("0.00"), ge=0)


class LeadCreate(LeadBase):
    tag_ids: Optional[List[uuid.UUID]] = None


class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    source_id: Optional[uuid.UUID] = None
    assigned_to_id: Optional[uuid.UUID] = None
    estimated_value: Optional[Decimal] = None
    score: Optional[int] = None
    tag_ids: Optional[List[uuid.UUID]] = None


class LeadResponse(LeadBase):
    id: uuid.UUID
    lead_code: str
    score: int
    is_converted: bool
    converted_at: Optional[datetime] = None
    converted_opportunity_id: Optional[uuid.UUID] = None
    converted_customer_id: Optional[uuid.UUID] = None
    source: Optional[LeadSourceResponse] = None
    tags: List[LeadTagResponse] = []
    notes: List[LeadNoteResponse] = []
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LeadMergeRequest(BaseModel):
    primary_lead_id: uuid.UUID
    secondary_lead_ids: List[uuid.UUID]


# --- Opportunity Stage Schemas ---
class OpportunityStageBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    probability_default: Decimal = Field(Decimal("10.00"), ge=0, le=100)
    display_order: int = 0
    is_active: bool = True


class OpportunityStageCreate(OpportunityStageBase):
    pass


class OpportunityStageResponse(OpportunityStageBase):
    id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Opportunity Schemas ---
class OpportunityBase(BaseModel):
    title: str = Field(..., max_length=255)
    customer_id: Optional[uuid.UUID] = None
    lead_id: Optional[uuid.UUID] = None
    stage_id: uuid.UUID
    expected_revenue: Decimal = Field(Decimal("0.00"), ge=0)
    probability: Optional[Decimal] = None
    expected_closing_date: Optional[datetime] = None
    owner_id: Optional[uuid.UUID] = None
    competitors: Optional[str] = None
    products_of_interest: Optional[str] = None


class OpportunityCreate(OpportunityBase):
    pass


class OpportunityUpdate(BaseModel):
    title: Optional[str] = None
    customer_id: Optional[uuid.UUID] = None
    stage_id: Optional[uuid.UUID] = None
    expected_revenue: Optional[Decimal] = None
    probability: Optional[Decimal] = None
    expected_closing_date: Optional[datetime] = None
    owner_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    won_reason: Optional[str] = None
    lost_reason: Optional[str] = None
    competitors: Optional[str] = None
    products_of_interest: Optional[str] = None


class OpportunityResponse(OpportunityBase):
    id: uuid.UUID
    opportunity_code: str
    status: str
    won_reason: Optional[str] = None
    lost_reason: Optional[str] = None
    stage: Optional[OpportunityStageResponse] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class OpportunityWinLossRequest(BaseModel):
    status: str = Field(..., max_length=50)  # 'Won' or 'Lost'
    reason: Optional[str] = None


# --- Activity Schemas ---
class ActivityBase(BaseModel):
    activity_type: str = Field(..., max_length=50)  # Call, Meeting, Email, Task, Follow-up, Reminder
    subject: str = Field(..., max_length=255)
    description: Optional[str] = None
    status: str = Field("Pending", max_length=50)
    priority: str = Field("Medium", max_length=20)
    due_date: Optional[datetime] = None
    owner_id: Optional[uuid.UUID] = None
    lead_id: Optional[uuid.UUID] = None
    opportunity_id: Optional[uuid.UUID] = None
    customer_id: Optional[uuid.UUID] = None
    campaign_id: Optional[uuid.UUID] = None
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None


class ActivityCreate(ActivityBase):
    pass


class ActivityUpdate(BaseModel):
    subject: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    owner_id: Optional[uuid.UUID] = None


class ActivityResponse(ActivityBase):
    id: uuid.UUID
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Meeting Schemas ---
class MeetingBase(BaseModel):
    subject: str = Field(..., max_length=255)
    meeting_type: str = Field("Meeting", max_length=50)
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    status: str = Field("Scheduled", max_length=50)
    organizer_id: Optional[uuid.UUID] = None
    lead_id: Optional[uuid.UUID] = None
    opportunity_id: Optional[uuid.UUID] = None
    customer_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class MeetingCreate(MeetingBase):
    pass


class MeetingUpdate(BaseModel):
    subject: Optional[str] = None
    meeting_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class MeetingResponse(MeetingBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Task Schemas ---
class TaskBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    status: str = Field("Pending", max_length=50)
    priority: str = Field("Medium", max_length=20)
    due_date: Optional[datetime] = None
    assigned_to_id: Optional[uuid.UUID] = None
    parent_task_id: Optional[uuid.UUID] = None
    lead_id: Optional[uuid.UUID] = None
    opportunity_id: Optional[uuid.UUID] = None
    customer_id: Optional[uuid.UUID] = None
    campaign_id: Optional[uuid.UUID] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    assigned_to_id: Optional[uuid.UUID] = None
    parent_task_id: Optional[uuid.UUID] = None


class TaskResponse(TaskBase):
    id: uuid.UUID
    task_code: str
    created_by_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Campaign Schemas ---
class CampaignBase(BaseModel):
    name: str = Field(..., max_length=255)
    type: str = Field("Email", max_length=50)
    status: str = Field("Planning", max_length=50)
    budget: Decimal = Field(Decimal("0.00"), ge=0)
    actual_cost: Decimal = Field(Decimal("0.00"), ge=0)
    expected_revenue: Decimal = Field(Decimal("0.00"), ge=0)
    actual_revenue: Decimal = Field(Decimal("0.00"), ge=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    owner_id: Optional[uuid.UUID] = None


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    budget: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    expected_revenue: Optional[Decimal] = None
    actual_revenue: Optional[Decimal] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    owner_id: Optional[uuid.UUID] = None


class CampaignMemberCreate(BaseModel):
    lead_id: Optional[uuid.UUID] = None
    customer_id: Optional[uuid.UUID] = None
    status: str = Field("Invited", max_length=50)


class CampaignMemberResponse(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    lead_id: Optional[uuid.UUID] = None
    customer_id: Optional[uuid.UUID] = None
    status: str
    joined_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CampaignResponse(CampaignBase):
    id: uuid.UUID
    campaign_code: str
    members: List[CampaignMemberResponse] = []
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Lead Conversion Engine Schemas ---
class LeadConversionRequest(BaseModel):
    lead_id: uuid.UUID
    opportunity_title: Optional[str] = None
    stage_id: Optional[uuid.UUID] = None
    expected_revenue: Optional[Decimal] = None
    existing_customer_id: Optional[uuid.UUID] = None  # If null, search or create Customer


class LeadConversionResponse(BaseModel):
    lead_id: uuid.UUID
    opportunity_id: uuid.UUID
    customer_id: uuid.UUID
    is_existing_customer: bool
    converted_at: datetime


# --- Timeline Schemas ---
class TimelineEventResponse(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    event_type: str
    title: str
    description: Optional[str] = None
    timestamp: datetime
    user_id: Optional[uuid.UUID] = None
    extra_data: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(from_attributes=True)


# --- Analytics & Search Schemas ---
class CRMAnalyticsSummary(BaseModel):
    total_leads: int
    converted_leads: int
    conversion_rate: float
    total_opportunities: int
    open_opportunities_value: Decimal
    forecast_revenue: Decimal
    total_campaigns: int
    average_campaign_roi: float


class LeadFunnelReport(BaseModel):
    stage_counts: Dict[str, int]
    stage_values: Dict[str, Decimal]


class CampaignROIReport(BaseModel):
    campaign_id: uuid.UUID
    campaign_name: str
    budget: Decimal
    actual_cost: Decimal
    actual_revenue: Decimal
    roi_percentage: float


class CRMSearchResult(BaseModel):
    leads: List[LeadResponse] = []
    opportunities: List[OpportunityResponse] = []
    campaigns: List[CampaignResponse] = []
    tasks: List[TaskResponse] = []
    meetings: List[MeetingResponse] = []
