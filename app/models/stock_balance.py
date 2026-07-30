from datetime import datetime, timezone
import uuid
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import UUIDMixin


class StockBalance(Base, UUIDMixin):
    """
    StockBalance ORM model.
    Read-optimized projection/cache table aggregating current available, reserved, damaged, and in-transit quantities.
    This table is a performance projection and is derived from StockLedger history.
    """
    __tablename__ = "stock_balances"
    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", "storage_location_id", name="uq_stock_balance_prod_wh_loc"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to Product master record",
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to Warehouse facility",
    )
    storage_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_locations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Optional reference to sub-storage location",
    )
    available_quantity: Mapped[float] = mapped_column(
        Numeric(18, 4),
        default=0.0,
        nullable=False,
        comment="Available physical stock quantity",
    )
    reserved_quantity: Mapped[float] = mapped_column(
        Numeric(18, 4),
        default=0.0,
        nullable=False,
        comment="Reserved stock quantity for pending allocations",
    )
    damaged_quantity: Mapped[float] = mapped_column(
        Numeric(18, 4),
        default=0.0,
        nullable=False,
        comment="Damaged or non-usable stock quantity",
    )
    in_transit_quantity: Mapped[float] = mapped_column(
        Numeric(18, 4),
        default=0.0,
        nullable=False,
        comment="Stock quantity currently in transit between locations",
    )
    last_calculated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Timestamp when projection balance was last refreshed from ledger",
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", lazy="selectin")
    storage_location: Mapped[Optional["StorageLocation"]] = relationship("StorageLocation", lazy="selectin")

    def __repr__(self) -> str:
        return f"<StockBalance(product_id={self.product_id}, warehouse_id={self.warehouse_id}, available={self.available_quantity})>"
