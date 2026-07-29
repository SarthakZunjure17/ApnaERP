import datetime
from typing import Any, Dict, Optional
import uuid
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class FinancialPostingQueue(Base, UUIDMixin, TimestampMixin):
    """
    FinancialPostingQueue ORM Model.
    Exposes and queues structured financial posting payloads (gross pay, statutory liabilities, net payables)
    for future General Ledger / Accounting integration without executing GL entries directly.
    """
    __tablename__ = "financial_posting_queues"

    payroll_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payroll_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    posting_status: Mapped[str] = mapped_column(
        String(50),
        default="Pending",
        nullable=False,
        index=True,
        comment="Pending, Posted, Failed",
    )

    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Structured financial posting summary payload",
    )

    posted_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    payroll_period: Mapped["PayrollPeriod"] = relationship("PayrollPeriod")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<FinancialPostingQueue(id={self.id}, period_id={self.payroll_period_id}, "
            f"status='{self.posting_status}')>"
        )
