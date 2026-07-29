from typing import List, Optional
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class Warehouse(Base, UUIDMixin, TimestampMixin):
    """
    Warehouse ORM model representing physical inventory storage facilities.
    """
    __tablename__ = "warehouses"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique warehouse code identifier (e.g. WH_MAIN_01)",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Warehouse facility name",
    )
    address: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Physical street address",
    )
    contact_person: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Primary warehouse contact manager name",
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="Contact telephone number",
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Contact email address",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Active status flag",
    )

    # Relationships
    locations: Mapped[List["StorageLocation"]] = relationship(
        "StorageLocation",
        back_populates="warehouse",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Warehouse(code='{self.code}', name='{self.name}')>"
