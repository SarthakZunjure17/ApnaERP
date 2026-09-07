from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import List, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_events import domain_event_publisher
from app.core.redis import redis_manager
from app.exceptions.base import (
    NotFoundException,
    ValidationException,
)
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_return import (
    PurchaseReturn,
    PurchaseReturnItem,
)
from app.repositories.inventory_repos import product_repository, warehouse_repository
from app.repositories.procurement_repos import (
    purchase_order_repository,
    purchase_return_repository,
    supplier_repository,
)
from app.schemas.procurement import (
    PurchaseReturnCreate,
    PurchaseReturnUpdate,
)
from app.services.audit_log import audit_log_service
from app.services.stock_engine_services import stock_movement_service

logger = logging.getLogger("app.services.purchase_return")


class PurchaseReturnService:
    """
    Domain service for managing Purchase Returns, return requests, approval, and stock reversal execution via StockMovementService.
    """
    async def create_return(
        self, db: AsyncSession, obj_in: PurchaseReturnCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> PurchaseReturn:
        po = await purchase_order_repository.get_by_id(db, obj_in.purchase_order_id)
        if not po:
            raise NotFoundException(f"Purchase Order with ID '{obj_in.purchase_order_id}' not found.")

        if po.status not in ("Approved", "Dispatched", "Partially Received", "Fully Received"):
            raise ValidationException(
                f"Cannot create Purchase Return against PO in status '{po.status}'. PO must be Approved, Dispatched, or Received."
            )

        supplier = await supplier_repository.get_by_id(db, obj_in.supplier_id)
        if not supplier:
            raise NotFoundException(f"Supplier with ID '{obj_in.supplier_id}' not found.")

        if po.supplier_id != obj_in.supplier_id:
            raise ValidationException("Supplier does not match the purchase order supplier.")

        wh = await warehouse_repository.get_by_id(db, obj_in.warehouse_id)
        if not wh:
            raise NotFoundException(f"Warehouse with ID '{obj_in.warehouse_id}' not found.")
        if hasattr(wh, "is_active") and not wh.is_active:
            raise ValidationException(f"Warehouse '{wh.name}' is inactive.")

        if not obj_in.items:
            raise ValidationException("At least one return item is required.")

        # Safe sequential return number generation
        year = datetime.now(timezone.utc).year
        count = await purchase_return_repository.get_max_number_suffix(db, prefix=f"PRTN-{year}-") + 1
        rtn_num = f"PRTN-{year}-{count:05d}"

        tot_amount = Decimal("0.0")
        items: List[PurchaseReturnItem] = []

        for item_in in obj_in.items:
            po_item = next((i for i in po.items if i.id == item_in.po_item_id), None)
            if not po_item:
                raise NotFoundException(f"PO Item with ID '{item_in.po_item_id}' not found in PO #{po.po_number}.")

            if po_item.product_id != item_in.product_id:
                raise ValidationException("Product ID does not match the purchase order item product.")

            product = await product_repository.get_by_id(db, item_in.product_id)
            if not product:
                raise NotFoundException(f"Product with ID '{item_in.product_id}' not found.")

            ret_qty = Decimal(str(item_in.return_quantity))
            if ret_qty <= Decimal("0.0"):
                raise ValidationException("Return quantity must be strictly greater than zero.")

            avail_ret = Decimal(str(po_item.received_quantity)) - Decimal(str(po_item.returned_quantity))
            if ret_qty > avail_ret:
                raise ValidationException(
                    f"Return quantity ({ret_qty}) exceeds net received stock ({avail_ret}) for SKU '{product.sku}'."
                )

            price = Decimal(str(item_in.unit_price))
            if price < Decimal("0.0"):
                raise ValidationException("Unit price cannot be negative.")

            line_val = ret_qty * price
            tot_amount += line_val

            items.append(
                PurchaseReturnItem(
                    po_item_id=item_in.po_item_id,
                    product_id=item_in.product_id,
                    return_quantity=ret_qty,
                    unit_price=price,
                    reason=item_in.reason or obj_in.reason_code,
                )
            )

        ret = PurchaseReturn(
            return_number=rtn_num,
            purchase_order_id=obj_in.purchase_order_id,
            supplier_id=obj_in.supplier_id,
            warehouse_id=obj_in.warehouse_id,
            return_date=datetime.now(timezone.utc),
            reason_code=obj_in.reason_code,
            supplier_return_ref=obj_in.supplier_return_ref,
            total_return_amount=tot_amount,
            status="Draft",
            created_by=current_user_id,
            remarks=obj_in.remarks,
            items=items,
        )
        db.add(ret)
        await db.commit()
        await db.refresh(ret)

        await audit_log_service.log_event(
            db,
            action="PURCHASE_RETURN_CREATE",
            entity_type="PurchaseReturn",
            entity_id=ret.id,
            user_id=current_user_id,
            new_data={"return_number": ret.return_number, "total_return_amount": float(ret.total_return_amount)},
        )
        return ret

    async def get_return(self, db: AsyncSession, return_id: uuid.UUID) -> PurchaseReturn:
        ret = await purchase_return_repository.get_by_id(db, return_id)
        if not ret:
            raise NotFoundException(f"Purchase Return with ID '{return_id}' not found.")
        return ret

    async def update_return(
        self,
        db: AsyncSession,
        return_id: uuid.UUID,
        obj_in: PurchaseReturnUpdate,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> PurchaseReturn:
        ret = await self.get_return(db, return_id)
        if ret.status != "Draft":
            raise ValidationException(f"Cannot edit Purchase Return in state '{ret.status}'. Only Draft returns can be edited.")

        if obj_in.reason_code is not None:
            ret.reason_code = obj_in.reason_code
        if obj_in.supplier_return_ref is not None:
            ret.supplier_return_ref = obj_in.supplier_return_ref
        if obj_in.remarks is not None:
            ret.remarks = obj_in.remarks

        if obj_in.items is not None:
            if not obj_in.items:
                raise ValidationException("Purchase Return must contain at least one item.")
            po = await purchase_order_repository.get_by_id(db, ret.purchase_order_id)
            ret.items.clear()
            tot_amount = Decimal("0.0")
            for item_in in obj_in.items:
                po_item = next((i for i in po.items if i.id == item_in.po_item_id), None)
                if not po_item:
                    raise NotFoundException(f"PO Item with ID '{item_in.po_item_id}' not found.")
                ret_qty = Decimal(str(item_in.return_quantity))
                avail_ret = Decimal(str(po_item.received_quantity)) - Decimal(str(po_item.returned_quantity))
                if ret_qty > avail_ret:
                    raise ValidationException(f"Return quantity ({ret_qty}) exceeds net received stock ({avail_ret}).")
                price = Decimal(str(item_in.unit_price))
                tot_amount += ret_qty * price
                ret.items.append(
                    PurchaseReturnItem(
                        purchase_return_id=ret.id,
                        po_item_id=item_in.po_item_id,
                        product_id=item_in.product_id,
                        return_quantity=ret_qty,
                        unit_price=price,
                        reason=item_in.reason or ret.reason_code,
                    )
                )
            ret.total_return_amount = tot_amount

        await db.commit()
        await db.refresh(ret)
        return ret

    async def approve_return(
        self, db: AsyncSession, return_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> PurchaseReturn:
        ret = await self.get_return(db, return_id)
        if ret.status in ("Approved", "Processed", "Cancelled"):
            raise ValidationException(f"Purchase Return is already in state '{ret.status}'.")

        ret.status = "Approved"
        ret.approved_by = current_user_id
        await db.commit()
        await db.refresh(ret)
        return ret

    async def process_return(
        self, db: AsyncSession, return_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> PurchaseReturn:
        """
        Processes Purchase Return by atomically executing stock reversal (STOCK_OUT via StockMovementService)
        and updating PO returned quantities within a single locked transaction.
        """
        ret = await self.get_return(db, return_id)
        if ret.status in ("Processed", "Cancelled"):
            raise ValidationException(f"Cannot process return in state '{ret.status}'. Return is already {ret.status.lower()}.")

        # 1. Row-lock PurchaseOrder and its items for concurrency safety
        po = await purchase_order_repository.get_for_update(db, ret.purchase_order_id)
        if not po:
            raise NotFoundException(f"Purchase Order with ID '{ret.purchase_order_id}' not found.")

        # 2. Re-validate quantities under lock to prevent race condition over-returns
        for item in ret.items:
            po_item = next((i for i in po.items if i.id == item.po_item_id), None)
            if not po_item:
                raise NotFoundException(f"PO Item with ID '{item.po_item_id}' not found in PO #{po.po_number}.")

            ret_qty = Decimal(str(item.return_quantity))
            avail_ret = Decimal(str(po_item.received_quantity)) - Decimal(str(po_item.returned_quantity))
            if ret_qty > avail_ret:
                raise ValidationException(
                    f"Return quantity ({ret_qty}) exceeds available returnable stock ({avail_ret}) for PO item."
                )

        # 3. Execute Stock Movement OUT via StockMovementService for each return line item
        for item in ret.items:
            ret_qty = Decimal(str(item.return_quantity))
            await stock_movement_service.stock_out(
                db,
                product_id=item.product_id,
                warehouse_id=ret.warehouse_id,
                quantity=ret_qty,
                reference_type="PurchaseReturn",
                reference_id=ret.id,
                reason=f"Purchase Return #{ret.return_number} ({ret.reason_code})",
                notes=item.reason or ret.remarks,
                current_user_id=current_user_id,
                commit=False,
            )

            # Update PO Item returned quantity counter
            po_item = next((i for i in po.items if i.id == item.po_item_id), None)
            if po_item:
                po_item.returned_quantity += ret_qty

        ret.status = "Processed"
        ret.approved_by = current_user_id
        await db.commit()
        await db.refresh(ret)

        await audit_log_service.log_event(
            db,
            action="PURCHASE_RETURN_POST",
            entity_type="PurchaseReturn",
            entity_id=ret.id,
            user_id=current_user_id,
            new_data={
                "return_number": ret.return_number,
                "status": "Processed",
                "total_return_amount": float(ret.total_return_amount),
            },
        )

        # Publish Domain Event
        domain_event_publisher.publish(
            "PurchaseReturned",
            {
                "return_id": str(ret.id),
                "return_number": ret.return_number,
                "purchase_order_id": str(ret.purchase_order_id),
                "supplier_id": str(ret.supplier_id),
                "total_return_amount": float(ret.total_return_amount),
            },
        )

        await redis_manager.delete_pattern("return:*")
        await redis_manager.delete_pattern("stock_balance:*")
        await redis_manager.delete_pattern("po:*")
        return ret

    async def cancel_return(
        self, db: AsyncSession, return_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> PurchaseReturn:
        ret = await self.get_return(db, return_id)
        if ret.status in ("Processed", "Cancelled"):
            raise ValidationException(f"Cannot cancel Purchase Return in state '{ret.status}'.")

        old_status = ret.status
        ret.status = "Cancelled"
        await db.commit()
        await db.refresh(ret)

        await audit_log_service.log_event(
            db,
            action="PURCHASE_RETURN_CANCEL",
            entity_type="PurchaseReturn",
            entity_id=ret.id,
            user_id=current_user_id,
            previous_data={"status": old_status},
            new_data={"status": "Cancelled"},
        )
        return ret

    async def list_returns(
        self,
        db: AsyncSession,
        supplier_id: Optional[uuid.UUID] = None,
        purchase_order_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[PurchaseReturn], int]:
        return await purchase_return_repository.get_multi_paginated(
            db, supplier_id=supplier_id, purchase_order_id=purchase_order_id, status=status, skip=skip, limit=limit
        )


purchase_return_service = PurchaseReturnService()

