from typing import Optional
import uuid
from sqlalchemy import Boolean, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class LeaveBalance(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    LeaveBalance ORM model representing available leave entitlements per employee, leave type, and leave year.
    Acts as the authoritative single source of truth for leave availability.
    """
    __tablename__ = "leave_balances"
    __table_args__ = (
        UniqueConstraint(
            "employee_id", "leave_type_id", "leave_year", name="uq_employee_leave_type_year"
        ),
    )

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
    leave_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Calendar leave year (e.g. 2026)",
    )

    opening_balance: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Opening leave balance at start of leave year",
    )
    allocated_days: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Annual allocated leave days",
    )
    earned_days: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Accrued/earned leave days during the year",
    )
    availed_days: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Leave days used/taken by employee",
    )
    encashed_days: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Leave days cashed out/encashed by employee",
    )
    carried_forward_days: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Unused leave carried forward from previous year",
    )

    remaining_days: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Current available remaining leave balance (derived)",
    )

    last_updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who performed last manual adjustment",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="True if leave balance is active",
    )

    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id], lazy="joined")
    leave_type = relationship("LeaveType", foreign_keys=[leave_type_id], lazy="joined")
    updater = relationship("User", foreign_keys=[last_updated_by], lazy="selectin")

    def calculate_remaining_days(self) -> float:
        """
        Derives remaining available leave days using the mathematical formula:
        remaining = opening + allocated + earned + carried_forward - availed - encashed
        """
        return round(
            (self.opening_balance or 0.0)
            + (self.allocated_days or 0.0)
            + (self.earned_days or 0.0)
            + (self.carried_forward_days or 0.0)
            - (self.availed_days or 0.0)
            - (self.encashed_days or 0.0),
            2,
        )

    def __repr__(self) -> str:
        return f"<LeaveBalance(employee_id='{self.employee_id}', leave_type_id='{self.leave_type_id}', year={self.leave_year}, remaining={self.remaining_days})>"
