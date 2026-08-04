from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class PurchaseReturn(Base, UUIDMixin, TimestampMixin):
    """
    PurchaseReturn ORM model.
    Represents physical return of received stock back to a Supplier.
    Executing/Processing a PurchaseReturn invokes existing Warehouse Operations / Stock Ledger with OUT direction (`RETURN_OUT`).
    Lifecycle states: Draft -> Approved -> Processed (or Cancelled).
    """
    __tablename__ = "purchase_returns"

    return_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique Purchase Return tracking number (e.g. PRTN-2026-00001)",
    )
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to original Purchase Order",
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to target Supplier",
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Source Warehouse from which stock is returned",
    )
    return_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Effective date and time of return dispatch",
    )
    reason_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Standard return reason code: Damaged, Defective, Incorrect Spec, Excess Delivery",
    )
    supplier_return_ref: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Optional supplier RMA or credit reference number",
    )
    total_return_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0"),
        nullable=False,
        comment="Aggregated financial value of returned goods",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Draft",
        nullable=False,
        index=True,
        comment="Status: Draft, Approved, Processed, Cancelled",
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
        comment="User ID who approved/processed the return",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Return notes or shipping instructions",
    )

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", lazy="selectin")
    supplier: Mapped["Supplier"] = relationship("Supplier", lazy="selectin")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", lazy="selectin")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by], lazy="selectin")
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by], lazy="selectin")
    items: Mapped[List["PurchaseReturnItem"]] = relationship(
        "PurchaseReturnItem", back_populates="purchase_return", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<PurchaseReturn(number='{self.return_number}', po_id='{self.purchase_order_id}', status='{self.status}')>"


class PurchaseReturnItem(Base, UUIDMixin, TimestampMixin):
    """
    PurchaseReturnItem ORM model.
    Line items returned under a PurchaseReturn document.
    """
    __tablename__ = "purchase_return_items"

    purchase_return_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_returns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent PurchaseReturn",
    )
    po_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_order_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to originating PurchaseOrderItem",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to returned Product",
    )
    return_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Quantity of stock being returned",
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Credit or return price per unit",
    )
    reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Line item specific return reason notes",
    )

    # Relationships
    purchase_return: Mapped["PurchaseReturn"] = relationship("PurchaseReturn", back_populates="items")
    po_item: Mapped["PurchaseOrderItem"] = relationship("PurchaseOrderItem", lazy="selectin")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")

    def __repr__(self) -> str:
        return f"<PurchaseReturnItem(product_id='{self.product_id}', return_qty={self.return_quantity})>"
