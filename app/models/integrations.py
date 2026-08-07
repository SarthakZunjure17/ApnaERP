import datetime
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class ApiKey(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    ApiKey ORM Model.
    Granular API Key authentication and scope tracking.
    """
    __tablename__ = "api_keys"

    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    scopes: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False, comment="Permission scopes list")
    expires_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<ApiKey(name='{self.name}', prefix='{self.prefix}', revoked={self.is_revoked})>"


class WebhookSubscription(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    WebhookSubscription ORM Model.
    Webhook registrations for real-time outbound event notifications.
    """
    __tablename__ = "webhook_subscriptions"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    secret_token: Mapped[str] = mapped_column(String(255), nullable=False, comment="HMAC signature secret")
    event_types: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False, comment="Subscribed domain event types")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    headers_json: Mapped[Optional[Dict[str, str]]] = mapped_column(JSONB, default=dict, nullable=True)

    # Relationships
    deliveries: Mapped[List["WebhookDelivery"]] = relationship(
        "WebhookDelivery", back_populates="subscription", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<WebhookSubscription(name='{self.name}', target='{self.target_url}', active={self.is_active})>"


class WebhookDelivery(Base, UUIDMixin, TimestampMixin):
    """
    WebhookDelivery ORM Model.
    Audit and retry log for webhook event delivery attempts.
    """
    __tablename__ = "webhook_deliveries"

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    next_retry_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="Pending", nullable=False, index=True, comment="Pending, Delivered, Failed, Retrying"
    )

    # Relationships
    subscription: Mapped["WebhookSubscription"] = relationship("WebhookSubscription", back_populates="deliveries")

    def __repr__(self) -> str:
        return f"<WebhookDelivery(event='{self.event_type}', status='{self.status}', attempts={self.attempt_count})>"


class ProviderConfiguration(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    ProviderConfiguration ORM Model.
    Pluggable external provider settings (Storage, Communication, Auth, Payment).
    """
    __tablename__ = "provider_configurations"

    provider_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Storage, Email, SMS, WhatsApp, Push, OAuth2, LDAP, MFA",
    )
    provider_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Local, MinIO, S3, AzureBlob, GCS, SMTP, Twilio, MetaCloud, FCM",
    )
    settings_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<ProviderConfiguration(type='{self.provider_type}', name='{self.provider_name}', active={self.is_active})>"


class BackupMetadata(Base, UUIDMixin, TimestampMixin):
    """
    BackupMetadata ORM Model.
    Database and storage snapshot backup registry.
    """
    __tablename__ = "backup_metadata"

    backup_name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    backup_type: Mapped[str] = mapped_column(
        String(30), default="FullDatabase", nullable=False, comment="FullDatabase, FileStorage, ConfigurationOnly"
    )
    status: Mapped[str] = mapped_column(
        String(30), default="Completed", nullable=False, index=True, comment="InProgress, Completed, Failed, Restored"
    )
    checksum: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<BackupMetadata(name='{self.backup_name}', type='{self.backup_type}', size={self.file_size_bytes})>"


class SystemConfiguration(Base, UUIDMixin, TimestampMixin):
    """
    SystemConfiguration ORM Model.
    Dynamic runtime system-wide settings registry.
    """
    __tablename__ = "system_configurations"

    config_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(
        String(30), default="String", nullable=False, comment="String, Integer, Boolean, Float, JSON"
    )
    category: Mapped[str] = mapped_column(
        String(50), default="General", nullable=False, index=True, comment="General, Security, RateLimit, Cache, Email"
    )
    is_encrypted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<SystemConfiguration(key='{self.config_key}', category='{self.category}')>"
