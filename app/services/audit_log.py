import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.request_context import (
    api_endpoint_var,
    client_ip_var,
    http_method_var,
    request_id_var,
    user_agent_var,
)
from app.models.audit_log import AuditLog
from app.repositories.audit_log import audit_log_repository
from app.schemas.audit_log import AuditLogCreate
from app.services.base_service import BaseService
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.sorting import SortCriterion

logger = logging.getLogger("app.services.audit_log")


class AuditLogService(BaseService[audit_log_repository.__class__]):
    """
    Service layer for Audit Logging system.
    Provides non-blocking event recording and administrative search endpoints.
    """
    def __init__(self):
        super().__init__(audit_log_repository)

    async def log_event(
        self,
        db: AsyncSession,
        *,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        username: Optional[str] = None,
        previous_data: Optional[Dict[str, Any]] = None,
        new_data: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = 200,
        http_method: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Creates an audit log entry automatically filling missing request context from contextvars.
        """
        log_in = AuditLogCreate(
            user_id=user_id,
            username=username,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            previous_data=previous_data,
            new_data=new_data,
            http_method=http_method or http_method_var.get(),
            api_endpoint=api_endpoint or api_endpoint_var.get(),
            request_id=request_id or request_id_var.get(),
            ip_address=ip_address or client_ip_var.get(),
            user_agent=user_agent or user_agent_var.get(),
            status_code=status_code,
        )
        logger.info(f"[AUDIT] Action: '{action}' | Entity: '{entity_type}' (ID: {entity_id}) | User: '{username}'")
        return await self.repository.create(db, obj_in=log_in)

    async def get_filtered_logs(
        self,
        db: AsyncSession,
        *,
        params: PaginationParams,
        user_id: Optional[uuid.UUID] = None,
        username: Optional[str] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        status_code: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sorting: Optional[List[SortCriterion]] = None,
    ) -> PaginatedResult[AuditLog]:
        return await self.repository.get_filtered_logs(
            db,
            params=params,
            user_id=user_id,
            username=username,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            status_code=status_code,
            start_date=start_date,
            end_date=end_date,
            sorting=sorting,
        )

    async def get_entity_history(
        self,
        db: AsyncSession,
        *,
        entity_type: str,
        entity_id: str,
        params: PaginationParams,
    ) -> PaginatedResult[AuditLog]:
        return await self.repository.get_by_entity(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            params=params,
        )


audit_log_service = AuditLogService()
