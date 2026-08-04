from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_events import domain_event_publisher
from app.core.redis import redis_manager
from app.exceptions.base import (
    NotFoundException,
    ValidationException,
)
from app.models.purchase_requisition import (
    PurchaseRequisition,
    PurchaseRequisitionItem,
)
from app.repositories.inventory_repos import product_repository
from app.repositories.procurement_repos import purchase_requisition_repository
from app.schemas.procurement import (
    PurchaseRequisitionCreate,
    PurchaseRequisitionUpdate,
)
from app.services.approval_engine import ApprovalEngineService
from app.services.audit_log import audit_log_service

logger = logging.getLogger("app.services.purchase_requisition")


class PurchaseRequisitionService:
    """
    Domain service for Purchase Requisition management, submission, approval engine integration, cancellation, and fulfillment tracking.
    """
    async def create_requisition(
        self, db: AsyncSession, obj_in: PurchaseRequisitionCreate, requester_id: uuid.UUID
    ) -> PurchaseRequisition:
        # Generate Requisition Number (PR-YYYY-XXXXX)
        count = (await purchase_requisition_repository.get_multi_paginated(db, limit=1))[1] + 1
        req_num = f"PR-{datetime.now().year}-{count:05d}"

        tot_est = Decimal("0.0")
        items: List[PurchaseRequisitionItem] = []

        for item_in in obj_in.items:
            product = await product_repository.get_by_id(db, item_in.product_id)
            if not product:
                raise NotFoundException(f"Product with ID '{item_in.product_id}' not found.")

            line_tot = Decimal(str(item_in.quantity)) * Decimal(str(item_in.estimated_unit_price))
            tot_est += line_tot

            items.append(
                PurchaseRequisitionItem(
                    product_id=item_in.product_id,
                    quantity=Decimal(str(item_in.quantity)),
                    estimated_unit_price=Decimal(str(item_in.estimated_unit_price)),
                    required_date=item_in.required_date or obj_in.required_date,
                    status="Pending",
                )
            )

        requisition = PurchaseRequisition(
            requisition_number=req_num,
            requester_id=requester_id,
            department_id=obj_in.department_id,
            required_date=obj_in.required_date,
            priority=obj_in.priority,
            status="Draft",
            total_estimated_amount=tot_est,
            remarks=obj_in.remarks,
            items=items,
        )
        db.add(requisition)
        await db.commit()
        await db.refresh(requisition)

        await audit_log_service.log_event(
            db,
            action="PURCHASE_REQUISITION_CREATE",
            entity_type="PurchaseRequisition",
            entity_id=requisition.id,
            user_id=requester_id,
        )
        return requisition

    async def get_requisition(self, db: AsyncSession, requisition_id: uuid.UUID) -> PurchaseRequisition:
        pr = await purchase_requisition_repository.get_by_id(db, requisition_id)
        if not pr:
            raise NotFoundException(f"Purchase Requisition with ID '{requisition_id}' not found.")
        return pr

    async def submit_requisition(
        self, db: AsyncSession, requisition_id: uuid.UUID, requester_id: uuid.UUID
    ) -> PurchaseRequisition:
        pr = await self.get_requisition(db, requisition_id)
        if pr.status not in ("Draft", "Rejected"):
            raise ValidationException(f"Only Draft or Rejected requisitions can be submitted. Current status: '{pr.status}'.")

        pr.status = "Submitted"
        await db.commit()

        # Submit to ApprovalEngineService if configured
        try:
            approval_service = ApprovalEngineService(db)
            await approval_service.submit_request(
                module_name="purchase_requisition",
                entity_type="PurchaseRequisition",
                entity_id=pr.id,
                requester_id=requester_id,
                title=f"Purchase Requisition #{pr.requisition_number}",
            )
        except Exception as exc:
            logger.info(f"No active approval workflow for purchase_requisition or auto-approved: {exc}")
            # Auto-approve if no explicit workflow exists
            pr.status = "Approved"
            await db.commit()

        await db.refresh(pr)

        # Publish Domain Event
        domain_event_publisher.publish(
            "PurchaseRequisitionSubmitted",
            {
                "requisition_id": str(pr.id),
                "requisition_number": pr.requisition_number,
                "requester_id": str(pr.requester_id),
                "total_estimated_amount": float(pr.total_estimated_amount),
            },
        )

        await redis_manager.delete_pattern("requisition:*")
        return pr

    async def approve_requisition(
        self, db: AsyncSession, requisition_id: uuid.UUID, approver_id: Optional[uuid.UUID] = None
    ) -> PurchaseRequisition:
        pr = await self.get_requisition(db, requisition_id)
        if pr.status in ("Approved", "Cancelled", "Fulfilled"):
            raise ValidationException(f"Requisition is already in terminal/approved state '{pr.status}'.")

        pr.status = "Approved"
        await db.commit()
        await db.refresh(pr)
        await redis_manager.delete_pattern("requisition:*")
        return pr

    async def reject_requisition(
        self, db: AsyncSession, requisition_id: uuid.UUID, reason: Optional[str] = None
    ) -> PurchaseRequisition:
        pr = await self.get_requisition(db, requisition_id)
        pr.status = "Rejected"
        if reason:
            pr.remarks = (pr.remarks or "") + f"\n[Rejected]: {reason}"
        await db.commit()
        await db.refresh(pr)
        await redis_manager.delete_pattern("requisition:*")
        return pr

    async def cancel_requisition(
        self, db: AsyncSession, requisition_id: uuid.UUID, user_id: Optional[uuid.UUID] = None
    ) -> PurchaseRequisition:
        pr = await self.get_requisition(db, requisition_id)
        if pr.status in ("Fulfilled", "Cancelled"):
            raise ValidationException(f"Cannot cancel requisition in state '{pr.status}'.")

        pr.status = "Cancelled"
        for item in pr.items:
            item.status = "Cancelled"

        await db.commit()
        await db.refresh(pr)
        await redis_manager.delete_pattern("requisition:*")
        return pr

    async def list_requisitions(
        self,
        db: AsyncSession,
        department_id: Optional[uuid.UUID] = None,
        requester_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[PurchaseRequisition], int]:
        return await purchase_requisition_repository.get_multi_paginated(
            db,
            department_id=department_id,
            requester_id=requester_id,
            status=status,
            priority=priority,
            skip=skip,
            limit=limit,
        )


purchase_requisition_service = PurchaseRequisitionService()
