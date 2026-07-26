import uuid
from typing import Any, Optional
from fastapi import APIRouter, Depends, File as FastAPIFile, Form, Query, Response, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.dependencies.query_params import get_pagination_params, get_search_params, get_sorting_params
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.file import FileResponse
from app.schemas.responses import PaginatedResponse, SuccessResponse, create_paginated_response, create_success_response
from app.services.file import file_service
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortCriterion

router = APIRouter()


@router.post(
    "/files/upload",
    response_model=SuccessResponse[FileResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload Enterprise File",
    description="Uploads a file asset with validation, SHA256 checksum duplicate detection, and optional entity attachment.",
)
async def upload_file(
    file: UploadFile = FastAPIFile(..., description="Binary file upload payload"),
    entity_type: Optional[str] = Form(default=None, description="Target ERP entity type attached to (e.g. Employee, Invoice)"),
    entity_id: Optional[str] = Form(default=None, description="Primary Key ID of attached target entity"),
    is_public: bool = Form(default=False, description="Public access flag"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    file_record = await file_service.upload_file(
        db,
        upload_file=file,
        uploader=current_user,
        entity_type=entity_type,
        entity_id=entity_id,
        is_public=is_public,
    )
    return create_success_response(data=file_record, message="File uploaded successfully.")


@router.get(
    "/files/{id}",
    response_model=SuccessResponse[FileResponse],
    status_code=status.HTTP_200_OK,
    summary="Get File Metadata by ID",
    description="Retrieves metadata details for an uploaded file asset.",
)
async def get_file_metadata(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    file_record = await file_service.get_by_id(db, id)
    return create_success_response(data=file_record, message="File metadata retrieved successfully.")


@router.get(
    "/files/download/{id}",
    status_code=status.HTTP_200_OK,
    summary="Download File Binary",
    description="Downloads the raw binary content of an uploaded file asset.",
)
async def download_file(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    file_record, file_bytes = await file_service.get_file_for_download(db, file_id=id, current_user=current_user)
    
    headers = {
        "Content-Disposition": f'attachment; filename="{file_record.original_filename}"',
        "Content-Type": file_record.mime_type,
    }
    return Response(content=file_bytes, media_type=file_record.mime_type, headers=headers)


@router.delete(
    "/files/{id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete File",
    description="Deletes a file asset from disk storage and database. Allowed for original uploader or Super Admin.",
)
async def delete_file(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    await file_service.delete_file_with_authorization(db, file_id=id, current_user=current_user)
    return MessageResponse(message=f"File '{id}' deleted successfully.")


@router.get(
    "/files",
    response_model=PaginatedResponse[FileResponse],
    status_code=status.HTTP_200_OK,
    summary="List Files",
    description="Retrieves a paginated list of uploaded file records with filtering and search.",
)
async def list_files(
    entity_type: Optional[str] = Query(default=None, description="Filter by attached entity type"),
    entity_id: Optional[str] = Query(default=None, description="Filter by attached entity ID"),
    uploaded_by_id: Optional[uuid.UUID] = Query(default=None, description="Filter by uploader user UUID"),
    q: Optional[str] = Depends(get_search_params),
    params: PaginationParams = Depends(get_pagination_params),
    sorting: Optional[list[SortCriterion]] = Depends(get_sorting_params),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    paginated_result = await file_service.get_filtered_files(
        db,
        params=params,
        entity_type=entity_type,
        entity_id=entity_id,
        uploaded_by_id=uploaded_by_id,
        search_term=q,
        sorting=sorting,
    )
    return create_paginated_response(paginated_result, message="Files retrieved successfully.")
