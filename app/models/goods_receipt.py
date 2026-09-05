from datetime import datetime, timezone
import uuid
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class GoodsReceipt(Base, UUIDMixin, TimestampMixin):
    """
    GoodsReceipt ORM model.
    Represents incoming physical stock documents (e.g. from procurement, vendor delivery, or initial receiving).
    Lifecycle states: Draft -> Approved -> Received (or Cancelled).
    Receiving/Executing a GoodsReceipt generates immutable StockLedger IN entries.
    """
    __tablename__ = "goods_receipts"

    receipt_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique goods receipt document number",
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Destination warehouse facility",
    )
    supplier_reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Optional supplier invoice or challan reference number",
    )
    external_reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Optional external document reference (e.g., PO number)",
    )
    receipt_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Effective date and time of physical receipt (UTC)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Draft",
        nullable=False,
        index=True,
        comment="Document status: Draft, Received, Cancelled",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Remarks or receiving notes",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who created the receipt document",
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who approved or received the document",
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when document was approved/received (UTC)",
    )

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", lazy="selectin")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by], lazy="selectin")
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by], lazy="selectin")
    items: Mapped[List["GoodsReceiptItem"]] = relationship(
        "GoodsReceiptItem", back_populates="goods_receipt", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def notes(self) -> Optional[str]:
        return self.remarks

    @notes.setter
    def notes(self, val: Optional[str]):
        self.remarks = val

    @property
    def received_by(self) -> Optional[uuid.UUID]:
        return self.approved_by

    @received_by.setter
    def received_by(self, val: Optional[uuid.UUID]):
        self.approved_by = val

    def __repr__(self) -> str:
        return f"<GoodsReceipt(id={self.id}, number='{self.receipt_number}', status='{self.status}')>"


class GoodsReceiptItem(Base, UUIDMixin):
    """
    GoodsReceiptItem ORM model.
    Line items associated with a GoodsReceipt document.
    """
    __tablename__ = "goods_receipt_items"

    goods_receipt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("goods_receipts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent GoodsReceipt document reference",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Reference to Product master record",
    )
    storage_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Destination storage location within warehouse",
    )
    quantity: Mapped[float] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Received quantity",
    )
    unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("unit_of_measures.id", ondelete="SET NULL"),
        nullable=True,
        comment="Unit of Measure for received quantity",
    )
    unit_cost: Mapped[Optional[float]] = mapped_column(
        Numeric(18, 4),
        nullable=True,
        comment="Unit cost of received goods",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Line item remarks or condition notes",
    )

    # Relationships
    goods_receipt: Mapped["GoodsReceipt"] = relationship("GoodsReceipt", back_populates="items")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
    storage_location: Mapped[Optional["StorageLocation"]] = relationship("StorageLocation", lazy="selectin")
    unit: Mapped[Optional["UnitOfMeasure"]] = relationship("UnitOfMeasure", lazy="selectin")

    @property
    def notes(self) -> Optional[str]:
        return self.remarks

    @notes.setter
    def notes(self, val: Optional[str]):
        self.remarks = val

    def __repr__(self) -> str:
        return f"<GoodsReceiptItem(id={self.id}, product_id={self.product_id}, qty={self.quantity})>"
