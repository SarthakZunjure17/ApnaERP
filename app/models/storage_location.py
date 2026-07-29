from typing import List, Optional
import uuid
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class StorageLocation(Base, UUIDMixin, TimestampMixin):
    """
    StorageLocation ORM model representing internal warehouse storage sub-locations
    (Shelf, Rack, Bin, Floor, Cold Storage, Quarantine, Receiving, Dispatch).
    Supports infinite location hierarchy per warehouse.
    """
    __tablename__ = "storage_locations"

    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key referencing target Warehouse facility",
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_locations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Foreign key referencing parent StorageLocation for hierarchy",
    )
    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Location code identifier within warehouse (e.g. RACK_A_SHELF_2)",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Display name of the location",
    )
    location_type: Mapped[str] = mapped_column(
        String(50),
        default="Bin",
        nullable=False,
        index=True,
        comment="Location type: Shelf, Rack, Bin, Floor, Cold Storage, Quarantine, Receiving, Dispatch",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Active status flag",
    )

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship(
        "Warehouse",
        back_populates="locations",
        lazy="selectin",
    )
    parent: Mapped[Optional["StorageLocation"]] = relationship(
        "StorageLocation",
        remote_side="StorageLocation.id",
        back_populates="children",
        lazy="selectin",
    )
    children: Mapped[List["StorageLocation"]] = relationship(
        "StorageLocation",
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<StorageLocation(code='{self.code}', name='{self.name}', type='{self.location_type}')>"
