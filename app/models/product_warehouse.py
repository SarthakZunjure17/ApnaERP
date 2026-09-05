from decimal import Decimal
from typing import Optional
import uuid
from sqlalchemy import Boolean, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class ProductWarehouse(Base, UUIDMixin, TimestampMixin):
    """
    ProductWarehouse ORM model representing product-specific warehouse configuration.
    Defines stocking rules, reorder thresholds, safety stocks, and preferred bin locations per warehouse facility.
    Configuration ONLY — actual balances are tracked in the Stock Ledger (v0.6.1).
    """
    __tablename__ = "product_warehouses"
    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", name="uq_product_warehouse"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key referencing target Product master record",
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key referencing target Warehouse facility",
    )
    preferred_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional default/preferred StorageLocation within this warehouse",
    )
    reorder_level: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4),
        nullable=True,
        comment="Warehouse-specific stock reorder point threshold",
    )
    reorder_quantity: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4),
        nullable=True,
        comment="Warehouse-specific suggested replenishment order quantity",
    )
    minimum_stock: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4),
        nullable=True,
        comment="Warehouse-specific minimum safety stock floor threshold",
    )
    maximum_stock: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4),
        nullable=True,
        comment="Warehouse-specific maximum storage capacity ceiling threshold",
    )
    safety_stock: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4),
        nullable=True,
        comment="Warehouse-specific designated safety buffer quantity",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Active status flag for product-warehouse assignment",
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="warehouse_configs",
        lazy="selectin",
    )
    warehouse: Mapped["Warehouse"] = relationship(
        "Warehouse",
        back_populates="product_configs",
        lazy="selectin",
    )
    preferred_location: Mapped[Optional["StorageLocation"]] = relationship(
        "StorageLocation",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ProductWarehouse(product_id='{self.product_id}', warehouse_id='{self.warehouse_id}', is_active={self.is_active})>"
