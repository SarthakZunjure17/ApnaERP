import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class Notification(Base, UUIDMixin, TimestampMixin):
    """
    Centralized Notification ORM model tracking user in-app and email notifications.
    """
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK referencing recipient User",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Notification headline title",
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full notification message text",
    )
    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="IN_APP",
        server_default="IN_APP",
        index=True,
        comment="Notification channel type (IN_APP, EMAIL, SYSTEM, ALERT)",
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="MEDIUM",
        server_default="MEDIUM",
        index=True,
        comment="Notification urgency priority level (LOW, MEDIUM, HIGH, URGENT)",
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
        comment="True if notification has been marked as read by user",
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when notification was marked as read (UTC)",
    )

    # Relationships
    user = relationship("User", backref="notifications", lazy="selectin")


class NotificationTemplate(Base, UUIDMixin, TimestampMixin):
    """
    Notification Template ORM model defining reusable Jinja2 dynamic templates for Emails and In-App messages.
    """
    __tablename__ = "notification_templates"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique identifier name of notification template",
    )
    subject: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Email subject line template (supports Jinja2 variables)",
    )
    template_body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Jinja2 template body text or HTML content",
    )
    template_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="EMAIL",
        server_default="EMAIL",
        index=True,
        comment="Target channel type (EMAIL, IN_APP)",
    )
