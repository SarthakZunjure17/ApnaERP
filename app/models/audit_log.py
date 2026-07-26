import uuid
from typing import Any, Dict, Optional
from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """
    Centralized Audit Log ORM model recording all significant user actions,
    data mutations, security events, and request metadata.
    """
    __tablename__ = "audit_logs"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="User ID who performed the action (nullable for unauthenticated/system actions)",
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Username of the performing actor",
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Action performed (e.g. LOGIN, USER_REGISTER, ROLE_ASSIGN, CREATE, UPDATE, DELETE)",
    )
    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Target entity type (e.g. User, Role, Permission, Order)",
    )
    entity_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Primary Key ID of the target entity",
    )
    previous_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="State snapshot of entity prior to modification",
    )
    new_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="State snapshot of entity after modification",
    )
    http_method: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="HTTP request method (GET, POST, PUT, DELETE)",
    )
    api_endpoint: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="API endpoint URL path",
    )
    request_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Unique correlation request ID",
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        comment="Client IP address",
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Client User-Agent header string",
    )
    status_code: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="HTTP response status code",
    )
