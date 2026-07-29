from typing import List, Optional
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class Country(Base, UUIDMixin, TimestampMixin):
    """
    Country ORM model representing a country entity reusable across the ERP platform.
    """
    __tablename__ = "countries"

    code: Mapped[str] = mapped_column(
        String(10),
        unique=True,
        index=True,
        nullable=False,
        comment="ISO country code (e.g. IND, USA, GBR)",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Full country name",
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Default currency code (e.g. INR, USD, GBP)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Active status flag",
    )

    # Relationships
    statutory_rules: Mapped[List["StatutoryRule"]] = relationship(
        "StatutoryRule",
        back_populates="country",
        lazy="selectin",
    )
    statutory_profiles: Mapped[List["EmployeeStatutoryProfile"]] = relationship(
        "EmployeeStatutoryProfile",
        back_populates="country",
        lazy="selectin",
    )
