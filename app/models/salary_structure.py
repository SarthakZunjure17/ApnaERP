import datetime
from typing import List, Optional
import uuid
from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class SalaryStructure(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    SalaryStructure ORM model representing reusable salary structure templates.
    Serves as an organization-wide compensation template composed of multiple salary components.
    """
    __tablename__ = "salary_structures"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique salary structure code (e.g. EXEC_PAY_V1, ENG_BAND_3)",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique human-readable structure name (e.g. Executive Standard Compensation)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Detailed structure description",
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        default="INR",
        nullable=False,
        comment="ISO currency code for structure values",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="True if structure is active for assignment",
    )
    effective_from: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        comment="Start date when this structure policy becomes effective",
    )
    effective_to: Mapped[Optional[datetime.date]] = mapped_column(
        Date,
        nullable=True,
        comment="End date when this structure policy expires (nullable for ongoing structures)",
    )

    # Relationships
    components: Mapped[List["SalaryStructureComponent"]] = relationship(
        "SalaryStructureComponent",
        back_populates="structure",
        cascade="all, delete-orphan",
        order_by="SalaryStructureComponent.component_order",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<SalaryStructure(code='{self.code}', name='{self.name}', currency='{self.currency}', active={self.is_active})>"


class SalaryStructureComponent(Base, UUIDMixin, TimestampMixin):
    """
    SalaryStructureComponent ORM model mapping SalaryComponents to SalaryStructures with order and value overrides.
    """
    __tablename__ = "salary_structure_components"
    __table_args__ = (
        UniqueConstraint("salary_structure_id", "salary_component_id", name="uq_structure_component"),
    )

    salary_structure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("salary_structures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign Key referencing parent SalaryStructure",
    )
    salary_component_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("salary_components.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign Key referencing assigned SalaryComponent",
    )
    component_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Sequence order position within the structure",
    )
    component_value: Mapped[float] = mapped_column(
        Numeric(12, 2),
        default=0.00,
        nullable=False,
        comment="Default amount or baseline value for this component in the structure",
    )
    calculation_method_override: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Optional calculation method override (Fixed, Percentage, Formula)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="True if component is active in this structure",
    )

    # Relationships
    structure: Mapped["SalaryStructure"] = relationship("SalaryStructure", back_populates="components")
    component: Mapped["SalaryComponent"] = relationship("SalaryComponent", lazy="joined")

    def __repr__(self) -> str:
        return f"<SalaryStructureComponent(structure_id='{self.salary_structure_id}', component_id='{self.salary_component_id}', order={self.component_order})>"
