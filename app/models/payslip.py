import datetime
from typing import Optional
import uuid
from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class Payslip(Base, UUIDMixin, TimestampMixin):
    """
    Payslip ORM model representing a generated permanent employee payroll document.
    Links to a PayrollRecord and optional stored PDF File artifact.
    """
    __tablename__ = "payslips"

    payroll_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payroll_records.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        comment="Foreign Key referencing source PayrollRecord (1:1 constraint)",
    )
    payslip_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique payslip document number (e.g. PS-202601-0001)",
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign Key referencing target Employee",
    )
    payroll_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payroll_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign Key referencing parent PayrollPeriod",
    )
    gross_salary: Mapped[float] = mapped_column(
        Numeric(12, 2),
        default=0.00,
        nullable=False,
        comment="Calculated gross salary amount",
    )
    total_earnings: Mapped[float] = mapped_column(
        Numeric(12, 2),
        default=0.00,
        nullable=False,
        comment="Total earnings sum",
    )
    total_deductions: Mapped[float] = mapped_column(
        Numeric(12, 2),
        default=0.00,
        nullable=False,
        comment="Total deductions sum",
    )
    net_salary: Mapped[float] = mapped_column(
        Numeric(12, 2),
        default=0.00,
        nullable=False,
        comment="Calculated net salary amount",
    )
    pdf_file_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Foreign Key referencing generated PDF File artifact",
    )
    generated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when payslip PDF was generated",
    )
    published_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when payslip was published to employee",
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="Draft",
        nullable=False,
        index=True,
        comment="Payslip lifecycle status: Draft, Generated, Published",
    )

    # Relationships
    payroll_record: Mapped["PayrollRecord"] = relationship("PayrollRecord", lazy="selectin")
    employee: Mapped["Employee"] = relationship("Employee", lazy="selectin")
    payroll_period: Mapped["PayrollPeriod"] = relationship("PayrollPeriod", lazy="selectin")
    pdf_file: Mapped[Optional["File"]] = relationship("File", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Payslip(number='{self.payslip_number}', employee_id='{self.employee_id}', status='{self.status}')>"
