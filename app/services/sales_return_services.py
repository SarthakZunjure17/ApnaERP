from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import NotFoundException, ValidationException
from app.models.sales_return import SalesReturn, SalesReturnItem
from app.repositories.sales_repos import (
    sales_order_repository,
    sales_return_repository,
)
from app.repositories.inventory_repos import product_repository, warehouse_repository
from app.schemas.sales import SalesReturnCreate
from app.schemas.warehouse_operations import GoodsReceiptCreate, GoodsReceiptItemCreate
from app.services.audit_log import audit_log_service
from app.services.warehouse_operations_services import goods_receipt_service


class SalesReturnService:
    async def _generate_return_number(self, db: AsyncSession) -> str:
        uid = uuid.uuid4().hex[:6].upper()
        return f"SR-{datetime.now(timezone.utc).strftime('%Y%m')}-{uid}"

    async def create_return(
        self, db: AsyncSession, obj_in: SalesReturnCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> SalesReturn:
        order = await sales_order_repository.get_by_id(db, obj_in.sales_order_id)
        if not order:
            raise NotFoundException(f"Sales Order ID '{obj_in.sales_order_id}' not found.")

        wh = await warehouse_repository.get_by_id(db, obj_in.warehouse_id)
        if not wh:
            raise NotFoundException(f"Warehouse ID '{obj_in.warehouse_id}' not found.")

        ret_number = await self._generate_return_number(db)
        sales_return = await sales_return_repository.create(
            db,
            obj_in={
                "return_number": ret_number,
                "sales_order_id": obj_in.sales_order_id,
                "delivery_order_id": obj_in.delivery_order_id,
                "customer_id": order.customer_id,
                "warehouse_id": obj_in.warehouse_id,
                "return_date": datetime.now(timezone.utc),
                "status": "Draft",
                "reason_code": obj_in.reason_code,
                "remarks": obj_in.remarks,
                "created_by": current_user_id,
                "total_refund_amount": Decimal("0.00"),
            },
        )

        total_refund = Decimal("0.00")
        for item_in in obj_in.items:
            so_item = next((i for i in order.items if i.id == item_in.sales_order_item_id), None)
            if not so_item:
                raise NotFoundException(f"SalesOrderItem ID '{item_in.sales_order_item_id}' not found in order.")

            refund = round(so_item.unit_price * item_in.quantity, 2)
            total_refund += refund

            ret_item = SalesReturnItem(
                sales_return_id=sales_return.id,
                sales_order_item_id=so_item.id,
                product_id=item_in.product_id,
                quantity=item_in.quantity,
                unit_price=so_item.unit_price,
                refund_amount=refund,
                reason=item_in.reason,
            )
            sales_return.items.append(ret_item)

        sales_return.total_refund_amount = total_refund
        await db.commit()

        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="SALES_RETURN_CREATE",
            entity_type="SalesReturn",
            entity_id=str(sales_return.id),
            new_data={"return_number": ret_number, "total_refund": float(total_refund)},
        )
        return sales_return

    async def approve_return(
        self, db: AsyncSession, return_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> SalesReturn:
        ret = await sales_return_repository.get_by_id(db, return_id)
        if not ret:
            raise NotFoundException(f"Sales Return ID '{return_id}' not found.")

        if ret.status not in ("Draft", "Submitted"):
            raise ValidationException(f"Sales Return in status '{ret.status}' cannot be approved.")

        ret.status = "Approved"
        ret.approved_by = current_user_id
        await db.commit()

        # Execute stock reversal via GoodsReceipt in Warehouse Operations
        try:
            gr_items = [
                GoodsReceiptItemCreate(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_cost=item.unit_price,
                    remarks=f"Sales Return {ret.return_number}",
                )
                for item in ret.items
            ]
            gr_code = f"GR-SR-{ret.return_number}"
            gr_in = GoodsReceiptCreate(
                receipt_number=gr_code,
                warehouse_id=ret.warehouse_id,
                receipt_date=datetime.now(timezone.utc),
                receipt_type="Return",
                remarks=f"Stock reversal for Sales Return {ret.return_number}",
                items=gr_items,
            )
            gr = await goods_receipt_service.create_receipt(db, obj_in=gr_in, current_user_id=current_user_id)
            await goods_receipt_service.approve_receipt(db, gr.id, current_user_id=current_user_id)
            gr_executed = await goods_receipt_service.receive_receipt(db, gr.id, current_user_id=current_user_id)
            ret.goods_receipt_id = gr_executed.id
        except Exception as e:
            pass

        ret.status = "Completed"
        await db.commit()

        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="SALES_RETURN_APPROVE",
            entity_type="SalesReturn",
            entity_id=str(return_id),
        )
        return ret

    async def get_return(self, db: AsyncSession, return_id: uuid.UUID) -> SalesReturn:
        r = await sales_return_repository.get_by_id(db, return_id)
        if not r:
            raise NotFoundException(f"Sales Return ID '{return_id}' not found.")
        return r

    async def list_returns(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        status: Optional[str] = None,
        sales_order_id: Optional[uuid.UUID] = None,
        customer_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SalesReturn], int]:
        return await sales_return_repository.search_returns(
            db, query=query, status=status, sales_order_id=sales_order_id, customer_id=customer_id, skip=skip, limit=limit
        )


sales_return_service = SalesReturnService()
