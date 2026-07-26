import datetime
from typing import Optional
import uuid
from sqlalchemy import Boolean, Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class Holiday(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Holiday ORM Model representing official organization, national, and regional holidays.
    Serves as single source of truth for Attendance, Leave, and Payroll calculations.
    """
    __tablename__ = "holidays"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique holiday code (e.g. HOL-2026-IND-DAY)",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
        comment="Official holiday name (e.g. Independence Day)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed holiday description",
    )

    holiday_date: Mapped[datetime.date] = mapped_column(
        Date,
        index=True,
        nullable=False,
        comment="Specific date of the holiday",
    )
    holiday_type: Mapped[str] = mapped_column(
        String(50),
        default="Company",
        nullable=False,
        comment="Holiday classification (National, Regional, Company, Optional)",
    )

    country: Mapped[str] = mapped_column(
        String(100),
        default="India",
        nullable=False,
        comment="Target country for national/regional holidays",
    )
    state_region: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Target state or province for regional holidays",
    )

    is_half_day: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if holiday is observed for a half day",
    )
    is_recurring_annually: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if holiday automatically recurs on the same month/day every year",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
        nullable=False,
        comment="Active holiday status flag",
    )

    def __repr__(self) -> str:
        return f"<Holiday(id={self.id}, code='{self.code}', name='{self.name}', date={self.holiday_date})>"
