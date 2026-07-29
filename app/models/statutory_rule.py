import datetime
from typing import List, Optional
import uuid
from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class StatutoryRule(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    StatutoryRule ORM model representing a statutory deduction policy rule (Provident Fund, ESI, Professional Tax, Income Tax, Other).
    Supports country independence, calculation methods (Fixed, Percentage, Slab), priority ordering, and effective dating.
    """
    __tablename__ = "statutory_rules"

    rule_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique statutory rule code identifier (e.g. IND_PF_STANDARD, IND_PT_MH)",
    )
    rule_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Human-readable statutory rule name",
    )
    country_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("countries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key referencing applicable Country",
    )
    rule_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Rule Type: Provident Fund, ESI, Professional Tax, Income Tax, Other",
    )
    calculation_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Calculation Method: Fixed, Percentage, Slab",
    )
    effective_from: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        comment="Effective start date of rule policy",
    )
    effective_to: Mapped[Optional[datetime.date]] = mapped_column(
        Date,
        nullable=True,
        comment="Optional effective end date of rule policy",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Active status flag",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Evaluation priority order (1 is highest priority)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed statutory rule description",
    )

    # Relationships
    country: Mapped["Country"] = relationship(
        "Country",
        back_populates="statutory_rules",
        lazy="selectin",
    )
    slabs: Mapped[List["StatutoryRuleSlab"]] = relationship(
        "StatutoryRuleSlab",
        back_populates="rule",
        cascade="all, delete-orphan",
        order_by="StatutoryRuleSlab.sequence",
        lazy="selectin",
    )


class StatutoryRuleSlab(Base, UUIDMixin, TimestampMixin):
    """
    StatutoryRuleSlab ORM model representing a tiered salary slab boundary for slab-based statutory calculations.
    """
    __tablename__ = "statutory_rule_slabs"

    statutory_rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("statutory_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key referencing parent StatutoryRule",
    )
    min_amount: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Lower salary boundary for slab (inclusive)",
    )
    max_amount: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Upper salary boundary for slab (inclusive, null means infinity)",
    )
    percentage: Mapped[float] = mapped_column(
        Numeric(5, 2),
        default=0.00,
        nullable=False,
        comment="Percentage rate applied in slab",
    )
    fixed_amount: Mapped[float] = mapped_column(
        Numeric(12, 2),
        default=0.00,
        nullable=False,
        comment="Fixed deduction amount applied in slab",
    )
    sequence: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Sequence index ordering slabs within rule",
    )

    # Relationships
    rule: Mapped["StatutoryRule"] = relationship(
        "StatutoryRule",
        back_populates="slabs",
        lazy="selectin",
    )
