from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.integrations import BulkImportResult
from app.services.integration_services import ImportExportService

router = APIRouter()


@router.post("/import", response_model=BulkImportResult, status_code=status.HTTP_200_OK)
async def bulk_import(
    domain: str = Form(...),
    entity_name: str = Form(...),
    file_format: str = Form("csv"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    service = ImportExportService(db)
    result = await service.process_bulk_import(
        domain=domain,
        entity_name=entity_name,
        file_format=file_format,
        content=content,
    )
    return result
