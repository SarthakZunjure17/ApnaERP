import datetime
from typing import Optional
import uuid
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class Attendance(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Attendance ORM Model.
    Represents an employee's daily attendance record, containing check-in/out timestamps,
    calculated worked/expected/late/early-departure minutes, attendance status,
    manual correction details, and locked status for payroll processing.
    """
    __tablename__ = "attendance"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT", name="fk_attendance_employee_id"),
        nullable=False,
        index=True,
        comment="Foreign key referencing employee",
    )

    attendance_date: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Specific calendar date of attendance record",
    )

    shift_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shifts.id", ondelete="SET NULL", name="fk_attendance_shift_id"),
        nullable=True,
        index=True,
        comment="Foreign key referencing assigned shift schedule at check-in time",
    )

    check_in_time: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when employee checked in (UTC)",
    )

    check_out_time: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when employee checked out (UTC)",
    )

    break_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total break time taken during shift in minutes",
    )

    worked_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total effective working time in minutes",
    )

    expected_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Required standard working time for the shift in minutes",
    )

    late_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Tardiness duration beyond shift grace period in minutes",
    )

    early_departure_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Duration left before shift completion in minutes",
    )

    attendance_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Absent",
        index=True,
        comment="Attendance classification status (Present, Late, Half Day, Absent, Holiday, Weekend, On Leave, Missing Check-in, Missing Check-out)",
    )

    is_manual_correction: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if attendance record was manually corrected by HR/Manager",
    )

    corrected_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", name="fk_attendance_corrected_by_user_id"),
        nullable=True,
        comment="Foreign key referencing user who performed manual correction",
    )

    correction_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Audit rationale for manual attendance correction",
    )

    is_locked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="True if attendance is locked for payroll processing",
    )

    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id], lazy="selectin")
    shift = relationship("Shift", foreign_keys=[shift_id], lazy="selectin")
    corrected_by_user = relationship("User", foreign_keys=[corrected_by_user_id], lazy="selectin")

    __table_args__ = (
        UniqueConstraint("employee_id", "attendance_date", name="uq_attendance_employee_date"),
        Index("ix_attendance_employee_date", "employee_id", "attendance_date"),
    )

    def __repr__(self) -> str:
        return f"<Attendance id={self.id} emp={self.employee_id} date={self.attendance_date} status='{self.attendance_status}'>"
