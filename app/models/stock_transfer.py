from datetime import datetime, timezone
import uuid
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class StockTransfer(Base, UUIDMixin, TimestampMixin):
    """
    StockTransfer ORM model.
    Represents inter-warehouse or intra-warehouse stock transfers.
    Lifecycle states: Draft -> Approved -> In Transit (dispatch OUT) -> Completed (receive IN) (or Cancelled).
    Dispatching generates StockLedger OUT entries at source warehouse.
    Completing/Receiving generates StockLedger IN entries at destination warehouse.
    """
    __tablename__ = "stock_transfers"

    transfer_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique stock transfer document number",
    )
    source_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Source warehouse facility",
    )
    destination_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Destination warehouse facility",
    )
    source_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional source storage location within source warehouse",
    )
    destination_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional destination storage location within destination warehouse",
    )
    transfer_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Effective date and time of transfer initiation (UTC)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Draft",
        nullable=False,
        index=True,
        comment="Document status: Draft, In Transit, Completed, Cancelled",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Remarks or transfer notes",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who created the transfer proposal",
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who approved or dispatched the transfer",
    )
    completed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who completed/received the transfer at destination",
    )

    # Relationships
    source_warehouse: Mapped["Warehouse"] = relationship("Warehouse", foreign_keys=[source_warehouse_id], lazy="selectin")
    destination_warehouse: Mapped["Warehouse"] = relationship("Warehouse", foreign_keys=[destination_warehouse_id], lazy="selectin")
    source_location: Mapped[Optional["StorageLocation"]] = relationship("StorageLocation", foreign_keys=[source_location_id], lazy="selectin")
    destination_location: Mapped[Optional["StorageLocation"]] = relationship("StorageLocation", foreign_keys=[destination_location_id], lazy="selectin")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by], lazy="selectin")
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by], lazy="selectin")
    completer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[completed_by], lazy="selectin")
    items: Mapped[List["StockTransferItem"]] = relationship(
        "StockTransferItem", back_populates="stock_transfer", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<StockTransfer(id={self.id}, number='{self.transfer_number}', status='{self.status}')>"


class StockTransferItem(Base, UUIDMixin):
    """
    StockTransferItem ORM model.
    Line items associated with a StockTransfer document.
    """
    __tablename__ = "stock_transfer_items"

    transfer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_transfers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent StockTransfer document reference",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Reference to Product master record",
    )
    quantity: Mapped[float] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Transferred stock quantity",
    )
    unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("unit_of_measures.id", ondelete="SET NULL"),
        nullable=True,
        comment="Unit of Measure for transferred quantity",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Line item remarks",
    )

    # Relationships
    stock_transfer: Mapped["StockTransfer"] = relationship("StockTransfer", back_populates="items")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
    unit: Mapped[Optional["UnitOfMeasure"]] = relationship("UnitOfMeasure", lazy="selectin")

    def __repr__(self) -> str:
        return f"<StockTransferItem(id={self.id}, product_id={self.product_id}, qty={self.quantity})>"
