import uuid
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class ProductDocument(Base, UUIDMixin, TimestampMixin):
    """
    ProductDocument ORM model linking uploaded file records to products.
    Document Types: Manual, Warranty, Specification, Compliance, Certificate, Image.
    """
    __tablename__ = "product_documents"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key referencing target Product",
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key referencing stored File record",
    )
    document_type: Mapped[str] = mapped_column(
        String(50),
        default="Specification",
        nullable=False,
        index=True,
        comment="Document type: Manual, Warranty, Specification, Compliance, Certificate, Image",
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="documents",
        lazy="selectin",
    )
    file: Mapped["File"] = relationship(
        "File",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ProductDocument(product_id='{self.product_id}', file_id='{self.file_id}', document_type='{self.document_type}')>"
