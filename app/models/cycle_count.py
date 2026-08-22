from datetime import datetime, timezone
import uuid
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class CycleCount(Base, UUIDMixin, TimestampMixin):
    """
    CycleCount ORM Model.
    Physical stock auditing document.
    Status: Draft, In Progress, Completed, Approved, Cancelled.
    Upon approval, generates an InventoryAdjustment to sync physical stock with ledger.
    """
    __tablename__ = "cycle_counts"

    count_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique count document tracking number (e.g. CC-2026-0001)",
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Target warehouse being audited",
    )
    storage_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional target sub-location/rack/bin",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Draft",
        nullable=False,
        index=True,
        comment="Status: Draft, In Progress, Completed, Approved, Cancelled",
    )
    planned_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=True,
        comment="Planned date of cycle count",
    )
    counted_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID of auditor performing the count",
    )
    approved_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID of inventory manager approving the count and generating adjustment",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Audit remarks or notes",
    )

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", lazy="selectin")
    storage_location: Mapped[Optional["StorageLocation"]] = relationship("StorageLocation", lazy="selectin")
    counted_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[counted_by_id], lazy="selectin")
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id], lazy="selectin")
    items: Mapped[List["CycleCountItem"]] = relationship(
        "CycleCountItem",
        back_populates="cycle_count",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<CycleCount(id={self.id}, count_number='{self.count_number}', status='{self.status}')>"


class CycleCountItem(Base, UUIDMixin, TimestampMixin):
    """
    CycleCountItem ORM Model.
    Individual item audit record within a cycle count document.
    """
    __tablename__ = "cycle_count_items"

    cycle_count_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cycle_counts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent cycle count document ID",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Audited Product master ID",
    )
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional audited Batch ID",
    )
    system_qty: Mapped[float] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Recorded quantity in StockBalance at start of audit",
    )
    counted_qty: Mapped[float] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Actual physically counted quantity",
    )
    variance_qty: Mapped[float] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Calculated variance: (counted_qty - system_qty)",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Item specific discrepancy notes",
    )

    # Relationships
    cycle_count: Mapped["CycleCount"] = relationship("CycleCount", back_populates="items")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
    batch: Mapped[Optional["Batch"]] = relationship("Batch", lazy="selectin")

    def __repr__(self) -> str:
        return f"<CycleCountItem(id={self.id}, product_id={self.product_id}, system_qty={self.system_qty}, counted_qty={self.counted_qty})>"
