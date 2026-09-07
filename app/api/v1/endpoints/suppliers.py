import math
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.procurement import (
    PaginatedSupplierResponse,
    SupplierAddressCreate,
    SupplierAddressUpdate,
    SupplierAddressResponse,
    SupplierCategoryCreate,
    SupplierCategoryUpdate,
    SupplierCategoryResponse,
    SupplierContactCreate,
    SupplierContactUpdate,
    SupplierContactResponse,
    SupplierCreate,
    SupplierDocumentCreate,
    SupplierDocumentUpdate,
    SupplierDocumentResponse,
    SupplierRatingCreate,
    SupplierRatingResponse,
    SupplierResponse,
    SupplierUpdate,
)
from app.services.supplier_services import supplier_service

router = APIRouter()


# =============================================================================
# Supplier Categories
# =============================================================================

@router.post("/categories", response_model=SupplierCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier_category(
    obj_in: SupplierCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.create")),
):
    return await supplier_service.create_category(db, obj_in, current_user_id=current_user.id)


@router.get("/categories", response_model=List[SupplierCategoryResponse])
async def list_supplier_categories(
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.read")),
):
    items, _ = await supplier_service.list_categories(db, search=search, skip=skip, limit=limit)
    return items


@router.get("/categories/{category_id}", response_model=SupplierCategoryResponse)
async def get_supplier_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.read")),
):
    return await supplier_service.get_category(db, category_id)


@router.patch("/categories/{category_id}", response_model=SupplierCategoryResponse)
@router.put("/categories/{category_id}", response_model=SupplierCategoryResponse)
async def update_supplier_category(
    category_id: uuid.UUID,
    obj_in: SupplierCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.update")),
):
    return await supplier_service.update_category(db, category_id, obj_in, current_user_id=current_user.id)


@router.delete("/categories/{category_id}")
async def delete_supplier_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.delete")),
):
    await supplier_service.delete_category(db, category_id, current_user_id=current_user.id)
    return {"success": True, "message": "Supplier category deleted successfully"}


# =============================================================================
# Supplier Master
# =============================================================================

@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    obj_in: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.create")),
):
    return await supplier_service.create_supplier(db, obj_in, current_user_id=current_user.id)


@router.get("", response_model=PaginatedSupplierResponse)
async def list_suppliers(
    category_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    is_preferred: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.read")),
):
    skip = (page - 1) * size
    items, total = await supplier_service.list_suppliers(
        db,
        category_id=category_id,
        status=status,
        is_preferred=is_preferred,
        search=search,
        skip=skip,
        limit=size,
    )
    pages = math.ceil(total / size) if total > 0 else 0
    return PaginatedSupplierResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.read")),
):
    return await supplier_service.get_supplier(db, supplier_id)


@router.patch("/{supplier_id}", response_model=SupplierResponse)
@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: uuid.UUID,
    obj_in: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.update")),
):
    return await supplier_service.update_supplier(db, supplier_id, obj_in, current_user_id=current_user.id)


@router.delete("/{supplier_id}")
async def delete_supplier(
    supplier_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.delete")),
):
    await supplier_service.delete_supplier(db, supplier_id, current_user_id=current_user.id)
    return {"success": True, "message": "Supplier deleted successfully"}


# =============================================================================
# Status Lifecycle Operations
# =============================================================================

@router.post("/{supplier_id}/activate", response_model=SupplierResponse)
async def activate_supplier(
    supplier_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.update")),
):
    return await supplier_service.activate_supplier(db, supplier_id, current_user_id=current_user.id)


@router.post("/{supplier_id}/deactivate", response_model=SupplierResponse)
async def deactivate_supplier(
    supplier_id: uuid.UUID,
    reason: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.update")),
):
    return await supplier_service.deactivate_supplier(db, supplier_id, reason=reason, current_user_id=current_user.id)


@router.post("/{supplier_id}/blacklist", response_model=SupplierResponse)
async def blacklist_supplier(
    supplier_id: uuid.UUID,
    reason: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.blacklist")),
):
    return await supplier_service.blacklist_supplier(db, supplier_id, reason, current_user_id=current_user.id)


# =============================================================================
# Supplier Contacts
# =============================================================================

@router.get("/{supplier_id}/contacts", response_model=List[SupplierContactResponse])
async def list_supplier_contacts(
    supplier_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.read")),
):
    return await supplier_service.list_contacts(db, supplier_id)


@router.post("/{supplier_id}/contacts", response_model=SupplierContactResponse, status_code=status.HTTP_201_CREATED)
async def add_supplier_contact(
    supplier_id: uuid.UUID,
    obj_in: SupplierContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.update")),
):
    return await supplier_service.add_contact(db, supplier_id, obj_in, current_user_id=current_user.id)


@router.get("/{supplier_id}/contacts/{contact_id}", response_model=SupplierContactResponse)
async def get_supplier_contact(
    supplier_id: uuid.UUID,
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.read")),
):
    return await supplier_service.get_contact(db, supplier_id, contact_id)


@router.patch("/{supplier_id}/contacts/{contact_id}", response_model=SupplierContactResponse)
@router.put("/{supplier_id}/contacts/{contact_id}", response_model=SupplierContactResponse)
async def update_supplier_contact(
    supplier_id: uuid.UUID,
    contact_id: uuid.UUID,
    obj_in: SupplierContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.update")),
):
    return await supplier_service.update_contact(db, supplier_id, contact_id, obj_in, current_user_id=current_user.id)


@router.delete("/{supplier_id}/contacts/{contact_id}")
async def delete_supplier_contact(
    supplier_id: uuid.UUID,
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.update")),
):
    await supplier_service.delete_contact(db, supplier_id, contact_id, current_user_id=current_user.id)
    return {"success": True, "message": "Supplier contact deleted successfully"}


# =============================================================================
# Supplier Addresses
# =============================================================================

@router.get("/{supplier_id}/addresses", response_model=List[SupplierAddressResponse])
async def list_supplier_addresses(
    supplier_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.read")),
):
    return await supplier_service.list_addresses(db, supplier_id)


@router.post("/{supplier_id}/addresses", response_model=SupplierAddressResponse, status_code=status.HTTP_201_CREATED)
async def add_supplier_address(
    supplier_id: uuid.UUID,
    obj_in: SupplierAddressCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.update")),
):
    return await supplier_service.add_address(db, supplier_id, obj_in, current_user_id=current_user.id)


@router.get("/{supplier_id}/addresses/{address_id}", response_model=SupplierAddressResponse)
async def get_supplier_address(
    supplier_id: uuid.UUID,
    address_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.read")),
):
    return await supplier_service.get_address(db, supplier_id, address_id)


@router.patch("/{supplier_id}/addresses/{address_id}", response_model=SupplierAddressResponse)
@router.put("/{supplier_id}/addresses/{address_id}", response_model=SupplierAddressResponse)
async def update_supplier_address(
    supplier_id: uuid.UUID,
    address_id: uuid.UUID,
    obj_in: SupplierAddressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.update")),
):
    return await supplier_service.update_address(db, supplier_id, address_id, obj_in, current_user_id=current_user.id)


@router.delete("/{supplier_id}/addresses/{address_id}")
async def delete_supplier_address(
    supplier_id: uuid.UUID,
    address_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.update")),
):
    await supplier_service.delete_address(db, supplier_id, address_id, current_user_id=current_user.id)
    return {"success": True, "message": "Supplier address deleted successfully"}


# =============================================================================
# Supplier Documents
# =============================================================================

@router.get("/{supplier_id}/documents", response_model=List[SupplierDocumentResponse])
async def list_supplier_documents(
    supplier_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.read")),
):
    return await supplier_service.list_documents(db, supplier_id)


@router.post("/{supplier_id}/documents", response_model=SupplierDocumentResponse, status_code=status.HTTP_201_CREATED)
async def add_supplier_document(
    supplier_id: uuid.UUID,
    obj_in: SupplierDocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.update")),
):
    return await supplier_service.add_document(db, supplier_id, obj_in, current_user_id=current_user.id)


@router.get("/{supplier_id}/documents/{document_id}", response_model=SupplierDocumentResponse)
async def get_supplier_document(
    supplier_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.read")),
):
    return await supplier_service.get_document(db, supplier_id, document_id)


@router.patch("/{supplier_id}/documents/{document_id}", response_model=SupplierDocumentResponse)
@router.put("/{supplier_id}/documents/{document_id}", response_model=SupplierDocumentResponse)
async def update_supplier_document(
    supplier_id: uuid.UUID,
    document_id: uuid.UUID,
    obj_in: SupplierDocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.update")),
):
    return await supplier_service.update_document(db, supplier_id, document_id, obj_in, current_user_id=current_user.id)


@router.delete("/{supplier_id}/documents/{document_id}")
async def delete_supplier_document(
    supplier_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.update")),
):
    await supplier_service.delete_document(db, supplier_id, document_id, current_user_id=current_user.id)
    return {"success": True, "message": "Supplier document deleted successfully"}


# =============================================================================
# Supplier Ratings
# =============================================================================

@router.get("/{supplier_id}/ratings", response_model=List[SupplierRatingResponse])
async def list_supplier_ratings(
    supplier_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.read")),
):
    return await supplier_service.list_ratings(db, supplier_id)


@router.post("/{supplier_id}/ratings", response_model=SupplierRatingResponse, status_code=status.HTTP_201_CREATED)
async def rate_supplier(
    supplier_id: uuid.UUID,
    obj_in: SupplierRatingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.create")),
):
    return await supplier_service.add_rating(db, supplier_id, obj_in, reviewer_id=current_user.id)

