from typing import List, Optional
import uuid
from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
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
    __table_args__ = (
        UniqueConstraint("warehouse_id", "code", name="uq_warehouse_location_code"),
    )

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
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Storage location description or notes",
    )
    location_type: Mapped[str] = mapped_column(
        String(50),
        default="Bin",
        nullable=False,
        index=True,
        comment="Location type: Storage, Receiving, Shipping, Quarantine, Returns, Damaged, Shelf, Rack, Bin, Floor, Cold Storage",
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

    @property
    def parent_location_id(self) -> Optional[uuid.UUID]:
        return self.parent_id

    def __repr__(self) -> str:
        return f"<StorageLocation(code='{self.code}', name='{self.name}', type='{self.location_type}')>"
