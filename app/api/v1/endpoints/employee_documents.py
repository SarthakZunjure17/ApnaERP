from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.user import User
from app.schemas.employee_document import (
    DocumentRejectRequest,
    DocumentVerifyRequest,
    EmployeeDocumentCreate,
    EmployeeDocumentListResponse,
    EmployeeDocumentResponse,
    EmployeeDocumentUpdate,
)
from app.services.employee_document import EmployeeDocumentService

router = APIRouter()


@router.get(
    "/employee-documents",
    response_model=EmployeeDocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Employee Documents",
    description="Retrieves a paginated list of employee documents with search and filtering.",
    dependencies=[Depends(has_permission("employee_document.read"))]
)
async def list_employee_documents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for document type, number, or status"),
    db: AsyncSession = Depends(get_db),
) -> EmployeeDocumentListResponse:
    """Lists employee documents with pagination."""
    service = EmployeeDocumentService(db)
    result = await service.get_documents_list(page=page, page_size=page_size, search=search)
    return EmployeeDocumentListResponse.model_validate(result)


@router.get(
    "/employee-documents/{id}",
    response_model=EmployeeDocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Employee Document Details",
    description="Retrieves single employee document details by UUID.",
    dependencies=[Depends(has_permission("employee_document.read"))]
)
async def get_employee_document_by_id(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> EmployeeDocumentResponse:
    """Retrieves document by ID."""
    service = EmployeeDocumentService(db)
    doc = await service.get_document_by_id(id)
    return EmployeeDocumentResponse.model_validate(doc)


@router.get(
    "/employees/{employee_id}/documents",
    response_model=List[EmployeeDocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Employee Documents for Employee",
    description="Retrieves all active personnel documents linked to a specific employee.",
    dependencies=[Depends(has_permission("employee_document.read"))]
)
async def get_documents_by_employee(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> List[EmployeeDocumentResponse]:
    """Retrieves all documents for an employee."""
    service = EmployeeDocumentService(db)
    docs = await service.get_documents_by_employee(employee_id)
    return [EmployeeDocumentResponse.model_validate(d) for d in docs]


@router.post(
    "/employee-documents",
    response_model=EmployeeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Link File as Employee Document",
    description="Links an existing storage File ID as a digital personnel document for an employee.",
    dependencies=[Depends(has_permission("employee_document.create"))]
)
async def create_employee_document(
    payload: EmployeeDocumentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmployeeDocumentResponse:
    """Creates a new employee document link."""
    service = EmployeeDocumentService(db)
    doc = await service.create_document(data=payload, current_user=current_user, request=request)
    return EmployeeDocumentResponse.model_validate(doc)


@router.put(
    "/employee-documents/{id}",
    response_model=EmployeeDocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Employee Document",
    description="Updates document metadata, document number, dates, or notes.",
    dependencies=[Depends(has_permission("employee_document.update"))]
)
async def update_employee_document(
    id: uuid.UUID,
    payload: EmployeeDocumentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmployeeDocumentResponse:
    """Updates an existing document."""
    service = EmployeeDocumentService(db)
    doc = await service.update_document(
        document_id=id, data=payload, current_user=current_user, request=request
    )
    return EmployeeDocumentResponse.model_validate(doc)


@router.delete(
    "/employee-documents/{id}",
    response_model=EmployeeDocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft Delete Employee Document",
    description="Soft-deletes an employee document metadata link.",
    dependencies=[Depends(has_permission("employee_document.delete"))]
)
async def delete_employee_document(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmployeeDocumentResponse:
    """Soft deletes a document."""
    service = EmployeeDocumentService(db)
    doc = await service.delete_document(
        document_id=id, current_user=current_user, request=request
    )
    return EmployeeDocumentResponse.model_validate(doc)


@router.patch(
    "/employee-documents/{id}/restore",
    response_model=EmployeeDocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Restore Soft-Deleted Employee Document",
    description="Restores a soft-deleted employee document metadata link.",
    dependencies=[Depends(has_permission("employee_document.restore"))]
)
async def restore_employee_document(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmployeeDocumentResponse:
    """Restores a soft-deleted document."""
    service = EmployeeDocumentService(db)
    doc = await service.restore_document(
        document_id=id, current_user=current_user, request=request
    )
    return EmployeeDocumentResponse.model_validate(doc)


@router.patch(
    "/employee-documents/{id}/verify",
    response_model=EmployeeDocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Employee Document",
    description="Marks an employee document as Verified, recording verifier ID and verification timestamp.",
    dependencies=[Depends(has_permission("employee_document.verify"))]
)
async def verify_employee_document(
    id: uuid.UUID,
    payload: DocumentVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmployeeDocumentResponse:
    """Verifies a document."""
    service = EmployeeDocumentService(db)
    doc = await service.verify_document(
        document_id=id, payload=payload, current_user=current_user, request=request
    )
    return EmployeeDocumentResponse.model_validate(doc)


@router.patch(
    "/employee-documents/{id}/reject",
    response_model=EmployeeDocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject Employee Document",
    description="Marks an employee document as Rejected with rejection notes.",
    dependencies=[Depends(has_permission("employee_document.verify"))]
)
async def reject_employee_document(
    id: uuid.UUID,
    payload: DocumentRejectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmployeeDocumentResponse:
    """Rejects a document."""
    service = EmployeeDocumentService(db)
    doc = await service.reject_document(
        document_id=id, payload=payload, current_user=current_user, request=request
    )
    return EmployeeDocumentResponse.model_validate(doc)
