import datetime
from typing import Optional
import uuid
from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class EmployeeCompensation(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    EmployeeCompensation ORM model representing employee salary structure assignments and compensation history.
    Maintains revision history, effective date ranges, and approval status.
    """
    __tablename__ = "employee_compensations"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign Key referencing assigned Employee",
    )
    salary_structure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("salary_structures.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign Key referencing assigned SalaryStructure template",
    )
    effective_from: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Start date when this compensation policy takes effect",
    )
    effective_to: Mapped[Optional[datetime.date]] = mapped_column(
        Date,
        nullable=True,
        comment="End date when this compensation policy expires (nullable if ongoing)",
    )
    annual_ctc: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Total Cost to Company (CTC) per annum",
    )
    monthly_gross_salary: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Monthly gross salary amount before statutory deductions",
    )
    monthly_net_salary: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Estimated monthly net salary amount (reserved for future calculation)",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="Draft",
        nullable=False,
        index=True,
        comment="Compensation status: Draft, Active, Expired, Cancelled",
    )
    revision_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Sequential revision number (increments with salary revisions)",
    )
    previous_compensation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employee_compensations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Foreign Key referencing previous compensation version if revised",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Remarks or justification for compensation assignment/revision",
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID of authorized HR/Payroll Manager who activated this compensation",
    )
    approved_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when compensation was activated and approved",
    )

    # Relationships
    employee: Mapped["Employee"] = relationship("Employee", lazy="joined")
    salary_structure: Mapped["SalaryStructure"] = relationship("SalaryStructure", lazy="joined")
    previous_compensation: Mapped[Optional["EmployeeCompensation"]] = relationship(
        "EmployeeCompensation", remote_side="EmployeeCompensation.id", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<EmployeeCompensation(employee_id='{self.employee_id}', "
            f"structure_id='{self.salary_structure_id}', ctc={self.annual_ctc}, "
            f"status='{self.status}', revision={self.revision_number})>"
        )
