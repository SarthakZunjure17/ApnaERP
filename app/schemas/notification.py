import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema


class NotificationCreate(BaseModel):
    """
    Schema for creating a Notification record in database.
    """
    user_id: uuid.UUID
    title: str
    message: str
    notification_type: str = "IN_APP"
    priority: str = "MEDIUM"
    is_read: bool = False
    read_at: Optional[datetime] = None


class NotificationResponse(UUIDSchema, TimestampSchema):
    """
    Output schema for Notification details.
    """
    user_id: uuid.UUID
    title: str
    message: str
    notification_type: str
    priority: str
    is_read: bool
    read_at: Optional[datetime] = None


class NotificationSendRequest(BaseModel):
    """
    Schema for requesting to send a notification (via direct message or template).
    """
    user_id: uuid.UUID
    title: Optional[str] = None
    message: Optional[str] = None
    template_name: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    notification_type: str = "IN_APP"
    priority: str = "MEDIUM"


class NotificationTemplateCreate(BaseModel):
    """
    Schema for creating a Notification Template.
    """
    name: str = Field(..., max_length=100, description="Unique template identifier name")
    subject: Optional[str] = Field(default=None, max_length=255, description="Email subject template")
    template_body: str = Field(..., description="Jinja2 template body text or HTML")
    template_type: str = Field(default="EMAIL", description="Target type (EMAIL, IN_APP)")


class NotificationTemplateUpdate(BaseModel):
    """
    Schema for updating a Notification Template.
    """
    name: Optional[str] = Field(default=None, max_length=100)
    subject: Optional[str] = Field(default=None, max_length=255)
    template_body: Optional[str] = None
    template_type: Optional[str] = None


class NotificationTemplateResponse(UUIDSchema, TimestampSchema):
    """
    Output schema for Notification Template details.
    """
    name: str
    subject: Optional[str] = None
    template_body: str
    template_type: str
