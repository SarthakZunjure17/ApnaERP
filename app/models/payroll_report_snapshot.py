import datetime
from typing import Any, Dict, Optional
import uuid
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class PayrollReportSnapshot(Base, UUIDMixin, TimestampMixin):
    """
    PayrollReportSnapshot ORM Model.
    Stores generated payroll report audit snapshots (Salary Register, Department-wise, Summaries, Cost Center, etc.).
    """
    __tablename__ = "payroll_report_snapshots"

    payroll_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payroll_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    report_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Salary Register, Department-wise Payroll, Employee Salary History, Payroll Summary, Deduction Summary, Earnings Summary, Cost Center Report, Monthly Payroll Register",
    )

    format: Mapped[str] = mapped_column(
        String(10),
        default="PDF",
        nullable=False,
        comment="PDF, EXCEL, CSV",
    )

    generated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    generated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    file_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )

    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Filter parameters, summary totals, and generation context",
    )

    # Relationships
    payroll_period: Mapped["PayrollPeriod"] = relationship("PayrollPeriod")  # noqa: F821
    generator: Mapped["User"] = relationship("User")  # noqa: F821
    file: Mapped[Optional["File"]] = relationship("File")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<PayrollReportSnapshot(id={self.id}, type='{self.report_type}', "
            f"period_id={self.payroll_period_id}, format='{self.format}')>"
        )
