from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """
    Schema for system health check endpoint response.
    """
    status: str = Field(default="healthy", description="System health status")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Running environment")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC Timestamp of health check")
    components: Optional[Dict[str, str]] = Field(default=None, description="Detailed component statuses")


class RootResponse(BaseModel):
    """
    Schema for root endpoint response.
    """
    message: str = Field(..., description="Welcome message")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    docs_url: str = Field(..., description="API Documentation URL")
