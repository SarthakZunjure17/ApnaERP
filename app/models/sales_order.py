from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class SalesOrder(Base, UUIDMixin, TimestampMixin):
    """
    SalesOrder ORM model representing customer sales orders.
    Lifecycle states: Draft -> Submitted -> Approved / Rejected -> Partially Delivered -> Fully Delivered -> Closed (or Cancelled).
    Tracks quotation links, delivery status, shipping/billing addresses, payment terms, and totals.
    """
    __tablename__ = "sales_orders"

    order_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique sales order document number (e.g. SO-2026-0001)",
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Reference to Customer master record",
    )
    quotation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_quotations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional reference to originating SalesQuotation",
    )
    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Order booking timestamp (UTC)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Draft",
        nullable=False,
        index=True,
        comment="Document status: Draft, Submitted, Approved, Rejected, Partially Delivered, Fully Delivered, Closed, Cancelled",
    )
    delivery_status: Mapped[str] = mapped_column(
        String(20),
        default="Pending",
        nullable=False,
        index=True,
        comment="Fulfillment status: Pending, Partial, Delivered, Cancelled",
    )
    revision_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Incremental order revision counter",
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        default="INR",
        nullable=False,
        comment="Transaction currency code",
    )
    subtotal_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Sum of gross line items before discount & taxes",
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
        comment="Net total sales order amount",
    )
    payment_terms: Mapped[str] = mapped_column(
        String(100),
        default="Net 30",
        nullable=False,
        comment="Payment terms description",
    )
    shipping_address_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_addresses.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK referencing shipping CustomerAddress",
    )
    billing_address_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_addresses.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK referencing billing CustomerAddress",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Special delivery instructions or order notes",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who created the sales order",
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who approved the sales order",
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when order was approved (UTC)",
    )

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", lazy="selectin")
    quotation: Mapped[Optional["SalesQuotation"]] = relationship("SalesQuotation", lazy="selectin")
    shipping_address: Mapped[Optional["CustomerAddress"]] = relationship("CustomerAddress", foreign_keys=[shipping_address_id], lazy="selectin")
    billing_address: Mapped[Optional["CustomerAddress"]] = relationship("CustomerAddress", foreign_keys=[billing_address_id], lazy="selectin")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by], lazy="selectin")
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by], lazy="selectin")
    items: Mapped[List["SalesOrderItem"]] = relationship(
        "SalesOrderItem", back_populates="sales_order", cascade="all, delete-orphan", lazy="selectin"
    )


class SalesOrderItem(Base, UUIDMixin):
    """
    SalesOrderItem ORM model.
    Line items associated with a SalesOrder document.
    """
    __tablename__ = "sales_order_items"

    sales_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent SalesOrder reference",
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
        comment="Product line item description",
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Ordered quantity",
    )
    delivered_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0000"),
        nullable=False,
        comment="Quantity physically delivered so far",
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Agreed unit price",
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
        comment="Tax rate percentage",
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
        comment="Net total for this order line item",
    )
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Fulfillment source Warehouse ID",
    )
    delivery_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Promised delivery date (UTC)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Pending",
        nullable=False,
        comment="Item fulfillment status: Pending, Partial, Delivered, Cancelled",
    )

    sales_order: Mapped["SalesOrder"] = relationship("SalesOrder", back_populates="items")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse", lazy="selectin")
