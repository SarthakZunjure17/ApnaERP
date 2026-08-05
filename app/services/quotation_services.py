from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import NotFoundException, ValidationException
from app.models.sales_quotation import SalesQuotation, SalesQuotationItem
from app.repositories.sales_repos import (
    customer_repository,
    sales_quotation_repository,
)
from app.repositories.inventory_repos import product_repository
from app.schemas.sales import SalesQuotationCreate, SalesQuotationUpdate
from app.services.audit_log import audit_log_service
from app.services.pricing_services import discount_service


class QuotationService:
    async def _generate_quotation_number(self, db: AsyncSession) -> str:
        count_stmt = await sales_quotation_repository.get_all(db, limit=1)
        # Unique timestamp based code
        uid = uuid.uuid4().hex[:6].upper()
        return f"SQ-{datetime.now(timezone.utc).strftime('%Y%m')}-{uid}"

    async def create_quotation(
        self, db: AsyncSession, obj_in: SalesQuotationCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> SalesQuotation:
        cust = await customer_repository.get_by_id(db, obj_in.customer_id)
        if not cust or cust.is_deleted:
            raise NotFoundException(f"Customer ID '{obj_in.customer_id}' not found.")

        q_number = await self._generate_quotation_number(db)
        quotation = await sales_quotation_repository.create(
            db,
            obj_in={
                "quotation_number": q_number,
                "customer_id": obj_in.customer_id,
                "quotation_date": datetime.now(timezone.utc),
                "validity_date": obj_in.validity_date,
                "currency": obj_in.currency,
                "status": "Draft",
                "revision_number": 1,
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

        for item_in in obj_in.items:
            prod = await product_repository.get_by_id(db, item_in.product_id)
            if not prod:
                raise NotFoundException(f"Product ID '{item_in.product_id}' not found.")

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

            item_obj = SalesQuotationItem(
                quotation_id=quotation.id,
                product_id=item_in.product_id,
                description=item_in.description or prod.name,
                quantity=item_in.quantity,
                unit_price=item_in.unit_price,
                discount_type=item_in.discount_type,
                discount_value=item_in.discount_value,
                discount_amount=disc_amt,
                tax_rate=item_in.tax_rate,
                tax_amount=tax_amt,
                line_total=line_tot,
                warehouse_id=item_in.warehouse_id,
            )
            quotation.items.append(item_obj)

        net_total = subtotal - total_discount + total_tax
        quotation.subtotal_amount = subtotal
        quotation.discount_amount = total_discount
        quotation.tax_amount = total_tax
        quotation.total_amount = net_total

        await db.commit()

        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="QUOTATION_CREATE",
            entity_type="SalesQuotation",
            entity_id=str(quotation.id),
            new_data={"quotation_number": q_number, "total_amount": float(net_total)},
        )
        return quotation

    async def update_quotation(
        self,
        db: AsyncSession,
        quotation_id: uuid.UUID,
        obj_in: SalesQuotationUpdate,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> SalesQuotation:
        quotation = await sales_quotation_repository.get_by_id(db, quotation_id)
        if not quotation:
            raise NotFoundException(f"Quotation ID '{quotation_id}' not found.")

        if quotation.status not in ("Draft", "Submitted"):
            raise ValidationException(f"Cannot update quotation in status '{quotation.status}'.")

        quotation.revision_number += 1
        if obj_in.validity_date:
            quotation.validity_date = obj_in.validity_date
        if obj_in.currency:
            quotation.currency = obj_in.currency
        if obj_in.remarks is not None:
            quotation.remarks = obj_in.remarks

        if obj_in.items is not None:
            # Clear items and recalculate
            quotation.items.clear()
            subtotal = Decimal("0.00")
            total_discount = Decimal("0.00")
            total_tax = Decimal("0.00")

            for item_in in obj_in.items:
                prod = await product_repository.get_by_id(db, item_in.product_id)
                if not prod:
                    raise NotFoundException(f"Product ID '{item_in.product_id}' not found.")

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

                item_obj = SalesQuotationItem(
                    quotation_id=quotation.id,
                    product_id=item_in.product_id,
                    description=item_in.description or prod.name,
                    quantity=item_in.quantity,
                    unit_price=item_in.unit_price,
                    discount_type=item_in.discount_type,
                    discount_value=item_in.discount_value,
                    discount_amount=disc_amt,
                    tax_rate=item_in.tax_rate,
                    tax_amount=tax_amt,
                    line_total=line_tot,
                    warehouse_id=item_in.warehouse_id,
                )
                db.add(item_obj)

            quotation.subtotal_amount = subtotal
            quotation.discount_amount = total_discount
            quotation.tax_amount = total_tax
            quotation.total_amount = subtotal - total_discount + total_tax

        await db.commit()
        full_q = await sales_quotation_repository.get_by_id(db, quotation.id)
        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="QUOTATION_UPDATE",
            entity_type="SalesQuotation",
            entity_id=str(quotation_id),
            new_data={"revision_number": quotation.revision_number},
        )
        return full_q

    async def get_quotation(self, db: AsyncSession, quotation_id: uuid.UUID) -> SalesQuotation:
        q = await sales_quotation_repository.get_by_id(db, quotation_id)
        if not q:
            raise NotFoundException(f"Quotation ID '{quotation_id}' not found.")
        return q

    async def list_quotations(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        status: Optional[str] = None,
        customer_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SalesQuotation], int]:
        return await sales_quotation_repository.search_quotations(
            db, query=query, status=status, customer_id=customer_id, skip=skip, limit=limit
        )

    async def submit_quotation(
        self, db: AsyncSession, quotation_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> SalesQuotation:
        q = await self.get_quotation(db, quotation_id)
        if q.status != "Draft":
            raise ValidationException(f"Quotation in status '{q.status}' cannot be submitted.")

        q.status = "Submitted"
        await db.commit()
        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="QUOTATION_SUBMIT",
            entity_type="SalesQuotation",
            entity_id=str(quotation_id),
        )
        return await self.get_quotation(db, quotation_id)

    async def approve_quotation(
        self, db: AsyncSession, quotation_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> SalesQuotation:
        q = await self.get_quotation(db, quotation_id)
        if q.status not in ("Draft", "Submitted"):
            raise ValidationException(f"Quotation in status '{q.status}' cannot be approved.")

        q.status = "Approved"
        q.approved_by = current_user_id
        q.approved_at = datetime.now(timezone.utc)
        await db.commit()
        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="QUOTATION_APPROVE",
            entity_type="SalesQuotation",
            entity_id=str(quotation_id),
        )
        return await self.get_quotation(db, quotation_id)

    async def reject_quotation(
        self, db: AsyncSession, quotation_id: uuid.UUID, reason: Optional[str] = None, current_user_id: Optional[uuid.UUID] = None
    ) -> SalesQuotation:
        q = await self.get_quotation(db, quotation_id)
        if q.status not in ("Draft", "Submitted"):
            raise ValidationException(f"Quotation in status '{q.status}' cannot be rejected.")

        q.status = "Rejected"
        if reason:
            q.remarks = f"{q.remarks or ''} [Rejected: {reason}]".strip()
        await db.commit()
        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="QUOTATION_REJECT",
            entity_type="SalesQuotation",
            entity_id=str(quotation_id),
        )
        return await self.get_quotation(db, quotation_id)

    async def clone_quotation(
        self, db: AsyncSession, quotation_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> SalesQuotation:
        source_q = await self.get_quotation(db, quotation_id)
        new_number = await self._generate_quotation_number(db)

        cloned = await sales_quotation_repository.create(
            db,
            obj_in={
                "quotation_number": new_number,
                "customer_id": source_q.customer_id,
                "quotation_date": datetime.now(timezone.utc),
                "validity_date": source_q.validity_date,
                "currency": source_q.currency,
                "status": "Draft",
                "revision_number": 1,
                "subtotal_amount": source_q.subtotal_amount,
                "discount_amount": source_q.discount_amount,
                "tax_amount": source_q.tax_amount,
                "total_amount": source_q.total_amount,
                "remarks": f"Cloned from {source_q.quotation_number}",
                "created_by": current_user_id,
            },
        )

        for item in source_q.items:
            item_obj = SalesQuotationItem(
                quotation_id=cloned.id,
                product_id=item.product_id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount_type=item.discount_type,
                discount_value=item.discount_value,
                discount_amount=item.discount_amount,
                tax_rate=item.tax_rate,
                tax_amount=item.tax_amount,
                line_total=item.line_total,
                warehouse_id=item.warehouse_id,
            )
            db.add(item_obj)

        await db.commit()
        return await sales_quotation_repository.get_by_id(db, cloned.id)

    async def expire_quotations(self, db: AsyncSession) -> int:
        now = datetime.now(timezone.utc)
        # Find active quotations past validity_date
        quots, _ = await sales_quotation_repository.search_quotations(db, status="Submitted", limit=500)
        expired_count = 0
        for q in quots:
            if q.validity_date and q.validity_date < now:
                q.status = "Expired"
                expired_count += 1
        if expired_count > 0:
            await db.commit()
        return expired_count


quotation_service = QuotationService()
