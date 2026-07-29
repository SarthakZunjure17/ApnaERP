import datetime
from decimal import Decimal
from typing import Optional
import uuid
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class PayrollAdjustment(Base, UUIDMixin, TimestampMixin):
    """
    PayrollAdjustment ORM Model.
    Represents variable pay, earnings, deductions, bonuses, arrears, reimbursements,
    loan recoveries, and manual adjustments associated with an employee for a payroll period.
    """
    __tablename__ = "payroll_adjustments"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    payroll_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payroll_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    adjustment_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Bonus, Incentive, Commission, Overtime, Arrear, Reimbursement, Loan Recovery, Manual Addition, Manual Deduction",
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Adjustment numerical amount",
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        default="INR",
        nullable=False,
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="Pending",
        nullable=False,
        index=True,
        comment="Pending, Approved, Rejected, Applied",
    )

    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    approved_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    employee: Mapped["Employee"] = relationship("Employee")  # noqa: F821
    payroll_period: Mapped["PayrollPeriod"] = relationship("PayrollPeriod")  # noqa: F821
    approver: Mapped[Optional["User"]] = relationship("User")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<PayrollAdjustment(id={self.id}, employee_id={self.employee_id}, "
            f"type='{self.adjustment_type}', amount={self.amount}, status='{self.status}')>"
        )
