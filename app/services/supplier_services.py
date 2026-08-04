from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_events import domain_event_publisher
from app.core.redis import redis_manager
from app.exceptions.base import (
    DuplicateResourceException,
    NotFoundException,
    ValidationException,
)
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.supplier import (
    Supplier,
    SupplierAddress,
    SupplierCategory,
    SupplierContact,
    SupplierDocument,
    SupplierRating,
)
from app.repositories.procurement_repos import (
    supplier_address_repository,
    supplier_category_repository,
    supplier_contact_repository,
    supplier_document_repository,
    supplier_rating_repository,
    supplier_repository,
)
from app.schemas.procurement import (
    SupplierAddressCreate,
    SupplierCategoryCreate,
    SupplierCategoryUpdate,
    SupplierContactCreate,
    SupplierCreate,
    SupplierDocumentCreate,
    SupplierRatingCreate,
    SupplierUpdate,
)
from app.services.audit_log import audit_log_service

logger = logging.getLogger("app.services.supplier")


class SupplierService:
    """
    Domain service for managing Supplier master records, categories, contacts, addresses, documents, ratings, and status.
    """
    async def create_category(self, db: AsyncSession, obj_in: SupplierCategoryCreate) -> SupplierCategory:
        existing = await supplier_category_repository.get_by_code(db, obj_in.code)
        if existing:
            raise DuplicateResourceException(f"Supplier category with code '{obj_in.code}' already exists.")

        cat = await supplier_category_repository.create(db, obj_in=obj_in)
        return cat

    async def list_categories(self, db: AsyncSession) -> List[SupplierCategory]:
        return await supplier_category_repository.get_all(db)

    async def create_supplier(
        self, db: AsyncSession, obj_in: SupplierCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> Supplier:
        existing = await supplier_repository.get_by_code(db, obj_in.code)
        if existing:
            raise DuplicateResourceException(f"Supplier with code '{obj_in.code}' already exists.")

        data = obj_in.model_dump(exclude={"contacts", "addresses"})
        supplier = Supplier(**data)
        db.add(supplier)
        await db.flush()

        # Add contacts
        if obj_in.contacts:
            for c_in in obj_in.contacts:
                contact = SupplierContact(supplier_id=supplier.id, **c_in.model_dump())
                db.add(contact)

        # Add addresses
        if obj_in.addresses:
            for a_in in obj_in.addresses:
                addr = SupplierAddress(supplier_id=supplier.id, **a_in.model_dump())
                db.add(addr)

        await db.commit()

        # Re-fetch supplier with eager relationships
        supplier = await supplier_repository.get_by_code(db, obj_in.code)

        # Publish Domain Event
        domain_event_publisher.publish(
            "SupplierCreated",
            {
                "supplier_id": str(supplier.id),
                "supplier_code": supplier.code,
                "name": supplier.name,
                "currency": supplier.currency,
            },
        )

        # Invalidate Cache
        await redis_manager.delete_pattern("supplier:*")

        # Audit Log
        await audit_log_service.log_event(
            db,
            action="SUPPLIER_CREATE",
            entity_type="Supplier",
            entity_id=supplier.id,
            user_id=current_user_id,
        )
        return supplier

    async def get_supplier(self, db: AsyncSession, supplier_id: uuid.UUID) -> Supplier:
        supplier = await supplier_repository.get_by_id(db, supplier_id)
        if not supplier or supplier.is_deleted:
            raise NotFoundException(f"Supplier with ID '{supplier_id}' not found.")
        return supplier

    async def update_supplier(
        self, db: AsyncSession, supplier_id: uuid.UUID, obj_in: SupplierUpdate, current_user_id: Optional[uuid.UUID] = None
    ) -> Supplier:
        supplier = await self.get_supplier(db, supplier_id)
        updated = await supplier_repository.update(db, db_obj=supplier, obj_in=obj_in)
        await redis_manager.delete_pattern("supplier:*")

        await audit_log_service.log_event(
            db,
            action="SUPPLIER_UPDATE",
            entity_type="Supplier",
            entity_id=supplier.id,
            user_id=current_user_id,
        )
        return updated

    async def blacklist_supplier(
        self, db: AsyncSession, supplier_id: uuid.UUID, reason: str, current_user_id: Optional[uuid.UUID] = None
    ) -> Supplier:
        supplier = await self.get_supplier(db, supplier_id)
        supplier.status = "Blacklisted"
        if supplier.notes:
            supplier.notes += f"\n[Blacklisted]: {reason}"
        else:
            supplier.notes = f"[Blacklisted]: {reason}"

        await db.commit()
        await db.refresh(supplier)
        await redis_manager.delete_pattern("supplier:*")

        await audit_log_service.log_event(
            db,
            action="SUPPLIER_BLACKLIST",
            entity_type="Supplier",
            entity_id=supplier.id,
            user_id=current_user_id,
        )
        return supplier

    async def add_rating(
        self, db: AsyncSession, supplier_id: uuid.UUID, obj_in: SupplierRatingCreate, reviewer_id: uuid.UUID
    ) -> SupplierRating:
        supplier = await self.get_supplier(db, supplier_id)
        rating = SupplierRating(
            supplier_id=supplier.id,
            reviewer_id=reviewer_id,
            score=obj_in.score,
            comments=obj_in.comments,
        )
        db.add(rating)
        await db.flush()

        # Recalculate average rating
        stmt = select(func.avg(SupplierRating.score)).where(SupplierRating.supplier_id == supplier.id)
        res = await db.execute(stmt)
        avg_score = res.scalar()
        if avg_score is not None:
            supplier.rating = Decimal(str(round(avg_score, 2)))

        await db.commit()
        await db.refresh(rating)
        await redis_manager.delete_pattern("supplier:*")
        return rating

    async def list_suppliers(
        self,
        db: AsyncSession,
        category_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        is_preferred: Optional[bool] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Supplier], int]:
        return await supplier_repository.get_multi_paginated(
            db,
            category_id=category_id,
            status=status,
            is_preferred=is_preferred,
            search=search,
            skip=skip,
            limit=limit,
        )


class SupplierPerformanceService:
    """
    Domain service for calculating and updating supplier performance metrics (on-time delivery, quality rating, spend).
    """
    async def recalculate_supplier_performance(self, db: AsyncSession, supplier_id: uuid.UUID) -> None:
        supplier = await supplier_repository.get_by_id(db, supplier_id)
        if not supplier:
            return

        # Calculate Total Spend from Approved/Closed POs
        spend_stmt = (
            select(func.coalesce(func.sum(PurchaseOrder.total_amount), Decimal("0.0")))
            .where(PurchaseOrder.supplier_id == supplier_id)
            .where(PurchaseOrder.status.in_(["Approved", "Closed"]))
        )
        spend_res = await db.execute(spend_stmt)
        total_spend = Decimal(str(spend_res.scalar() or 0.0))
        supplier.total_spend = total_spend

        await db.commit()
        await db.refresh(supplier)


supplier_service = SupplierService()
supplier_performance_service = SupplierPerformanceService()
