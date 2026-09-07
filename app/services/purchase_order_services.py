from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.domain_events import domain_event_publisher
from app.core.redis import redis_manager
from app.exceptions.base import (
    NotFoundException,
    ValidationException,
)
from app.models.goods_receipt import GoodsReceipt, GoodsReceiptItem
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.user import User
from app.repositories.inventory_repos import product_repository, warehouse_repository
from app.repositories.warehouse_operations_repos import goods_receipt_repository
from app.repositories.procurement_repos import (

    purchase_order_repository,
    supplier_quotation_repository,
    supplier_repository,
)
from app.schemas.approval_workflow import ApprovalRequestCreate
from app.schemas.procurement import (
    PurchaseOrderAmend,
    PurchaseOrderCreate,
    PurchaseOrderFromQuotationCreate,
    PurchaseOrderReceiveCreate,
    PurchaseOrderReceiveItem,
    PurchaseOrderUpdate,
)
from app.services.approval_engine import ApprovalEngineService
from app.services.audit_log import audit_log_service
from app.services.warehouse_operations_services import warehouse_execution_service

logger = logging.getLogger("app.services.purchase_order")


class PurchaseOrderService:
    """
    Domain service for managing Purchase Orders, line items, approval workflows, revisions, and lifecycle tracking.
    """

    def _calculate_totals(
        self, items: List[PurchaseOrderItem]
    ) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
        subtotal = Decimal("0.0")
        tax_total = Decimal("0.0")
        disc_total = Decimal("0.0")

        for item in items:
            gross = item.quantity * item.unit_price
            disc_val = gross * (item.discount_pct / Decimal("100.0"))
            after_disc = gross - disc_val
            tax_val = after_disc * (item.tax_pct / Decimal("100.0"))
            item.total_price = after_disc + tax_val

            subtotal += gross
            disc_total += disc_val
            tax_total += tax_val

        final_total = subtotal - disc_total + tax_total
        return subtotal, tax_total, disc_total, final_total

    async def _generate_po_number(self, db: AsyncSession) -> str:
        current_year = datetime.now(timezone.utc).year
        prefix = f"PO-{current_year}-"
        max_suffix = await purchase_order_repository.get_max_number_suffix(db, prefix=prefix)
        next_seq = max_suffix + 1
        return f"{prefix}{next_seq:05d}"

    async def create_order(
        self, db: AsyncSession, obj_in: PurchaseOrderCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> PurchaseOrder:
        supplier = await supplier_repository.get_by_id(db, obj_in.supplier_id)
        if not supplier:
            raise NotFoundException(f"Supplier with ID '{obj_in.supplier_id}' not found.")
        if hasattr(supplier, "is_active") and not supplier.is_active:
            raise ValidationException("Cannot create Purchase Order for an inactive supplier.")
        if supplier.status == "Blacklisted":
            raise ValidationException("Cannot create Purchase Order for a blacklisted supplier.")
        if supplier.status == "Inactive":
            raise ValidationException("Cannot create Purchase Order for an inactive supplier.")

        if not obj_in.items:
            raise ValidationException("Purchase Order must contain at least one item.")

        po_num = await self._generate_po_number(db)

        items: List[PurchaseOrderItem] = []
        for item_in in obj_in.items:
            product = await product_repository.get_by_id(db, item_in.product_id)
            if not product:
                raise NotFoundException(f"Product with ID '{item_in.product_id}' not found.")
            if hasattr(product, "is_active") and not product.is_active:
                raise ValidationException(f"Product '{product.name}' is inactive.")

            wh = await warehouse_repository.get_by_id(db, item_in.warehouse_id)
            if not wh:
                raise NotFoundException(f"Warehouse with ID '{item_in.warehouse_id}' not found.")
            if hasattr(wh, "is_active") and not wh.is_active:
                raise ValidationException(f"Warehouse '{wh.name}' is inactive.")

            qty = Decimal(str(item_in.quantity))
            if qty <= Decimal("0.0"):
                raise ValidationException("Item quantity must be greater than zero.")
            price = Decimal(str(item_in.unit_price))
            if price < Decimal("0.0"):
                raise ValidationException("Item unit price cannot be negative.")
            disc_pct = Decimal(str(item_in.discount_pct or 0.0))
            if disc_pct < Decimal("0.0") or disc_pct > Decimal("100.0"):
                raise ValidationException("Item discount percentage must be between 0 and 100.")
            tax_pct = Decimal(str(item_in.tax_pct or 0.0))
            if tax_pct < Decimal("0.0") or tax_pct > Decimal("100.0"):
                raise ValidationException("Item tax percentage must be between 0 and 100.")

            items.append(
                PurchaseOrderItem(
                    product_id=item_in.product_id,
                    description=item_in.description or product.name,
                    quantity=qty,
                    received_quantity=Decimal("0.0"),
                    returned_quantity=Decimal("0.0"),
                    unit_price=price,
                    discount_pct=disc_pct,
                    tax_pct=tax_pct,
                    total_price=Decimal("0.0"),
                    warehouse_id=item_in.warehouse_id,
                    storage_location_id=item_in.storage_location_id,
                    expected_delivery_date=item_in.expected_delivery_date or obj_in.expected_delivery_date,
                    status="Pending",
                )
            )

        subtotal, tax_amount, discount_amount, total_amount = self._calculate_totals(items)

        po = PurchaseOrder(
            po_number=po_num,
            origin_type=obj_in.origin_type,
            origin_document_id=obj_in.origin_document_id,
            supplier_id=obj_in.supplier_id,
            order_date=obj_in.order_date or datetime.now(timezone.utc),
            expected_delivery_date=obj_in.expected_delivery_date,
            payment_terms=obj_in.payment_terms or supplier.payment_terms,
            currency=obj_in.currency or supplier.currency or "USD",
            shipping_address=obj_in.shipping_address,
            billing_address=obj_in.billing_address,
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            status="Draft",
            revision_number=1,
            created_by=current_user_id,
            notes=obj_in.notes,
            items=items,
        )
        db.add(po)
        await db.commit()
        await db.refresh(po)

        await audit_log_service.log_event(
            db,
            action="PURCHASE_ORDER_CREATE",
            entity_type="PurchaseOrder",
            entity_id=po.id,
            user_id=current_user_id,
            new_data={
                "po_number": po.po_number,
                "supplier_id": str(po.supplier_id),
                "total_amount": float(po.total_amount),
                "origin_type": po.origin_type,
            },
        )
        return await self.get_order(db, po.id)

    async def create_from_quotation(
        self,
        db: AsyncSession,
        quotation_id: uuid.UUID,
        obj_in: PurchaseOrderFromQuotationCreate,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> PurchaseOrder:
        quotation = await supplier_quotation_repository.get_by_id(db, quotation_id)
        if not quotation:
            raise NotFoundException(f"Supplier Quotation with ID '{quotation_id}' not found.")

        if quotation.status != "Approved":
            raise ValidationException(
                f"Cannot create Purchase Order from quotation in '{quotation.status}' status. Quotation must be Approved/Awarded."
            )

        existing_po = await purchase_order_repository.get_by_origin(
            db, origin_type="Quotation", origin_document_id=quotation.id
        )
        if existing_po:
            raise ValidationException(
                f"A Purchase Order (#{existing_po.po_number}) has already been created from this quotation."
            )

        supplier = await supplier_repository.get_by_id(db, quotation.supplier_id)
        if not supplier:
            raise NotFoundException(f"Supplier with ID '{quotation.supplier_id}' not found.")
        if hasattr(supplier, "is_active") and not supplier.is_active:
            raise ValidationException("Cannot create Purchase Order for an inactive supplier.")
        if supplier.status in ("Blacklisted", "Inactive"):
            raise ValidationException(f"Cannot create Purchase Order for a {supplier.status.lower()} supplier.")

        wh = await warehouse_repository.get_by_id(db, obj_in.warehouse_id)
        if not wh:
            raise NotFoundException(f"Warehouse with ID '{obj_in.warehouse_id}' not found.")
        if hasattr(wh, "is_active") and not wh.is_active:
            raise ValidationException(f"Warehouse '{wh.name}' is inactive.")

        if not quotation.items:
            raise ValidationException("Quotation contains no line items to convert to Purchase Order.")

        po_num = await self._generate_po_number(db)

        items: List[PurchaseOrderItem] = []
        for q_item in quotation.items:
            product = await product_repository.get_by_id(db, q_item.product_id)
            if not product:
                raise NotFoundException(f"Product with ID '{q_item.product_id}' not found.")

            items.append(
                PurchaseOrderItem(
                    product_id=q_item.product_id,
                    description=q_item.remarks or product.name,
                    quantity=q_item.quantity,
                    received_quantity=Decimal("0.0"),
                    returned_quantity=Decimal("0.0"),
                    unit_price=q_item.unit_price,
                    discount_pct=q_item.discount_pct,
                    tax_pct=q_item.tax_pct,
                    total_price=q_item.total_price,
                    warehouse_id=obj_in.warehouse_id,
                    expected_delivery_date=obj_in.expected_delivery_date,
                    status="Pending",
                )
            )

        subtotal, tax_amount, discount_amount, total_amount = self._calculate_totals(items)

        po = PurchaseOrder(
            po_number=po_num,
            origin_type="Quotation",
            origin_document_id=quotation.id,
            supplier_id=quotation.supplier_id,
            order_date=datetime.now(timezone.utc),
            expected_delivery_date=obj_in.expected_delivery_date,
            payment_terms=quotation.payment_terms or supplier.payment_terms,
            currency=quotation.currency or "USD",
            shipping_address=obj_in.shipping_address,
            billing_address=obj_in.billing_address,
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            status="Draft",
            revision_number=1,
            created_by=current_user_id,
            notes=obj_in.notes or quotation.notes,
            items=items,
        )
        db.add(po)
        await db.commit()
        await db.refresh(po)

        await audit_log_service.log_event(
            db,
            action="PURCHASE_ORDER_CREATE",
            entity_type="PurchaseOrder",
            entity_id=po.id,
            user_id=current_user_id,
            new_data={
                "po_number": po.po_number,
                "supplier_id": str(po.supplier_id),
                "total_amount": float(po.total_amount),
                "origin_type": "Quotation",
                "origin_document_id": str(quotation.id),
            },
        )
        return await self.get_order(db, po.id)

    async def get_order(self, db: AsyncSession, po_id: uuid.UUID) -> PurchaseOrder:
        po = await purchase_order_repository.get_by_id(db, po_id)
        if not po:
            raise NotFoundException(f"Purchase Order with ID '{po_id}' not found.")
        return po

    async def update_order(
        self,
        db: AsyncSession,
        po_id: uuid.UUID,
        obj_in: PurchaseOrderUpdate,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> PurchaseOrder:
        po = await self.get_order(db, po_id)
        if po.status != "Draft":
            raise ValidationException(
                f"Cannot update Purchase Order in status '{po.status}'. Only Draft orders can be updated directly."
            )

        old_data = {"status": po.status, "total_amount": float(po.total_amount)}

        if obj_in.supplier_id and obj_in.supplier_id != po.supplier_id:
            supplier = await supplier_repository.get_by_id(db, obj_in.supplier_id)
            if not supplier:
                raise NotFoundException(f"Supplier with ID '{obj_in.supplier_id}' not found.")
            if hasattr(supplier, "is_active") and not supplier.is_active:
                raise ValidationException("Cannot assign an inactive supplier.")
            if supplier.status in ("Blacklisted", "Inactive"):
                raise ValidationException(f"Cannot assign a {supplier.status.lower()} supplier.")
            po.supplier_id = obj_in.supplier_id

        if obj_in.order_date:
            po.order_date = obj_in.order_date
        if obj_in.expected_delivery_date:
            po.expected_delivery_date = obj_in.expected_delivery_date
        if obj_in.payment_terms is not None:
            po.payment_terms = obj_in.payment_terms
        if obj_in.currency:
            po.currency = obj_in.currency
        if obj_in.shipping_address is not None:
            po.shipping_address = obj_in.shipping_address
        if obj_in.billing_address is not None:
            po.billing_address = obj_in.billing_address
        if obj_in.notes is not None:
            po.notes = obj_in.notes

        if obj_in.items is not None:
            if not obj_in.items:
                raise ValidationException("Purchase Order must contain at least one item.")

            po.items.clear()
            for item_in in obj_in.items:
                product = await product_repository.get_by_id(db, item_in.product_id)
                if not product:
                    raise NotFoundException(f"Product with ID '{item_in.product_id}' not found.")
                if hasattr(product, "is_active") and not product.is_active:
                    raise ValidationException(f"Product '{product.name}' is inactive.")

                wh = await warehouse_repository.get_by_id(db, item_in.warehouse_id)
                if not wh:
                    raise NotFoundException(f"Warehouse with ID '{item_in.warehouse_id}' not found.")
                if hasattr(wh, "is_active") and not wh.is_active:
                    raise ValidationException(f"Warehouse '{wh.name}' is inactive.")

                qty = Decimal(str(item_in.quantity))
                if qty <= Decimal("0.0"):
                    raise ValidationException("Item quantity must be greater than zero.")
                price = Decimal(str(item_in.unit_price))
                if price < Decimal("0.0"):
                    raise ValidationException("Item unit price cannot be negative.")
                disc_pct = Decimal(str(item_in.discount_pct or 0.0))
                if disc_pct < Decimal("0.0") or disc_pct > Decimal("100.0"):
                    raise ValidationException("Item discount percentage must be between 0 and 100.")
                tax_pct = Decimal(str(item_in.tax_pct or 0.0))
                if tax_pct < Decimal("0.0") or tax_pct > Decimal("100.0"):
                    raise ValidationException("Item tax percentage must be between 0 and 100.")

                po.items.append(
                    PurchaseOrderItem(
                        purchase_order_id=po.id,
                        product_id=item_in.product_id,
                        description=item_in.description or product.name,
                        quantity=qty,
                        received_quantity=Decimal("0.0"),
                        returned_quantity=Decimal("0.0"),
                        unit_price=price,
                        discount_pct=disc_pct,
                        tax_pct=tax_pct,
                        total_price=Decimal("0.0"),
                        warehouse_id=item_in.warehouse_id,
                        storage_location_id=item_in.storage_location_id,
                        expected_delivery_date=item_in.expected_delivery_date or po.expected_delivery_date,
                        status="Pending",
                    )
                )

            subtotal, tax_amount, discount_amount, total_amount = self._calculate_totals(po.items)
            po.subtotal = subtotal
            po.tax_amount = tax_amount
            po.discount_amount = discount_amount
            po.total_amount = total_amount

        await db.commit()
        await db.refresh(po)

        await audit_log_service.log_event(
            db,
            action="PURCHASE_ORDER_UPDATE",
            entity_type="PurchaseOrder",
            entity_id=po.id,
            user_id=current_user_id,
            previous_data=old_data,
            new_data={"status": po.status, "total_amount": float(po.total_amount)},
        )
        return await self.get_order(db, po.id)

    async def submit_order(
        self, db: AsyncSession, po_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> PurchaseOrder:
        po = await self.get_order(db, po_id)
        if po.status not in ("Draft", "Rejected"):
            raise ValidationException(f"Only Draft or Rejected orders can be submitted. Current status: '{po.status}'.")

        supplier = await supplier_repository.get_by_id(db, po.supplier_id)
        if not supplier:
            raise NotFoundException(f"Supplier with ID '{po.supplier_id}' not found.")
        if hasattr(supplier, "is_active") and not supplier.is_active:
            raise ValidationException("Cannot submit Purchase Order for an inactive supplier.")
        if supplier.status in ("Blacklisted", "Inactive"):
            raise ValidationException(f"Cannot submit Purchase Order for a {supplier.status.lower()} supplier.")

        if not po.items:
            raise ValidationException("Purchase Order must contain at least one item before submission.")

        po.status = "Submitted"
        await db.commit()

        # Submit to ApprovalEngineService via start_workflow
        approval_service = ApprovalEngineService(db)
        actor_user = None
        if current_user_id:
            from app.repositories.user import user_repository
            actor_user = await user_repository.get_by_id(db, current_user_id)
        if not actor_user:
            actor_user = User(
                id=current_user_id or po.created_by or uuid.uuid4(),
                email="system@apnaerp.com",
                username="system",
                is_active=True,
            )

        try:
            workflow_data = ApprovalRequestCreate(
                workflow_code="WF_PURCHASE_ORDER",
                entity_type="PurchaseOrder",
                entity_id=str(po.id),
                comments=f"Purchase Order #{po.po_number} - Supplier: {supplier.name} - Total: {po.currency} {po.total_amount}",
            )
            await approval_service.start_workflow(workflow_data, actor_user)
        except Exception as exc:
            logger.info(f"No configured approval workflow for PurchaseOrder ({exc}). Status remains Submitted.")

        await db.commit()
        await db.refresh(po)

        await audit_log_service.log_event(
            db,
            action="PURCHASE_ORDER_SUBMIT",
            entity_type="PurchaseOrder",
            entity_id=po.id,
            user_id=current_user_id,
            new_data={"status": po.status, "po_number": po.po_number, "total_amount": float(po.total_amount)},
        )

        await redis_manager.delete_pattern("po:*")
        return await self.get_order(db, po.id)

    async def approve_order(
        self, db: AsyncSession, po_id: uuid.UUID, approver_id: Optional[uuid.UUID] = None
    ) -> PurchaseOrder:
        po = await self.get_order(db, po_id)
        if po.status in ("Approved", "Closed", "Cancelled", "Dispatched"):
            raise ValidationException(f"Purchase Order is already in state '{po.status}'.")

        po.status = "Approved"
        po.approved_by = approver_id
        po.approved_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(po)

        await audit_log_service.log_event(
            db,
            action="PURCHASE_ORDER_APPROVE",
            entity_type="PurchaseOrder",
            entity_id=po.id,
            user_id=approver_id,
            new_data={"status": "Approved", "po_number": po.po_number, "approved_by": str(approver_id) if approver_id else None},
        )

        domain_event_publisher.publish(
            "PurchaseOrderApproved",
            {
                "po_id": str(po.id),
                "po_number": po.po_number,
                "supplier_id": str(po.supplier_id),
                "total_amount": float(po.total_amount),
            },
        )

        await redis_manager.delete_pattern("po:*")
        return await self.get_order(db, po.id)

    async def reject_order(
        self,
        db: AsyncSession,
        po_id: uuid.UUID,
        rejecter_id: Optional[uuid.UUID] = None,
        reason: Optional[str] = None,
    ) -> PurchaseOrder:
        po = await self.get_order(db, po_id)
        if po.status != "Submitted":
            raise ValidationException(f"Only Submitted orders can be rejected. Current status: '{po.status}'.")

        po.status = "Rejected"
        if reason:
            po.notes = f"{po.notes}\nRejection Reason: {reason}" if po.notes else f"Rejection Reason: {reason}"

        await db.commit()
        await db.refresh(po)

        await audit_log_service.log_event(
            db,
            action="PURCHASE_ORDER_REJECT",
            entity_type="PurchaseOrder",
            entity_id=po.id,
            user_id=rejecter_id,
            new_data={"status": "Rejected", "po_number": po.po_number, "reason": reason},
        )

        await redis_manager.delete_pattern("po:*")
        return await self.get_order(db, po.id)

    async def amend_order(
        self,
        db: AsyncSession,
        po_id: uuid.UUID,
        obj_in: PurchaseOrderAmend,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> PurchaseOrder:
        po = await self.get_order(db, po_id)
        if po.status not in ("Approved", "Dispatched"):
            raise ValidationException(
                f"Only Approved or Dispatched Purchase Orders can be amended. Current status: '{po.status}'."
            )

        total_received = sum(Decimal(str(item.received_quantity)) for item in po.items)
        if total_received > Decimal("0.0"):
            raise ValidationException("Cannot amend a Purchase Order after physical receiving has started.")

        old_revision = po.revision_number
        po.revision_number += 1
        po.status = "Draft"
        po.approved_by = None
        po.approved_at = None

        if obj_in.expected_delivery_date:
            po.expected_delivery_date = obj_in.expected_delivery_date
        if obj_in.payment_terms is not None:
            po.payment_terms = obj_in.payment_terms
        if obj_in.shipping_address is not None:
            po.shipping_address = obj_in.shipping_address
        if obj_in.billing_address is not None:
            po.billing_address = obj_in.billing_address
        if obj_in.notes is not None:
            po.notes = obj_in.notes
        if obj_in.amendment_reason:
            po.notes = f"{po.notes}\nAmendment Rev {po.revision_number}: {obj_in.amendment_reason}" if po.notes else f"Amendment Rev {po.revision_number}: {obj_in.amendment_reason}"

        if obj_in.items is not None:
            if not obj_in.items:
                raise ValidationException("Amended Purchase Order must contain at least one item.")

            po.items.clear()
            for item_in in obj_in.items:
                product = await product_repository.get_by_id(db, item_in.product_id)
                if not product:
                    raise NotFoundException(f"Product with ID '{item_in.product_id}' not found.")
                wh = await warehouse_repository.get_by_id(db, item_in.warehouse_id)
                if not wh:
                    raise NotFoundException(f"Warehouse with ID '{item_in.warehouse_id}' not found.")

                qty = Decimal(str(item_in.quantity))
                if qty <= Decimal("0.0"):
                    raise ValidationException("Item quantity must be greater than zero.")
                price = Decimal(str(item_in.unit_price))
                if price < Decimal("0.0"):
                    raise ValidationException("Item unit price cannot be negative.")
                disc_pct = Decimal(str(item_in.discount_pct or 0.0))
                tax_pct = Decimal(str(item_in.tax_pct or 0.0))

                po.items.append(
                    PurchaseOrderItem(
                        purchase_order_id=po.id,
                        product_id=item_in.product_id,
                        description=item_in.description or product.name,
                        quantity=qty,
                        received_quantity=Decimal("0.0"),
                        returned_quantity=Decimal("0.0"),
                        unit_price=price,
                        discount_pct=disc_pct,
                        tax_pct=tax_pct,
                        total_price=Decimal("0.0"),
                        warehouse_id=item_in.warehouse_id,
                        storage_location_id=item_in.storage_location_id,
                        expected_delivery_date=item_in.expected_delivery_date or po.expected_delivery_date,
                        status="Pending",
                    )
                )

            subtotal, tax_amount, discount_amount, total_amount = self._calculate_totals(po.items)
            po.subtotal = subtotal
            po.tax_amount = tax_amount
            po.discount_amount = discount_amount
            po.total_amount = total_amount

        await db.commit()
        await db.refresh(po)

        await audit_log_service.log_event(
            db,
            action="PURCHASE_ORDER_AMEND",
            entity_type="PurchaseOrder",
            entity_id=po.id,
            user_id=current_user_id,
            previous_data={"revision_number": old_revision, "status": "Approved"},
            new_data={"revision_number": po.revision_number, "status": po.status, "total_amount": float(po.total_amount)},
        )

        await redis_manager.delete_pattern("po:*")
        return await self.get_order(db, po.id)

    async def dispatch_order(
        self, db: AsyncSession, po_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> PurchaseOrder:
        po = await self.get_order(db, po_id)
        if po.status != "Approved":
            raise ValidationException(f"Only Approved orders can be dispatched. Current status: '{po.status}'.")

        po.status = "Dispatched"
        await db.commit()
        await db.refresh(po)

        await audit_log_service.log_event(
            db,
            action="PURCHASE_ORDER_DISPATCH",
            entity_type="PurchaseOrder",
            entity_id=po.id,
            user_id=current_user_id,
            new_data={"status": "Dispatched", "po_number": po.po_number},
        )

        await redis_manager.delete_pattern("po:*")
        return await self.get_order(db, po.id)

    async def cancel_order(
        self, db: AsyncSession, po_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> PurchaseOrder:
        po = await self.get_order(db, po_id)
        if po.status in ("Closed", "Cancelled"):
            raise ValidationException(f"Cannot cancel PO in state '{po.status}'.")

        total_received = sum(Decimal(str(item.received_quantity)) for item in po.items)
        if total_received > Decimal("0.0"):
            raise ValidationException("Cannot cancel a Purchase Order that has received physical goods.")

        old_status = po.status
        po.status = "Cancelled"
        for item in po.items:
            item.status = "Cancelled"

        await db.commit()
        await db.refresh(po)

        await audit_log_service.log_event(
            db,
            action="PURCHASE_ORDER_CANCEL",
            entity_type="PurchaseOrder",
            entity_id=po.id,
            user_id=current_user_id,
            previous_data={"status": old_status},
            new_data={"status": "Cancelled"},
        )

        domain_event_publisher.publish(
            "PurchaseOrderCancelled",
            {
                "po_id": str(po.id),
                "po_number": po.po_number,
                "supplier_id": str(po.supplier_id),
            },
        )

        await redis_manager.delete_pattern("po:*")
        return await self.get_order(db, po.id)

    async def close_order(
        self, db: AsyncSession, po_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> PurchaseOrder:
        po = await self.get_order(db, po_id)
        if po.status in ("Closed", "Cancelled"):
            raise ValidationException(f"Order is already '{po.status}'.")

        po.status = "Closed"
        await db.commit()
        await db.refresh(po)
        await redis_manager.delete_pattern("po:*")
        return await self.get_order(db, po.id)

    async def reopen_order(
        self, db: AsyncSession, po_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> PurchaseOrder:
        po = await self.get_order(db, po_id)
        if po.status != "Closed":
            raise ValidationException("Only Closed Purchase Orders can be reopened.")

        po.status = "Approved"
        po.revision_number += 1
        await db.commit()
        await db.refresh(po)
        await redis_manager.delete_pattern("po:*")
        return await self.get_order(db, po.id)

    async def list_orders(
        self,
        db: AsyncSession,
        supplier_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        origin_type: Optional[str] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        product_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[PurchaseOrder], int]:
        return await purchase_order_repository.get_multi_paginated(
            db,
            supplier_id=supplier_id,
            status=status,
            origin_type=origin_type,
            warehouse_id=warehouse_id,
            product_id=product_id,
            search=search,
            skip=skip,
            limit=limit,
        )

    async def receive_goods(
        self,
        db: AsyncSession,
        po_id: uuid.UUID,
        receiving_items: List[Any],
        supplier_ref: Optional[str] = None,
        remarks: Optional[str] = None,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> GoodsReceipt:
        """
        Receives physical stock against an Approved, Dispatched, or Partially Received Purchase Order.
        Atomically executes StockMovementService.stock_in via WarehouseExecutionService, updates PO item received quantities,
        updates PO status (Partially Received / Fully Received), posts the GoodsReceipt, and writes audit events in a single transaction.
        """
        if not receiving_items:
            raise ValidationException("At least one line item is required for receiving.")

        # 1. Row-lock PurchaseOrder and its items to prevent concurrent over-receiving
        po = await purchase_order_repository.get_for_update(db, po_id)
        if not po:
            raise NotFoundException(f"Purchase Order with ID '{po_id}' not found.")

        # 2. Status Validation
        if po.status not in ("Approved", "Dispatched", "Partially Received"):
            raise ValidationException(
                f"Cannot receive goods for Purchase Order in '{po.status}' status. PO must be Approved, Dispatched, or Partially Received."
            )

        # 3. Validate Supplier
        supplier = await supplier_repository.get_by_id(db, po.supplier_id)
        if not supplier:
            raise NotFoundException(f"Supplier with ID '{po.supplier_id}' not found.")
        if hasattr(supplier, "is_active") and not supplier.is_active:
            raise ValidationException("Cannot receive goods from an inactive supplier.")
        if supplier.status in ("Blacklisted", "Inactive"):
            raise ValidationException(f"Cannot receive goods from a {supplier.status.lower()} supplier.")

        target_wh_id = po.items[0].warehouse_id if po.items else None

        receipt_items: List[GoodsReceiptItem] = []
        year = datetime.now(timezone.utc).year
        gr_count = await goods_receipt_repository.get_max_number_suffix(db, prefix=f"GRN-{year}-") + 1
        gr_number = f"GRN-{year}-{gr_count:05d}"


        # 4. Validate Each Line Item
        for rec_item in receiving_items:
            if hasattr(rec_item, "po_item_id"):
                po_item_id = rec_item.po_item_id
                raw_qty = rec_item.quantity
                storage_loc_id = rec_item.storage_location_id
                batch_id = rec_item.batch_id
                batch_num = rec_item.batch_number
                exp_date = rec_item.expiry_date
                mfg_date = rec_item.manufacturing_date
                serials = rec_item.serial_numbers
                item_remarks = rec_item.remarks
            else:
                po_item_id = uuid.UUID(str(rec_item["po_item_id"])) if not isinstance(rec_item["po_item_id"], uuid.UUID) else rec_item["po_item_id"]
                raw_qty = rec_item["quantity"]
                storage_loc_id = uuid.UUID(str(rec_item["storage_location_id"])) if rec_item.get("storage_location_id") and not isinstance(rec_item.get("storage_location_id"), uuid.UUID) else rec_item.get("storage_location_id")
                batch_id = uuid.UUID(str(rec_item["batch_id"])) if rec_item.get("batch_id") and not isinstance(rec_item.get("batch_id"), uuid.UUID) else rec_item.get("batch_id")
                batch_num = rec_item.get("batch_number")
                exp_date = rec_item.get("expiry_date")
                mfg_date = rec_item.get("manufacturing_date")
                serials = rec_item.get("serial_numbers")
                item_remarks = rec_item.get("remarks")

            qty = Decimal(str(raw_qty))
            if qty <= Decimal("0.0"):
                raise ValidationException("Received quantity must be strictly greater than zero.")

            po_item = next((item for item in po.items if item.id == po_item_id), None)
            if not po_item:
                raise NotFoundException(f"PO Item with ID '{po_item_id}' not found in PO #{po.po_number}.")

            # Over-receiving Validation: remaining = ordered_qty - received_qty + returned_qty
            ordered_qty = Decimal(str(po_item.quantity))
            already_received = Decimal(str(po_item.received_quantity))
            returned_qty = Decimal(str(po_item.returned_quantity))
            remaining_qty = ordered_qty - already_received + returned_qty

            if qty > remaining_qty:
                raise ValidationException(
                    f"Received quantity ({qty}) exceeds remaining order quantity ({remaining_qty}) for PO line item."
                )

            # Product Validation
            product = await product_repository.get_by_id(db, po_item.product_id)
            if not product:
                raise NotFoundException(f"Product with ID '{po_item.product_id}' not found.")
            if hasattr(product, "is_active") and not product.is_active:
                raise ValidationException(f"Product SKU '{product.sku}' is inactive.")

            # Batch validation if product is batch tracked
            if getattr(product, "is_batch_tracked", False):
                if not batch_id and not batch_num:
                    raise ValidationException(f"Product SKU '{product.sku}' is batch-tracked; batch information is required.")

            # Serial validation if product is serial tracked
            if getattr(product, "is_serial_tracked", False):
                if not serials:
                    raise ValidationException(f"Product SKU '{product.sku}' is serial-tracked; serial numbers are required.")
                if len(serials) != int(qty):
                    raise ValidationException(f"Serial count ({len(serials)}) does not match received quantity ({qty}).")
                if len(set(serials)) != len(serials):
                    raise ValidationException("Duplicate serial numbers provided in receiving list.")

            receipt_items.append(
                GoodsReceiptItem(
                    product_id=product.id,
                    storage_location_id=storage_loc_id,
                    quantity=float(qty),
                    unit_id=product.base_unit_id,
                    unit_cost=float(po_item.unit_price),
                    batch_id=batch_id,
                    batch_number=batch_num,
                    expiry_date=exp_date,
                    manufacturing_date=mfg_date,
                    serial_numbers=list(serials) if serials else None,
                    remarks=item_remarks or f"Received against PO #{po.po_number}",
                )
            )

        now = datetime.now(timezone.utc)
        receipt = GoodsReceipt(
            receipt_number=gr_number,
            warehouse_id=target_wh_id,
            supplier_reference=supplier_ref,
            external_reference=po.po_number,
            receipt_date=now,
            status="Draft",
            remarks=remarks or f"Goods Receipt against Purchase Order #{po.po_number}",
            created_by=current_user_id,
            approved_by=current_user_id,
            approved_at=now,
            items=receipt_items,
        )
        db.add(receipt)
        await db.flush()

        # 5. Execute stock IN via WarehouseExecutionService (which uses StockMovementService.stock_in with commit=False)
        await warehouse_execution_service.execute_goods_receipt(db, receipt, current_user_id=current_user_id)

        # 6. Update PO Item Quantities and Statuses
        for rec_item in receiving_items:
            if hasattr(rec_item, "po_item_id"):
                po_item_id = rec_item.po_item_id
                raw_qty = rec_item.quantity
            else:
                po_item_id = uuid.UUID(str(rec_item["po_item_id"])) if not isinstance(rec_item["po_item_id"], uuid.UUID) else rec_item["po_item_id"]
                raw_qty = rec_item["quantity"]
            qty = Decimal(str(raw_qty))
            po_item = next(item for item in po.items if item.id == po_item_id)
            po_item.received_quantity += qty
            if po_item.received_quantity >= po_item.quantity:
                po_item.status = "Fully Received"
            elif po_item.received_quantity > Decimal("0.0"):
                po_item.status = "Partially Received"

        # 7. Update PO Header Status
        all_fully_received = all(item.received_quantity >= item.quantity for item in po.items)
        old_po_status = po.status
        if all_fully_received:
            po.status = "Fully Received"
        else:
            po.status = "Partially Received"

        receipt.status = "Received"
        await db.commit()
        await db.refresh(receipt)
        await db.refresh(po)

        # 8. Audit Logging
        await audit_log_service.log_event(
            db,
            action="PURCHASE_RECEIPT_CREATE",
            entity_type="GoodsReceipt",
            entity_id=receipt.id,
            user_id=current_user_id,
            new_data={"receipt_number": receipt.receipt_number, "po_number": po.po_number, "item_count": len(receipt.items)},
        )
        await audit_log_service.log_event(
            db,
            action="PURCHASE_RECEIPT_POST",
            entity_type="GoodsReceipt",
            entity_id=receipt.id,
            user_id=current_user_id,
            new_data={"receipt_number": receipt.receipt_number, "status": "Received"},
        )
        po_action = "PURCHASE_ORDER_FULLY_RECEIVED" if po.status == "Fully Received" else "PURCHASE_ORDER_PARTIAL_RECEIVE"
        await audit_log_service.log_event(
            db,
            action=po_action,
            entity_type="PurchaseOrder",
            entity_id=po.id,
            user_id=current_user_id,
            previous_data={"status": old_po_status},
            new_data={"status": po.status, "po_number": po.po_number},
        )

        domain_event_publisher.publish(
            "GoodsReceived",
            {
                "receipt_id": str(receipt.id),
                "receipt_number": receipt.receipt_number,
                "po_id": str(po.id),
                "po_number": po.po_number,
                "status": po.status,
            },
        )

        await redis_manager.delete_pattern("po:*")
        await redis_manager.delete_pattern("stock_balance:*")
        return receipt

    async def get_po_receipts(self, db: AsyncSession, po_id: uuid.UUID) -> List[GoodsReceipt]:
        po = await self.get_order(db, po_id)
        stmt = (
            select(GoodsReceipt)
            .options(selectinload(GoodsReceipt.items).selectinload(GoodsReceiptItem.product))
            .where(GoodsReceipt.external_reference == po.po_number)
            .order_by(GoodsReceipt.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


purchase_order_service = PurchaseOrderService()
