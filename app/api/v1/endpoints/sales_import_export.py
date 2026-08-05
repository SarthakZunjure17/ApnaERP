from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.services.sales_import_export_services import sales_import_export_service

router = APIRouter()


@router.get("/export/customers", response_class=Response)
async def export_customers_csv(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.customer.read")),
):
    csv_data = await sales_import_export_service.export_customers_csv(db)
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=customers_export.csv"})


@router.get("/export/quotations", response_class=Response)
async def export_quotations_csv(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.quotation.read")),
):
    csv_data = await sales_import_export_service.export_quotations_csv(db)
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=quotations_export.csv"})


@router.get("/export/orders", response_class=Response)
async def export_orders_csv(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.order.read")),
):
    csv_data = await sales_import_export_service.export_orders_csv(db)
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=orders_export.csv"})


@router.post("/import/customers", status_code=status.HTTP_201_CREATED)
async def import_customers_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.customer.create")),
):
    content = await file.read()
    created_codes = await sales_import_export_service.import_customers_csv(db, content.decode("utf-8"))
    return {"message": f"Successfully imported {len(created_codes)} customers.", "imported_codes": created_codes}
