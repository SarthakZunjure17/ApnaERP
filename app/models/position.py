import uuid
from typing import List, Optional
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class Position(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Position ORM model representing job roles within enterprise departments.
    Supports position reporting hierarchy, employment categories, grade/level,
    and headcount capacity controls.
    """
    __tablename__ = "positions"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique position code (e.g. POS-ENG-001)",
    )
    title: Mapped[str] = mapped_column(
        String(150),
        index=True,
        nullable=False,
        comment="Job title (e.g. Senior Backend Engineer)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed position role description and responsibilities",
    )

    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK referencing owning Department",
    )
    parent_position_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Parent reporting position for hierarchy tree",
    )

    employment_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Permanent",
        comment="Employment category (Permanent, Contract, Temporary, Internship)",
    )
    grade: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Job grade (e.g. G5, Band A)",
    )
    level: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Job level (e.g. L4, L5, Principal)",
    )

    maximum_headcount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Maximum allowed headcount capacity for this position",
    )
    current_headcount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Current count of active assigned employees",
    )

    is_managerial: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if position holds manager/leadership authority",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Position active status flag",
    )

    # Relationships
    department = relationship("Department", lazy="selectin")
    parent_position = relationship(
        "Position",
        remote_side="[Position.id]",
        foreign_keys=[parent_position_id],
        lazy="selectin",
    )
    employees = relationship(
        "Employee",
        back_populates="position",
        foreign_keys="[Employee.position_id]",
    )

    @property
    def department_name(self) -> Optional[str]:
        return self.department.name if self.department else None

    @property
    def parent_position_title(self) -> Optional[str]:
        return self.parent_position.title if self.parent_position else None
