import datetime
from typing import Optional
import uuid
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class LeaveRequest(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    LeaveRequest ORM model representing workflow-driven employee leave applications.
    Manages state transitions (Draft -> Pending -> Approved/Rejected -> Cancelled/Completed),
    day calculations, policy validations, and leave balance updates.
    """
    __tablename__ = "leave_requests"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign Key to Target Employee",
    )
    leave_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leave_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign Key to Leave Type Policy",
    )

    start_date: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Leave start date (inclusive)",
    )
    end_date: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Leave end date (inclusive)",
    )
    total_days: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Calculated net leave duration (excluding weekends/holidays)",
    )

    is_half_day: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if leave is for half a day",
    )
    half_day_session: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Half day session (e.g. First Half, Second Half, Morning, Afternoon)",
    )

    reason: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Employee leave application reason",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="Draft",
        nullable=False,
        index=True,
        comment="Workflow status: Draft, Pending, Approved, Rejected, Cancelled, Completed",
    )

    submitted_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when leave request was submitted for approval",
    )

    reviewed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when leave request was reviewed (approved/rejected)",
    )
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User ID of reviewer who approved/rejected the request",
    )
    reviewer_comments: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Approval/rejection comments from reviewer",
    )

    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id], lazy="joined")
    leave_type = relationship("LeaveType", foreign_keys=[leave_type_id], lazy="joined")
    reviewer = relationship("User", foreign_keys=[reviewed_by], lazy="selectin")

    def __repr__(self) -> str:
        return f"<LeaveRequest(id='{self.id}', employee_id='{self.employee_id}', status='{self.status}', dates='{self.start_date}' to '{self.end_date}', total_days={self.total_days})>"
