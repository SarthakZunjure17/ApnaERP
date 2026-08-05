from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class SalesQuotation(Base, UUIDMixin, TimestampMixin):
    """
    SalesQuotation ORM model representing customer sales quotes.
    Lifecycle states: Draft -> Submitted -> Approved / Rejected -> Expired / Converted / Closed.
    Supports revision numbers, validity dates, line item taxes and discounts.
    """
    __tablename__ = "sales_quotations"

    quotation_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique quotation document number (e.g. SQ-2026-0001)",
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Reference to Customer master record",
    )
    quotation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Quotation issue timestamp (UTC)",
    )
    validity_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Expiration timestamp for quotation acceptance (UTC)",
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        default="INR",
        nullable=False,
        comment="Transaction currency code",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Draft",
        nullable=False,
        index=True,
        comment="Document status: Draft, Submitted, Approved, Rejected, Expired, Converted, Closed",
    )
    revision_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Incremental quotation revision counter",
    )
    subtotal_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Sum of gross line items before document discount & taxes",
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Total discount amount applied across all lines & document",
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Total tax amount computed",
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Net total quotation amount",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Terms, conditions or quotation remarks",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who created the quotation",
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who approved the quotation",
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when quotation was approved (UTC)",
    )

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", lazy="selectin")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by], lazy="selectin")
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by], lazy="selectin")
    items: Mapped[List["SalesQuotationItem"]] = relationship(
        "SalesQuotationItem", back_populates="quotation", cascade="all, delete-orphan", lazy="selectin"
    )


class SalesQuotationItem(Base, UUIDMixin):
    """
    SalesQuotationItem ORM model.
    Line items associated with a SalesQuotation document.
    """
    __tablename__ = "sales_quotation_items"

    quotation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_quotations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent SalesQuotation reference",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Reference to Product master record",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Product or service line item description",
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Quoted item quantity",
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Quoted unit price",
    )
    discount_type: Mapped[str] = mapped_column(
        String(20),
        default="Percentage",
        nullable=False,
        comment="Line discount type: Percentage or FixedAmount",
    )
    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0000"),
        nullable=False,
        comment="Line discount percentage or amount value",
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Calculated line item discount amount",
    )
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Tax rate percentage (e.g. 18.00 for 18% GST)",
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Calculated line item tax amount",
    )
    line_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        comment="Net total for this line item",
    )
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        comment="Target fulfillment warehouse for line item",
    )

    quotation: Mapped["SalesQuotation"] = relationship("SalesQuotation", back_populates="items")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse", lazy="selectin")
