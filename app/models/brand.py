from typing import Optional
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class Brand(Base, UUIDMixin, TimestampMixin):
    """
    Brand ORM model representing product manufacturer or trademark brands.
    """
    __tablename__ = "brands"

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique brand name",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Brand description or notes",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Active status flag",
    )

    def __repr__(self) -> str:
        return f"<Brand(name='{self.name}', is_active={self.is_active})>"
