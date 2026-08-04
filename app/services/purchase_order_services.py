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
from app.models.goods_receipt import GoodsReceipt
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.repositories.inventory_repos import product_repository, warehouse_repository
from app.repositories.procurement_repos import (
    purchase_order_repository,
    supplier_repository,
)
from app.schemas.procurement import (
    PurchaseOrderCreate,
    PurchaseOrderUpdate,
)
from app.schemas.warehouse_operations import GoodsReceiptCreate, GoodsReceiptItemCreate
from app.services.approval_engine import ApprovalEngineService
from app.services.audit_log import audit_log_service
from app.services.supplier_services import supplier_performance_service
from app.services.warehouse_operations_services import (
    goods_receipt_service,
    warehouse_execution_service,
)

logger = logging.getLogger("app.services.purchase_order")


class PurchaseOrderService:
    """
    Domain service for managing Purchase Orders, line items, approval workflows, revisions, and Goods Receipt integration.
    """
    async def create_order(
        self, db: AsyncSession, obj_in: PurchaseOrderCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> PurchaseOrder:
        supplier = await supplier_repository.get_by_id(db, obj_in.supplier_id)
        if not supplier or supplier.is_deleted:
            raise NotFoundException(f"Supplier with ID '{obj_in.supplier_id}' not found.")
        if supplier.status == "Blacklisted":
            raise ValidationException("Cannot create Purchase Order for a blacklisted supplier.")

        # Generate PO Number (PO-YYYY-XXXXX)
        count = (await purchase_order_repository.get_multi_paginated(db, limit=1))[1] + 1
        po_num = f"PO-{datetime.now().year}-{count:05d}"

        subtotal = Decimal("0.0")
        tax_total = Decimal("0.0")
        disc_total = Decimal("0.0")

        items: List[PurchaseOrderItem] = []
        for item_in in obj_in.items:
            product = await product_repository.get_by_id(db, item_in.product_id)
            if not product:
                raise NotFoundException(f"Product with ID '{item_in.product_id}' not found.")

            wh = await warehouse_repository.get_by_id(db, item_in.warehouse_id)
            if not wh:
                raise NotFoundException(f"Warehouse with ID '{item_in.warehouse_id}' not found.")

            qty = Decimal(str(item_in.quantity))
            price = Decimal(str(item_in.unit_price))
            disc_pct = Decimal(str(item_in.discount_pct))
            tax_pct = Decimal(str(item_in.tax_pct))

            gross = qty * price
            disc_val = gross * (disc_pct / Decimal("100.0"))
            after_disc = gross - disc_val
            tax_val = after_disc * (tax_pct / Decimal("100.0"))
            line_tot = after_disc + tax_val

            subtotal += gross
            disc_total += disc_val
            tax_total += tax_val

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
                    total_price=line_tot,
                    warehouse_id=item_in.warehouse_id,
                    storage_location_id=item_in.storage_location_id,
                    expected_delivery_date=item_in.expected_delivery_date or obj_in.expected_delivery_date,
                    status="Pending",
                )
            )

        final_total = subtotal - disc_total + tax_total

        po = PurchaseOrder(
            po_number=po_num,
            origin_type=obj_in.origin_type,
            origin_document_id=obj_in.origin_document_id,
            supplier_id=obj_in.supplier_id,
            order_date=obj_in.order_date or datetime.now(timezone.utc),
            expected_delivery_date=obj_in.expected_delivery_date,
            payment_terms=obj_in.payment_terms or supplier.payment_terms,
            currency=obj_in.currency or supplier.currency,
            shipping_address=obj_in.shipping_address,
            billing_address=obj_in.billing_address,
            subtotal=subtotal,
            tax_amount=tax_total,
            discount_amount=disc_total,
            total_amount=final_total,
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
        )
        return po

    async def get_order(self, db: AsyncSession, po_id: uuid.UUID) -> PurchaseOrder:
        po = await purchase_order_repository.get_by_id(db, po_id)
        if not po:
            raise NotFoundException(f"Purchase Order with ID '{po_id}' not found.")
        return po

    async def submit_order(
        self, db: AsyncSession, po_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> PurchaseOrder:
        po = await self.get_order(db, po_id)
        if po.status not in ("Draft", "Rejected"):
            raise ValidationException(f"Only Draft or Rejected orders can be submitted. Current status: '{po.status}'.")

        po.status = "Submitted"
        await db.commit()

        # Submit to ApprovalEngineService if workflow configured
        try:
            approval_service = ApprovalEngineService(db)
            await approval_service.submit_request(
                module_name="purchase_order",
                entity_type="PurchaseOrder",
                entity_id=po.id,
                requester_id=current_user_id or po.created_by or uuid.uuid4(),
                title=f"Purchase Order #{po.po_number}",
            )
        except Exception as exc:
            logger.info(f"No active approval workflow for purchase_order or auto-approved: {exc}")
            po.status = "Approved"
            po.approved_by = current_user_id
            po.approved_at = datetime.now(timezone.utc)
            await db.commit()

        await db.refresh(po)

        if po.status == "Approved":
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
        return po

    async def approve_order(
        self, db: AsyncSession, po_id: uuid.UUID, approver_id: Optional[uuid.UUID] = None
    ) -> PurchaseOrder:
        po = await self.get_order(db, po_id)
        if po.status in ("Approved", "Closed", "Cancelled"):
            raise ValidationException(f"Purchase Order is already in state '{po.status}'.")

        po.status = "Approved"
        po.approved_by = approver_id
        po.approved_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(po)

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
        return po

    async def cancel_order(
        self, db: AsyncSession, po_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> PurchaseOrder:
        po = await self.get_order(db, po_id)
        if po.status in ("Closed", "Cancelled"):
            raise ValidationException(f"Cannot cancel PO in state '{po.status}'.")

        total_received = sum(Decimal(str(item.received_quantity)) for item in po.items)
        if total_received > Decimal("0.0"):
            raise ValidationException("Cannot cancel a Purchase Order that has received physical goods.")

        po.status = "Cancelled"
        for item in po.items:
            item.status = "Cancelled"

        await db.commit()
        await db.refresh(po)

        domain_event_publisher.publish(
            "PurchaseOrderCancelled",
            {
                "po_id": str(po.id),
                "po_number": po.po_number,
                "supplier_id": str(po.supplier_id),
            },
        )

        await redis_manager.delete_pattern("po:*")
        return po

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
        return po

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
        return po

    async def receive_goods(
        self,
        db: AsyncSession,
        po_id: uuid.UUID,
        receiving_items: List[Dict[str, Any]],
        supplier_ref: Optional[str] = None,
        remarks: Optional[str] = None,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> GoodsReceipt:
        """
        Integrates Purchase Order receiving with existing GoodsReceipt / Warehouse Operations Engine.
        Does NOT duplicate stock receiving logic.
        """
        po = await self.get_order(db, po_id)
        if po.status not in ("Approved", "Partially Received"):
            raise ValidationException(f"Goods can only be received for Approved or Partially Received POs. Current status: '{po.status}'.")

        if not receiving_items:
            raise ValidationException("At least one item must be specified for receiving.")

        # Determine target warehouse from first line item
        target_warehouse_id = po.items[0].warehouse_id

        gr_items: List[GoodsReceiptItemCreate] = []
        for recv in receiving_items:
            po_item_id = uuid.UUID(str(recv["po_item_id"]))
            recv_qty = Decimal(str(recv["quantity"]))

            # Find matching PO Item
            po_item = next((i for i in po.items if i.id == po_item_id), None)
            if not po_item:
                raise NotFoundException(f"PO Item with ID '{po_item_id}' not found in PO #{po.po_number}.")

            rem_qty = Decimal(str(po_item.quantity)) - Decimal(str(po_item.received_quantity))
            if recv_qty > rem_qty:
                raise ValidationException(f"Receiving quantity ({recv_qty}) exceeds remaining ordered quantity ({rem_qty}) for SKU '{po_item.product_id}'.")

            gr_items.append(
                GoodsReceiptItemCreate(
                    product_id=po_item.product_id,
                    quantity=recv_qty,
                    unit_id=None,
                    storage_location_id=po_item.storage_location_id,
                    remarks=f"PO #{po.po_number} Receipt",
                )
            )

            # Update PO Item receiving counter
            po_item.received_quantity += recv_qty
            if po_item.received_quantity >= po_item.quantity:
                po_item.status = "Fully Received"
            else:
                po_item.status = "Partially Received"

        # 1. Create GoodsReceipt via GoodsReceiptService
        gr_in = GoodsReceiptCreate(
            receipt_number=f"GR-{uuid.uuid4().hex[:8].upper()}",
            warehouse_id=target_warehouse_id,
            supplier_reference=supplier_ref,
            external_reference=f"PO:{po.po_number}",
            remarks=remarks or f"Receipt for Purchase Order #{po.po_number}",
            items=gr_items,
        )
        receipt = await goods_receipt_service.create_receipt(db, obj_in=gr_in, current_user_id=current_user_id)

        # 2. Execute GoodsReceipt physical stock ledger IN entry
        executed_receipt = await goods_receipt_service.receive_receipt(db, id=receipt.id, current_user_id=current_user_id)

        # 3. Update overall PO status
        all_fulfilled = all(Decimal(str(item.received_quantity)) >= Decimal(str(item.quantity)) for item in po.items)
        if all_fulfilled:
            po.status = "Fully Received"
        else:
            po.status = "Partially Received"

        await db.commit()
        await db.refresh(po)

        # Publish Domain Event
        domain_event_publisher.publish(
            "GoodsReceived",
            {
                "po_id": str(po.id),
                "po_number": po.po_number,
                "receipt_id": str(executed_receipt.id),
                "receipt_number": executed_receipt.receipt_number,
                "supplier_id": str(po.supplier_id),
            },
        )

        # Recalculate Supplier Performance
        await supplier_performance_service.recalculate_supplier_performance(db, po.supplier_id)

        await redis_manager.delete_pattern("po:*")
        return executed_receipt

    async def list_orders(
        self,
        db: AsyncSession,
        supplier_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        origin_type: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[PurchaseOrder], int]:
        return await purchase_order_repository.get_multi_paginated(
            db,
            supplier_id=supplier_id,
            status=status,
            origin_type=origin_type,
            search=search,
            skip=skip,
            limit=limit,
        )


purchase_order_service = PurchaseOrderService()
