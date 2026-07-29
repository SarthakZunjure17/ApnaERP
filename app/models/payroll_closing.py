import datetime
from typing import Optional
import uuid
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class PayrollClosing(Base, UUIDMixin, TimestampMixin):
    """
    PayrollClosing ORM Model.
    Tracks payroll period closing, reopening audit trails, and archival states.
    """
    __tablename__ = "payroll_closings"

    payroll_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payroll_periods.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    closed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    closed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    reopened_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    reopened_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    closing_remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="Closed",
        nullable=False,
        index=True,
        comment="Open, Closed, Archived",
    )

    # Relationships
    payroll_period: Mapped["PayrollPeriod"] = relationship("PayrollPeriod")  # noqa: F821
    closed_by_user: Mapped["User"] = relationship("User", foreign_keys=[closed_by])  # noqa: F821
    reopened_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reopened_by])  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<PayrollClosing(id={self.id}, period_id={self.payroll_period_id}, "
            f"status='{self.status}')>"
        )
