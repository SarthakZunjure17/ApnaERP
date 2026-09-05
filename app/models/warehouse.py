from typing import List, Optional
import uuid
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
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
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Detailed warehouse description or operating notes",
    )
    warehouse_type: Mapped[str] = mapped_column(
        String(50),
        default="MAIN",
        nullable=False,
        index=True,
        comment="Warehouse type: MAIN, DISTRIBUTION, RETAIL, VIRTUAL, TRANSIT",
    )
    address: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Legacy physical street address",
    )
    address_line_1: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Primary street address line",
    )
    address_line_2: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Secondary address line or suite",
    )
    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="City",
    )
    state: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="State or Province",
    )
    country: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Country",
    )
    postal_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Postal or ZIP code",
    )
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="UTC",
        nullable=False,
        comment="Facility operating timezone",
    )
    manager_employee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Assigned warehouse manager employee ID",
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
    manager: Mapped[Optional["Employee"]] = relationship(
        "Employee",
        foreign_keys=[manager_employee_id],
        lazy="selectin",
    )
    product_configs: Mapped[List["ProductWarehouse"]] = relationship(
        "ProductWarehouse",
        back_populates="warehouse",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Warehouse(code='{self.code}', name='{self.name}', type='{self.warehouse_type}')>"
