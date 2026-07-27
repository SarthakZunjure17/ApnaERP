import datetime
from typing import Optional
import uuid
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class ShiftAssignment(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    ShiftAssignment ORM Model.
    Represents an employee's shift assignment with effective start and end dates.
    Supports permanent, temporary, and rotation shift schedules.
    """
    __tablename__ = "shift_assignments"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT", name="fk_shift_assignment_employee_id"),
        nullable=False,
        index=True,
        comment="Foreign key referencing target Employee",
    )

    shift_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shifts.id", ondelete="RESTRICT", name="fk_shift_assignment_shift_id"),
        nullable=False,
        index=True,
        comment="Foreign key referencing assigned Shift",
    )

    effective_from: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Start date from which this shift assignment is effective",
    )

    effective_to: Mapped[Optional[datetime.date]] = mapped_column(
        Date,
        nullable=True,
        index=True,
        comment="End date until which this shift assignment is effective (NULL for open-ended)",
    )

    assignment_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Permanent",
        comment="Assignment schedule type: Permanent, Temporary, or Rotation",
    )

    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reason or operational justification for assignment",
    )

    assigned_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", name="fk_shift_assignment_assigned_by"),
        nullable=True,
        comment="User ID of admin or manager who created/authorized this assignment",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Flag indicating if assignment is active",
    )

    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id], lazy="joined")
    shift = relationship("Shift", foreign_keys=[shift_id], lazy="joined")
    assigner = relationship("User", foreign_keys=[assigned_by], lazy="joined")

    __table_args__ = (
        Index("idx_shift_assign_emp_dates", "employee_id", "effective_from", "effective_to"),
    )
