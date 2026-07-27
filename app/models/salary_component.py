from typing import Optional
from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class SalaryComponent(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    SalaryComponent ORM model representing organization-wide payroll component definitions.
    Defines earnings and deductions, calculation methods, taxability, and statutory applicability.
    """
    __tablename__ = "salary_components"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique component code identifier (e.g. BASIC, HRA, PF)",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique human-readable component name (e.g. Basic Salary, House Rent Allowance)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Detailed component description",
    )
    type: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
        comment="Component category type: Earning, Deduction",
    )
    calculation_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Calculation method: Fixed, Percentage, Formula",
    )
    default_value: Mapped[float] = mapped_column(
        Numeric(12, 2),
        default=0.00,
        nullable=False,
        comment="Default fixed amount value",
    )
    percentage_value: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Percentage value (e.g. 50.00 for 50%) when calculation_method is Percentage",
    )
    is_taxable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="True if component is subject to Income Tax calculations",
    )
    is_pf_applicable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="True if component forms part of Provident Fund (PF) calculations",
    )
    is_esi_applicable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="True if component forms part of Employee State Insurance (ESI) calculations",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="True if component is active for payroll configuration",
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        index=True,
        nullable=False,
        comment="Unique sequential ordering number for display and processing",
    )

    def __repr__(self) -> str:
        return f"<SalaryComponent(code='{self.code}', name='{self.name}', type='{self.type}', method='{self.calculation_method}')>"
