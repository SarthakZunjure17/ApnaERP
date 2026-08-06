from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.crm_services import CRMImportExportService

router = APIRouter()
import_export_service = CRMImportExportService()


@router.get("/leads/export")
async def export_leads(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export Leads as CSV."""
    csv_data = await import_export_service.export_leads_csv(db)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=crm_leads.csv"},
    )


@router.post("/leads/import", status_code=status.HTTP_201_CREATED)
async def import_leads(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk import Leads from CSV."""
    content = (await file.read()).decode("utf-8")
    count = await import_export_service.import_leads_csv(db, content, current_user_id=current_user.id)
    return {"imported_count": count}
