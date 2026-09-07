from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.procurement_report_snapshot import ProcurementReportSnapshot
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.purchase_requisition import PurchaseRequisition, PurchaseRequisitionItem
from app.models.purchase_return import PurchaseReturn, PurchaseReturnItem
from app.models.rfq import RFQ, RFQSupplier
from app.models.supplier import (
    Supplier,
    SupplierAddress,
    SupplierCategory,
    SupplierContact,
    SupplierDocument,
    SupplierRating,
)
from app.models.supplier_quotation import SupplierQuotation, SupplierQuotationItem
from app.repositories.base import BaseRepository
from app.schemas.procurement import (
    PurchaseOrderCreate,
    PurchaseOrderUpdate,
    PurchaseRequisitionCreate,
    PurchaseRequisitionUpdate,
    PurchaseReturnCreate,
    RFQCreate,
    RFQUpdate,
    SupplierAddressCreate,
    SupplierCategoryCreate,
    SupplierCategoryUpdate,
    SupplierContactCreate,
    SupplierCreate,
    SupplierDocumentCreate,
    SupplierQuotationCreate,
    SupplierQuotationUpdate,
    SupplierRatingCreate,
    SupplierUpdate,
)


class SupplierCategoryRepository(BaseRepository[SupplierCategory, SupplierCategoryCreate, SupplierCategoryUpdate]):
    def __init__(self):
        super().__init__(SupplierCategory)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[SupplierCategory]:
        stmt = select(SupplierCategory).where(SupplierCategory.code == code)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SupplierCategory], int]:
        stmt = select(SupplierCategory)
        if search:
            stmt = stmt.where(
                or_(
                    SupplierCategory.code.ilike(f"%{search}%"),
                    SupplierCategory.name.ilike(f"%{search}%"),
                )
            )
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(SupplierCategory.code.asc()).offset(skip).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all()), total

    async def count_active_suppliers(self, db: AsyncSession, category_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Supplier)
            .where(Supplier.category_id == category_id)
            .where(Supplier.is_deleted == False)
        )
        res = await db.execute(stmt)
        return res.scalar() or 0


class SupplierRepository(BaseRepository[Supplier, SupplierCreate, SupplierUpdate]):
    def __init__(self):
        super().__init__(Supplier)

    async def get_by_id(
        self, db: AsyncSession, id: Any, include_deleted: bool = False, for_update: bool = False
    ) -> Optional[Supplier]:
        stmt = (
            select(Supplier)
            .options(
                selectinload(Supplier.category),
                selectinload(Supplier.contacts),
                selectinload(Supplier.addresses),
                selectinload(Supplier.documents),
                selectinload(Supplier.ratings),
            )
            .where(Supplier.id == id)
        )
        if not include_deleted:
            stmt = stmt.where(Supplier.is_deleted == False)
        if for_update and db.bind and db.bind.dialect.name != "sqlite":
            stmt = stmt.with_for_update()
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[Supplier]:
        stmt = (
            select(Supplier)
            .options(
                selectinload(Supplier.category),
                selectinload(Supplier.contacts),
                selectinload(Supplier.addresses),
                selectinload(Supplier.documents),
                selectinload(Supplier.ratings),
            )
            .where(Supplier.code == code)
            .where(Supplier.is_deleted == False)
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        category_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        is_preferred: Optional[bool] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Supplier], int]:
        stmt = (
            select(Supplier)
            .options(
                selectinload(Supplier.category),
                selectinload(Supplier.contacts),
                selectinload(Supplier.addresses),
                selectinload(Supplier.documents),
            )
            .where(Supplier.is_deleted == False)
        )

        if category_id:
            stmt = stmt.where(Supplier.category_id == category_id)
        if status:
            stmt = stmt.where(Supplier.status == status)
        if is_preferred is not None:
            stmt = stmt.where(Supplier.is_preferred == is_preferred)
        if search:
            stmt = stmt.where(
                or_(
                    Supplier.code.ilike(f"%{search}%"),
                    Supplier.name.ilike(f"%{search}%"),
                    Supplier.gst_vat_number.ilike(f"%{search}%"),
                    Supplier.tax_id.ilike(f"%{search}%"),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(Supplier.created_at.desc()).offset(skip).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all()), total

    async def get_max_code_suffix(self, db: AsyncSession, prefix: str = "SUP-") -> int:
        stmt = select(Supplier.code).where(Supplier.code.like(f"{prefix}%"))
        res = await db.execute(stmt)
        codes = res.scalars().all()
        max_num = 0
        for code in codes:
            suffix = code[len(prefix):]
            if suffix.isdigit():
                num = int(suffix)
                if num > max_num:
                    max_num = num
        return max_num

    async def has_active_dependencies(self, db: AsyncSession, supplier_id: uuid.UUID) -> bool:
        # Check Purchase Orders
        po_stmt = select(func.count()).select_from(PurchaseOrder).where(PurchaseOrder.supplier_id == supplier_id)
        po_count = (await db.execute(po_stmt)).scalar() or 0
        if po_count > 0:
            return True

        # Check RFQ invitations
        rfq_stmt = select(func.count()).select_from(RFQSupplier).where(RFQSupplier.supplier_id == supplier_id)
        rfq_count = (await db.execute(rfq_stmt)).scalar() or 0
        if rfq_count > 0:
            return True

        # Check Supplier Quotations
        sq_stmt = select(func.count()).select_from(SupplierQuotation).where(SupplierQuotation.supplier_id == supplier_id)
        sq_count = (await db.execute(sq_stmt)).scalar() or 0
        if sq_count > 0:
            return True

        # Check Purchase Returns
        pr_stmt = select(func.count()).select_from(PurchaseReturn).where(PurchaseReturn.supplier_id == supplier_id)
        pr_count = (await db.execute(pr_stmt)).scalar() or 0
        if pr_count > 0:
            return True

        return False


class SupplierContactRepository(BaseRepository[SupplierContact, SupplierContactCreate, Any]):
    def __init__(self):
        super().__init__(SupplierContact)

    async def get_by_supplier(self, db: AsyncSession, supplier_id: uuid.UUID) -> List[SupplierContact]:
        stmt = select(SupplierContact).where(SupplierContact.supplier_id == supplier_id).order_by(SupplierContact.created_at.asc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_primary_contact(self, db: AsyncSession, supplier_id: uuid.UUID) -> Optional[SupplierContact]:
        stmt = select(SupplierContact).where(
            and_(SupplierContact.supplier_id == supplier_id, SupplierContact.is_primary == True)
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def clear_primary_contacts(
        self, db: AsyncSession, supplier_id: uuid.UUID, exclude_contact_id: Optional[uuid.UUID] = None
    ) -> None:
        stmt = select(SupplierContact).where(
            and_(SupplierContact.supplier_id == supplier_id, SupplierContact.is_primary == True)
        )
        if exclude_contact_id:
            stmt = stmt.where(SupplierContact.id != exclude_contact_id)
        res = await db.execute(stmt)
        contacts = res.scalars().all()
        for contact in contacts:
            contact.is_primary = False
            db.add(contact)


class SupplierAddressRepository(BaseRepository[SupplierAddress, SupplierAddressCreate, Any]):
    def __init__(self):
        super().__init__(SupplierAddress)

    async def get_by_supplier(self, db: AsyncSession, supplier_id: uuid.UUID) -> List[SupplierAddress]:
        stmt = select(SupplierAddress).where(SupplierAddress.supplier_id == supplier_id).order_by(SupplierAddress.created_at.asc())
        res = await db.execute(stmt)
        return list(res.scalars().all())


class SupplierDocumentRepository(BaseRepository[SupplierDocument, SupplierDocumentCreate, Any]):
    def __init__(self):
        super().__init__(SupplierDocument)

    async def get_by_supplier(self, db: AsyncSession, supplier_id: uuid.UUID) -> List[SupplierDocument]:
        stmt = (
            select(SupplierDocument)
            .options(selectinload(SupplierDocument.file))
            .where(SupplierDocument.supplier_id == supplier_id)
            .order_by(SupplierDocument.created_at.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


class SupplierRatingRepository(BaseRepository[SupplierRating, SupplierRatingCreate, Any]):
    def __init__(self):
        super().__init__(SupplierRating)

    async def get_by_supplier(self, db: AsyncSession, supplier_id: uuid.UUID) -> List[SupplierRating]:
        stmt = (
            select(SupplierRating)
            .options(selectinload(SupplierRating.reviewer))
            .where(SupplierRating.supplier_id == supplier_id)
            .order_by(SupplierRating.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def calculate_average_rating(self, db: AsyncSession, supplier_id: uuid.UUID) -> Optional[Decimal]:
        stmt = select(func.avg(SupplierRating.score)).where(SupplierRating.supplier_id == supplier_id)
        res = await db.execute(stmt)
        avg_score = res.scalar()
        if avg_score is not None:
            return Decimal(str(round(avg_score, 2)))
        return None


class PurchaseRequisitionRepository(
    BaseRepository[PurchaseRequisition, PurchaseRequisitionCreate, PurchaseRequisitionUpdate]
):
    def __init__(self):
        super().__init__(PurchaseRequisition)

    async def get_by_number(self, db: AsyncSession, requisition_number: str) -> Optional[PurchaseRequisition]:
        stmt = (
            select(PurchaseRequisition)
            .options(selectinload(PurchaseRequisition.items))
            .where(PurchaseRequisition.requisition_number == requisition_number)
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        department_id: Optional[uuid.UUID] = None,
        requester_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[PurchaseRequisition], int]:
        stmt = select(PurchaseRequisition).options(selectinload(PurchaseRequisition.items))

        if department_id:
            stmt = stmt.where(PurchaseRequisition.department_id == department_id)
        if requester_id:
            stmt = stmt.where(PurchaseRequisition.requester_id == requester_id)
        if status:
            stmt = stmt.where(PurchaseRequisition.status == status)
        if priority:
            stmt = stmt.where(PurchaseRequisition.priority == priority)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(PurchaseRequisition.created_at.desc()).offset(skip).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class RFQRepository(BaseRepository[RFQ, RFQCreate, RFQUpdate]):
    def __init__(self):
        super().__init__(RFQ)

    async def get_by_number(self, db: AsyncSession, rfq_number: str) -> Optional[RFQ]:
        stmt = (
            select(RFQ)
            .options(
                selectinload(RFQ.invited_suppliers),
                selectinload(RFQ.quotations),
            )
            .where(RFQ.rfq_number == rfq_number)
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[RFQ], int]:
        stmt = select(RFQ).options(selectinload(RFQ.invited_suppliers), selectinload(RFQ.quotations))

        if status:
            stmt = stmt.where(RFQ.status == status)
        if search:
            stmt = stmt.where(or_(RFQ.rfq_number.ilike(f"%{search}%"), RFQ.title.ilike(f"%{search}%")))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(RFQ.created_at.desc()).offset(skip).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class RFQSupplierRepository(BaseRepository[RFQSupplier, Any, Any]):
    def __init__(self):
        super().__init__(RFQSupplier)


class SupplierQuotationRepository(
    BaseRepository[SupplierQuotation, SupplierQuotationCreate, SupplierQuotationUpdate]
):
    def __init__(self):
        super().__init__(SupplierQuotation)

    async def get_by_number(self, db: AsyncSession, quotation_number: str) -> Optional[SupplierQuotation]:
        stmt = (
            select(SupplierQuotation)
            .options(selectinload(SupplierQuotation.items))
            .where(SupplierQuotation.quotation_number == quotation_number)
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        rfq_id: Optional[uuid.UUID] = None,
        supplier_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SupplierQuotation], int]:
        stmt = select(SupplierQuotation).options(selectinload(SupplierQuotation.items))

        if rfq_id:
            stmt = stmt.where(SupplierQuotation.rfq_id == rfq_id)
        if supplier_id:
            stmt = stmt.where(SupplierQuotation.supplier_id == supplier_id)
        if status:
            stmt = stmt.where(SupplierQuotation.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(SupplierQuotation.created_at.desc()).offset(skip).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class PurchaseOrderRepository(BaseRepository[PurchaseOrder, PurchaseOrderCreate, PurchaseOrderUpdate]):
    def __init__(self):
        super().__init__(PurchaseOrder)

    async def get_by_number(self, db: AsyncSession, po_number: str) -> Optional[PurchaseOrder]:
        stmt = (
            select(PurchaseOrder)
            .options(selectinload(PurchaseOrder.items))
            .where(PurchaseOrder.po_number == po_number)
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        supplier_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        origin_type: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[PurchaseOrder], int]:
        stmt = select(PurchaseOrder).options(selectinload(PurchaseOrder.items))

        if supplier_id:
            stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
        if status:
            stmt = stmt.where(PurchaseOrder.status == status)
        if origin_type:
            stmt = stmt.where(PurchaseOrder.origin_type == origin_type)
        if search:
            stmt = stmt.where(PurchaseOrder.po_number.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(PurchaseOrder.created_at.desc()).offset(skip).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class PurchaseReturnRepository(BaseRepository[PurchaseReturn, PurchaseReturnCreate, Any]):
    def __init__(self):
        super().__init__(PurchaseReturn)

    async def get_by_number(self, db: AsyncSession, return_number: str) -> Optional[PurchaseReturn]:
        stmt = (
            select(PurchaseReturn)
            .options(selectinload(PurchaseReturn.items))
            .where(PurchaseReturn.return_number == return_number)
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        supplier_id: Optional[uuid.UUID] = None,
        purchase_order_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[PurchaseReturn], int]:
        stmt = select(PurchaseReturn).options(selectinload(PurchaseReturn.items))

        if supplier_id:
            stmt = stmt.where(PurchaseReturn.supplier_id == supplier_id)
        if purchase_order_id:
            stmt = stmt.where(PurchaseReturn.purchase_order_id == purchase_order_id)
        if status:
            stmt = stmt.where(PurchaseReturn.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(PurchaseReturn.created_at.desc()).offset(skip).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class ProcurementReportSnapshotRepository(BaseRepository[ProcurementReportSnapshot, Any, Any]):
    def __init__(self):
        super().__init__(ProcurementReportSnapshot)

    async def get_latest_snapshot(self, db: AsyncSession) -> Optional[ProcurementReportSnapshot]:
        stmt = select(ProcurementReportSnapshot).order_by(ProcurementReportSnapshot.snapshot_date.desc()).limit(1)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()


# Singleton repository instances
supplier_category_repository = SupplierCategoryRepository()
supplier_repository = SupplierRepository()
supplier_contact_repository = SupplierContactRepository()
supplier_address_repository = SupplierAddressRepository()
supplier_document_repository = SupplierDocumentRepository()
supplier_rating_repository = SupplierRatingRepository()
purchase_requisition_repository = PurchaseRequisitionRepository()
rfq_repository = RFQRepository()
rfq_supplier_repository = RFQSupplierRepository()
supplier_quotation_repository = SupplierQuotationRepository()
purchase_order_repository = PurchaseOrderRepository()
purchase_return_repository = PurchaseReturnRepository()
procurement_report_snapshot_repository = ProcurementReportSnapshotRepository()
