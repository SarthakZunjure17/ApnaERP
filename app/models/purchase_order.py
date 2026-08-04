from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class PurchaseOrder(Base, UUIDMixin, TimestampMixin):
    """
    PurchaseOrder ORM model.
    Legally binding commercial order issued to a Supplier.
    Lifecycle states: Draft -> Submitted -> Approved -> Partially Received / Fully Received -> Closed (or Rejected/Cancelled).
    Supports revision history and multi-warehouse line item delivery destinations.
    """
    __tablename__ = "purchase_orders"

    po_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique Purchase Order tracking number (e.g. PO-2026-00001)",
    )
    origin_type: Mapped[str] = mapped_column(
        String(30),
        default="Manual",
        nullable=False,
        comment="Origin source: Manual, Requisition, RFQ, Quotation",
    )
    origin_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Optional document ID of origin Requisition, RFQ, or Quotation",
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to target Supplier",
    )
    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Date PO was issued",
    )
    expected_delivery_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Promised or expected overall delivery date",
    )
    payment_terms: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Agreed payment terms (e.g. Net 30)",
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        default="USD",
        nullable=False,
        comment="PO transaction currency code",
    )
    shipping_address: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Default shipping address text",
    )
    billing_address: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Default billing address text",
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
        comment="Final purchase order total amount",
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="Draft",
        nullable=False,
        index=True,
        comment="Status: Draft, Submitted, Approved, Rejected, Cancelled, Closed, Reopened",
    )
    revision_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="PO revision version counter",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who created the PO",
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who approved the PO",
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of PO approval",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Special terms or purchase notes",
    )

    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier", lazy="selectin")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by], lazy="selectin")
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by], lazy="selectin")
    items: Mapped[List["PurchaseOrderItem"]] = relationship(
        "PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<PurchaseOrder(number='{self.po_number}', supplier_id='{self.supplier_id}', status='{self.status}')>"


class PurchaseOrderItem(Base, UUIDMixin, TimestampMixin):
    """
    PurchaseOrderItem ORM model.
    Line items ordered under a PurchaseOrder with individual receiving and returning counters.
    """
    __tablename__ = "purchase_order_items"

    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent PurchaseOrder",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to ordered Product",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Item specification or description override",
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Ordered quantity",
    )
    received_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0"),
        nullable=False,
        comment="Cumulatively received stock quantity via GoodsReceipt",
    )
    returned_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0"),
        nullable=False,
        comment="Cumulatively returned stock quantity via PurchaseReturn",
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Agreed price per unit",
    )
    discount_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.0"),
        nullable=False,
        comment="Percentage discount for line item",
    )
    tax_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.0"),
        nullable=False,
        comment="Percentage tax for line item",
    )
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Final calculated line item price",
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Destination Warehouse for receiving this item",
    )
    storage_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional destination sub-storage location",
    )
    expected_delivery_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Line item specific expected delivery date",
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="Pending",
        nullable=False,
        index=True,
        comment="Line item receiving status: Pending, Partially Received, Fully Received, Cancelled",
    )

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="items")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", lazy="selectin")
    storage_location: Mapped[Optional["StorageLocation"]] = relationship("StorageLocation", lazy="selectin")

    def __repr__(self) -> str:
        return f"<PurchaseOrderItem(po_id='{self.purchase_order_id}', product_id='{self.product_id}', qty={self.quantity}, status='{self.status}')>"
