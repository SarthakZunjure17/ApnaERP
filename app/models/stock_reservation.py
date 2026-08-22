from datetime import datetime, timezone
import uuid
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class StockReservation(Base, UUIDMixin, TimestampMixin):
    """
    StockReservation ORM Model.
    Reserves stock for upcoming demand (Sales, Manufacturing, Procurement, Internal).
    Does NOT write StockLedger entries or alter physical stock quantities.
    Reduces available stock projection (available = physical - reserved).
    Status: Active, Fulfilled, Expired, Cancelled.
    """
    __tablename__ = "stock_reservations"

    reservation_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique stock reservation tracking number (e.g. RES-2026-0001)",
    )
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
        comment="Target Warehouse for reserved stock",
    )
    storage_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional target storage location",
    )
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional target batch",
    )
    quantity: Mapped[float] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Reserved stock quantity",
    )
    reserved_for_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Downstream module or demand type: Sales, Manufacturing, Procurement, Internal",
    )
    reserved_for_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Optional document ID (e.g. SalesOrder ID, WorkOrder ID)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Active",
        nullable=False,
        index=True,
        comment="Reservation status: Active, Fulfilled, Expired, Cancelled",
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Optional expiration date/time for auto-releasing the reservation",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reason or context notes",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who created the reservation",
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", lazy="selectin")
    storage_location: Mapped[Optional["StorageLocation"]] = relationship("StorageLocation", lazy="selectin")
    batch: Mapped[Optional["Batch"]] = relationship("Batch", lazy="selectin")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by], lazy="selectin")

    def __repr__(self) -> str:
        return f"<StockReservation(id={self.id}, number='{self.reservation_number}', product_id={self.product_id}, qty={self.quantity}, status='{self.status}')>"
