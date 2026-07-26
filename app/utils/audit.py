import logging
import uuid
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.audit_log import audit_log_service

logger = logging.getLogger("app.utils.audit")


async def log_audit(
    db: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: Optional[Any] = None,
    user_id: Optional[uuid.UUID] = None,
    username: Optional[str] = None,
    previous_data: Optional[Dict[str, Any]] = None,
    new_data: Optional[Dict[str, Any]] = None,
    status_code: Optional[int] = 200,
) -> None:
    """
    Reusable one-function call helper for audit logging across all ERP modules.
    Automatically captures request context (Request ID, IP, User-Agent, HTTP Method, API Endpoint) from contextvars.
    """
    try:
        await audit_log_service.log_event(
            db,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            user_id=user_id,
            username=username,
            previous_data=previous_data,
            new_data=new_data,
            status_code=status_code,
        )
    except Exception as exc:
        logger.error(f"Failed to record audit log entry for action '{action}': {exc}", exc_info=True)
