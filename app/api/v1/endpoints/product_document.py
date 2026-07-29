from typing import List
import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.models.user import User
from app.schemas.inventory import (
    ProductDocumentCreate,
    ProductDocumentResponse,
)
from app.services.inventory_services import product_document_service

router = APIRouter()


@router.post("/products/{product_id}/documents", response_model=ProductDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_product_document(
    product_id: uuid.UUID,
    doc_in: ProductDocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.document.upload")),
):
    """Attach an uploaded document file record to a product."""
    return await product_document_service.add_document(
        db, product_id, obj_in=doc_in, current_user_id=current_user.id
    )


@router.get("/products/{product_id}/documents", response_model=List[ProductDocumentResponse], status_code=status.HTTP_200_OK)
async def get_product_documents(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.document.read")),
):
    """Retrieve list of attached document files for a product."""
    return await product_document_service.get_documents(db, product_id)


@router.delete("/products/{product_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_document(
    product_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.document.delete")),
):
    """Remove attached document file record from a product."""
    await product_document_service.delete_document(
        db, product_id, document_id, current_user_id=current_user.id
    )

