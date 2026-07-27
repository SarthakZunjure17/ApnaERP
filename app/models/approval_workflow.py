import datetime
from typing import List, Optional
import uuid
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class ApprovalWorkflow(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    ApprovalWorkflow ORM model representing reusable approval workflow definitions.
    Defines module placement, workflow codes, names, and active status.
    """
    __tablename__ = "approval_workflows"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique workflow code identifier (e.g. WF_LEAVE_DEFAULT)",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
        comment="Human-readable workflow name (e.g. Standard Leave Approval Workflow)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Detailed workflow description",
    )
    module_name: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
        comment="Associated module name (e.g. leave, expense, purchase_order, platform)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="True if workflow definition is active",
    )

    # Relationships
    steps: Mapped[List["ApprovalStep"]] = relationship(
        "ApprovalStep",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="ApprovalStep.step_number",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<ApprovalWorkflow(code='{self.code}', name='{self.name}', module='{self.module_name}')>"


class ApprovalStep(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    ApprovalStep ORM model representing sequenced approval steps within a workflow.
    Bound to specific Role requirements.
    """
    __tablename__ = "approval_steps"
    __table_args__ = (
        UniqueConstraint("workflow_id", "step_number", name="uq_workflow_step_number"),
    )

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approval_workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent ApprovalWorkflow",
    )
    step_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Sequential step number (1, 2, 3...)",
    )
    approver_role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to Role authorized to approve this step",
    )
    required_approvals: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Number of required approvals at this step",
    )
    auto_approve: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if step is auto-approved under business conditions",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="True if step is active",
    )

    # Relationships
    workflow: Mapped["ApprovalWorkflow"] = relationship("ApprovalWorkflow", back_populates="steps")
    approver_role = relationship("Role", foreign_keys=[approver_role_id], lazy="joined")

    def __repr__(self) -> str:
        return f"<ApprovalStep(workflow_id='{self.workflow_id}', step={self.step_number}, role_id='{self.approver_role_id}')>"


class ApprovalRequest(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    ApprovalRequest ORM model representing active workflow approval execution instances.
    Points to generic target entity (entity_type, entity_id).
    """
    __tablename__ = "approval_requests"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approval_workflows.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to ApprovalWorkflow definition",
    )

    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Target domain entity type (e.g. LeaveRequest, ExpenseClaim, PurchaseOrder)",
    )
    entity_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Target domain entity ID/UUID",
    )

    current_step_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Current pending step number in approval sequence",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="Pending",
        nullable=False,
        index=True,
        comment="Approval status: Draft, Pending, Approved, Rejected, Cancelled",
    )

    submitted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to User who submitted the request",
    )
    submitted_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Submission timestamp (UTC)",
    )

    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Completion timestamp (UTC) when approved/rejected/cancelled",
    )

    # Relationships
    workflow: Mapped["ApprovalWorkflow"] = relationship("ApprovalWorkflow", lazy="joined")
    submitter = relationship("User", foreign_keys=[submitted_by], lazy="joined")
    history: Mapped[List["ApprovalHistory"]] = relationship(
        "ApprovalHistory",
        back_populates="approval_request",
        cascade="all, delete-orphan",
        order_by="ApprovalHistory.action_time",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<ApprovalRequest(id='{self.id}', entity='{self.entity_type}:{self.entity_id}', status='{self.status}', step={self.current_step_number})>"


class ApprovalHistory(Base, UUIDMixin, TimestampMixin):
    """
    ApprovalHistory ORM model representing immutable audit log entries of every approval action.
    """
    __tablename__ = "approval_histories"

    approval_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approval_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent ApprovalRequest",
    )
    step_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Step number at which action was taken",
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Action performed: Submitting, Approved Step, Rejected, Cancelled, Completed Workflow",
    )
    comments: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Comments/justification provided by action performer",
    )
    performed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to User who performed the action",
    )
    action_time: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Timestamp when action was performed (UTC)",
    )

    # Relationships
    approval_request: Mapped["ApprovalRequest"] = relationship("ApprovalRequest", back_populates="history")
    performer = relationship("User", foreign_keys=[performed_by], lazy="selectin")

    def __repr__(self) -> str:
        return f"<ApprovalHistory(request_id='{self.approval_request_id}', step={self.step_number}, action='{self.action}', by='{self.performed_by}')>"
