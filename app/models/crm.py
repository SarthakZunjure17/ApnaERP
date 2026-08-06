from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import List, Optional
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


# Association table for Lead Tags
lead_tags_association = Table(
    "lead_tags_association",
    Base.metadata,
    Column("lead_id", UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("lead_tags.id", ondelete="CASCADE"), primary_key=True),
)


class LeadSource(Base, UUIDMixin, TimestampMixin):
    """LeadSource ORM model."""
    __tablename__ = "lead_sources"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class LeadTag(Base, UUIDMixin, TimestampMixin):
    """LeadTag ORM model."""
    __tablename__ = "lead_tags"

    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(20), default="#3B82F6", nullable=True)


class Lead(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Lead ORM model."""
    __tablename__ = "leads"

    lead_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="New", index=True, nullable=False)
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lead_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    
    is_converted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    converted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    converted_opportunity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    converted_customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )

    source: Mapped[Optional[LeadSource]] = relationship("LeadSource", lazy="selectin")
    assigned_to: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_id], lazy="selectin")
    tags: Mapped[List[LeadTag]] = relationship("LeadTag", secondary=lead_tags_association, lazy="selectin")
    notes: Mapped[List["LeadNote"]] = relationship("LeadNote", back_populates="lead", cascade="all, delete-orphan", lazy="selectin")


class LeadNote(Base, UUIDMixin, TimestampMixin):
    """LeadNote ORM model."""
    __tablename__ = "lead_notes"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    lead: Mapped[Lead] = relationship("Lead", back_populates="notes")
    author: Mapped[Optional["User"]] = relationship("User", lazy="selectin")


class OpportunityStage(Base, UUIDMixin, TimestampMixin):
    """OpportunityStage ORM model."""
    __tablename__ = "opportunity_stages"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    probability_default: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("10.00"), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Opportunity(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Opportunity ORM model."""
    __tablename__ = "opportunities"

    opportunity_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True
    )
    stage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunity_stages.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    expected_revenue: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    probability: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("50.00"), nullable=False)
    expected_closing_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="Open", index=True, nullable=False)
    won_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lost_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    competitors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    products_of_interest: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    stage: Mapped[OpportunityStage] = relationship("OpportunityStage", lazy="selectin")
    customer: Mapped[Optional["Customer"]] = relationship("Customer", lazy="selectin")
    lead: Mapped[Optional[Lead]] = relationship("Lead", lazy="selectin")
    owner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[owner_id], lazy="selectin")


class Activity(Base, UUIDMixin, TimestampMixin):
    """Activity ORM model (Calls, Emails, Tasks, Reminders, Follow-ups)."""
    __tablename__ = "activities"

    activity_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    subject: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Pending", index=True, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="Medium", nullable=False)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=True, index=True
    )
    opportunity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=True, index=True
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True
    )

    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurrence_rule: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    owner: Mapped[Optional["User"]] = relationship("User", lazy="selectin")


class Meeting(Base, UUIDMixin, TimestampMixin):
    """Meeting / Customer Visit / Appointment ORM model."""
    __tablename__ = "meetings"

    subject: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    meeting_type: Mapped[str] = mapped_column(String(50), default="Meeting", index=True, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    meeting_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Scheduled", index=True, nullable=False)
    organizer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=True, index=True
    )
    opportunity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=True, index=True
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    organizer: Mapped[Optional["User"]] = relationship("User", lazy="selectin")


class Task(Base, UUIDMixin, TimestampMixin):
    """Task ORM model."""
    __tablename__ = "crm_tasks"

    task_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Pending", index=True, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="Medium", nullable=False)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    assigned_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    parent_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crm_tasks.id", ondelete="SET NULL"), nullable=True
    )

    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=True, index=True
    )
    opportunity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=True, index=True
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True
    )

    assigned_to: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_id], lazy="selectin")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id], lazy="selectin")


class Campaign(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Campaign ORM model."""
    __tablename__ = "campaigns"

    campaign_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="Email", index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Planning", index=True, nullable=False)
    budget: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    expected_revenue: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    actual_revenue: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    owner: Mapped[Optional["User"]] = relationship("User", lazy="selectin")
    members: Mapped[List["CampaignMember"]] = relationship(
        "CampaignMember", back_populates="campaign", cascade="all, delete-orphan", lazy="selectin"
    )


class CampaignMember(Base, UUIDMixin, TimestampMixin):
    """CampaignMember ORM model."""
    __tablename__ = "campaign_members"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=True, index=True
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="Invited", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    campaign: Mapped[Campaign] = relationship("Campaign", back_populates="members")
    lead: Mapped[Optional[Lead]] = relationship("Lead", lazy="selectin")
    customer: Mapped[Optional["Customer"]] = relationship("Customer", lazy="selectin")


class CRMReportSnapshot(Base, UUIDMixin, TimestampMixin):
    """CRMReportSnapshot ORM model."""
    __tablename__ = "crm_report_snapshots"

    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), default="Daily", nullable=False)
    total_leads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_opportunities: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    forecast_revenue: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    pipeline_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    conversion_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    metrics_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


class TimelineEvent(Base, UUIDMixin, TimestampMixin):
    """TimelineEvent ORM model for unified customer interaction logging."""
    __tablename__ = "timeline_events"

    entity_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # 'Lead', 'Opportunity', 'Customer', 'Campaign'
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
