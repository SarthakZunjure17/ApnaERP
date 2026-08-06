import datetime
from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.finance_ops import (
    CustomerInvoiceCreate,
    CustomerInvoiceResponse,
    CustomerStatementResponse,
)
from app.services.finance_ops_services import AccountsReceivableService

router = APIRouter()


@router.post("/invoices", response_model=CustomerInvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_customer_invoice(
    data: CustomerInvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AccountsReceivableService(db)
    return await service.create_invoice(data, current_user)


@router.post("/invoices/{invoice_id}/post", response_model=CustomerInvoiceResponse)
async def post_customer_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AccountsReceivableService(db)
    return await service.post_invoice(invoice_id, current_user)


@router.get("/customers/{customer_id}/statement", response_model=CustomerStatementResponse)
async def get_customer_statement(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AccountsReceivableService(db)
    return await service.get_customer_statement(customer_id)
