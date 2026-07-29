import hashlib
import logging
import uuid
from typing import List, Optional, Tuple
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.storage.local_provider import local_storage_provider
from app.exceptions.base import ForbiddenException, NotFoundException, ValidationException
from app.models.file import File
from app.models.user import User
from app.repositories.file import file_repository
from app.schemas.file import FileCreate
from app.services.base_service import BaseService
from app.utils.audit import log_audit
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.sorting import SortCriterion

logger = logging.getLogger("app.services.file")


class FileService(BaseService[file_repository.__class__]):
    """
    Service layer handling enterprise File upload, validation, SHA256 checksum deduplication,
    storage driver interaction, authorization, and audit logging.
    """
    def __init__(self):
        super().__init__(file_repository)
        self.storage = local_storage_provider

    @staticmethod
    def calculate_checksum(data: bytes) -> str:
        """
        Computes SHA256 hex digest for binary data.
        """
        return hashlib.sha256(data).hexdigest()

    def validate_file(self, filename: str, mime_type: str, file_size: int) -> str:
        """
        Validates file size limit, extension, and MIME type.
        """
        # Validate File Size
        if file_size > settings.max_upload_size_bytes:
            raise ValidationException(
                message=f"File size ({file_size / (1024 * 1024):.2f} MB) exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB} MB."
            )

        # Extract Extension
        parts = filename.rsplit(".", 1)
        ext = parts[1].lower() if len(parts) > 1 else ""
        if not ext or ext not in settings.ALLOWED_FILE_EXTENSIONS:
            raise ValidationException(
                message=f"File extension '{ext}' is not permitted. Allowed extensions: {', '.join(settings.ALLOWED_FILE_EXTENSIONS)}."
            )

        # Validate MIME Type
        if mime_type and mime_type.lower() not in settings.ALLOWED_MIME_TYPES:
            logger.warning(f"File upload MIME type warning: '{mime_type}' for filename '{filename}'")

        return ext

    async def upload_file(
        self,
        db: AsyncSession,
        *,
        upload_file: UploadFile,
        uploader: User,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        is_public: bool = False,
    ) -> File:
        """
        Processes multipart file upload, validates payload, checks for duplicate SHA256 checksum,
        persists binary to storage, inserts database record, and logs audit event.
        """
        content = await upload_file.read()
        file_size = len(content)
        original_filename = upload_file.filename or "uploaded_file"
        mime_type = upload_file.content_type or "application/octet-stream"

        ext = self.validate_file(original_filename, mime_type, file_size)

        # SHA256 Checksum calculation & Duplicate detection
        checksum = self.calculate_checksum(content)
        existing_file = await self.repository.get_by_checksum(db, checksum)
        if existing_file:
            logger.info(f"Duplicate file uploaded (SHA256: {checksum}). Returning existing file record '{existing_file.id}'")
            return existing_file

        # Generate unique stored filename
        unique_stored_name = f"{uuid.uuid4().hex}.{ext}"

        # Persist to physical storage
        storage_path = await self.storage.save_file(
            file_data=content,
            stored_filename=unique_stored_name,
        )

        file_in = FileCreate(
            original_filename=original_filename,
            stored_filename=unique_stored_name,
            file_extension=ext,
            mime_type=mime_type,
            file_size=file_size,
            storage_path=storage_path,
            uploaded_by_id=uploader.id,
            entity_type=entity_type,
            entity_id=entity_id,
            checksum=checksum,
            is_public=is_public,
        )

        file_record = await self.repository.create(db, obj_in=file_in)

        # Record audit log
        await log_audit(
            db,
            action="FILE_UPLOAD",
            entity_type="File",
            entity_id=file_record.id,
            user_id=uploader.id,
            username=uploader.username,
            new_data={
                "original_filename": original_filename,
                "file_size": file_size,
                "mime_type": mime_type,
                "checksum": checksum,
            },
            status_code=201,
        )

        return file_record

    async def upload_bytes(
        self,
        db: AsyncSession,
        *,
        content: bytes,
        filename: str,
        mime_type: str = "application/pdf",
        uploader: Optional[User] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        is_public: bool = False,
    ) -> File:
        """
        Saves raw bytes into storage, checks deduplication via SHA256, inserts File record, and logs audit event.
        """
        file_size = len(content)
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
        checksum = self.calculate_checksum(content)

        existing_file = await self.repository.get_by_checksum(db, checksum)
        if existing_file:
            logger.info(f"Duplicate file upload_bytes (SHA256: {checksum}). Returning existing file record '{existing_file.id}'")
            return existing_file

        unique_stored_name = f"{uuid.uuid4().hex}.{ext}"

        storage_path = await self.storage.save_file(
            file_data=content,
            stored_filename=unique_stored_name,
        )

        file_in = FileCreate(
            original_filename=filename,
            stored_filename=unique_stored_name,
            file_extension=ext,
            mime_type=mime_type,
            file_size=file_size,
            storage_path=storage_path,
            uploaded_by_id=uploader.id if uploader else None,
            entity_type=entity_type,
            entity_id=entity_id,
            checksum=checksum,
            is_public=is_public,
        )

        file_record = await self.repository.create(db, obj_in=file_in)

        await log_audit(
            db,
            action="FILE_UPLOAD",
            entity_type="File",
            entity_id=file_record.id,
            user_id=uploader.id if uploader else None,
            username=uploader.username if uploader else "system",
            new_data={
                "original_filename": filename,
                "file_size": file_size,
                "mime_type": mime_type,
                "checksum": checksum,
            },
            status_code=201,
        )

        return file_record

    async def get_file_for_download(
        self, db: AsyncSession, *, file_id: uuid.UUID, current_user: User
    ) -> Tuple[File, bytes]:
        """
        Retrieves file record and raw binary content for streaming download. Logs FILE_DOWNLOAD audit event.
        """
        file_record = await self.get_by_id(db, file_id)
        file_bytes = await self.storage.get_file(file_record.storage_path)

        await log_audit(
            db,
            action="FILE_DOWNLOAD",
            entity_type="File",
            entity_id=file_record.id,
            user_id=current_user.id,
            username=current_user.username,
            status_code=200,
        )

        return file_record, file_bytes

    async def delete_file_with_authorization(
        self, db: AsyncSession, *, file_id: uuid.UUID, current_user: User
    ) -> None:
        """
        Deletes physical file and database record if current_user is uploader or Super Admin.
        """
        file_record = await self.get_by_id(db, file_id)

        # Check authorization (Uploader or Super Admin only)
        if not current_user.is_superuser and str(file_record.uploaded_by_id) != str(current_user.id):
            raise ForbiddenException(
                message="Permission denied: Only the original file uploader or Super Admin can delete this file."
            )

        # Delete physical file from storage driver
        await self.storage.delete_file(file_record.storage_path)

        # Delete record from database
        await self.repository.delete(db, id=file_id)

        # Record audit log
        await log_audit(
            db,
            action="FILE_DELETE",
            entity_type="File",
            entity_id=file_id,
            user_id=current_user.id,
            username=current_user.username,
            previous_data={"original_filename": file_record.original_filename, "checksum": file_record.checksum},
            status_code=200,
        )

    async def get_filtered_files(
        self,
        db: AsyncSession,
        *,
        params: PaginationParams,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        uploaded_by_id: Optional[uuid.UUID] = None,
        search_term: Optional[str] = None,
        sorting: Optional[List[SortCriterion]] = None,
    ) -> PaginatedResult[File]:
        return await self.repository.get_filtered_files(
            db,
            params=params,
            entity_type=entity_type,
            entity_id=entity_id,
            uploaded_by_id=uploaded_by_id,
            search_term=search_term,
            sorting=sorting,
        )


file_service = FileService()
