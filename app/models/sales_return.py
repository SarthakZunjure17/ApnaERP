from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class SalesReturn(Base, UUIDMixin, TimestampMixin):
    """
    SalesReturn ORM model.
    Handles customer product returns, RMA processing, and inventory stock reversals via Warehouse Operations (GoodsReceipt).
    Lifecycle states: Draft -> Submitted -> Approved / Rejected -> Completed (or Cancelled).
    """
    __tablename__ = "sales_returns"

    return_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique sales return document number (e.g. SR-2026-0001)",
    )
    sales_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Parent SalesOrder reference",
    )
    delivery_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("delivery_orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional reference to originating DeliveryOrder",
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Customer reference",
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Receiving warehouse facility for returned goods",
    )
    goods_receipt_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("goods_receipts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK referencing executed GoodsReceipt stock reversal document",
    )
    return_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Return request timestamp (UTC)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Draft",
        nullable=False,
        index=True,
        comment="Document status: Draft, Submitted, Approved, Rejected, Completed, Cancelled",
    )
    reason_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Return reason: Damaged, Defective, WrongItem, CustomerCancellation, ExcessShipment, Other",
    )
    total_refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Calculated total refund credit note amount",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Return remarks or inspection notes",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who created the return request",
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who approved the return request",
    )

    # Relationships
    sales_order: Mapped["SalesOrder"] = relationship("SalesOrder", lazy="selectin")
    delivery_order: Mapped[Optional["DeliveryOrder"]] = relationship("DeliveryOrder", lazy="selectin")
    customer: Mapped["Customer"] = relationship("Customer", lazy="selectin")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", lazy="selectin")
    goods_receipt: Mapped[Optional["GoodsReceipt"]] = relationship("GoodsReceipt", lazy="selectin")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by], lazy="selectin")
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by], lazy="selectin")
    items: Mapped[List["SalesReturnItem"]] = relationship(
        "SalesReturnItem", back_populates="sales_return", cascade="all, delete-orphan", lazy="selectin"
    )


class SalesReturnItem(Base, UUIDMixin):
    """
    SalesReturnItem ORM model.
    Line items returned within a SalesReturn document.
    """
    __tablename__ = "sales_return_items"

    sales_return_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_returns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent SalesReturn reference",
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
        comment="Returned line quantity",
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Unit price credited",
    )
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        comment="Net refund amount for this line item",
    )
    reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Line item specific return reason",
    )

    sales_return: Mapped["SalesReturn"] = relationship("SalesReturn", back_populates="items")
    sales_order_item: Mapped["SalesOrderItem"] = relationship("SalesOrderItem", lazy="selectin")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
