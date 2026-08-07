import datetime
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------
# API Keys Schemas
# ---------------------------------------------------------
class ApiKeyCreate(BaseModel):
    name: str = Field(..., max_length=150, description="API Key friendly description name")
    scopes: List[str] = Field(default_factory=list, description="Scopes e.g., ['system.read', 'finance.write']")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Expiry in days (optional)")


class ApiKeyCreatedResponse(BaseModel):
    id: uuid.UUID
    name: str
    prefix: str
    raw_api_key: str = Field(..., description="Plaintext API Key returned ONLY ONCE upon creation")
    scopes: List[str]
    expires_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    prefix: str
    scopes: List[str]
    is_revoked: bool
    usage_count: int
    last_used_at: Optional[datetime.datetime] = None
    expires_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# Webhook Schemas
# ---------------------------------------------------------
class WebhookSubscriptionCreate(BaseModel):
    name: str = Field(..., max_length=150)
    target_url: str = Field(..., description="Target HTTPS webhook URL")
    event_types: List[str] = Field(..., description="Subscribed event names e.g., ['sales.order_created']")
    headers_json: Optional[Dict[str, str]] = Field(default_factory=dict)


class WebhookSubscriptionResponse(BaseModel):
    id: uuid.UUID
    name: str
    target_url: str
    secret_token: str
    event_types: List[str]
    is_active: bool
    headers_json: Optional[Dict[str, str]] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class WebhookDeliveryResponse(BaseModel):
    id: uuid.UUID
    subscription_id: uuid.UUID
    event_type: str
    payload_json: Dict[str, Any]
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    attempt_count: int
    status: str
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# Provider Configurations Schemas
# ---------------------------------------------------------
class ProviderConfigCreate(BaseModel):
    provider_type: str = Field(..., description="Storage, Email, SMS, WhatsApp, Push, OAuth2, LDAP, MFA")
    provider_name: str = Field(..., description="Local, MinIO, S3, AzureBlob, GCS, SMTP, Twilio, MetaCloud, FCM")
    settings_json: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    is_default: bool = False


class ProviderConfigResponse(BaseModel):
    id: uuid.UUID
    provider_type: str
    provider_name: str
    settings_json: Dict[str, Any]
    is_active: bool
    is_default: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# Storage & Communication Request/Response Schemas
# ---------------------------------------------------------
class FileUploadResponse(BaseModel):
    file_id: uuid.UUID
    file_name: str
    provider_type: str
    storage_path: str
    file_size_bytes: int
    content_type: str
    download_url: str


class CommunicationMessageRequest(BaseModel):
    channel: str = Field(..., description="email, sms, whatsapp, push")
    recipient: str = Field(..., description="Email, Phone Number (+1234567890), or Device Token")
    subject: Optional[str] = None
    content: str
    template_name: Optional[str] = None
    context_json: Optional[Dict[str, Any]] = None


class CommunicationMessageResponse(BaseModel):
    message_id: str
    channel: str
    recipient: str
    status: str = "Sent"
    provider_used: str
    sent_at: datetime.datetime = Field(default_factory=datetime.datetime.now)


# ---------------------------------------------------------
# Bulk Import / Export Schemas
# ---------------------------------------------------------
class BulkImportRequest(BaseModel):
    domain: str = Field(..., description="hr, payroll, inventory, procurement, sales, crm, finance")
    entity_name: str = Field(..., description="Employee, Product, SalesOrder, etc.")
    format: str = Field("csv", description="csv, excel, json, xml")
    file_id: uuid.UUID


class BulkImportResult(BaseModel):
    import_id: uuid.UUID
    domain: str
    entity_name: str
    total_rows: int
    imported_rows: int
    failed_rows: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "Completed"


# ---------------------------------------------------------
# Observability & Metrics Schemas
# ---------------------------------------------------------
class SystemMetricsResponse(BaseModel):
    cpu_usage_pct: float
    memory_usage_mb: float
    active_db_connections: int
    redis_connected: bool
    uptime_seconds: float
    http_requests_total: int
    error_rate_pct: float
    avg_latency_ms: float


class HealthCheckResponse(BaseModel):
    status: str = "Healthy"
    version: str = "v1.3.0"
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    checks: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "database": {"status": "UP", "response_time_ms": 1.2},
            "redis": {"status": "UP", "response_time_ms": 0.8},
            "celery": {"status": "UP", "active_workers": 2},
            "storage": {"status": "UP", "provider": "Local"},
        }
    )


# ---------------------------------------------------------
# Backup & Restore Schemas
# ---------------------------------------------------------
class BackupCreateRequest(BaseModel):
    backup_name: Optional[str] = None
    backup_type: str = Field("FullDatabase", description="FullDatabase, FileStorage, ConfigurationOnly")


class BackupResponse(BaseModel):
    id: uuid.UUID
    backup_name: str
    storage_path: str
    file_size_bytes: int
    backup_type: str
    status: str
    checksum: Optional[str] = None
    completed_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# System Configuration Schemas
# ---------------------------------------------------------
class SystemConfigSetRequest(BaseModel):
    config_key: str
    config_value: str
    value_type: str = "String"
    category: str = "General"
    is_encrypted: bool = False
    is_public: bool = False


class SystemConfigResponse(BaseModel):
    id: uuid.UUID
    config_key: str
    config_value: str
    value_type: str
    category: str
    is_encrypted: bool
    is_public: bool
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
