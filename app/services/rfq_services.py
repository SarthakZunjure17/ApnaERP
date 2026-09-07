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
    Domain service for managing RFQs (Requests For Quotations), inviting suppliers, issuing RFQs,
    generating Quotation Comparison Matrices, and explicit quotation award.
    """

    async def _generate_rfq_number(self, db: AsyncSession) -> str:
        year = datetime.now(timezone.utc).year
        max_num = await rfq_repository.get_max_number_suffix(db, year)
        return f"RFQ-{year}-{max_num + 1:05d}"

    async def create_rfq(
        self, db: AsyncSession, obj_in: RFQCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> RFQ:
        if obj_in.requisition_id:
            pr = await purchase_requisition_repository.get_by_id(db, obj_in.requisition_id)
            if not pr:
                raise NotFoundException(f"Purchase Requisition with ID '{obj_in.requisition_id}' not found.")

        rfq_num = await self._generate_rfq_number(db)

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
                if supplier and not supplier.is_deleted and supplier.status == "Active":
                    existing_invite = await rfq_supplier_repository.get_by_rfq_and_supplier(db, rfq.id, s_id)
                    if not existing_invite:
                        db.add(RFQSupplier(rfq_id=rfq.id, supplier_id=s_id, status="Invited"))

        await db.commit()
        await db.refresh(rfq)

        await audit_log_service.log_event(
            db,
            action="RFQ_CREATE",
            entity_type="RFQ",
            entity_id=rfq.id,
            user_id=current_user_id,
            new_data={"rfq_number": rfq_num, "title": rfq.title},
        )
        return await self.get_rfq(db, rfq.id)

    async def get_rfq(self, db: AsyncSession, rfq_id: uuid.UUID) -> RFQ:
        rfq = await rfq_repository.get_by_id(db, rfq_id)
        if not rfq:
            raise NotFoundException(f"RFQ with ID '{rfq_id}' not found.")
        return rfq

    async def update_rfq(
        self,
        db: AsyncSession,
        rfq_id: uuid.UUID,
        obj_in: RFQUpdate,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> RFQ:
        rfq = await self.get_rfq(db, rfq_id)
        if rfq.status != "Draft":
            raise ValidationException(f"Only Draft RFQs can be updated. Current status: '{rfq.status}'.")

        if obj_in.title is not None:
            rfq.title = obj_in.title
        if obj_in.submission_deadline is not None:
            rfq.submission_deadline = obj_in.submission_deadline
        if obj_in.terms_and_conditions is not None:
            rfq.terms_and_conditions = obj_in.terms_and_conditions
        if obj_in.notes is not None:
            rfq.notes = obj_in.notes

        await db.commit()
        await db.refresh(rfq)

        await audit_log_service.log_event(
            db,
            action="RFQ_UPDATE",
            entity_type="RFQ",
            entity_id=rfq.id,
            user_id=current_user_id,
        )
        return await self.get_rfq(db, rfq.id)

    async def issue_rfq(
        self, db: AsyncSession, rfq_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> RFQ:
        rfq = await self.get_rfq(db, rfq_id)
        if rfq.status != "Draft":
            raise ValidationException(f"Only Draft RFQs can be issued. Current status: '{rfq.status}'.")

        rfq.status = "Issued"
        await db.commit()
        await db.refresh(rfq)

        await audit_log_service.log_event(
            db,
            action="RFQ_ISSUE",
            entity_type="RFQ",
            entity_id=rfq.id,
            user_id=current_user_id,
        )

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
        return await self.get_rfq(db, rfq.id)

    async def cancel_rfq(
        self, db: AsyncSession, rfq_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> RFQ:
        rfq = await self.get_rfq(db, rfq_id)
        if rfq.status in ("Closed", "Cancelled"):
            raise ValidationException(f"Cannot cancel RFQ in status '{rfq.status}'.")

        rfq.status = "Cancelled"
        await db.commit()
        await db.refresh(rfq)

        await audit_log_service.log_event(
            db,
            action="RFQ_CANCEL",
            entity_type="RFQ",
            entity_id=rfq.id,
            user_id=current_user_id,
        )

        await redis_manager.delete_pattern("rfq:*")
        return await self.get_rfq(db, rfq.id)

    async def invite_supplier(
        self, db: AsyncSession, rfq_id: uuid.UUID, supplier_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> RFQSupplier:
        rfq = await self.get_rfq(db, rfq_id)
        if rfq.status not in ("Draft", "Issued"):
            raise ValidationException(f"Cannot invite suppliers to RFQ in status '{rfq.status}'.")

        supplier = await supplier_repository.get_by_id(db, supplier_id)
        if not supplier or supplier.is_deleted:
            raise NotFoundException(f"Supplier with ID '{supplier_id}' not found.")
        if supplier.status != "Active":
            raise ValidationException(f"Cannot invite supplier in '{supplier.status}' status. Supplier must be Active.")

        existing = await rfq_supplier_repository.get_by_rfq_and_supplier(db, rfq.id, supplier_id)
        if existing:
            raise ValidationException("Supplier is already invited to this RFQ.")

        invite = RFQSupplier(rfq_id=rfq.id, supplier_id=supplier_id, status="Invited")
        db.add(invite)
        await db.commit()
        await db.refresh(invite)

        await audit_log_service.log_event(
            db,
            action="RFQ_SUPPLIER_INVITED",
            entity_type="RFQSupplier",
            entity_id=invite.id,
            user_id=current_user_id,
            new_data={"rfq_id": str(rfq.id), "supplier_id": str(supplier_id)},
        )

        return invite

    async def remove_supplier(
        self, db: AsyncSession, rfq_id: uuid.UUID, supplier_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> None:
        rfq = await self.get_rfq(db, rfq_id)
        if rfq.status != "Draft":
            raise ValidationException("Cannot remove invited suppliers from a non-Draft RFQ.")

        invite = await rfq_supplier_repository.get_by_rfq_and_supplier(db, rfq.id, supplier_id)
        if not invite:
            raise NotFoundException(f"Supplier invitation for supplier '{supplier_id}' not found in RFQ.")

        await db.delete(invite)
        await db.commit()

    async def list_invited_suppliers(self, db: AsyncSession, rfq_id: uuid.UUID) -> List[RFQSupplier]:
        rfq = await self.get_rfq(db, rfq_id)
        return await rfq_supplier_repository.get_by_rfq(db, rfq.id)

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

        # Deterministic sort: total_amount ascending
        matrix_items.sort(key=lambda x: x["total_amount"])

        return RFQComparisonMatrix(
            rfq_id=rfq.id,
            rfq_number=rfq.rfq_number,
            title=rfq.title,
            quotations_count=len(quotations),
            comparison_items=matrix_items,
        )

    async def award_quotation(
        self,
        db: AsyncSession,
        rfq_id: uuid.UUID,
        quotation_id: uuid.UUID,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> RFQ:
        rfq = await self.get_rfq(db, rfq_id)
        if rfq.status in ("Closed", "Cancelled"):
            raise ValidationException(f"Cannot award quotation for RFQ in '{rfq.status}' status.")

        quotation = await supplier_quotation_repository.get_by_id(db, quotation_id)
        if not quotation:
            raise NotFoundException(f"Supplier Quotation with ID '{quotation_id}' not found.")
        if quotation.rfq_id != rfq.id:
            raise ValidationException(f"Supplier Quotation '{quotation.quotation_number}' does not belong to RFQ '{rfq.rfq_number}'.")
        if quotation.status not in ("Draft", "Submitted", "Under Review"):
            raise ValidationException(f"Cannot award quotation in '{quotation.status}' status.")

        # Update winning quotation
        quotation.status = "Approved"

        # Update other quotations belonging to this RFQ to Rejected
        all_quotations, _ = await supplier_quotation_repository.get_multi_paginated(db, rfq_id=rfq.id, limit=200)
        for other_q in all_quotations:
            if other_q.id != quotation.id and other_q.status in ("Draft", "Submitted", "Under Review"):
                other_q.status = "Rejected"

        # Close the RFQ (sourcing completed)
        rfq.status = "Closed"

        await db.commit()
        await db.refresh(rfq)

        # Audit event
        await audit_log_service.log_event(
            db,
            action="SUPPLIER_QUOTATION_AWARD",
            entity_type="RFQ",
            entity_id=rfq.id,
            user_id=current_user_id,
            new_data={"winning_quotation_id": str(quotation.id), "winning_quotation_number": quotation.quotation_number},
        )

        await redis_manager.delete_pattern("rfq:*")
        return await self.get_rfq(db, rfq.id)

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
