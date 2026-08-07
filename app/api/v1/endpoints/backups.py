import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.integrations import BackupCreateRequest, BackupResponse
from app.services.integration_services import BackupService

router = APIRouter()


@router.post("", response_model=BackupResponse, status_code=status.HTTP_201_CREATED)
async def create_backup(
    req: BackupCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = BackupService(db)
    backup = await service.create_backup(backup_name=req.backup_name, backup_type=req.backup_type)
    return backup


@router.post("/{backup_id}/restore", status_code=status.HTTP_200_OK)
async def restore_backup(
    backup_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = BackupService(db)
    success = await service.restore_backup(backup_id)
    if not success:
        raise HTTPException(status_code=404, detail="Backup record not found")
    return {"status": "Restored", "backup_id": backup_id}
