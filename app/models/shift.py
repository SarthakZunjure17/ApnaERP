import datetime
from typing import List, Optional
import uuid
from sqlalchemy import Boolean, Float, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class Shift(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Shift ORM model representing reusable work schedules.
    Defines working hours, break durations, grace periods, night shift flags,
    and flexible timing constraints for Attendance and Payroll modules.
    """
    __tablename__ = "shifts"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique shift identifier code (e.g. SHIFT-DAY-01)",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique shift name (e.g. Morning Shift, Night Shift)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed shift schedule description",
    )

    start_time: Mapped[datetime.time] = mapped_column(
        Time,
        nullable=False,
        comment="Shift start time (e.g. 09:00:00)",
    )
    end_time: Mapped[datetime.time] = mapped_column(
        Time,
        nullable=False,
        comment="Shift end time (e.g. 17:00:00 or 06:00:00 for overnight)",
    )

    break_duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
        comment="Total allocated break duration in minutes",
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
    maximum_working_hours: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=12.0,
        comment="Maximum allowed daily working hours including overtime",
    )

    is_night_shift: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if shift spans overnight across midnight",
    )
    is_flexible_shift: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if shift supports flexible start/end hours",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
        nullable=False,
        comment="Active shift status flag",
    )

    # Relationships
    employees = relationship(
        "Employee",
        back_populates="shift",
        foreign_keys="[Employee.shift_id]",
    )

    @property
    def duration_hours(self) -> float:
        """Calculates total shift duration in hours (accounting for overnight shifts)."""
        start_secs = self.start_time.hour * 3600 + self.start_time.minute * 60 + self.start_time.second
        end_secs = self.end_time.hour * 3600 + self.end_time.minute * 60 + self.end_time.second

        if end_secs >= start_secs:
            diff_secs = end_secs - start_secs
        else:
            # Overnight shift across midnight
            diff_secs = (24 * 3600 - start_secs) + end_secs

        return round(diff_secs / 3600.0, 2)
