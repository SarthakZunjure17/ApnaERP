from typing import List
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.models.user import User
from app.schemas.inventory import (
    UnitOfMeasureCreate,
    UnitOfMeasureResponse,
    UnitOfMeasureUpdate,
)
from app.services.inventory_services import unit_of_measure_service

router = APIRouter()


@router.get("", response_model=List[UnitOfMeasureResponse], status_code=status.HTTP_200_OK)
async def get_units_of_measure(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.unit.read")),
):
    """Retrieve list of units of measure."""
    return await unit_of_measure_service.get_units(db, skip=skip, limit=limit)


@router.get("/{id}", response_model=UnitOfMeasureResponse, status_code=status.HTTP_200_OK)
async def get_unit_of_measure(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.unit.read")),
):
    """Retrieve unit of measure by ID."""
    return await unit_of_measure_service.get_unit(db, id)


@router.post("", response_model=UnitOfMeasureResponse, status_code=status.HTTP_201_CREATED)
async def create_unit_of_measure(
    unit_in: UnitOfMeasureCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.unit.create")),
):
    """Create a new unit of measure."""
    return await unit_of_measure_service.create_unit(db, obj_in=unit_in, current_user_id=current_user.id)


@router.put("/{id}", response_model=UnitOfMeasureResponse, status_code=status.HTTP_200_OK)
async def update_unit_of_measure(
    id: uuid.UUID,
    unit_in: UnitOfMeasureUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.unit.update")),
):
    """Update an existing unit of measure."""
    return await unit_of_measure_service.update_unit(db, id, obj_in=unit_in, current_user_id=current_user.id)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit_of_measure(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.unit.delete")),
):
    """Delete a unit of measure."""
    await unit_of_measure_service.delete_unit(db, id, current_user_id=current_user.id)

