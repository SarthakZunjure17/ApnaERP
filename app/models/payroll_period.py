import datetime
from typing import List, Optional
import uuid
from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class PayrollPeriod(Base, UUIDMixin, TimestampMixin):
    """
    PayrollPeriod ORM model representing a discrete payroll processing cycle (e.g. Monthly, Bi-weekly).
    Tracks period boundaries and lifecycle status: Draft, Processing, Completed, Locked.
    """
    __tablename__ = "payroll_periods"

    period_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique payroll period code identifier (e.g. 2026-01, PAY_2026_01)",
    )
    start_date: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        comment="Start date of the payroll period",
    )
    end_date: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        comment="End date of the payroll period",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="Draft",
        nullable=False,
        index=True,
        comment="Period processing status: Draft, Processing, Completed, Locked",
    )

    # Relationships
    records: Mapped[List["PayrollRecord"]] = relationship(
        "PayrollRecord",
        back_populates="payroll_period",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<PayrollPeriod(code='{self.period_code}', start={self.start_date}, end={self.end_date}, status='{self.status}')>"


class PayrollRecord(Base, UUIDMixin, TimestampMixin):
    """
    PayrollRecord ORM model representing generated payroll calculation results for a single employee in a period.
    Enforces one record per employee per payroll period.
    """
    __tablename__ = "payroll_records"
    __table_args__ = (
        UniqueConstraint("payroll_period_id", "employee_id", name="uq_period_employee_payroll"),
    )

    payroll_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payroll_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign Key referencing parent PayrollPeriod",
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign Key referencing target Employee",
    )
    employee_compensation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employee_compensations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign Key referencing active EmployeeCompensation snapshot",
    )
    working_days: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total schedule working days in period",
    )
    present_days: Mapped[float] = mapped_column(
        Numeric(5, 2),
        default=0.00,
        nullable=False,
        comment="Total attendance present days",
    )
    leave_days: Mapped[float] = mapped_column(
        Numeric(5, 2),
        default=0.00,
        nullable=False,
        comment="Total approved leave days",
    )
    paid_leave_days: Mapped[float] = mapped_column(
        Numeric(5, 2),
        default=0.00,
        nullable=False,
        comment="Total paid leave days",
    )
    unpaid_leave_days: Mapped[float] = mapped_column(
        Numeric(5, 2),
        default=0.00,
        nullable=False,
        comment="Total unpaid leave (LWP) days",
    )
    overtime_hours: Mapped[float] = mapped_column(
        Numeric(8, 2),
        default=0.00,
        nullable=False,
        comment="Overtime hours worked (future ready)",
    )
    gross_salary: Mapped[float] = mapped_column(
        Numeric(12, 2),
        default=0.00,
        nullable=False,
        comment="Gross salary amount before deductions",
    )
    total_earnings: Mapped[float] = mapped_column(
        Numeric(12, 2),
        default=0.00,
        nullable=False,
        comment="Sum of all earning component amounts",
    )
    total_deductions: Mapped[float] = mapped_column(
        Numeric(12, 2),
        default=0.00,
        nullable=False,
        comment="Sum of all deduction component amounts",
    )
    net_salary: Mapped[float] = mapped_column(
        Numeric(12, 2),
        default=0.00,
        nullable=False,
        comment="Calculated Net Salary (Gross - Total Deductions)",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="Draft",
        nullable=False,
        index=True,
        comment="Payroll record status: Draft, Calculated, Approved, Paid",
    )

    # Relationships
    payroll_period: Mapped["PayrollPeriod"] = relationship("PayrollPeriod", back_populates="records")
    employee: Mapped["Employee"] = relationship("Employee", lazy="selectin")
    employee_compensation: Mapped["EmployeeCompensation"] = relationship("EmployeeCompensation", lazy="selectin")
    components: Mapped[List["PayrollRecordComponent"]] = relationship(
        "PayrollRecordComponent",
        back_populates="payroll_record",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<PayrollRecord(period_id='{self.payroll_period_id}', "
            f"employee_id='{self.employee_id}', gross={self.gross_salary}, "
            f"net={self.net_salary}, status='{self.status}')>"
        )


class PayrollRecordComponent(Base, UUIDMixin, TimestampMixin):
    """
    PayrollRecordComponent ORM model representing detailed line-item salary component amounts in a generated payroll record.
    """
    __tablename__ = "payroll_record_components"

    payroll_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payroll_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign Key referencing parent PayrollRecord",
    )
    salary_component_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("salary_components.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign Key referencing source SalaryComponent",
    )
    component_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Snapshot name of the component",
    )
    component_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Component category: Earning, Deduction",
    )
    amount: Mapped[float] = mapped_column(
        Numeric(12, 2),
        default=0.00,
        nullable=False,
        comment="Calculated component amount for the period",
    )

    # Relationships
    payroll_record: Mapped["PayrollRecord"] = relationship("PayrollRecord", back_populates="components")
    salary_component: Mapped["SalaryComponent"] = relationship("SalaryComponent", lazy="selectin")

    def __repr__(self) -> str:
        return f"<PayrollRecordComponent(record_id='{self.payroll_record_id}', name='{self.component_name}', type='{self.component_type}', amount={self.amount})>"
