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
)
from app.services.audit_log import audit_log_service
from app.services.stock_engine_services import stock_ledger_service

logger = logging.getLogger("app.services.purchase_return")


class PurchaseReturnService:
    """
    Domain service for managing Purchase Returns, return requests, approval, and stock reversal execution via Stock Ledger.
    """
    async def create_return(
        self, db: AsyncSession, obj_in: PurchaseReturnCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> PurchaseReturn:
        po = await purchase_order_repository.get_by_id(db, obj_in.purchase_order_id)
        if not po:
            raise NotFoundException(f"Purchase Order with ID '{obj_in.purchase_order_id}' not found.")

        supplier = await supplier_repository.get_by_id(db, obj_in.supplier_id)
        if not supplier:
            raise NotFoundException(f"Supplier with ID '{obj_in.supplier_id}' not found.")

        wh = await warehouse_repository.get_by_id(db, obj_in.warehouse_id)
        if not wh:
            raise NotFoundException(f"Warehouse with ID '{obj_in.warehouse_id}' not found.")

        # Generate Return Number (PRTN-YYYY-XXXXX)
        count = (await purchase_return_repository.get_multi_paginated(db, limit=1))[1] + 1
        rtn_num = f"PRTN-{datetime.now().year}-{count:05d}"

        tot_amount = Decimal("0.0")
        items: List[PurchaseReturnItem] = []

        for item_in in obj_in.items:
            po_item = next((i for i in po.items if i.id == item_in.po_item_id), None)
            if not po_item:
                raise NotFoundException(f"PO Item with ID '{item_in.po_item_id}' not found in PO #{po.po_number}.")

            product = await product_repository.get_by_id(db, item_in.product_id)
            if not product:
                raise NotFoundException(f"Product with ID '{item_in.product_id}' not found.")

            ret_qty = Decimal(str(item_in.return_quantity))
            avail_ret = Decimal(str(po_item.received_quantity)) - Decimal(str(po_item.returned_quantity))
            if ret_qty > avail_ret:
                raise ValidationException(f"Return quantity ({ret_qty}) exceeds net received stock ({avail_ret}) for SKU '{product.sku}'.")

            price = Decimal(str(item_in.unit_price))
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
        )
        return ret

    async def get_return(self, db: AsyncSession, return_id: uuid.UUID) -> PurchaseReturn:
        ret = await purchase_return_repository.get_by_id(db, return_id)
        if not ret:
            raise NotFoundException(f"Purchase Return with ID '{return_id}' not found.")
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
        Processes Purchase Return by executing stock reversal (OUT ledger entry) and updating PO returned quantities.
        """
        ret = await self.get_return(db, return_id)
        if ret.status in ("Processed", "Cancelled"):
            raise ValidationException(f"Cannot process return in state '{ret.status}'.")

        po = await purchase_order_repository.get_by_id(db, ret.purchase_order_id)

        # Execute stock reversal for each returned line item
        for item in ret.items:
            await stock_ledger_service.create_ledger_entry(
                db,
                product_id=item.product_id,
                warehouse_id=ret.warehouse_id,
                storage_location_id=None,
                transaction_type_code="RETURN_OUT",
                quantity=Decimal(str(item.return_quantity)),
                direction="OUT",
                reference_type="PurchaseReturn",
                reference_id=ret.id,
                remarks=f"Purchase Return #{ret.return_number} ({ret.reason_code})",
                current_user_id=current_user_id,
            )

            # Update PO Item returned quantity counter
            if po:
                po_item = next((i for i in po.items if i.id == item.po_item_id), None)
                if po_item:
                    po_item.returned_quantity += Decimal(str(item.return_quantity))

        ret.status = "Processed"
        ret.approved_by = current_user_id
        await db.commit()
        await db.refresh(ret)

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
