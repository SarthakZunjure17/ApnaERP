import uuid
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class ProductAttribute(Base, UUIDMixin, TimestampMixin):
    """
    ProductAttribute ORM model defining reusable product attribute metadata schemas
    (e.g., Color, Size, Voltage, Expiry Required).
    Data Types: Text, Number, Boolean, Date, List.
    """
    __tablename__ = "product_attributes"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Attribute display name",
    )
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique attribute code identifier",
    )
    data_type: Mapped[str] = mapped_column(
        String(30),
        default="Text",
        nullable=False,
        comment="Attribute data type: Text, Number, Boolean, Date, List",
    )

    def __repr__(self) -> str:
        return f"<ProductAttribute(code='{self.code}', name='{self.name}', data_type='{self.data_type}')>"


class ProductAttributeValue(Base, UUIDMixin, TimestampMixin):
    """
    ProductAttributeValue ORM model mapping product attribute values to specific products.
    """
    __tablename__ = "product_attribute_values"
    __table_args__ = (
        UniqueConstraint("product_id", "attribute_id", name="uq_product_attribute"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key referencing target Product",
    )
    attribute_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_attributes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key referencing target ProductAttribute definition",
    )
    value: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Assigned attribute value as string representation",
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="attributes",
        lazy="selectin",
    )
    attribute: Mapped["ProductAttribute"] = relationship(
        "ProductAttribute",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ProductAttributeValue(product_id='{self.product_id}', attribute_id='{self.attribute_id}', value='{self.value}')>"
