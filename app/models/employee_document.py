import datetime
from typing import Optional
import uuid
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class EmployeeDocument(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    EmployeeDocument ORM Model.
    Represents digital personnel files, verification status, and metadata linked to Employee and File entities.
    """
    __tablename__ = "employee_documents"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    document_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    document_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    issue_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)

    verification_status: Mapped[str] = mapped_column(String(50), default="Pending", nullable=False)

    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    verified_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    employee: Mapped["Employee"] = relationship("Employee")  # noqa: F821
    file: Mapped["File"] = relationship("File")  # noqa: F821
    verifier: Mapped[Optional["User"]] = relationship("User", foreign_keys=[verified_by])  # noqa: F821

    def __repr__(self) -> str:
        return f"<EmployeeDocument(id={self.id}, type='{self.document_type}', status='{self.verification_status}')>"
