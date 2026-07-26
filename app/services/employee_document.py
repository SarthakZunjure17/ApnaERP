import datetime
import json
import logging
from typing import Any, Dict, List, Optional
import uuid
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import ApnaERPException
from app.models.employee_document import EmployeeDocument
from app.models.user import User
from app.repositories.employee import employee_repository
from app.repositories.employee_document import employee_document_repository
from app.repositories.file import file_repository
from app.schemas.employee_document import (
    DocumentRejectRequest,
    DocumentVerifyRequest,
    EmployeeDocumentCreate,
    EmployeeDocumentResponse,
    EmployeeDocumentUpdate,
)
from app.tasks.document_tasks import send_document_notification_task
from app.utils.audit import log_audit
from app.utils.pagination import PaginationParams

logger = logging.getLogger("app.services.employee_document")

CACHE_DOC_PREFIX = "employee_document:list:"


class EmployeeDocumentService:
    """
    Business service layer managing Employee Documents, file linking, verification/rejection workflows,
    expiry constraints, Redis caching, audit logging, and background Celery task notifications.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = employee_document_repository
        self.emp_repo = employee_repository
        self.file_repo = file_repository

    async def _invalidate_document_cache(self, employee_id: uuid.UUID) -> None:
        """Invalidates employee document list cache from Redis."""
        cache_key = f"{CACHE_DOC_PREFIX}{employee_id}"
        try:
            await redis_manager.delete(cache_key)
            logger.info(f"[EmployeeDocumentService] Invalidated Redis cache for employee '{employee_id}'.")
        except Exception as e:
            logger.warning(f"[EmployeeDocumentService] Redis cache invalidation error: {e}")

    async def _validate_dates(self, issue_date: Optional[datetime.date], expiry_date: Optional[datetime.date]) -> None:
        """Validates that expiry_date is not earlier than issue_date."""
        if issue_date and expiry_date and expiry_date < issue_date:
            raise ApnaERPException(
                message="Expiry date cannot be earlier than issue date.",
                status_code=400,
                error_code="INVALID_EXPIRY_DATE"
            )

    async def create_document(
        self, data: EmployeeDocumentCreate, current_user: Optional[User] = None, request: Optional[Request] = None
    ) -> EmployeeDocument:
        """
        Links an existing File to an active Employee record after executing business validations.
        """
        # Validate Employee existence & active status
        emp = await self.emp_repo.get_by_id(self.db, data.employee_id)
        if not emp or emp.is_deleted:
            raise ApnaERPException(
                message=f"Employee with ID '{data.employee_id}' not found.",
                status_code=404,
                error_code="EMPLOYEE_NOT_FOUND"
            )

        # Validate File existence & active status
        storage_file = await self.file_repo.get_by_id(self.db, data.file_id)
        if not storage_file or getattr(storage_file, "is_deleted", False):
            raise ApnaERPException(
                message=f"File with ID '{data.file_id}' not found.",
                status_code=404,
                error_code="FILE_NOT_FOUND"
            )

        # Validate dates
        await self._validate_dates(data.issue_date, data.expiry_date)

        # Validate duplicate active mandatory document of same type
        if data.is_mandatory:
            if await self.repo.exists_mandatory_document_type(self.db, data.employee_id, data.document_type.value):
                raise ApnaERPException(
                    message=f"Active mandatory document of type '{data.document_type.value}' already exists for this employee.",
                    status_code=400,
                    error_code="DUPLICATE_MANDATORY_DOCUMENT"
                )

        doc = await self.repo.create(self.db, obj_in=data)

        # Audit Log
        await log_audit(
            db=self.db,
            action="DOCUMENT_UPLOAD",
            entity_type="EmployeeDocument",
            entity_id=str(doc.id),
            user_id=current_user.id if current_user else None,
            username=current_user.username if current_user else None,
            new_data={
                "employee_id": str(doc.employee_id),
                "file_id": str(doc.file_id),
                "document_type": doc.document_type,
                "verification_status": doc.verification_status,
            },
            status_code=201,
        )

        # Invalidate Cache
        await self._invalidate_document_cache(doc.employee_id)

        # Dispatch Celery background task notification
        try:
            send_document_notification_task.delay(
                event="DOCUMENT_UPLOADED",
                document_id=str(doc.id),
                employee_id=str(doc.employee_id),
                document_type=doc.document_type,
                status=doc.verification_status,
            )
        except Exception as e:
            logger.warning(f"[EmployeeDocumentService] Celery task enqueue failed: {e}")

        return doc

    async def get_document_by_id(self, document_id: uuid.UUID) -> EmployeeDocument:
        """Retrieves active document by ID."""
        doc = await self.repo.get_by_id(self.db, document_id)
        if not doc or doc.is_deleted:
            raise ApnaERPException(
                message=f"Employee document with ID '{document_id}' not found.",
                status_code=404,
                error_code="DOCUMENT_NOT_FOUND"
            )
        return doc

    async def get_documents_by_employee(self, employee_id: uuid.UUID) -> List[EmployeeDocument]:
        """Retrieves documents for an employee, cached via Redis."""
        cache_key = f"{CACHE_DOC_PREFIX}{employee_id}"
        try:
            cached_raw = await redis_manager.get(cache_key)
            if cached_raw:
                logger.info(f"[EmployeeDocumentService] Returning documents for employee '{employee_id}' from Redis.")
                items = json.loads(cached_raw)
                return [EmployeeDocumentResponse.model_validate(item) for item in items]
        except Exception as e:
            logger.warning(f"[EmployeeDocumentService] Redis cache read error: {e}")

        docs = await self.repo.get_by_employee(self.db, employee_id)
        resp_list = [EmployeeDocumentResponse.model_validate(d) for d in docs]

        try:
            json_str = json.dumps([item.model_dump(mode="json") for item in resp_list])
            await redis_manager.set(cache_key, json_str, ex=3600)
            logger.info(f"[EmployeeDocumentService] Cached documents for employee '{employee_id}' in Redis.")
        except Exception as e:
            logger.warning(f"[EmployeeDocumentService] Redis cache set error: {e}")

        return docs

    async def get_documents_list(
        self, page: int = 1, page_size: int = 10, search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Paginated list of employee documents."""
        params = PaginationParams(page=page, page_size=page_size)
        paginated_res = await self.repo.get_multi_paginated(
            self.db,
            params=params,
            search_term=search,
            search_fields=["document_type", "document_number", "verification_status"],
        )
        return {
            "total": paginated_res.total,
            "page": paginated_res.page,
            "page_size": paginated_res.page_size,
            "items": paginated_res.items,
        }

    async def update_document(
        self,
        document_id: uuid.UUID,
        data: EmployeeDocumentUpdate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None
    ) -> EmployeeDocument:
        """Updates document details."""
        doc = await self.get_document_by_id(document_id)
        prev_data = {
            "document_number": doc.document_number,
            "issue_date": str(doc.issue_date) if doc.issue_date else None,
            "expiry_date": str(doc.expiry_date) if doc.expiry_date else None,
        }

        update_dict = data.model_dump(exclude_unset=True)

        issue_date = update_dict.get("issue_date", doc.issue_date)
        expiry_date = update_dict.get("expiry_date", doc.expiry_date)
        await self._validate_dates(issue_date, expiry_date)

        updated_doc = await self.repo.update(self.db, db_obj=doc, obj_in=data)

        # Audit Log
        await log_audit(
            db=self.db,
            action="DOCUMENT_UPDATE",
            entity_type="EmployeeDocument",
            entity_id=str(document_id),
            user_id=current_user.id if current_user else None,
            username=current_user.username if current_user else None,
            previous_data=prev_data,
            new_data={
                "document_number": updated_doc.document_number,
                "expiry_date": str(updated_doc.expiry_date) if updated_doc.expiry_date else None,
            },
            status_code=200,
        )

        # Invalidate Cache
        await self._invalidate_document_cache(updated_doc.employee_id)

        return updated_doc

    async def verify_document(
        self,
        document_id: uuid.UUID,
        payload: DocumentVerifyRequest,
        current_user: User,
        request: Optional[Request] = None
    ) -> EmployeeDocument:
        """Verifies an employee document."""
        doc = await self.get_document_by_id(document_id)

        doc.verification_status = "Verified"
        doc.verified_by = current_user.id
        doc.verified_at = datetime.datetime.now(datetime.timezone.utc)
        if payload.notes:
            doc.notes = f"{doc.notes or ''}\n[Verified Note]: {payload.notes}".strip()

        await self.db.commit()
        await self.db.refresh(doc)

        # Audit Log
        await log_audit(
            db=self.db,
            action="DOCUMENT_VERIFY",
            entity_type="EmployeeDocument",
            entity_id=str(document_id),
            user_id=current_user.id,
            username=current_user.username,
            previous_data={"status": "Pending"},
            new_data={"status": "Verified", "verified_by": str(current_user.id)},
            status_code=200,
        )

        # Invalidate Cache
        await self._invalidate_document_cache(doc.employee_id)

        # Dispatch Celery background notification
        try:
            send_document_notification_task.delay(
                event="DOCUMENT_VERIFIED",
                document_id=str(doc.id),
                employee_id=str(doc.employee_id),
                document_type=doc.document_type,
                status="Verified",
            )
        except Exception as e:
            logger.warning(f"[EmployeeDocumentService] Celery task enqueue failed: {e}")

        return doc

    async def reject_document(
        self,
        document_id: uuid.UUID,
        payload: DocumentRejectRequest,
        current_user: User,
        request: Optional[Request] = None
    ) -> EmployeeDocument:
        """Rejects an employee document with notes."""
        doc = await self.get_document_by_id(document_id)

        doc.verification_status = "Rejected"
        doc.verified_by = current_user.id
        doc.verified_at = datetime.datetime.now(datetime.timezone.utc)
        if payload.notes:
            doc.notes = f"{doc.notes or ''}\n[Rejection Note]: {payload.notes}".strip()

        await self.db.commit()
        await self.db.refresh(doc)

        # Audit Log
        await log_audit(
            db=self.db,
            action="DOCUMENT_REJECT",
            entity_type="EmployeeDocument",
            entity_id=str(document_id),
            user_id=current_user.id,
            username=current_user.username,
            previous_data={"status": doc.verification_status},
            new_data={"status": "Rejected", "verified_by": str(current_user.id), "notes": doc.notes},
            status_code=200,
        )

        # Invalidate Cache
        await self._invalidate_document_cache(doc.employee_id)

        # Dispatch Celery background notification
        try:
            send_document_notification_task.delay(
                event="DOCUMENT_REJECTED",
                document_id=str(doc.id),
                employee_id=str(doc.employee_id),
                document_type=doc.document_type,
                status="Rejected",
            )
        except Exception as e:
            logger.warning(f"[EmployeeDocumentService] Celery task enqueue failed: {e}")

        return doc

    async def delete_document(
        self, document_id: uuid.UUID, current_user: Optional[User] = None, request: Optional[Request] = None
    ) -> EmployeeDocument:
        """Soft deletes an employee document."""
        doc = await self.get_document_by_id(document_id)

        await self.repo.soft_delete(self.db, id=document_id)
        deleted_doc = await self.repo.get_by_id(self.db, document_id, include_deleted=True)

        # Audit Log
        await log_audit(
            db=self.db,
            action="DOCUMENT_DELETE",
            entity_type="EmployeeDocument",
            entity_id=str(document_id),
            user_id=current_user.id if current_user else None,
            username=current_user.username if current_user else None,
            previous_data={"document_type": doc.document_type, "employee_id": str(doc.employee_id)},
            new_data={"is_deleted": True},
            status_code=200,
        )

        # Invalidate Cache
        await self._invalidate_document_cache(doc.employee_id)

        return deleted_doc

    async def restore_document(
        self, document_id: uuid.UUID, current_user: Optional[User] = None, request: Optional[Request] = None
    ) -> EmployeeDocument:
        """Restores a soft-deleted document."""
        doc = await self.repo.get_by_id(self.db, document_id, include_deleted=True)
        if not doc:
            raise ApnaERPException(
                message=f"Employee document with ID '{document_id}' not found.",
                status_code=404,
                error_code="DOCUMENT_NOT_FOUND"
            )

        if not doc.is_deleted:
            raise ApnaERPException(
                message="Employee document is not deleted.",
                status_code=400,
                error_code="NOT_DELETED_ERROR"
            )

        await self.repo.restore(self.db, id=document_id)
        restored_doc = await self.repo.get_by_id(self.db, document_id)

        # Audit Log
        await log_audit(
            db=self.db,
            action="DOCUMENT_RESTORE",
            entity_type="EmployeeDocument",
            entity_id=str(document_id),
            user_id=current_user.id if current_user else None,
            username=current_user.username if current_user else None,
            previous_data={"is_deleted": True},
            new_data={"is_deleted": False},
            status_code=200,
        )

        # Invalidate Cache
        await self._invalidate_document_cache(restored_doc.employee_id)

        return restored_doc
