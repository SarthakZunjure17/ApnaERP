from datetime import datetime, timezone
import uuid
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
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
    transaction_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory_transaction_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Reference to InventoryTransactionType",
    )
    reference_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Upstream document or module type (e.g. OpeningStock, InventoryAdjustment)",
    )
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Upstream document or record UUID",
    )
    quantity: Mapped[float] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Quantity of stock moved (always positive magnitude)",
    )
    unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("unit_of_measures.id", ondelete="SET NULL"),
        nullable=True,
        comment="Unit of Measure for the transaction quantity",
    )
    direction: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Direction of movement: IN, OUT, TRANSFER, ADJUSTMENT, SYSTEM",
    )
    running_balance: Mapped[float] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Calculated total running balance for product at target warehouse after movement",
    )
    transaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        comment="Effective date and time of transaction (UTC)",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Remarks or justification notes",
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
    transaction_type: Mapped["InventoryTransactionType"] = relationship("InventoryTransactionType", lazy="selectin")
    unit: Mapped[Optional["UnitOfMeasure"]] = relationship("UnitOfMeasure", lazy="selectin")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by], lazy="selectin")

    def __repr__(self) -> str:
        return f"<StockLedger(id={self.id}, product_id={self.product_id}, direction='{self.direction}', qty={self.quantity}, running_balance={self.running_balance})>"
