from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.schemas.inventory_advanced import InventoryDashboardSummary
from app.services.inventory_report_services import inventory_analytics_service

router = APIRouter()


@router.get(
    "/dashboard",
    response_model=InventoryDashboardSummary,
    dependencies=[Depends(has_permission("inventory.analytics.read"))],
)
async def get_inventory_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Redis-cached Inventory Executive Dashboard KPIs."""
    return await inventory_analytics_service.get_dashboard_summary(db)
