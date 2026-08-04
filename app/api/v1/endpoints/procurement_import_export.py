from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.procurement import ProcurementImportResult
from app.services.procurement_import_export_services import procurement_import_export_service

router = APIRouter()


@router.get("/export", response_class=Response)
async def export_to_csv(
    entity_type: str = Query(..., description="suppliers, purchase_orders"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.import_export.execute")),
):
    csv_str = await procurement_import_export_service.export_to_csv(db, entity_type=entity_type)
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={entity_type}_export.csv"},
    )


@router.post("/import", response_model=ProcurementImportResult, status_code=status.HTTP_200_OK)
async def import_from_csv(
    entity_type: str = Query(..., description="suppliers"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.import_export.execute")),
):
    content = (await file.read()).decode("utf-8")
    return await procurement_import_export_service.import_from_csv(db, entity_type=entity_type, csv_content=content)
