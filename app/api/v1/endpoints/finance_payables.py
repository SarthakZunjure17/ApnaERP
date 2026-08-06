import datetime
from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.finance_ops import (
    SupplierBillCreate,
    SupplierBillResponse,
    VendorStatementResponse,
)
from app.services.finance_ops_services import AccountsPayableService

router = APIRouter()


@router.post("/bills", response_model=SupplierBillResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier_bill(
    data: SupplierBillCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AccountsPayableService(db)
    return await service.create_bill(data, current_user)


@router.post("/bills/{bill_id}/post", response_model=SupplierBillResponse)
async def post_supplier_bill(
    bill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AccountsPayableService(db)
    return await service.post_bill(bill_id, current_user)


@router.get("/suppliers/{supplier_id}/statement", response_model=VendorStatementResponse)
async def get_vendor_statement(
    supplier_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AccountsPayableService(db)
    return await service.get_vendor_statement(supplier_id)
