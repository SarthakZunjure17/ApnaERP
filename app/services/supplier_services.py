import asyncio
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
from app.models.file import File
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
    SupplierAddressUpdate,
    SupplierCategoryCreate,
    SupplierCategoryUpdate,
    SupplierContactCreate,
    SupplierContactUpdate,
    SupplierCreate,
    SupplierDocumentCreate,
    SupplierDocumentUpdate,
    SupplierRatingCreate,
    SupplierUpdate,
)
from app.services.audit_log import audit_log_service

logger = logging.getLogger("app.services.supplier")


def mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Masks sensitive supplier fields such as bank account numbers for audit logs.
    """
    masked = dict(data)
    if masked.get("bank_account_number"):
        raw = str(masked["bank_account_number"])
        if len(raw) > 4:
            masked["bank_account_number"] = f"****{raw[-4:]}"
        else:
            masked["bank_account_number"] = "****"
    return masked


class SupplierService:
    """
    Authoritative domain service for managing Supplier master records, categories,
    contacts, addresses, documents, ratings, lifecycle transitions, and audit trails.
    """

    def __init__(self):
        self._contact_lock = asyncio.Lock()

    # -------------------------------------------------------------------------
    # Supplier Category Management
    # -------------------------------------------------------------------------

    async def create_category(
        self, db: AsyncSession, obj_in: SupplierCategoryCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> SupplierCategory:
        existing = await supplier_category_repository.get_by_code(db, obj_in.code)
        if existing:
            raise DuplicateResourceException(f"Supplier category with code '{obj_in.code}' already exists.")

        cat = await supplier_category_repository.create(db, obj_in=obj_in)

        # Audit Log
        await audit_log_service.log_event(
            db,
            action="SUPPLIER_CATEGORY_CREATE",
            entity_type="SupplierCategory",
            entity_id=cat.id,
            user_id=current_user_id,
            new_data={"code": cat.code, "name": cat.name, "description": cat.description},
        )
        return cat

    async def get_category(self, db: AsyncSession, category_id: uuid.UUID) -> SupplierCategory:
        cat = await supplier_category_repository.get_by_id(db, category_id)
        if not cat:
            raise NotFoundException(f"Supplier category with ID '{category_id}' not found.")
        return cat

    async def update_category(
        self,
        db: AsyncSession,
        category_id: uuid.UUID,
        obj_in: SupplierCategoryUpdate,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> SupplierCategory:
        cat = await self.get_category(db, category_id)
        prev_data = {"name": cat.name, "description": cat.description}
        updated = await supplier_category_repository.update(db, db_obj=cat, obj_in=obj_in)

        await audit_log_service.log_event(
            db,
            action="SUPPLIER_CATEGORY_UPDATE",
            entity_type="SupplierCategory",
            entity_id=cat.id,
            user_id=current_user_id,
            previous_data=prev_data,
            new_data=obj_in.model_dump(exclude_unset=True),
        )
        return updated

    async def delete_category(
        self, db: AsyncSession, category_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> bool:
        cat = await self.get_category(db, category_id)
        active_suppliers_count = await supplier_category_repository.count_active_suppliers(db, category_id)
        if active_suppliers_count > 0:
            raise ValidationException(
                f"Cannot delete category '{cat.name}' because it is referenced by {active_suppliers_count} active supplier(s)."
            )

        deleted = await supplier_category_repository.delete(db, id=category_id)
        await audit_log_service.log_event(
            db,
            action="SUPPLIER_CATEGORY_DELETE",
            entity_type="SupplierCategory",
            entity_id=category_id,
            user_id=current_user_id,
        )
        return deleted

    async def list_categories(
        self, db: AsyncSession, search: Optional[str] = None, skip: int = 0, limit: int = 50
    ) -> Tuple[List[SupplierCategory], int]:
        return await supplier_category_repository.get_multi_paginated(db, search=search, skip=skip, limit=limit)

    # -------------------------------------------------------------------------
    # Supplier Master Management
    # -------------------------------------------------------------------------

    async def generate_supplier_code(self, db: AsyncSession) -> str:
        """
        Generates next sequential SUP-00001 formatted supplier code safely.
        """
        max_num = await supplier_repository.get_max_code_suffix(db, prefix="SUP-")
        return f"SUP-{max_num + 1:05d}"

    async def create_supplier(
        self, db: AsyncSession, obj_in: SupplierCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> Supplier:
        # 1. Resolve Code
        code = obj_in.code.strip() if obj_in.code else await self.generate_supplier_code(db)
        existing = await supplier_repository.get_by_code(db, code)
        if existing:
            raise DuplicateResourceException(f"Supplier with code '{code}' already exists.")

        # 2. Validate Category FK if provided
        if obj_in.category_id:
            cat = await supplier_category_repository.get_by_id(db, obj_in.category_id)
            if not cat:
                raise NotFoundException(f"Supplier category with ID '{obj_in.category_id}' not found.")

        # 3. Validate Commercial Defaults
        if obj_in.credit_limit < Decimal("0.0"):
            raise ValidationException("Credit limit cannot be negative.")

        data = obj_in.model_dump(exclude={"contacts", "addresses"})
        data["code"] = code
        supplier = Supplier(**data)
        db.add(supplier)
        await db.flush()

        # 4. Add Contacts (Ensure single primary contact)
        if obj_in.contacts:
            has_primary = False
            for c_in in obj_in.contacts:
                is_prim = c_in.is_primary
                if is_prim:
                    if has_primary:
                        is_prim = False
                    else:
                        has_primary = True
                contact = SupplierContact(
                    supplier_id=supplier.id,
                    contact_name=c_in.contact_name,
                    designation=c_in.designation,
                    email=c_in.email,
                    phone=c_in.phone,
                    is_primary=is_prim,
                )
                db.add(contact)

        # 5. Add Addresses
        if obj_in.addresses:
            for a_in in obj_in.addresses:
                addr = SupplierAddress(supplier_id=supplier.id, **a_in.model_dump())
                db.add(addr)

        await db.commit()

        # Re-fetch supplier with eager relationships
        supplier = await supplier_repository.get_by_code(db, code)

        # Domain Event
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
        masked_payload = mask_sensitive_data(
            {"code": supplier.code, "name": supplier.name, "currency": supplier.currency, "status": supplier.status}
        )
        await audit_log_service.log_event(
            db,
            action="SUPPLIER_CREATE",
            entity_type="Supplier",
            entity_id=supplier.id,
            user_id=current_user_id,
            new_data=masked_payload,
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

        # Validate category if changed
        if obj_in.category_id is not None:
            cat = await supplier_category_repository.get_by_id(db, obj_in.category_id)
            if not cat:
                raise NotFoundException(f"Supplier category with ID '{obj_in.category_id}' not found.")

        # Validate credit limit if changed
        if obj_in.credit_limit is not None and obj_in.credit_limit < Decimal("0.0"):
            raise ValidationException("Credit limit cannot be negative.")

        prev_data = mask_sensitive_data(
            {
                "name": supplier.name,
                "payment_terms": supplier.payment_terms,
                "credit_limit": str(supplier.credit_limit),
                "status": supplier.status,
            }
        )

        updated = await supplier_repository.update(db, db_obj=supplier, obj_in=obj_in)
        await redis_manager.delete_pattern("supplier:*")

        new_data = mask_sensitive_data(obj_in.model_dump(exclude_unset=True))
        await audit_log_service.log_event(
            db,
            action="SUPPLIER_UPDATE",
            entity_type="Supplier",
            entity_id=supplier.id,
            user_id=current_user_id,
            previous_data=prev_data,
            new_data=new_data,
        )
        return updated

    async def activate_supplier(
        self, db: AsyncSession, supplier_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> Supplier:
        supplier = await self.get_supplier(db, supplier_id)
        if supplier.status == "Active":
            raise ValidationException("Supplier is already Active.")

        prev_status = supplier.status
        supplier.status = "Active"
        await db.commit()
        await db.refresh(supplier)
        await redis_manager.delete_pattern("supplier:*")

        await audit_log_service.log_event(
            db,
            action="SUPPLIER_ACTIVATE",
            entity_type="Supplier",
            entity_id=supplier.id,
            user_id=current_user_id,
            previous_data={"status": prev_status},
            new_data={"status": "Active"},
        )
        return supplier

    async def deactivate_supplier(
        self,
        db: AsyncSession,
        supplier_id: uuid.UUID,
        reason: Optional[str] = None,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> Supplier:
        supplier = await self.get_supplier(db, supplier_id)
        if supplier.status == "Inactive":
            raise ValidationException("Supplier is already Inactive.")

        prev_status = supplier.status
        supplier.status = "Inactive"
        if reason:
            if supplier.notes:
                supplier.notes += f"\n[Deactivated]: {reason}"
            else:
                supplier.notes = f"[Deactivated]: {reason}"

        await db.commit()
        await db.refresh(supplier)
        await redis_manager.delete_pattern("supplier:*")

        await audit_log_service.log_event(
            db,
            action="SUPPLIER_DEACTIVATE",
            entity_type="Supplier",
            entity_id=supplier.id,
            user_id=current_user_id,
            previous_data={"status": prev_status},
            new_data={"status": "Inactive", "reason": reason},
        )
        return supplier

    async def blacklist_supplier(
        self, db: AsyncSession, supplier_id: uuid.UUID, reason: str, current_user_id: Optional[uuid.UUID] = None
    ) -> Supplier:
        supplier = await self.get_supplier(db, supplier_id)
        if supplier.status == "Blacklisted":
            raise ValidationException("Supplier is already Blacklisted.")

        prev_status = supplier.status
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
            previous_data={"status": prev_status},
            new_data={"status": "Blacklisted", "reason": reason},
        )
        return supplier

    async def delete_supplier(
        self, db: AsyncSession, supplier_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> bool:
        supplier = await self.get_supplier(db, supplier_id)
        has_deps = await supplier_repository.has_active_dependencies(db, supplier_id)
        if has_deps:
            raise ValidationException("Cannot delete supplier referenced by historical procurement records.")

        deleted = await supplier_repository.soft_delete(db, id=supplier_id)
        await redis_manager.delete_pattern("supplier:*")

        await audit_log_service.log_event(
            db,
            action="SUPPLIER_DELETE",
            entity_type="Supplier",
            entity_id=supplier_id,
            user_id=current_user_id,
        )
        return deleted

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

    # -------------------------------------------------------------------------
    # Supplier Contacts Management
    # -------------------------------------------------------------------------

    async def add_contact(
        self,
        db: AsyncSession,
        supplier_id: uuid.UUID,
        obj_in: SupplierContactCreate,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> SupplierContact:
        async with self._contact_lock:
            supplier = await self.get_supplier(db, supplier_id)

            # If marked as primary, atomically clear any previous primary contact
            if obj_in.is_primary:
                await supplier_contact_repository.clear_primary_contacts(db, supplier_id)

            contact = SupplierContact(
                supplier_id=supplier.id,
                contact_name=obj_in.contact_name,
                designation=obj_in.designation,
                email=obj_in.email,
                phone=obj_in.phone,
                is_primary=obj_in.is_primary,
            )
            db.add(contact)
            await db.commit()
            await db.refresh(contact)
            await redis_manager.delete_pattern("supplier:*")

            await audit_log_service.log_event(
                db,
                action="SUPPLIER_CONTACT_CREATE",
                entity_type="SupplierContact",
                entity_id=contact.id,
                user_id=current_user_id,
                new_data={"supplier_id": str(supplier_id), "contact_name": contact.contact_name, "is_primary": contact.is_primary},
            )
            return contact

    async def get_contact(self, db: AsyncSession, supplier_id: uuid.UUID, contact_id: uuid.UUID) -> SupplierContact:
        await self.get_supplier(db, supplier_id)
        contact = await supplier_contact_repository.get_by_id(db, contact_id)
        if not contact or contact.supplier_id != supplier_id:
            raise NotFoundException(f"Supplier contact with ID '{contact_id}' not found for this supplier.")
        return contact

    async def update_contact(
        self,
        db: AsyncSession,
        supplier_id: uuid.UUID,
        contact_id: uuid.UUID,
        obj_in: SupplierContactUpdate,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> SupplierContact:
        async with self._contact_lock:
            contact = await self.get_contact(db, supplier_id, contact_id)

            if obj_in.is_primary is True:
                await supplier_contact_repository.clear_primary_contacts(db, supplier_id, exclude_contact_id=contact_id)

            prev_data = {"contact_name": contact.contact_name, "email": contact.email, "is_primary": contact.is_primary}
            updated = await supplier_contact_repository.update(db, db_obj=contact, obj_in=obj_in)
            await redis_manager.delete_pattern("supplier:*")

            await audit_log_service.log_event(
                db,
                action="SUPPLIER_CONTACT_UPDATE",
                entity_type="SupplierContact",
                entity_id=contact.id,
                user_id=current_user_id,
                previous_data=prev_data,
                new_data=obj_in.model_dump(exclude_unset=True),
            )
            return updated

    async def delete_contact(
        self,
        db: AsyncSession,
        supplier_id: uuid.UUID,
        contact_id: uuid.UUID,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> bool:
        contact = await self.get_contact(db, supplier_id, contact_id)
        deleted = await supplier_contact_repository.delete(db, id=contact.id)
        await redis_manager.delete_pattern("supplier:*")

        await audit_log_service.log_event(
            db,
            action="SUPPLIER_CONTACT_DELETE",
            entity_type="SupplierContact",
            entity_id=contact_id,
            user_id=current_user_id,
        )
        return deleted

    async def list_contacts(self, db: AsyncSession, supplier_id: uuid.UUID) -> List[SupplierContact]:
        await self.get_supplier(db, supplier_id)
        return await supplier_contact_repository.get_by_supplier(db, supplier_id)

    # -------------------------------------------------------------------------
    # Supplier Addresses Management
    # -------------------------------------------------------------------------

    async def add_address(
        self,
        db: AsyncSession,
        supplier_id: uuid.UUID,
        obj_in: SupplierAddressCreate,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> SupplierAddress:
        supplier = await self.get_supplier(db, supplier_id)
        valid_types = ["Billing", "Shipping", "Head Office", "Branch"]
        if obj_in.address_type not in valid_types:
            raise ValidationException(f"Invalid address type '{obj_in.address_type}'. Must be one of {valid_types}.")

        addr = SupplierAddress(supplier_id=supplier.id, **obj_in.model_dump())
        db.add(addr)
        await db.commit()
        await db.refresh(addr)
        await redis_manager.delete_pattern("supplier:*")

        await audit_log_service.log_event(
            db,
            action="SUPPLIER_ADDRESS_CREATE",
            entity_type="SupplierAddress",
            entity_id=addr.id,
            user_id=current_user_id,
            new_data={"supplier_id": str(supplier_id), "address_type": addr.address_type, "city": addr.city},
        )
        return addr

    async def get_address(self, db: AsyncSession, supplier_id: uuid.UUID, address_id: uuid.UUID) -> SupplierAddress:
        await self.get_supplier(db, supplier_id)
        addr = await supplier_address_repository.get_by_id(db, address_id)
        if not addr or addr.supplier_id != supplier_id:
            raise NotFoundException(f"Supplier address with ID '{address_id}' not found for this supplier.")
        return addr

    async def update_address(
        self,
        db: AsyncSession,
        supplier_id: uuid.UUID,
        address_id: uuid.UUID,
        obj_in: SupplierAddressUpdate,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> SupplierAddress:
        addr = await self.get_address(db, supplier_id, address_id)
        if obj_in.address_type:
            valid_types = ["Billing", "Shipping", "Head Office", "Branch"]
            if obj_in.address_type not in valid_types:
                raise ValidationException(f"Invalid address type '{obj_in.address_type}'. Must be one of {valid_types}.")

        prev_data = {"address_type": addr.address_type, "city": addr.city, "postal_code": addr.postal_code}
        updated = await supplier_address_repository.update(db, db_obj=addr, obj_in=obj_in)
        await redis_manager.delete_pattern("supplier:*")

        await audit_log_service.log_event(
            db,
            action="SUPPLIER_ADDRESS_UPDATE",
            entity_type="SupplierAddress",
            entity_id=addr.id,
            user_id=current_user_id,
            previous_data=prev_data,
            new_data=obj_in.model_dump(exclude_unset=True),
        )
        return updated

    async def delete_address(
        self,
        db: AsyncSession,
        supplier_id: uuid.UUID,
        address_id: uuid.UUID,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> bool:
        addr = await self.get_address(db, supplier_id, address_id)
        deleted = await supplier_address_repository.delete(db, id=addr.id)
        await redis_manager.delete_pattern("supplier:*")

        await audit_log_service.log_event(
            db,
            action="SUPPLIER_ADDRESS_DELETE",
            entity_type="SupplierAddress",
            entity_id=address_id,
            user_id=current_user_id,
        )
        return deleted

    async def list_addresses(self, db: AsyncSession, supplier_id: uuid.UUID) -> List[SupplierAddress]:
        await self.get_supplier(db, supplier_id)
        return await supplier_address_repository.get_by_supplier(db, supplier_id)

    # -------------------------------------------------------------------------
    # Supplier Documents Management
    # -------------------------------------------------------------------------

    async def add_document(
        self,
        db: AsyncSession,
        supplier_id: uuid.UUID,
        obj_in: SupplierDocumentCreate,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> SupplierDocument:
        supplier = await self.get_supplier(db, supplier_id)

        # Validate canonical file existence
        stmt = select(File).where(File.id == obj_in.file_id)
        file_obj = (await db.execute(stmt)).scalar_one_or_none()
        if not file_obj:
            raise NotFoundException(f"Canonical file with ID '{obj_in.file_id}' not found.")

        doc = SupplierDocument(supplier_id=supplier.id, **obj_in.model_dump())
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        await redis_manager.delete_pattern("supplier:*")

        await audit_log_service.log_event(
            db,
            action="SUPPLIER_DOCUMENT_CREATE",
            entity_type="SupplierDocument",
            entity_id=doc.id,
            user_id=current_user_id,
            new_data={"supplier_id": str(supplier_id), "document_type": doc.document_type, "file_id": str(doc.file_id)},
        )
        return doc

    async def get_document(self, db: AsyncSession, supplier_id: uuid.UUID, document_id: uuid.UUID) -> SupplierDocument:
        await self.get_supplier(db, supplier_id)
        doc = await supplier_document_repository.get_by_id(db, document_id)
        if not doc or doc.supplier_id != supplier_id:
            raise NotFoundException(f"Supplier document with ID '{document_id}' not found for this supplier.")
        return doc

    async def update_document(
        self,
        db: AsyncSession,
        supplier_id: uuid.UUID,
        document_id: uuid.UUID,
        obj_in: SupplierDocumentUpdate,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> SupplierDocument:
        doc = await self.get_document(db, supplier_id, document_id)
        prev_data = {"document_type": doc.document_type, "description": doc.description}
        updated = await supplier_document_repository.update(db, db_obj=doc, obj_in=obj_in)
        await redis_manager.delete_pattern("supplier:*")

        await audit_log_service.log_event(
            db,
            action="SUPPLIER_DOCUMENT_UPDATE",
            entity_type="SupplierDocument",
            entity_id=doc.id,
            user_id=current_user_id,
            previous_data=prev_data,
            new_data=obj_in.model_dump(exclude_unset=True),
        )
        return updated

    async def delete_document(
        self,
        db: AsyncSession,
        supplier_id: uuid.UUID,
        document_id: uuid.UUID,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> bool:
        doc = await self.get_document(db, supplier_id, document_id)
        deleted = await supplier_document_repository.delete(db, id=doc.id)
        await redis_manager.delete_pattern("supplier:*")

        await audit_log_service.log_event(
            db,
            action="SUPPLIER_DOCUMENT_DELETE",
            entity_type="SupplierDocument",
            entity_id=document_id,
            user_id=current_user_id,
        )
        return deleted

    async def list_documents(self, db: AsyncSession, supplier_id: uuid.UUID) -> List[SupplierDocument]:
        await self.get_supplier(db, supplier_id)
        return await supplier_document_repository.get_by_supplier(db, supplier_id)

    # -------------------------------------------------------------------------
    # Supplier Ratings Management
    # -------------------------------------------------------------------------

    async def add_rating(
        self, db: AsyncSession, supplier_id: uuid.UUID, obj_in: SupplierRatingCreate, reviewer_id: uuid.UUID
    ) -> SupplierRating:
        supplier = await self.get_supplier(db, supplier_id)
        if obj_in.score < Decimal("1.0") or obj_in.score > Decimal("5.0"):
            raise ValidationException("Supplier rating score must be between 1.00 and 5.00.")

        rating = SupplierRating(
            supplier_id=supplier.id,
            reviewer_id=reviewer_id,
            score=obj_in.score,
            comments=obj_in.comments,
        )
        db.add(rating)
        await db.flush()

        # Recalculate average rating
        avg_score = await supplier_rating_repository.calculate_average_rating(db, supplier.id)
        if avg_score is not None:
            supplier.rating = avg_score

        await db.commit()
        await db.refresh(rating)
        await redis_manager.delete_pattern("supplier:*")

        await audit_log_service.log_event(
            db,
            action="SUPPLIER_RATING_CREATE",
            entity_type="SupplierRating",
            entity_id=rating.id,
            user_id=reviewer_id,
            new_data={"supplier_id": str(supplier_id), "score": str(rating.score), "new_average": str(supplier.rating)},
        )
        return rating

    async def list_ratings(self, db: AsyncSession, supplier_id: uuid.UUID) -> List[SupplierRating]:
        await self.get_supplier(db, supplier_id)
        return await supplier_rating_repository.get_by_supplier(db, supplier_id)


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

