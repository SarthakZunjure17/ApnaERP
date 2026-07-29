from typing import Optional
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class UnitOfMeasure(Base, UUIDMixin, TimestampMixin):
    """
    UnitOfMeasure ORM model representing measurement units for inventory tracking, purchasing, and sales.
    (e.g. Piece, Kilogram, Gram, Liter, Meter, Box, Pack).
    """
    __tablename__ = "unit_of_measures"

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Name of measurement unit (e.g. Kilogram)",
    )
    symbol: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
        comment="Unit symbol abbreviation (e.g. kg, pcs, L)",
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Measurement category: Weight, Volume, Length, Count, Time",
    )
    precision: Mapped[int] = mapped_column(
        Integer,
        default=2,
        nullable=False,
        comment="Decimal precision allowed for quantities in this unit",
    )
    base_unit: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Reference symbol of the primary base unit in this category",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Active status flag",
    )

    def __repr__(self) -> str:
        return f"<UnitOfMeasure(name='{self.name}', symbol='{self.symbol}', category='{self.category}')>"
