from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class SupplierQuotation(Base, UUIDMixin, TimestampMixin):
    """
    SupplierQuotation ORM model.
    Commercial bid/quotation submitted by a Supplier in response to an RFQ or direct request.
    Lifecycle states: Draft -> Submitted -> Under Review -> Approved (or Rejected/Expired).
    """
    __tablename__ = "supplier_quotations"

    quotation_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique quotation tracking number (e.g. SQ-2026-00001)",
    )
    rfq_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional associated RFQ FK",
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to quoting Supplier",
    )
    quotation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Date quotation was issued by supplier",
    )
    validity_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Expiration date of quotation validity",
    )
    lead_time_days: Mapped[int] = mapped_column(
        Integer,
        default=7,
        nullable=False,
        comment="Promised delivery lead time in calendar days",
    )
    payment_terms: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Quoted payment terms (e.g. Net 30)",
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        default="USD",
        nullable=False,
        comment="Quoted transaction currency code",
    )
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0"),
        nullable=False,
        comment="Sum of line item totals before tax and discount",
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0"),
        nullable=False,
        comment="Total calculated tax amount",
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0"),
        nullable=False,
        comment="Total calculated discount amount",
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0"),
        nullable=False,
        comment="Final quoted total amount",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Draft",
        nullable=False,
        index=True,
        comment="Status: Draft, Submitted, Under Review, Approved, Rejected, Expired",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Supplier notes or terms",
    )

    # Relationships
    rfq: Mapped[Optional["RFQ"]] = relationship("RFQ", back_populates="quotations", lazy="selectin")
    supplier: Mapped["Supplier"] = relationship("Supplier", lazy="selectin")
    items: Mapped[List["SupplierQuotationItem"]] = relationship(
        "SupplierQuotationItem", back_populates="quotation", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<SupplierQuotation(number='{self.quotation_number}', supplier_id='{self.supplier_id}', total={self.total_amount})>"


class SupplierQuotationItem(Base, UUIDMixin, TimestampMixin):
    """
    SupplierQuotationItem ORM model.
    Line items specified in a SupplierQuotation.
    """
    __tablename__ = "supplier_quotation_items"

    quotation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_quotations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent SupplierQuotation",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to quoted Product",
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Quoted quantity",
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Quoted price per unit",
    )
    discount_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.0"),
        nullable=False,
        comment="Line item percentage discount",
    )
    tax_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.0"),
        nullable=False,
        comment="Line item percentage tax",
    )
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Calculated line item total price",
    )
    delivery_days: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Item-specific lead time in days",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Line item remarks or spec variations",
    )

    # Relationships
    quotation: Mapped["SupplierQuotation"] = relationship("SupplierQuotation", back_populates="items")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")

    def __repr__(self) -> str:
        return f"<SupplierQuotationItem(product_id='{self.product_id}', total_price={self.total_price})>"
