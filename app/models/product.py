from typing import List, Optional
import uuid
from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class Product(Base, UUIDMixin, TimestampMixin):
    """
    Product ORM model representing product items in the Product Master catalog.
    """
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Stock Keeping Unit (globally unique item code)",
    )
    barcode: Mapped[Optional[str]] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
        comment="Global Trade Item Number / Barcode (unique if provided)",
    )
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
        comment="Product title / display name",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Product detailed description",
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign key referencing product category",
    )
    brand_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Foreign key referencing brand",
    )
    base_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("unit_of_measures.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign key referencing default base UnitOfMeasure",
    )
    purchase_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("unit_of_measures.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Foreign key referencing purchase UnitOfMeasure",
    )
    sales_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("unit_of_measures.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Foreign key referencing sales UnitOfMeasure",
    )
    product_type: Mapped[str] = mapped_column(
        String(50),
        default="Inventory",
        nullable=False,
        index=True,
        comment="Product type: Inventory, Service, Consumable, Digital, Asset",
    )
    track_inventory: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Flag indicating if inventory stock levels are tracked",
    )
    allow_negative_stock: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Flag allowing negative stock balances",
    )
    default_warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        comment="Foreign key referencing default warehouse for stocking",
    )
    weight: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 3),
        nullable=True,
        comment="Weight metric",
    )
    height: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 3),
        nullable=True,
        comment="Height metric",
    )
    width: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 3),
        nullable=True,
        comment="Width metric",
    )
    length: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 3),
        nullable=True,
        comment="Length metric",
    )
    volume: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 3),
        nullable=True,
        comment="Volume metric",
    )
    image_file_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
        comment="Foreign key referencing primary product thumbnail image file",
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="Draft",
        nullable=False,
        index=True,
        comment="Product lifecycle status: Draft, Active, Discontinued, Archived",
    )

    # Relationships
    category: Mapped["ProductCategory"] = relationship(
        "ProductCategory",
        lazy="selectin",
    )
    brand: Mapped[Optional["Brand"]] = relationship(
        "Brand",
        lazy="selectin",
    )
    base_unit: Mapped["UnitOfMeasure"] = relationship(
        "UnitOfMeasure",
        foreign_keys=[base_unit_id],
        lazy="selectin",
    )
    purchase_unit: Mapped[Optional["UnitOfMeasure"]] = relationship(
        "UnitOfMeasure",
        foreign_keys=[purchase_unit_id],
        lazy="selectin",
    )
    sales_unit: Mapped[Optional["UnitOfMeasure"]] = relationship(
        "UnitOfMeasure",
        foreign_keys=[sales_unit_id],
        lazy="selectin",
    )
    default_warehouse: Mapped[Optional["Warehouse"]] = relationship(
        "Warehouse",
        lazy="selectin",
    )

    attributes: Mapped[List["ProductAttributeValue"]] = relationship(
        "ProductAttributeValue",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    documents: Mapped[List["ProductDocument"]] = relationship(
        "ProductDocument",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Product(sku='{self.sku}', name='{self.name}', status='{self.status}')>"
