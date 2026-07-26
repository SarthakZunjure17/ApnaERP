import uuid
from typing import List, Optional
from sqlalchemy import Boolean, Float, Integer, String, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class HRConfiguration(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    HRConfiguration ORM model representing organization-wide HR policies.
    Serves as the centralized single source of truth for future HR modules
    (Attendance, Leave, Payroll, Recruitment, Performance, Shift Scheduling).
    """
    __tablename__ = "hr_configurations"

    organization_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment="Official organization name",
    )
    organization_code: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
        comment="Unique identifier code for organization",
    )

    timezone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="UTC",
        comment="Default IANA timezone name (e.g. Asia/Kolkata, UTC)",
    )
    country: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="India",
        comment="Country of primary enterprise operation",
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="INR",
        comment="Primary currency ISO code (e.g. INR, USD, EUR)",
    )

    standard_working_hours_per_day: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=8.0,
        comment="Standard expected daily working hours",
    )
    standard_working_days_per_week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        comment="Standard expected weekly working days",
    )
    weekend_configuration: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: ["Saturday", "Sunday"],
        comment="JSON list of non-working weekend days (e.g. ['Saturday', 'Sunday'])",
    )

    default_shift_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="General Shift",
        comment="Default enterprise work shift label",
    )
    grace_period_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=15,
        comment="Allowed late arrival grace period in minutes",
    )
    minimum_working_hours: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=4.0,
        comment="Minimum required hours for half-day credit",
    )

    default_probation_period_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=90,
        comment="Default employee probation duration in days",
    )
    leave_year_start_month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Month (1-12) when annual leave quota resets",
    )
    payroll_cycle: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Monthly",
        comment="Enterprise payroll frequency (Monthly, Biweekly, Weekly)",
    )
    fiscal_year_start_month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=4,
        comment="Month (1-12) marking fiscal year start",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
        nullable=False,
        comment="Flag indicating active configuration status",
    )
