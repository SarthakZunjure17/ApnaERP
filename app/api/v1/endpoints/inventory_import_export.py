from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.schemas.inventory_advanced import ImportResult
from app.services.inventory_import_export_services import inventory_import_export_service

router = APIRouter()


@router.get(
    "/export/{entity_type}",
    dependencies=[Depends(has_permission("inventory.import_export.execute"))],
)
async def export_inventory_data(
    entity_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export inventory data to CSV (products, stock_balances, batches, serials)."""
    csv_data = await inventory_import_export_service.export_to_csv(db, entity_type=entity_type)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={entity_type}_export.csv"},
    )


@router.post(
    "/import/{entity_type}",
    response_model=ImportResult,
    dependencies=[Depends(has_permission("inventory.import_export.execute"))],
)
async def import_inventory_data(
    entity_type: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import inventory data from CSV file."""
    content = await file.read()
    csv_text = content.decode("utf-8")
    return await inventory_import_export_service.import_from_csv(db, entity_type=entity_type, csv_content=csv_text)
