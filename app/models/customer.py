from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class CustomerCategory(Base, UUIDMixin, TimestampMixin):
    """
    CustomerCategory ORM model.
    Classifies customers by tier/type (e.g. Enterprise, B2B, Retail, Wholesale, Government).
    """
    __tablename__ = "customer_categories"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique customer category code",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
        comment="Human-readable category name",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Category description",
    )

    customers: Mapped[List["Customer"]] = relationship("Customer", back_populates="category", lazy="selectin")


class Customer(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Customer ORM model representing commercial clients in ApnaERP.
    Tracks credit limits, payment terms, tax numbers, ratings, and statuses.
    """
    __tablename__ = "customers"

    customer_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique customer identification code (e.g. CUST-001)",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
        comment="Legal or business customer name",
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK referencing CustomerCategory",
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        index=True,
        nullable=True,
        comment="Primary customer email address",
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Primary customer phone number",
    )
    website: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Customer website URL",
    )
    tax_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        index=True,
        nullable=True,
        comment="GST / VAT / Tax ID registration number",
    )
    credit_limit: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Approved credit limit amount in default currency",
    )
    credit_days: Mapped[int] = mapped_column(
        Numeric(5, 0),
        default=30,
        nullable=False,
        comment="Allowed credit period in days (payment terms)",
    )
    payment_terms: Mapped[str] = mapped_column(
        String(100),
        default="Net 30",
        nullable=False,
        comment="Payment term code or description (e.g. Net 30, Immediate, COD)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Active",
        nullable=False,
        index=True,
        comment="Customer status: Active, Inactive, Blacklisted",
    )
    is_preferred: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Flag indicating VIP/preferred customer status",
    )
    rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        default=Decimal("5.00"),
        nullable=False,
        comment="Customer performance or risk rating score (0.00 to 5.00)",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Internal notes or customer risk assessment",
    )

    # Relationships
    category: Mapped[Optional["CustomerCategory"]] = relationship("CustomerCategory", back_populates="customers", lazy="selectin")
    contacts: Mapped[List["CustomerContact"]] = relationship(
        "CustomerContact", back_populates="customer", cascade="all, delete-orphan", lazy="selectin"
    )
    addresses: Mapped[List["CustomerAddress"]] = relationship(
        "CustomerAddress", back_populates="customer", cascade="all, delete-orphan", lazy="selectin"
    )
    documents: Mapped[List["CustomerDocument"]] = relationship(
        "CustomerDocument", back_populates="customer", cascade="all, delete-orphan", lazy="selectin"
    )


class CustomerContact(Base, UUIDMixin, TimestampMixin):
    """
    CustomerContact ORM model.
    Personnel contacts associated with a customer entity.
    """
    __tablename__ = "customer_contacts"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent Customer reference",
    )
    contact_person: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment="Full name of contact person",
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Contact email address",
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Contact phone number",
    )
    designation: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Role / Designation within customer company",
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if this is the primary point of contact",
    )

    customer: Mapped["Customer"] = relationship("Customer", back_populates="contacts")


class CustomerAddress(Base, UUIDMixin, TimestampMixin):
    """
    CustomerAddress ORM model.
    Physical, billing, and shipping locations for a customer.
    """
    __tablename__ = "customer_addresses"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent Customer reference",
    )
    address_type: Mapped[str] = mapped_column(
        String(20),
        default="Billing",
        nullable=False,
        comment="Address type: Billing, Shipping, Both",
    )
    address_line1: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Street address line 1",
    )
    address_line2: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Street address line 2",
    )
    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="City name",
    )
    state: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="State or Province",
    )
    postal_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Postal or ZIP code",
    )
    country: Mapped[str] = mapped_column(
        String(100),
        default="India",
        nullable=False,
        comment="Country name",
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if default address for this address_type",
    )

    customer: Mapped["Customer"] = relationship("Customer", back_populates="addresses")


class CustomerDocument(Base, UUIDMixin, TimestampMixin):
    """
    CustomerDocument ORM model.
    Document attachments linked to a Customer entity.
    """
    __tablename__ = "customer_documents"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent Customer reference",
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK referencing File model attachment",
    )
    document_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Document classification (e.g. Tax Certificate, Credit Agreement, Contract)",
    )

    customer: Mapped["Customer"] = relationship("Customer", back_populates="documents")
    file: Mapped["File"] = relationship("File", lazy="selectin")
