import math
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.sales import (
    CustomerAddressCreate,
    CustomerAddressResponse,
    CustomerCategoryCreate,
    CustomerCategoryResponse,
    CustomerContactCreate,
    CustomerContactResponse,
    CustomerCreate,
    CustomerDocumentCreate,
    CustomerDocumentResponse,
    CustomerResponse,
    CustomerUpdate,
)
from app.services.customer_services import customer_service

router = APIRouter()


@router.post("/categories", response_model=CustomerCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_customer_category(
    obj_in: CustomerCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.customer.create")),
):
    return await customer_service.create_category(db, obj_in, current_user_id=current_user.id)


@router.get("/categories", response_model=List[CustomerCategoryResponse])
async def list_customer_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.customer.read")),
):
    return await customer_service.list_categories(db)


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    obj_in: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.customer.create")),
):
    return await customer_service.create_customer(db, obj_in, current_user_id=current_user.id)


@router.get("", response_model=dict)
async def list_customers(
    query: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    category_id: Optional[uuid.UUID] = Query(None),
    is_preferred: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.customer.read")),
):
    skip = (page - 1) * page_size
    items, total = await customer_service.list_customers(
        db, query=query, status=status_filter, category_id=category_id, is_preferred=is_preferred, skip=skip, limit=page_size
    )
    pages = math.ceil(total / page_size) if total > 0 else 1
    return {
        "items": [CustomerResponse.model_validate(c) for c in items],
        "total": total,
        "page": page,
        "size": page_size,
        "pages": pages,
    }


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.customer.read")),
):
    return await customer_service.get_customer(db, customer_id)


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: uuid.UUID,
    obj_in: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.customer.update")),
):
    return await customer_service.update_customer(db, customer_id, obj_in, current_user_id=current_user.id)


@router.delete("/{customer_id}", response_model=CustomerResponse)
async def delete_customer(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.customer.delete")),
):
    return await customer_service.delete_customer(db, customer_id, current_user_id=current_user.id)


@router.post("/{customer_id}/contacts", response_model=CustomerContactResponse, status_code=status.HTTP_201_CREATED)
async def add_customer_contact(
    customer_id: uuid.UUID,
    obj_in: CustomerContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.customer.update")),
):
    return await customer_service.add_contact(db, customer_id, obj_in)


@router.get("/{customer_id}/contacts", response_model=List[CustomerContactResponse])
async def list_customer_contacts(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.customer.read")),
):
    return await customer_service.list_contacts(db, customer_id)


@router.post("/{customer_id}/addresses", response_model=CustomerAddressResponse, status_code=status.HTTP_201_CREATED)
async def add_customer_address(
    customer_id: uuid.UUID,
    obj_in: CustomerAddressCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.customer.update")),
):
    return await customer_service.add_address(db, customer_id, obj_in)


@router.get("/{customer_id}/addresses", response_model=List[CustomerAddressResponse])
async def list_customer_addresses(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.customer.read")),
):
    return await customer_service.list_addresses(db, customer_id)


@router.post("/{customer_id}/documents", response_model=CustomerDocumentResponse, status_code=status.HTTP_201_CREATED)
async def attach_customer_document(
    customer_id: uuid.UUID,
    obj_in: CustomerDocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.customer.update")),
):
    return await customer_service.attach_document(db, customer_id, obj_in)


@router.get("/{customer_id}/documents", response_model=List[CustomerDocumentResponse])
async def list_customer_documents(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.customer.read")),
):
    return await customer_service.list_documents(db, customer_id)
