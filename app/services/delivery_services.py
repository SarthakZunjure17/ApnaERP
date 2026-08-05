from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import NotFoundException, ValidationException
from app.models.delivery_order import DeliveryOrder, DeliveryOrderItem
from app.repositories.sales_repos import (
    delivery_order_repository,
    sales_order_repository,
)
from app.repositories.inventory_repos import product_repository, warehouse_repository
from app.schemas.sales import DeliveryOrderCreate
from app.schemas.warehouse_operations import GoodsIssueCreate, GoodsIssueItemCreate
from app.services.audit_log import audit_log_service
from app.services.warehouse_operations_services import goods_issue_service


class DeliveryService:
    async def _generate_delivery_number(self, db: AsyncSession) -> str:
        uid = uuid.uuid4().hex[:6].upper()
        return f"DO-{datetime.now(timezone.utc).strftime('%Y%m')}-{uid}"

    async def create_delivery(
        self, db: AsyncSession, obj_in: DeliveryOrderCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> DeliveryOrder:
        order = await sales_order_repository.get_by_id(db, obj_in.sales_order_id)
        if not order:
            raise NotFoundException(f"Sales Order ID '{obj_in.sales_order_id}' not found.")

        if order.status not in ("Approved", "Partially Delivered"):
            raise ValidationException(f"Cannot dispatch delivery for Sales Order in status '{order.status}'.")

        wh = await warehouse_repository.get_by_id(db, obj_in.warehouse_id)
        if not wh:
            raise NotFoundException(f"Warehouse ID '{obj_in.warehouse_id}' not found.")

        del_number = await self._generate_delivery_number(db)
        delivery = await delivery_order_repository.create(
            db,
            obj_in={
                "delivery_number": del_number,
                "sales_order_id": obj_in.sales_order_id,
                "warehouse_id": obj_in.warehouse_id,
                "dispatch_date": datetime.now(timezone.utc),
                "carrier": obj_in.carrier,
                "tracking_number": obj_in.tracking_number,
                "status": "Draft",
                "delivery_notes": obj_in.delivery_notes,
                "created_by": current_user_id,
            },
        )

        gi_items: List[GoodsIssueItemCreate] = []

        for item_in in obj_in.items:
            # Find matching sales order item
            so_item = next((i for i in order.items if i.id == item_in.sales_order_item_id), None)
            if not so_item:
                raise NotFoundException(f"SalesOrderItem ID '{item_in.sales_order_item_id}' not found in order.")

            remaining_qty = so_item.quantity - so_item.delivered_quantity
            if item_in.quantity > remaining_qty:
                raise ValidationException(
                    f"Delivery quantity {item_in.quantity} exceeds remaining order item balance {remaining_qty}."
                )

            so_item.delivered_quantity += item_in.quantity
            if so_item.delivered_quantity >= so_item.quantity:
                so_item.status = "Delivered"
            else:
                so_item.status = "Partial"

            del_item = DeliveryOrderItem(
                delivery_order_id=delivery.id,
                sales_order_item_id=so_item.id,
                product_id=item_in.product_id,
                quantity=item_in.quantity,
            )
            delivery.items.append(del_item)

            gi_items.append(
                GoodsIssueItemCreate(
                    product_id=item_in.product_id,
                    quantity=item_in.quantity,
                    remarks=f"Sales Delivery {del_number}",
                )
            )

        # Evaluate overall Sales Order status
        all_delivered = all(i.delivered_quantity >= i.quantity for i in order.items)
        if all_delivered:
            order.delivery_status = "Delivered"
            order.status = "Fully Delivered"
        else:
            order.delivery_status = "Partial"
            order.status = "Partially Delivered"

        await db.commit()

        # Trigger Warehouse Operations via GoodsIssue
        try:
            gi_code = f"GI-SO-{delivery.delivery_number}"
            gi_in = GoodsIssueCreate(
                issue_number=gi_code,
                warehouse_id=obj_in.warehouse_id,
                issue_date=datetime.now(timezone.utc),
                issue_reason="Sales",
                remarks=f"Stock issue for Sales Delivery {del_number}",
                items=gi_items,
            )
            gi = await goods_issue_service.create_issue(db, obj_in=gi_in, current_user_id=current_user_id)
            await goods_issue_service.approve_issue(db, gi.id, current_user_id=current_user_id)
            gi_executed = await goods_issue_service.issue_issue(db, gi.id, current_user_id=current_user_id)
            delivery.goods_issue_id = gi_executed.id
        except Exception as e:
            logger.warning(f"Warehouse GoodsIssue stock deduction skipped or failed for Delivery {del_number}: {e}")

        delivery.status = "Delivered"
        await db.commit()

        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="DELIVERY_ORDER_CREATE",
            entity_type="DeliveryOrder",
            entity_id=str(delivery.id),
            new_data={"delivery_number": del_number, "sales_order_id": str(order.id)},
        )
        return delivery

    async def get_delivery(self, db: AsyncSession, delivery_id: uuid.UUID) -> DeliveryOrder:
        d = await delivery_order_repository.get_by_id(db, delivery_id)
        if not d:
            raise NotFoundException(f"Delivery Order ID '{delivery_id}' not found.")
        return d

    async def list_deliveries(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        status: Optional[str] = None,
        sales_order_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[DeliveryOrder], int]:
        return await delivery_order_repository.search_deliveries(
            db, query=query, status=status, sales_order_id=sales_order_id, warehouse_id=warehouse_id, skip=skip, limit=limit
        )

    async def cancel_delivery(
        self, db: AsyncSession, delivery_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> DeliveryOrder:
        delivery = await self.get_delivery(db, delivery_id)
        if delivery.status == "Cancelled":
            raise ValidationException("Delivery Order is already cancelled.")

        delivery.status = "Cancelled"
        await db.commit()
        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="DELIVERY_ORDER_CANCEL",
            entity_type="DeliveryOrder",
            entity_id=str(delivery_id),
        )
        return delivery


delivery_service = DeliveryService()
