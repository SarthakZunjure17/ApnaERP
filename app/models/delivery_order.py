from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class DeliveryOrder(Base, UUIDMixin, TimestampMixin):
    """
    DeliveryOrder ORM model representing outbound shipments for Sales Orders.
    Fulfills sales order items and invokes Warehouse Operations (GoodsIssue) for physical stock removal.
    Lifecycle states: Draft -> Dispatched -> Delivered (or Cancelled).
    """
    __tablename__ = "delivery_orders"

    delivery_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique delivery note number (e.g. DO-2026-0001)",
    )
    sales_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Parent SalesOrder reference",
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Dispatching warehouse facility",
    )
    goods_issue_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("goods_issues.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK referencing executed GoodsIssue stock movement document",
    )
    dispatch_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Dispatch date and time (UTC)",
    )
    carrier: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Logistics courier / carrier name (e.g. BlueDart, FedEx, Internal Truck)",
    )
    tracking_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        index=True,
        nullable=True,
        comment="Carrier consignment or tracking reference number",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Draft",
        nullable=False,
        index=True,
        comment="Delivery status: Draft, Dispatched, Delivered, Cancelled",
    )
    delivery_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Packing notes, special handling or recipient remarks",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who created the delivery note",
    )

    # Relationships
    sales_order: Mapped["SalesOrder"] = relationship("SalesOrder", lazy="selectin")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", lazy="selectin")
    goods_issue: Mapped[Optional["GoodsIssue"]] = relationship("GoodsIssue", lazy="selectin")
    creator: Mapped[Optional["User"]] = relationship("User", lazy="selectin")
    items: Mapped[List["DeliveryOrderItem"]] = relationship(
        "DeliveryOrderItem", back_populates="delivery_order", cascade="all, delete-orphan", lazy="selectin"
    )


class DeliveryOrderItem(Base, UUIDMixin):
    """
    DeliveryOrderItem ORM model.
    Line items dispatched within a DeliveryOrder document.
    """
    __tablename__ = "delivery_order_items"

    delivery_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("delivery_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent DeliveryOrder reference",
    )
    sales_order_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_order_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Reference to specific SalesOrderItem",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Reference to Product master record",
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Dispatched line quantity",
    )

    delivery_order: Mapped["DeliveryOrder"] = relationship("DeliveryOrder", back_populates="items")
    sales_order_item: Mapped["SalesOrderItem"] = relationship("SalesOrderItem", lazy="selectin")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
