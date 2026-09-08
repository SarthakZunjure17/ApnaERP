from typing import Any, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permission
from app.models.user import User
from app.schemas.finance import CompanyCreate, CompanyResponse, CompanyUpdate
from app.services.finance_services import CompanyService

router = APIRouter()
company_service = CompanyService()


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    obj_in: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.company.create")),
) -> Any:
    try:
        return await company_service.create_company(db, obj_in, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[CompanyResponse])
async def list_companies(
    query: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.company.read")),
) -> Any:
    companies, _ = await company_service.list_companies(
        db, query=query, is_active=is_active, skip=skip, limit=limit
    )
    return companies


@router.get("/default", response_model=Optional[CompanyResponse])
async def get_default_company(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.company.read")),
) -> Any:
    company = await company_service.get_default_company(db)
    if not company:
        raise HTTPException(status_code=404, detail="Default company not found")
    return company


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.company.read")),
) -> Any:
    company = await company_service.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: uuid.UUID,
    obj_in: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.company.update")),
) -> Any:
    try:
        return await company_service.update_company(db, company_id, obj_in, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.company.delete")),
) -> None:
    try:
        await company_service.delete_company(db, company_id, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
