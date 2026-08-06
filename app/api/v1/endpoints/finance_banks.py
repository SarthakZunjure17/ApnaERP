from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.finance_ops import (
    BankAccountCreate,
    BankAccountResponse,
    BankTransactionCreate,
    BankTransactionResponse,
)
from app.services.finance_ops_services import BankService

router = APIRouter()


@router.post("/accounts", response_model=BankAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_bank_account(
    data: BankAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = BankService(db)
    return await service.create_bank_account(data)


@router.post("/transactions", response_model=BankTransactionResponse, status_code=status.HTTP_201_CREATED)
async def record_bank_transaction(
    data: BankTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = BankService(db)
    return await service.record_transaction(data)
