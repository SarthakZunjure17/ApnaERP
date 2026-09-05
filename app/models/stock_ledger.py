from datetime import datetime, timezone
import uuid
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import UUIDMixin


class StockLedger(Base, UUIDMixin):
    """
    StockLedger ORM model.
    Immutable transaction log recording all physical stock movements across products, warehouses, and storage locations.
    No stock modification may occur without creating an immutable entry in this table.
    """
    __tablename__ = "stock_ledgers"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Reference to Product master record",
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Reference to Warehouse facility",
    )
    storage_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional reference to sub-storage location (Rack/Shelf/Bin)",
    )
    movement_type: Mapped[str] = mapped_column(
        String(50),
        default="STOCK_IN",
        nullable=False,
        index=True,
        comment="Generic movement type: STOCK_IN, STOCK_OUT, ADJUSTMENT",
    )
    direction: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Direction of movement: IN, OUT",
    )
    quantity: Mapped[float] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Quantity of stock moved (always positive magnitude)",
    )
    quantity_before: Mapped[float] = mapped_column(
        Numeric(18, 4),
        default=0.0,
        nullable=False,
        comment="Locked stock balance quantity before movement",
    )
    quantity_after: Mapped[float] = mapped_column(
        Numeric(18, 4),
        default=0.0,
        nullable=False,
        comment="Locked stock balance quantity after movement",
    )
    running_balance: Mapped[float] = mapped_column(
        Numeric(18, 4),
        default=0.0,
        nullable=False,
        comment="Calculated total running balance for product at target warehouse after movement",
    )
    transaction_type_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory_transaction_types.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
        comment="Optional reference to InventoryTransactionType",
    )
    unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("unit_of_measures.id", ondelete="SET NULL"),
        nullable=True,
        comment="Unit of Measure for the transaction quantity",
    )
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional associated batch ID",
    )
    reference_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Upstream document or module type (e.g. OpeningStock, InventoryAdjustment, ManualMovement)",
    )
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Upstream document or record UUID",
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        comment="Client-supplied or system idempotency key for movement deduplication",
    )
    reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Business reason for movement",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional descriptive notes",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Remarks or justification notes",
    )
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Extensible JSON metadata",
    )
    transaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        comment="Effective date and time of transaction (UTC)",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who executed the inventory movement",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Record creation timestamp (UTC)",
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", lazy="selectin")
    storage_location: Mapped[Optional["StorageLocation"]] = relationship("StorageLocation", lazy="selectin")
    transaction_type: Mapped[Optional["InventoryTransactionType"]] = relationship("InventoryTransactionType", lazy="selectin")
    unit: Mapped[Optional["UnitOfMeasure"]] = relationship("UnitOfMeasure", lazy="selectin")
    batch: Mapped[Optional["Batch"]] = relationship("Batch", lazy="selectin")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by], lazy="selectin")

    @property
    def unit_of_measure_id(self) -> Optional[uuid.UUID]:
        return self.unit_id

    @unit_of_measure_id.setter
    def unit_of_measure_id(self, val: Optional[uuid.UUID]):
        self.unit_id = val

    def __repr__(self) -> str:
        return f"<StockLedger(id={self.id}, product_id={self.product_id}, type='{self.movement_type}', direction='{self.direction}', qty={self.quantity}, running_balance={self.running_balance})>"

