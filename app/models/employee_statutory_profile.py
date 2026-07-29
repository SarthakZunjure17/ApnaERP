import datetime
from typing import Optional
import uuid
from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class EmployeeStatutoryProfile(Base, UUIDMixin, TimestampMixin):
    """
    EmployeeStatutoryProfile ORM model configuring an employee's statutory compliance flags, numbers, and effective dates.
    Enforces that only one active profile exists per employee at a given time.
    """
    __tablename__ = "employee_statutory_profiles"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key referencing Employee",
    )
    country_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("countries.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign key referencing Country jurisdiction",
    )
    pf_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Flag indicating if Provident Fund deduction is enabled",
    )
    esi_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Flag indicating if ESI deduction is enabled",
    )
    professional_tax_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Flag indicating if Professional Tax deduction is enabled",
    )
    income_tax_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Flag indicating if Income Tax deduction is enabled",
    )
    tax_identification_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Tax ID / Permanent Account Number (PAN / SSN)",
    )
    pf_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Provident Fund Account / UAN Number",
    )
    esi_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="ESI Insurance Number",
    )
    effective_from: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        comment="Effective start date of statutory profile",
    )
    effective_to: Mapped[Optional[datetime.date]] = mapped_column(
        Date,
        nullable=True,
        comment="Optional effective end date of statutory profile",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Active status flag",
    )

    # Relationships
    employee: Mapped["Employee"] = relationship(
        "Employee",
        lazy="selectin",
    )
    country: Mapped["Country"] = relationship(
        "Country",
        back_populates="statutory_profiles",
        lazy="selectin",
    )
