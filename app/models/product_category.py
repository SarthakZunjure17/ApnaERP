from typing import List, Optional
import uuid
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class ProductCategory(Base, UUIDMixin, TimestampMixin):
    """
    ProductCategory ORM model representing hierarchical product categories.
    Supports infinite category tree nesting.
    """
    __tablename__ = "product_categories"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique category code identifier (e.g. CAT_ELECTRONICS)",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Display category name",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Detailed category description",
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_categories.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Foreign key referencing parent ProductCategory for nesting",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Active status flag",
    )

    # Relationships
    parent: Mapped[Optional["ProductCategory"]] = relationship(
        "ProductCategory",
        remote_side="ProductCategory.id",
        back_populates="children",
        lazy="selectin",
    )
    children: Mapped[List["ProductCategory"]] = relationship(
        "ProductCategory",
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ProductCategory(code='{self.code}', name='{self.name}', parent_id='{self.parent_id}')>"
