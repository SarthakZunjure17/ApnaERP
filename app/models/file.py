import uuid
from typing import Optional
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class File(Base, UUIDMixin, TimestampMixin):
    """
    Centralized File & Document ORM model tracking uploaded enterprise assets,
    storage paths, SHA256 checksums, access controls, and entity attachments.
    """
    __tablename__ = "files"

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original client filename",
    )
    stored_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Unique generated stored filename",
    )
    file_extension: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="File extension without leading dot (e.g. pdf, png)",
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="MIME content type string",
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="File size in bytes",
    )
    storage_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Relative path to stored asset (internal use only)",
    )
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK referencing User who uploaded the file",
    )
    entity_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Target ERP entity type attached to (e.g. Employee, Invoice)",
    )
    entity_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Primary Key ID of target attached entity",
    )
    checksum: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA256 hex digest checksum for duplicate detection",
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="True if publicly accessible without authentication",
    )

    # Relationships
    uploader = relationship("User", backref="uploaded_files", lazy="selectin")
