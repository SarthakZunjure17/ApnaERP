import datetime
from typing import List, Optional
import uuid
from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class Employee(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Employee ORM Model.
    Represents enterprise workforce core entity, reporting structure, department placement, and profile links.
    """
    __tablename__ = "employees"

    employee_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    preferred_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    work_email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    personal_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    work_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    personal_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )

    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    employment_type: Mapped[str] = mapped_column(String(50), default="Full Time", nullable=False)
    employment_status: Mapped[str] = mapped_column(String(50), default="Active", nullable=False)

    joining_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    confirmation_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    exit_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    date_of_birth: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    profile_photo_file_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    department: Mapped["Department"] = relationship("Department")  # noqa: F821

    manager: Mapped[Optional["Employee"]] = relationship(
        "Employee",
        remote_side="Employee.id",
        back_populates="direct_reports",
    )

    direct_reports: Mapped[List["Employee"]] = relationship(
        "Employee",
        back_populates="manager",
    )

    user: Mapped[Optional["User"]] = relationship("User")  # noqa: F821

    profile_photo: Mapped[Optional["File"]] = relationship("File")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Employee(id={self.id}, code='{self.employee_code}', email='{self.work_email}')>"
