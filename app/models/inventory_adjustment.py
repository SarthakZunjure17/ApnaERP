from datetime import datetime, timezone
import uuid
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class InventoryAdjustment(Base, UUIDMixin, TimestampMixin):
    """
    InventoryAdjustment ORM model.
    Represents formal stock adjustment proposals (Increase or Decrease) driven by audit/cycle count discrepancies.
    Lifecycle states: Draft -> Approved -> Applied (or Cancelled).
    Applying an adjustment generates an immutable StockLedger entry.
    """
    __tablename__ = "inventory_adjustments"

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
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional reference to sub-storage location",
    )
    adjustment_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Adjustment type: Increase or Decrease",
    )
    reason: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Reason or justification for inventory adjustment",
    )
    expected_quantity: Mapped[float] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Recorded system balance prior to adjustment",
    )
    actual_quantity: Mapped[float] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Physically counted stock quantity",
    )
    difference: Mapped[float] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Calculated adjustment difference magnitude (actual - expected)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Draft",
        nullable=False,
        index=True,
        comment="Adjustment state: Draft, Approved, Applied, Cancelled",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who created the adjustment draft",
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who approved the adjustment proposal",
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when adjustment was approved (UTC)",
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", lazy="selectin")
    storage_location: Mapped[Optional["StorageLocation"]] = relationship("StorageLocation", lazy="selectin")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by], lazy="selectin")
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by], lazy="selectin")

    def __repr__(self) -> str:
        return f"<InventoryAdjustment(id={self.id}, type='{self.adjustment_type}', diff={self.difference}, status='{self.status}')>"
