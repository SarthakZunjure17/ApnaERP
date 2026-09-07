from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import List, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_events import domain_event_publisher
from app.core.redis import redis_manager
from app.exceptions.base import (
    ApnaERPException,
    NotFoundException,
    ValidationException,
)
from app.models.purchase_requisition import (
    PurchaseRequisition,
    PurchaseRequisitionItem,
)
from app.repositories.department import department_repository
from app.repositories.inventory_repos import product_repository
from app.repositories.procurement_repos import purchase_requisition_repository
from app.repositories.user import user_repository
from app.schemas.approval_workflow import ApprovalRequestCreate
from app.schemas.procurement import (
    PurchaseRequisitionCreate,
    PurchaseRequisitionUpdate,
)
from app.services.approval_engine import ApprovalEngineService
from app.services.audit_log import audit_log_service

logger = logging.getLogger("app.services.purchase_requisition")


class PurchaseRequisitionService:
    """
    Domain service for Purchase Requisition management, line item validation, Draft updates,
    canonical Approval Engine workflow integration, cancellation, and fulfillment tracking.
    """

    async def _generate_requisition_number(self, db: AsyncSession) -> str:
        year = datetime.now(timezone.utc).year
        max_num = await purchase_requisition_repository.get_max_number_suffix(db, year)
        return f"PR-{year}-{max_num + 1:05d}"

    async def create_requisition(
        self, db: AsyncSession, obj_in: PurchaseRequisitionCreate, requester_id: uuid.UUID
    ) -> PurchaseRequisition:
        # 1. Validate Requester
        requester = await user_repository.get_by_id(db, requester_id)
        if not requester or not requester.is_active:
            raise NotFoundException(f"Requester User with ID '{requester_id}' not found or inactive.")

        # 2. Validate Department if provided
        if obj_in.department_id:
            dept = await department_repository.get_by_id(db, obj_in.department_id)
            if not dept or dept.is_deleted:
                raise NotFoundException(f"Department with ID '{obj_in.department_id}' not found.")

        # 3. Validate items
        if not obj_in.items:
            raise ValidationException("Purchase requisition must contain at least one line item.")

        req_num = await self._generate_requisition_number(db)
        tot_est = Decimal("0.0")
        items: List[PurchaseRequisitionItem] = []

        for item_in in obj_in.items:
            product = await product_repository.get_by_id(db, item_in.product_id)
            if not product:
                raise NotFoundException(f"Product with ID '{item_in.product_id}' not found.")
            if not product.is_active:
                raise ValidationException(f"Product '{product.name}' is inactive.")

            qty = Decimal(str(item_in.quantity))
            if qty <= 0:
                raise ValidationException("Item quantity must be greater than 0.")

            price = Decimal(str(item_in.estimated_unit_price or 0))
            if price < 0:
                raise ValidationException("Estimated unit price cannot be negative.")

            line_tot = qty * price
            tot_est += line_tot

            items.append(
                PurchaseRequisitionItem(
                    product_id=item_in.product_id,
                    quantity=qty,
                    estimated_unit_price=price,
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
            new_data={"requisition_number": req_num, "total_estimated_amount": float(tot_est)},
        )
        return await self.get_requisition(db, requisition.id)

    async def get_requisition(self, db: AsyncSession, requisition_id: uuid.UUID) -> PurchaseRequisition:
        pr = await purchase_requisition_repository.get_by_id(db, requisition_id)
        if not pr:
            raise NotFoundException(f"Purchase Requisition with ID '{requisition_id}' not found.")
        return pr

    async def update_requisition(
        self,
        db: AsyncSession,
        requisition_id: uuid.UUID,
        obj_in: PurchaseRequisitionUpdate,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> PurchaseRequisition:
        pr = await self.get_requisition(db, requisition_id)
        if pr.status != "Draft":
            raise ValidationException(f"Only Draft purchase requisitions can be updated. Current status: '{pr.status}'.")

        if obj_in.department_id is not None:
            dept = await department_repository.get_by_id(db, obj_in.department_id)
            if not dept or dept.is_deleted:
                raise NotFoundException(f"Department with ID '{obj_in.department_id}' not found.")
            pr.department_id = obj_in.department_id

        if obj_in.required_date is not None:
            pr.required_date = obj_in.required_date
        if obj_in.priority is not None:
            pr.priority = obj_in.priority
        if obj_in.remarks is not None:
            pr.remarks = obj_in.remarks

        await db.commit()
        await db.refresh(pr)

        await audit_log_service.log_event(
            db,
            action="PURCHASE_REQUISITION_UPDATE",
            entity_type="PurchaseRequisition",
            entity_id=pr.id,
            user_id=current_user_id,
        )
        return await self.get_requisition(db, pr.id)

    async def submit_requisition(
        self, db: AsyncSession, requisition_id: uuid.UUID, requester_id: uuid.UUID
    ) -> PurchaseRequisition:
        pr = await self.get_requisition(db, requisition_id)
        if pr.status not in ("Draft", "Rejected"):
            raise ValidationException(f"Only Draft or Rejected requisitions can be submitted. Current status: '{pr.status}'.")

        pr.status = "Submitted"
        await db.commit()

        # Submit to ApprovalEngineService via canonical start_workflow
        requester_user = await user_repository.get_by_id(db, requester_id)
        if requester_user:
            try:
                approval_service = ApprovalEngineService(db)
                req_create = ApprovalRequestCreate(
                    workflow_code="WF_PURCHASE_REQUISITION",
                    entity_type="PurchaseRequisition",
                    entity_id=str(pr.id),
                    comments=f"Purchase Requisition #{pr.requisition_number}",
                )
                await approval_service.start_workflow(
                    data=req_create,
                    current_user=requester_user,
                )
            except ApnaERPException as exc:
                if exc.error_code == "WORKFLOW_NOT_FOUND":
                    logger.info("No active approval workflow configured for WF_PURCHASE_REQUISITION. Requisition remains Submitted.")
                elif exc.error_code == "DUPLICATE_APPROVAL_REQUEST":
                    logger.warning(f"Duplicate approval request for PR {pr.id}: {exc}")
                else:
                    logger.error(f"Approval workflow startup returned error: {exc}")
            except Exception as exc:
                logger.error(f"Failed to start approval workflow: {exc}")

        await db.refresh(pr)

        # Audit Log
        await audit_log_service.log_event(
            db,
            action="PURCHASE_REQUISITION_SUBMIT",
            entity_type="PurchaseRequisition",
            entity_id=pr.id,
            user_id=requester_id,
        )

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
        return await self.get_requisition(db, pr.id)

    async def approve_requisition(
        self, db: AsyncSession, requisition_id: uuid.UUID, approver_id: Optional[uuid.UUID] = None
    ) -> PurchaseRequisition:
        pr = await self.get_requisition(db, requisition_id)
        if pr.status in ("Approved", "Cancelled", "Fulfilled"):
            raise ValidationException(f"Requisition is already in terminal/approved state '{pr.status}'.")

        pr.status = "Approved"
        await db.commit()
        await db.refresh(pr)

        await audit_log_service.log_event(
            db,
            action="PURCHASE_REQUISITION_APPROVE",
            entity_type="PurchaseRequisition",
            entity_id=pr.id,
            user_id=approver_id,
        )

        await redis_manager.delete_pattern("requisition:*")
        return await self.get_requisition(db, pr.id)

    async def reject_requisition(
        self, db: AsyncSession, requisition_id: uuid.UUID, reason: Optional[str] = None, current_user_id: Optional[uuid.UUID] = None
    ) -> PurchaseRequisition:
        pr = await self.get_requisition(db, requisition_id)
        if pr.status in ("Approved", "Cancelled", "Fulfilled"):
            raise ValidationException(f"Cannot reject requisition in status '{pr.status}'.")

        pr.status = "Rejected"
        if reason:
            pr.remarks = (pr.remarks or "") + f"\n[Rejected]: {reason}"
        await db.commit()
        await db.refresh(pr)

        await audit_log_service.log_event(
            db,
            action="PURCHASE_REQUISITION_REJECT",
            entity_type="PurchaseRequisition",
            entity_id=pr.id,
            user_id=current_user_id,
        )

        await redis_manager.delete_pattern("requisition:*")
        return await self.get_requisition(db, pr.id)

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

        await audit_log_service.log_event(
            db,
            action="PURCHASE_REQUISITION_CANCEL",
            entity_type="PurchaseRequisition",
            entity_id=pr.id,
            user_id=user_id,
        )

        await redis_manager.delete_pattern("requisition:*")
        return await self.get_requisition(db, pr.id)

    async def list_requisitions(
        self,
        db: AsyncSession,
        department_id: Optional[uuid.UUID] = None,
        requester_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[PurchaseRequisition], int]:
        return await purchase_requisition_repository.get_multi_paginated(
            db,
            department_id=department_id,
            requester_id=requester_id,
            status=status,
            priority=priority,
            search=search,
            skip=skip,
            limit=limit,
        )


purchase_requisition_service = PurchaseRequisitionService()
