import uuid
from typing import Optional
from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class LeaveType(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    LeaveType ORM model representing organizational leave policies.
    Defines rules such as annual allocation, carry-forward limits, consecutive day caps,
    half-day permission, approval requirements, and gender restrictions.
    """
    __tablename__ = "leave_types"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique leave type code (e.g. ANNUAL, SICK, CASUAL, MATERNITY)",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique leave type display name (e.g. Annual Leave, Sick Leave)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description of leave policy and entitlement criteria",
    )

    is_paid: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="True if leave is paid, False for unpaid leave",
    )
    requires_approval: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="True if leave application requires manager/HR approval",
    )
    allow_half_day: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="True if half-day leave applications are permitted",
    )
    allow_negative_balance: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if leave balance can go negative (leave deficit)",
    )

    annual_allocation: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Default annual allocated leave days (>= 0)",
    )
    carry_forward_allowed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if unused leave can be carried forward to next year",
    )
    max_carry_forward: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Maximum number of leave days that can be carried forward",
    )
    max_consecutive_days: Mapped[Optional[int]] = mapped_column(
        Integer,
        default=30,
        nullable=True,
        comment="Maximum allowed consecutive leave days in a single request",
    )
    gender_restriction: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Optional gender restriction (e.g. Female for Maternity, Male for Paternity)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="True if leave policy is active and selectable",
    )

    def __repr__(self) -> str:
        return f"<LeaveType(code='{self.code}', name='{self.name}', annual_allocation={self.annual_allocation})>"
