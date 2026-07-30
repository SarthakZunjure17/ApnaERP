from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.models.user import User
from app.schemas.stock_engine import InventoryTransactionTypeResponse
from app.services.stock_engine_services import inventory_transaction_type_service

router = APIRouter()


@router.get("", response_model=List[InventoryTransactionTypeResponse], status_code=status.HTTP_200_OK)
async def get_transaction_types(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.transaction.read")),
):
    """Retrieve list of all active inventory transaction types."""
    return await inventory_transaction_type_service.get_all_active_types(db)
