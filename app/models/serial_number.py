import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import UUIDMixin


class SerialNumber(Base, UUIDMixin):
    """
    SerialNumber ORM Model.
    Individual serial number tracking for high-value or serialized inventory items.
    Status: Available, Reserved, Sold, Returned, Scrapped, Lost.
    """
    __tablename__ = "serial_numbers"

    serial_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Globally unique serial number string",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Reference to serialized Product master record",
    )
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Current warehouse location of the serialized item",
    )
    storage_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Current storage location/rack/bin of the serialized item",
    )
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional associated batch ID",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Available",
        nullable=False,
        index=True,
        comment="Status: Available, Reserved, Sold, Returned, Scrapped, Lost",
    )
    history: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        default=list,
        nullable=True,
        comment="Chronological movement and lifecycle history log",
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse", lazy="selectin")
    storage_location: Mapped[Optional["StorageLocation"]] = relationship("StorageLocation", lazy="selectin")
    batch: Mapped[Optional["Batch"]] = relationship("Batch", lazy="selectin")

    def __repr__(self) -> str:
        return f"<SerialNumber(id={self.id}, serial_number='{self.serial_number}', product_id={self.product_id}, status='{self.status}')>"
