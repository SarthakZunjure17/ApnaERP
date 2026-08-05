from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class PriceList(Base, UUIDMixin, TimestampMixin):
    """
    PriceList ORM model.
    Catalog price lists (e.g. Standard Retail, Wholesale, Preferred Partner).
    """
    __tablename__ = "price_lists"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique price list code",
    )
    name: Mapped[str] = mapped_column(
        String(150),
        index=True,
        nullable=False,
        comment="Human-readable price list name",
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        default="INR",
        nullable=False,
        comment="Currency code (e.g. INR, USD, EUR)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Active price list flag",
    )
    valid_from: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Effective start timestamp (UTC)",
    )
    valid_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Effective end timestamp (UTC)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Price list description",
    )

    rules: Mapped[List["PricingRule"]] = relationship(
        "PricingRule", back_populates="price_list", cascade="all, delete-orphan", lazy="selectin"
    )


class PricingRule(Base, UUIDMixin, TimestampMixin):
    """
    PricingRule ORM model.
    Product specific prices and quantity break tiers within a PriceList.
    """
    __tablename__ = "pricing_rules"

    price_list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("price_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent PriceList reference",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Target Product reference",
    )
    min_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("1.0000"),
        nullable=False,
        comment="Minimum purchase quantity threshold for price tier",
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Unit price for this product and tier",
    )
    valid_from: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Effective start timestamp (UTC)",
    )
    valid_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Effective end timestamp (UTC)",
    )

    price_list: Mapped["PriceList"] = relationship("PriceList", back_populates="rules")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")


class DiscountRule(Base, UUIDMixin, TimestampMixin):
    """
    DiscountRule ORM model.
    Configurable discount policies (Percentage or Fixed Amount, Line or Document level).
    """
    __tablename__ = "discount_rules"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique discount rule code",
    )
    name: Mapped[str] = mapped_column(
        String(150),
        index=True,
        nullable=False,
        comment="Discount rule name",
    )
    discount_type: Mapped[str] = mapped_column(
        String(20),
        default="Line",
        nullable=False,
        comment="Application target: Line or Document",
    )
    calculation_type: Mapped[str] = mapped_column(
        String(20),
        default="Percentage",
        nullable=False,
        comment="Calculation method: Percentage or FixedAmount",
    )
    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Discount rate percentage or fixed amount value",
    )
    min_order_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0000"),
        nullable=False,
        comment="Minimum total order value threshold required to qualify",
    )
    min_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0000"),
        nullable=False,
        comment="Minimum item quantity threshold required to qualify",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Active status flag",
    )
    valid_from: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Effective start timestamp (UTC)",
    )
    valid_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Effective end timestamp (UTC)",
    )
