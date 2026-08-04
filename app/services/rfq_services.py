from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_events import domain_event_publisher
from app.core.redis import redis_manager
from app.exceptions.base import (
    NotFoundException,
    ValidationException,
)
from app.models.rfq import RFQ, RFQSupplier
from app.repositories.procurement_repos import (
    purchase_requisition_repository,
    rfq_repository,
    rfq_supplier_repository,
    supplier_quotation_repository,
    supplier_repository,
)
from app.schemas.procurement import RFQComparisonMatrix, RFQCreate, RFQUpdate
from app.services.audit_log import audit_log_service

logger = logging.getLogger("app.services.rfq")


class RFQService:
    """
    Domain service for managing RFQs (Requests For Quotations), inviting suppliers, issuing RFQs, and generating Quotation Comparison Matrices.
    """
    async def create_rfq(
        self, db: AsyncSession, obj_in: RFQCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> RFQ:
        if obj_in.requisition_id:
            pr = await purchase_requisition_repository.get_by_id(db, obj_in.requisition_id)
            if not pr:
                raise NotFoundException(f"Purchase Requisition with ID '{obj_in.requisition_id}' not found.")

        # Generate RFQ Number (RFQ-YYYY-XXXXX)
        count = (await rfq_repository.get_multi_paginated(db, limit=1))[1] + 1
        rfq_num = f"RFQ-{datetime.now().year}-{count:05d}"

        rfq = RFQ(
            rfq_number=rfq_num,
            title=obj_in.title,
            requisition_id=obj_in.requisition_id,
            submission_deadline=obj_in.submission_deadline,
            status="Draft",
            terms_and_conditions=obj_in.terms_and_conditions,
            notes=obj_in.notes,
        )
        db.add(rfq)
        await db.flush()

        # Add invited suppliers if provided
        if obj_in.supplier_ids:
            for s_id in obj_in.supplier_ids:
                supplier = await supplier_repository.get_by_id(db, s_id)
                if supplier and not supplier.is_deleted and supplier.status != "Blacklisted":
                    db.add(RFQSupplier(rfq_id=rfq.id, supplier_id=s_id, status="Invited"))

        await db.commit()
        await db.refresh(rfq)

        await audit_log_service.log_event(
            db,
            action="RFQ_CREATE",
            entity_type="RFQ",
            entity_id=rfq.id,
            user_id=current_user_id,
        )
        return rfq

    async def get_rfq(self, db: AsyncSession, rfq_id: uuid.UUID) -> RFQ:
        rfq = await rfq_repository.get_by_id(db, rfq_id)
        if not rfq:
            raise NotFoundException(f"RFQ with ID '{rfq_id}' not found.")
        return rfq

    async def issue_rfq(
        self, db: AsyncSession, rfq_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> RFQ:
        rfq = await self.get_rfq(db, rfq_id)
        if rfq.status != "Draft":
            raise ValidationException(f"Only Draft RFQs can be issued. Current status: '{rfq.status}'.")

        rfq.status = "Issued"
        await db.commit()
        await db.refresh(rfq)

        # Publish Domain Event
        domain_event_publisher.publish(
            "RFQIssued",
            {
                "rfq_id": str(rfq.id),
                "rfq_number": rfq.rfq_number,
                "title": rfq.title,
                "submission_deadline": rfq.submission_deadline.isoformat(),
            },
        )

        await redis_manager.delete_pattern("rfq:*")
        return rfq

    async def invite_supplier(
        self, db: AsyncSession, rfq_id: uuid.UUID, supplier_id: uuid.UUID
    ) -> RFQSupplier:
        rfq = await self.get_rfq(db, rfq_id)
        supplier = await supplier_repository.get_by_id(db, supplier_id)
        if not supplier or supplier.is_deleted or supplier.status == "Blacklisted":
            raise ValidationException("Cannot invite inactive or blacklisted supplier.")

        invite = RFQSupplier(rfq_id=rfq.id, supplier_id=supplier_id, status="Invited")
        db.add(invite)
        await db.commit()
        await db.refresh(invite)
        return invite

    async def get_comparison_matrix(self, db: AsyncSession, rfq_id: uuid.UUID) -> RFQComparisonMatrix:
        rfq = await self.get_rfq(db, rfq_id)
        quotations, _ = await supplier_quotation_repository.get_multi_paginated(db, rfq_id=rfq_id, limit=100)

        matrix_items: List[Dict[str, Any]] = []
        for q in quotations:
            supplier = await supplier_repository.get_by_id(db, q.supplier_id)
            matrix_items.append(
                {
                    "quotation_id": str(q.id),
                    "quotation_number": q.quotation_number,
                    "supplier_id": str(q.supplier_id),
                    "supplier_name": supplier.name if supplier else "Unknown",
                    "supplier_code": supplier.code if supplier else "",
                    "supplier_rating": float(supplier.rating) if supplier else 0.0,
                    "total_amount": float(q.total_amount),
                    "currency": q.currency,
                    "lead_time_days": q.lead_time_days,
                    "validity_date": q.validity_date.isoformat(),
                    "payment_terms": q.payment_terms,
                    "status": q.status,
                    "items_count": len(q.items),
                }
            )

        # Sort matrix items by total_amount ascending (lowest price first)
        matrix_items.sort(key=lambda x: x["total_amount"])

        return RFQComparisonMatrix(
            rfq_id=rfq.id,
            rfq_number=rfq.rfq_number,
            title=rfq.title,
            quotations_count=len(quotations),
            comparison_items=matrix_items,
        )

    async def list_rfqs(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[RFQ], int]:
        return await rfq_repository.get_multi_paginated(db, status=status, search=search, skip=skip, limit=limit)


rfq_service = RFQService()
