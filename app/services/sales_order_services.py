import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import NotFoundException, ValidationException
from app.models.sales_order import SalesOrder, SalesOrderItem
from app.models.user import User
from app.repositories.sales_repos import (
    customer_repository,
    sales_order_repository,
    sales_quotation_repository,
)
from app.repositories.inventory_repos import product_repository
from app.schemas.approval_workflow import ApprovalRequestCreate
from app.schemas.sales import SalesOrderCreate, SalesOrderUpdate
from app.services.approval_engine import ApprovalEngineService
from app.services.audit_log import audit_log_service
from app.services.customer_services import customer_service
from app.services.pricing_services import discount_service

logger = logging.getLogger(__name__)


class SalesOrderService:
    async def _generate_order_number(self, db: AsyncSession) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"SO-{year}-"
        max_suffix = await sales_order_repository.get_max_number_suffix(db, prefix=prefix)
        new_num = max_suffix + 1
        return f"{prefix}{new_num:05d}"

    async def create_order(
        self, db: AsyncSession, obj_in: SalesOrderCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> SalesOrder:
        cust = await customer_repository.get_by_id(db, obj_in.customer_id)
        if not cust or cust.is_deleted:
            raise NotFoundException(f"Customer ID '{obj_in.customer_id}' not found.")
        if cust.status != "Active":
            raise ValidationException(f"Customer '{cust.name}' is {cust.status.lower()} and cannot be used for sales orders.")

        if not obj_in.items:
            raise ValidationException("Sales Order must have at least one line item.")

        # If quotation_id is provided, verify it exists and is eligible
        if obj_in.quotation_id:
            quot = await sales_quotation_repository.get_for_update(db, obj_in.quotation_id)
            if not quot:
                raise NotFoundException(f"Sales Quotation ID '{obj_in.quotation_id}' not found.")
            if quot.status == "Converted":
                raise ValidationException("Quotation has already been converted to a Sales Order.")
            if quot.status != "Approved":
                raise ValidationException(f"Only Approved quotations can be converted to a Sales Order. Current status: '{quot.status}'.")

        so_number = await self._generate_order_number(db)
        order = await sales_order_repository.create(
            db,
            obj_in={
                "order_number": so_number,
                "customer_id": obj_in.customer_id,
                "quotation_id": obj_in.quotation_id,
                "order_date": datetime.now(timezone.utc),
                "status": "Draft",
                "delivery_status": "Pending",
                "revision_number": 1,
                "currency": obj_in.currency,
                "payment_terms": obj_in.payment_terms,
                "shipping_address_id": obj_in.shipping_address_id,
                "billing_address_id": obj_in.billing_address_id,
                "remarks": obj_in.remarks,
                "created_by": current_user_id,
                "subtotal_amount": Decimal("0.00"),
                "discount_amount": Decimal("0.00"),
                "tax_amount": Decimal("0.00"),
                "total_amount": Decimal("0.00"),
            },
        )

        subtotal = Decimal("0.00")
        total_discount = Decimal("0.00")
        total_tax = Decimal("0.00")
        total_qty = Decimal("0.00")

        for item_in in obj_in.items:
            if item_in.quantity <= Decimal("0.00"):
                raise ValidationException("Item quantity must be greater than 0.")
            if item_in.unit_price < Decimal("0.00"):
                raise ValidationException("Item unit price cannot be negative.")

            prod = await product_repository.get_by_id(db, item_in.product_id)
            if not prod:
                raise NotFoundException(f"Product ID '{item_in.product_id}' not found.")
            if hasattr(prod, "is_active") and not prod.is_active:
                raise ValidationException(f"Product '{prod.name}' is inactive and cannot be ordered.")

            gross = item_in.unit_price * item_in.quantity
            disc_amt = await discount_service.calculate_line_discount(
                item_in.unit_price, item_in.quantity, item_in.discount_type, item_in.discount_value
            )
            after_disc = gross - disc_amt
            tax_amt = round(after_disc * (item_in.tax_rate / Decimal("100.00")), 2)
            line_tot = after_disc + tax_amt

            subtotal += gross
            total_discount += disc_amt
            total_tax += tax_amt
            total_qty += item_in.quantity

            item_obj = SalesOrderItem(
                sales_order_id=order.id,
                product_id=item_in.product_id,
                description=item_in.description or prod.name,
                quantity=item_in.quantity,
                delivered_quantity=Decimal("0.0000"),
                unit_price=item_in.unit_price,
                discount_type=item_in.discount_type,
                discount_value=item_in.discount_value,
                discount_amount=disc_amt,
                tax_rate=item_in.tax_rate,
                tax_amount=tax_amt,
                line_total=line_tot,
                warehouse_id=item_in.warehouse_id,
                delivery_date=item_in.delivery_date,
                status="Pending",
            )
            order.items.append(item_obj)

        # Document-level discount evaluation
        doc_disc = await discount_service.evaluate_document_discounts(db, subtotal - total_discount, total_qty)
        total_discount += doc_disc

        net_total = subtotal - total_discount + total_tax
        order.subtotal_amount = subtotal
        order.discount_amount = total_discount
        order.tax_amount = total_tax
        order.total_amount = net_total

        # Update quotation status if linked
        if obj_in.quotation_id:
            quot = await sales_quotation_repository.get_by_id(db, obj_in.quotation_id)
            if quot:
                quot.status = "Converted"

        await db.commit()

        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="SALES_ORDER_CREATE",
            entity_type="SalesOrder",
            entity_id=str(order.id),
            new_data={"order_number": so_number, "total_amount": float(net_total)},
        )
        return order

    async def create_from_quotation(
        self, db: AsyncSession, quotation_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> SalesOrder:
        quotation = await sales_quotation_repository.get_for_update(db, quotation_id)
        if not quotation:
            raise NotFoundException(f"Sales Quotation ID '{quotation_id}' not found.")

        if quotation.status == "Converted":
            raise ValidationException("Quotation has already been converted to a Sales Order.")

        if quotation.status != "Approved":
            raise ValidationException(
                f"Only Approved quotations can be converted to a Sales Order. Current status: '{quotation.status}'."
            )

        cust = await customer_repository.get_by_id(db, quotation.customer_id)
        if not cust or cust.is_deleted:
            raise NotFoundException(f"Customer ID '{quotation.customer_id}' not found.")
        if cust.status != "Active":
            raise ValidationException(f"Customer '{cust.name}' is {cust.status.lower()} and cannot place orders.")

        if not quotation.items:
            raise ValidationException("Source quotation has no line items.")

        so_number = await self._generate_order_number(db)
        order = await sales_order_repository.create(
            db,
            obj_in={
                "order_number": so_number,
                "customer_id": quotation.customer_id,
                "quotation_id": quotation.id,
                "order_date": datetime.now(timezone.utc),
                "status": "Draft",
                "delivery_status": "Pending",
                "revision_number": 1,
                "currency": quotation.currency,
                "remarks": quotation.remarks,
                "created_by": current_user_id,
                "subtotal_amount": quotation.subtotal_amount,
                "discount_amount": quotation.discount_amount,
                "tax_amount": quotation.tax_amount,
                "total_amount": quotation.total_amount,
            },
        )

        for q_item in quotation.items:
            item_obj = SalesOrderItem(
                sales_order_id=order.id,
                product_id=q_item.product_id,
                description=q_item.description,
                quantity=q_item.quantity,
                delivered_quantity=Decimal("0.0000"),
                unit_price=q_item.unit_price,
                discount_type=q_item.discount_type,
                discount_value=q_item.discount_value,
                discount_amount=q_item.discount_amount,
                tax_rate=q_item.tax_rate,
                tax_amount=q_item.tax_amount,
                line_total=q_item.line_total,
                warehouse_id=q_item.warehouse_id,
                status="Pending",
            )
            order.items.append(item_obj)

        quotation.status = "Converted"
        await db.commit()

        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="SALES_ORDER_CREATE",
            entity_type="SalesOrder",
            entity_id=str(order.id),
            new_data={"order_number": so_number, "quotation_id": str(quotation.id), "total_amount": float(order.total_amount)},
        )
        return order

    async def update_order(
        self,
        db: AsyncSession,
        order_id: uuid.UUID,
        obj_in: SalesOrderUpdate,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> SalesOrder:
        order = await sales_order_repository.get_by_id(db, order_id)
        if not order:
            raise NotFoundException(f"Sales Order ID '{order_id}' not found.")

        if order.status != "Draft":
            raise ValidationException(f"Cannot update Sales Order in status '{order.status}'. Only Draft orders can be updated.")

        order.revision_number += 1
        if obj_in.payment_terms:
            order.payment_terms = obj_in.payment_terms
        if obj_in.shipping_address_id:
            order.shipping_address_id = obj_in.shipping_address_id
        if obj_in.billing_address_id:
            order.billing_address_id = obj_in.billing_address_id
        if obj_in.remarks is not None:
            order.remarks = obj_in.remarks

        if obj_in.items is not None:
            if not obj_in.items:
                raise ValidationException("Sales Order must have at least one line item.")
            order.items.clear()
            subtotal = Decimal("0.00")
            total_discount = Decimal("0.00")
            total_tax = Decimal("0.00")

            for item_in in obj_in.items:
                if item_in.quantity <= Decimal("0.00"):
                    raise ValidationException("Item quantity must be greater than 0.")
                if item_in.unit_price < Decimal("0.00"):
                    raise ValidationException("Item unit price cannot be negative.")

                prod = await product_repository.get_by_id(db, item_in.product_id)
                if not prod:
                    raise NotFoundException(f"Product ID '{item_in.product_id}' not found.")
                if hasattr(prod, "is_active") and not prod.is_active:
                    raise ValidationException(f"Product '{prod.name}' is inactive and cannot be ordered.")

                gross = item_in.unit_price * item_in.quantity
                disc_amt = await discount_service.calculate_line_discount(
                    item_in.unit_price, item_in.quantity, item_in.discount_type, item_in.discount_value
                )
                after_disc = gross - disc_amt
                tax_amt = round(after_disc * (item_in.tax_rate / Decimal("100.00")), 2)
                line_tot = after_disc + tax_amt

                subtotal += gross
                total_discount += disc_amt
                total_tax += tax_amt

                item_obj = SalesOrderItem(
                    sales_order_id=order.id,
                    product_id=item_in.product_id,
                    description=item_in.description or prod.name,
                    quantity=item_in.quantity,
                    delivered_quantity=Decimal("0.0000"),
                    unit_price=item_in.unit_price,
                    discount_type=item_in.discount_type,
                    discount_value=item_in.discount_value,
                    discount_amount=disc_amt,
                    tax_rate=item_in.tax_rate,
                    tax_amount=tax_amt,
                    line_total=line_tot,
                    warehouse_id=item_in.warehouse_id,
                    delivery_date=item_in.delivery_date,
                    status="Pending",
                )
                db.add(item_obj)

            order.subtotal_amount = subtotal
            order.discount_amount = total_discount
            order.tax_amount = total_tax
            order.total_amount = subtotal - total_discount + total_tax

        await db.commit()
        full_order = await sales_order_repository.get_by_id(db, order.id)
        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="SALES_ORDER_UPDATE",
            entity_type="SalesOrder",
            entity_id=str(order_id),
            new_data={"revision_number": order.revision_number},
        )
        return full_order

    async def get_order(self, db: AsyncSession, order_id: uuid.UUID) -> SalesOrder:
        order = await sales_order_repository.get_by_id(db, order_id)
        if not order:
            raise NotFoundException(f"Sales Order ID '{order_id}' not found.")
        return order

    async def list_orders(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        status: Optional[str] = None,
        delivery_status: Optional[str] = None,
        customer_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SalesOrder], int]:
        return await sales_order_repository.search_orders(
            db, query=query, status=status, delivery_status=delivery_status, customer_id=customer_id, skip=skip, limit=limit
        )

    async def submit_order(
        self, db: AsyncSession, order_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> SalesOrder:
        order = await self.get_order(db, order_id)
        if order.status != "Draft":
            raise ValidationException(f"Sales Order in status '{order.status}' cannot be submitted.")
        if not order.items:
            raise ValidationException("Sales Order must have at least one line item before submission.")

        cust = await customer_repository.get_by_id(db, order.customer_id)
        if cust and cust.status != "Active":
            raise ValidationException(f"Customer '{cust.name}' is {cust.status.lower()} and cannot be used for order submission.")

        order.status = "Submitted"
        await db.commit()

        # Submit to ApprovalEngineService via start_workflow
        approval_service = ApprovalEngineService(db)
        actor_user = None
        if current_user_id:
            from app.repositories.user import user_repository
            actor_user = await user_repository.get_by_id(db, current_user_id)
        if not actor_user:
            actor_user = User(
                id=current_user_id or order.created_by or uuid.uuid4(),
                email="system@apnaerp.com",
                username="system",
                is_active=True,
            )

        try:
            workflow_data = ApprovalRequestCreate(
                workflow_code="WF_SALES_ORDER",
                entity_type="SalesOrder",
                entity_id=str(order.id),
                comments=f"Sales Order #{order.order_number} - Total: {order.currency} {order.total_amount}",
            )
            await approval_service.start_workflow(workflow_data, actor_user)
        except Exception as exc:
            logger.info(f"No configured approval workflow for SalesOrder ({exc}). Status remains Submitted.")

        await db.commit()
        await db.refresh(order)

        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="SALES_ORDER_SUBMIT",
            entity_type="SalesOrder",
            entity_id=str(order_id),
        )
        return await self.get_order(db, order_id)

    async def approve_order(
        self, db: AsyncSession, order_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> SalesOrder:
        order = await self.get_order(db, order_id)
        if order.status not in ("Draft", "Submitted"):
            raise ValidationException(f"Sales Order in status '{order.status}' cannot be approved.")

        # Check Customer credit limit and active status before approving
        await customer_service.check_credit_limit(db, order.customer_id, order.total_amount)

        order.status = "Approved"
        order.approved_by = current_user_id
        order.approved_at = datetime.now(timezone.utc)
        await db.commit()
        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="SALES_ORDER_APPROVE",
            entity_type="SalesOrder",
            entity_id=str(order_id),
        )
        return order

    async def reject_order(
        self, db: AsyncSession, order_id: uuid.UUID, reason: Optional[str] = None, current_user_id: Optional[uuid.UUID] = None
    ) -> SalesOrder:
        order = await self.get_order(db, order_id)
        if order.status not in ("Draft", "Submitted"):
            raise ValidationException(f"Sales Order in status '{order.status}' cannot be rejected.")

        order.status = "Rejected"
        if reason:
            order.remarks = f"{order.remarks or ''} [Rejected: {reason}]".strip()
        await db.commit()
        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="SALES_ORDER_REJECT",
            entity_type="SalesOrder",
            entity_id=str(order_id),
        )
        return await self.get_order(db, order_id)

    async def cancel_order(
        self, db: AsyncSession, order_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> SalesOrder:
        order = await self.get_order(db, order_id)
        if order.status in ("Closed", "Cancelled", "Fulfilled", "Partially Fulfilled", "Fully Delivered"):
            raise ValidationException(f"Sales Order in status '{order.status}' cannot be cancelled.")

        # Ensure no delivered quantity has occurred
        for item in order.items:
            if item.delivered_quantity and item.delivered_quantity > Decimal("0.0000"):
                raise ValidationException("Cannot cancel Sales Order that has already had partial or complete fulfillment.")

        order.status = "Cancelled"
        order.delivery_status = "Cancelled"
        for item in order.items:
            item.status = "Cancelled"

        await db.commit()
        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="SALES_ORDER_CANCEL",
            entity_type="SalesOrder",
            entity_id=str(order_id),
        )
        return await self.get_order(db, order_id)

    async def close_order(
        self, db: AsyncSession, order_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> SalesOrder:
        order = await self.get_order(db, order_id)
        order.status = "Closed"
        await db.commit()
        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="SALES_ORDER_CLOSE",
            entity_type="SalesOrder",
            entity_id=str(order_id),
        )
        return order

    async def reopen_order(
        self, db: AsyncSession, order_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> SalesOrder:
        order = await self.get_order(db, order_id)
        if order.status != "Closed":
            raise ValidationException(f"Sales Order in status '{order.status}' is not closed.")

        order.status = "Approved"
        await db.commit()
        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="SALES_ORDER_REOPEN",
            entity_type="SalesOrder",
            entity_id=str(order_id),
        )
        return order


sales_order_service = SalesOrderService()
