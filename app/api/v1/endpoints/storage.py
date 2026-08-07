import uuid
from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.integrations import FileUploadResponse
from app.services.integration_services import StorageService

router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    service = StorageService(db, provider_type="Local")
    file_record = await service.store_file(
        file_name=file.filename or "upload.dat",
        content=content,
        content_type=file.content_type or "application/octet-stream",
        uploaded_by=current_user.id,
    )
    url = await service.provider.get_public_url(file_record.file_path)
    return FileUploadResponse(
        file_id=file_record.id,
        file_name=file_record.filename,
        provider_type="Local",
        storage_path=file_record.file_path,
        file_size_bytes=file_record.file_size,
        content_type=file_record.mime_type,
        download_url=url,
    )


@router.get("/download/{file_id}")
async def download_file(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = StorageService(db, provider_type="Local")
    file_record, content = await service.retrieve_file(file_id)
    return Response(
        content=content,
        media_type=file_record.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{file_record.filename}"'},
    )
