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
from app.models.supplier_quotation import (
    SupplierQuotation,
    SupplierQuotationItem,
)
from app.repositories.inventory_repos import product_repository
from app.repositories.procurement_repos import (
    rfq_repository,
    supplier_quotation_repository,
    supplier_repository,
)
from app.schemas.procurement import (
    SupplierQuotationCreate,
    SupplierQuotationUpdate,
)
from app.services.audit_log import audit_log_service

logger = logging.getLogger("app.services.quotation")


class QuotationService:
    """
    Domain service for managing Supplier Quotations, pricing calculation, tax & discount processing, and validity tracking.
    """
    async def create_quotation(
        self, db: AsyncSession, obj_in: SupplierQuotationCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> SupplierQuotation:
        supplier = await supplier_repository.get_by_id(db, obj_in.supplier_id)
        if not supplier or supplier.is_deleted:
            raise NotFoundException(f"Supplier with ID '{obj_in.supplier_id}' not found.")
        if supplier.status == "Blacklisted":
            raise ValidationException("Cannot accept quotation from a blacklisted supplier.")

        if obj_in.rfq_id:
            rfq = await rfq_repository.get_by_id(db, obj_in.rfq_id)
            if not rfq:
                raise NotFoundException(f"RFQ with ID '{obj_in.rfq_id}' not found.")

        # Generate Quotation Number (SQ-YYYY-XXXXX)
        count = (await supplier_quotation_repository.get_multi_paginated(db, limit=1))[1] + 1
        sq_num = f"SQ-{datetime.now().year}-{count:05d}"

        subtotal = Decimal("0.0")
        tax_total = Decimal("0.0")
        disc_total = Decimal("0.0")

        items: List[SupplierQuotationItem] = []
        for item_in in obj_in.items:
            product = await product_repository.get_by_id(db, item_in.product_id)
            if not product:
                raise NotFoundException(f"Product with ID '{item_in.product_id}' not found.")

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
                SupplierQuotationItem(
                    product_id=item_in.product_id,
                    quantity=qty,
                    unit_price=price,
                    discount_pct=disc_pct,
                    tax_pct=tax_pct,
                    total_price=line_tot,
                    delivery_days=item_in.delivery_days or obj_in.lead_time_days,
                    remarks=item_in.remarks,
                )
            )

        final_total = subtotal - disc_total + tax_total

        quotation = SupplierQuotation(
            quotation_number=sq_num,
            rfq_id=obj_in.rfq_id,
            supplier_id=obj_in.supplier_id,
            quotation_date=obj_in.quotation_date or datetime.now(timezone.utc),
            validity_date=obj_in.validity_date,
            lead_time_days=obj_in.lead_time_days,
            payment_terms=obj_in.payment_terms or supplier.payment_terms,
            currency=obj_in.currency or supplier.currency,
            subtotal=subtotal,
            tax_amount=tax_total,
            discount_amount=disc_total,
            total_amount=final_total,
            status="Submitted",
            notes=obj_in.notes,
            items=items,
        )
        db.add(quotation)
        await db.commit()
        await db.refresh(quotation)

        # Publish Domain Event
        domain_event_publisher.publish(
            "QuotationReceived",
            {
                "quotation_id": str(quotation.id),
                "quotation_number": quotation.quotation_number,
                "supplier_id": str(quotation.supplier_id),
                "total_amount": float(quotation.total_amount),
            },
        )

        await audit_log_service.log_event(
            db,
            action="QUOTATION_CREATE",
            entity_type="SupplierQuotation",
            entity_id=quotation.id,
            user_id=current_user_id,
        )
        return quotation

    async def get_quotation(self, db: AsyncSession, quotation_id: uuid.UUID) -> SupplierQuotation:
        sq = await supplier_quotation_repository.get_by_id(db, quotation_id)
        if not sq:
            raise NotFoundException(f"Supplier Quotation with ID '{quotation_id}' not found.")
        return sq

    async def approve_quotation(
        self, db: AsyncSession, quotation_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> SupplierQuotation:
        sq = await self.get_quotation(db, quotation_id)
        if sq.status in ("Approved", "Rejected", "Expired"):
            raise ValidationException(f"Quotation is in terminal state '{sq.status}'.")

        sq.status = "Approved"
        await db.commit()
        await db.refresh(sq)
        await redis_manager.delete_pattern("quotation:*")
        return sq

    async def list_quotations(
        self,
        db: AsyncSession,
        rfq_id: Optional[uuid.UUID] = None,
        supplier_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SupplierQuotation], int]:
        return await supplier_quotation_repository.get_multi_paginated(
            db, rfq_id=rfq_id, supplier_id=supplier_id, status=status, skip=skip, limit=limit
        )


quotation_service = QuotationService()
