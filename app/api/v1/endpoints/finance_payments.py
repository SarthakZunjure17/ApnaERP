from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.finance_ops import (
    PaymentVoucherCreate,
    PaymentVoucherResponse,
    ReceiptVoucherCreate,
    ReceiptVoucherResponse,
)
from app.services.finance_ops_services import PaymentService

router = APIRouter()


@router.post("/receipts", response_model=ReceiptVoucherResponse, status_code=status.HTTP_201_CREATED)
async def create_receipt_voucher(
    data: ReceiptVoucherCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PaymentService(db)
    return await service.create_receipt_voucher(data, current_user)


@router.post("/receipts/{voucher_id}/post", response_model=ReceiptVoucherResponse)
async def post_receipt_voucher(
    voucher_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PaymentService(db)
    return await service.post_receipt_voucher(voucher_id, current_user)


@router.post("/payments", response_model=PaymentVoucherResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_voucher(
    data: PaymentVoucherCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PaymentService(db)
    return await service.create_payment_voucher(data, current_user)


@router.post("/payments/{voucher_id}/post", response_model=PaymentVoucherResponse)
async def post_payment_voucher(
    voucher_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PaymentService(db)
    return await service.post_payment_voucher(voucher_id, current_user)
