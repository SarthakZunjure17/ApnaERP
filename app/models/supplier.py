from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class SupplierCategory(Base, UUIDMixin, TimestampMixin):
    """
    SupplierCategory ORM model.
    Classifies suppliers by industry, material type, or procurement category.
    """
    __tablename__ = "supplier_categories"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique supplier category code (e.g. CAT-RAW-MAT, CAT-ELECTRONICS)",
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
        comment="Optional category description",
    )

    # Relationships
    suppliers: Mapped[List["Supplier"]] = relationship("Supplier", back_populates="category", lazy="selectin")

    def __repr__(self) -> str:
        return f"<SupplierCategory(code='{self.code}', name='{self.name}')>"


class Supplier(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Supplier ORM model representing Vendor/Supplier master data.
    Stores tax identification, payment terms, credit limits, performance metrics, and status.
    """
    __tablename__ = "suppliers"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique supplier master code (e.g. SUP-00001)",
    )
    name: Mapped[str] = mapped_column(
        String(150),
        index=True,
        nullable=False,
        comment="Legal or trade name of supplier",
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional category classification FK",
    )
    gst_vat_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="GST / VAT registration identification number",
    )
    tax_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Corporate tax identification number (PAN / EIN)",
    )
    payment_terms: Mapped[str] = mapped_column(
        String(50),
        default="Net 30",
        nullable=False,
        comment="Default payment terms (e.g. Net 30, Net 60, Advance, Due on Receipt)",
    )
    credit_limit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0"),
        nullable=False,
        comment="Approved credit limit amount",
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        default="USD",
        nullable=False,
        comment="Default transaction currency code (ISO 4217)",
    )
    bank_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Bank name for electronic fund transfer",
    )
    bank_account_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Bank account number",
    )
    bank_ifsc_swift: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Bank IFSC or SWIFT / BIC code",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Active",
        nullable=False,
        index=True,
        comment="Status: Active, Inactive, Blacklisted",
    )
    is_preferred: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="True if vendor is a preferred partner",
    )
    rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        default=Decimal("0.0"),
        nullable=False,
        comment="Aggregated vendor performance rating (0.00 to 5.00)",
    )
    ontime_delivery_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("100.00"),
        nullable=False,
        comment="Historical on-time delivery percentage rate (0.00 - 100.00)",
    )
    quality_rating: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("100.00"),
        nullable=False,
        comment="Historical quality compliance percentage rate (0.00 - 100.00)",
    )
    total_spend: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0"),
        nullable=False,
        comment="Cumulative purchasing spend value",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Internal notes or remarks",
    )

    # Relationships
    category: Mapped[Optional["SupplierCategory"]] = relationship("SupplierCategory", back_populates="suppliers", lazy="selectin")
    contacts: Mapped[List["SupplierContact"]] = relationship("SupplierContact", back_populates="supplier", cascade="all, delete-orphan", lazy="selectin")
    addresses: Mapped[List["SupplierAddress"]] = relationship("SupplierAddress", back_populates="supplier", cascade="all, delete-orphan", lazy="selectin")
    documents: Mapped[List["SupplierDocument"]] = relationship("SupplierDocument", back_populates="supplier", cascade="all, delete-orphan", lazy="selectin")
    ratings: Mapped[List["SupplierRating"]] = relationship("SupplierRating", back_populates="supplier", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Supplier(code='{self.code}', name='{self.name}', status='{self.status}')>"


class SupplierContact(Base, UUIDMixin, TimestampMixin):
    """
    SupplierContact ORM model.
    Represents key contact persons for a supplier.
    """
    __tablename__ = "supplier_contacts"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent Supplier",
    )
    contact_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Full name of contact person",
    )
    designation: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Job title or designation",
    )
    email: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
        comment="Email address of contact person",
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Phone or mobile number",
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if this is the primary point of contact",
    )

    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="contacts")

    def __repr__(self) -> str:
        return f"<SupplierContact(name='{self.contact_name}', email='{self.email}')>"


class SupplierAddress(Base, UUIDMixin, TimestampMixin):
    """
    SupplierAddress ORM model.
    Stores physical billing, shipping, branch, and corporate address locations.
    """
    __tablename__ = "supplier_addresses"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent Supplier",
    )
    address_type: Mapped[str] = mapped_column(
        String(50),
        default="Billing",
        nullable=False,
        comment="Address classification: Billing, Shipping, Head Office, Branch",
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
        comment="City / Town",
    )
    state: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="State / Province",
    )
    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Country name",
    )
    postal_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Postal / Zip code",
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if primary location for address type",
    )

    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="addresses")

    def __repr__(self) -> str:
        return f"<SupplierAddress(type='{self.address_type}', city='{self.city}')>"


class SupplierDocument(Base, UUIDMixin, TimestampMixin):
    """
    SupplierDocument ORM model.
    Links digital attachments (tax certificates, contracts, ISO certificates) to suppliers via File storage.
    """
    __tablename__ = "supplier_documents"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent Supplier",
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to stored File entity",
    )
    document_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Document classification (e.g. Tax Certificate, NDA, ISO Audit)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Optional document summary or notes",
    )

    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="documents")
    file: Mapped["File"] = relationship("File", lazy="selectin")

    def __repr__(self) -> str:
        return f"<SupplierDocument(type='{self.document_type}', file_id='{self.file_id}')>"


class SupplierRating(Base, UUIDMixin, TimestampMixin):
    """
    SupplierRating ORM model.
    Historical rating reviews submitted by procurement evaluators.
    """
    __tablename__ = "supplier_ratings"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent Supplier",
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to User who evaluated the supplier",
    )
    score: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        comment="Rating score from 1.00 to 5.00",
    )
    review_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Timestamp of evaluation",
    )
    comments: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Evaluator comments and performance feedback",
    )

    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="ratings")
    reviewer: Mapped["User"] = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<SupplierRating(supplier_id='{self.supplier_id}', score={self.score})>"
