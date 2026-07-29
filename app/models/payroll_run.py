import datetime
from typing import Optional
import uuid
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class PayrollRun(Base, UUIDMixin, TimestampMixin):
    """
    PayrollRun ORM model representing a structured payroll execution batch.
    Groups payroll records into Regular, Off Cycle, or Adjustment runs per period.
    """
    __tablename__ = "payroll_runs"
    __table_args__ = (
        UniqueConstraint("payroll_period_id", "run_type", name="uq_period_run_type"),
    )

    payroll_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payroll_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to parent PayrollPeriod",
    )
    run_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique payroll run number (e.g. RUN-202601-001)",
    )
    run_type: Mapped[str] = mapped_column(
        String(30),
        default="Regular",
        nullable=False,
        index=True,
        comment="Type of payroll run: Regular, Off Cycle, Adjustment",
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="Draft",
        nullable=False,
        index=True,
        comment="Run status: Draft, Processing, Completed, Locked",
    )
    started_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who initiated the run execution",
    )
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when run was started",
    )
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when run finished completion",
    )
    locked_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when run was permanently locked",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Optional operational remarks or notes for this run",
    )

    # Relationships
    payroll_period: Mapped["PayrollPeriod"] = relationship("PayrollPeriod", lazy="selectin")
    starter: Mapped[Optional["User"]] = relationship("User", foreign_keys=[started_by], lazy="selectin")

    def __repr__(self) -> str:
        return f"<PayrollRun(run_number='{self.run_number}', period_id='{self.payroll_period_id}', type='{self.run_type}', status='{self.status}')>"
