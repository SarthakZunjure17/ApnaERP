from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import Any, List, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import NotFoundException, ValidationException
from app.models.supplier_quotation import SupplierQuotation, SupplierQuotationItem
from app.repositories.inventory_repos import product_repository
from app.repositories.procurement_repos import (
    rfq_repository,
    rfq_supplier_repository,
    supplier_quotation_repository,
    supplier_repository,
)
from app.schemas.procurement import SupplierQuotationCreate, SupplierQuotationUpdate
from app.services.audit_log import audit_log_service

logger = logging.getLogger("app.services.supplier_quotation")


class SupplierQuotationService:
    """
    Domain service for Supplier Quotation lifecycle, line item calculation, and RFQ response tracking.
    Completely isolated from Sales Quotations.
    """

    async def _generate_quotation_number(self, db: AsyncSession) -> str:
        now = datetime.now(timezone.utc)
        ym = now.strftime("%Y%m")
        max_num = await supplier_quotation_repository.get_max_number_suffix(db, ym)
        return f"SQ-{ym}-{max_num + 1:05d}"

    async def create_quotation(
        self, db: AsyncSession, obj_in: SupplierQuotationCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> SupplierQuotation:
        # 1. Supplier Validation
        supplier = await supplier_repository.get_by_id(db, obj_in.supplier_id)
        if not supplier or supplier.is_deleted:
            raise NotFoundException(f"Supplier with ID '{obj_in.supplier_id}' not found.")
        if supplier.status != "Active":
            raise ValidationException(f"Cannot create quotation for supplier in '{supplier.status}' status. Supplier must be Active.")

        # 2. RFQ Validation (if RFQ specified)
        if obj_in.rfq_id:
            rfq = await rfq_repository.get_by_id(db, obj_in.rfq_id)
            if not rfq:
                raise NotFoundException(f"RFQ with ID '{obj_in.rfq_id}' not found.")
            if rfq.status in ("Closed", "Cancelled"):
                raise ValidationException(f"Cannot submit quotation for RFQ in status '{rfq.status}'.")

            # Check if supplier was invited to this RFQ
            invited = await rfq_supplier_repository.get_by_rfq_and_supplier(db, obj_in.rfq_id, obj_in.supplier_id)
            if not invited:
                raise ValidationException("Supplier is not invited to this RFQ.")

        # 3. Items validation
        if not obj_in.items:
            raise ValidationException("Quotation must contain at least one line item.")

        q_number = await self._generate_quotation_number(db)
        quotation_date = obj_in.quotation_date or datetime.now(timezone.utc)

        quotation = SupplierQuotation(
            quotation_number=q_number,
            rfq_id=obj_in.rfq_id,
            supplier_id=obj_in.supplier_id,
            quotation_date=quotation_date,
            validity_date=obj_in.validity_date,
            lead_time_days=obj_in.lead_time_days,
            payment_terms=obj_in.payment_terms,
            currency=obj_in.currency or "USD",
            status="Draft",
            subtotal=Decimal("0.0"),
            tax_amount=Decimal("0.0"),
            discount_amount=Decimal("0.0"),
            total_amount=Decimal("0.0"),
            notes=obj_in.notes,
        )
        db.add(quotation)
        await db.flush()

        subtotal = Decimal("0.0")
        total_discount = Decimal("0.0")
        total_tax = Decimal("0.0")

        for item_in in obj_in.items:
            product = await product_repository.get_by_id(db, item_in.product_id)
            if not product:
                raise NotFoundException(f"Product with ID '{item_in.product_id}' not found.")
            if not product.is_active:
                raise ValidationException(f"Product '{product.name}' is inactive.")

            qty = Decimal(str(item_in.quantity))
            if qty <= 0:
                raise ValidationException("Item quantity must be greater than 0.")

            price = Decimal(str(item_in.unit_price))
            if price < 0:
                raise ValidationException("Item unit price cannot be negative.")

            disc_pct = Decimal(str(item_in.discount_pct or 0))
            tax_pct = Decimal(str(item_in.tax_pct or 0))

            if disc_pct < 0 or disc_pct > 100:
                raise ValidationException("Discount percentage must be between 0 and 100.")
            if tax_pct < 0 or tax_pct > 100:
                raise ValidationException("Tax percentage must be between 0 and 100.")

            line_sub = qty * price
            disc_amt = line_sub * (disc_pct / Decimal("100"))
            taxable = line_sub - disc_amt
            tax_amt = taxable * (tax_pct / Decimal("100"))
            line_tot = taxable + tax_amt

            subtotal += line_sub
            total_discount += disc_amt
            total_tax += tax_amt

            item_obj = SupplierQuotationItem(
                quotation_id=quotation.id,
                product_id=item_in.product_id,
                quantity=qty,
                unit_price=price,
                discount_pct=disc_pct,
                tax_pct=tax_pct,
                total_price=line_tot,
                delivery_days=item_in.delivery_days,
                remarks=item_in.remarks,
            )
            db.add(item_obj)

        quotation.subtotal = subtotal
        quotation.discount_amount = total_discount
        quotation.tax_amount = total_tax
        quotation.total_amount = subtotal - total_discount + total_tax

        await db.commit()
        await db.refresh(quotation)

        await audit_log_service.log_event(
            db=db,
            action="SUPPLIER_QUOTATION_CREATE",
            entity_type="SupplierQuotation",
            entity_id=quotation.id,
            user_id=current_user_id,
            new_data={"quotation_number": q_number, "total_amount": float(quotation.total_amount)},
        )

        return await self.get_quotation(db, quotation.id)

    async def get_quotation(self, db: AsyncSession, quotation_id: uuid.UUID) -> SupplierQuotation:
        quotation = await supplier_quotation_repository.get_by_id(db, quotation_id)
        if not quotation:
            raise NotFoundException(f"Supplier Quotation with ID '{quotation_id}' not found.")
        return quotation

    async def update_quotation(
        self,
        db: AsyncSession,
        quotation_id: uuid.UUID,
        obj_in: SupplierQuotationUpdate,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> SupplierQuotation:
        quotation = await self.get_quotation(db, quotation_id)
        if quotation.status != "Draft":
            raise ValidationException(f"Only Draft supplier quotations can be updated. Current status: '{quotation.status}'.")

        if obj_in.validity_date is not None:
            quotation.validity_date = obj_in.validity_date
        if obj_in.lead_time_days is not None:
            quotation.lead_time_days = obj_in.lead_time_days
        if obj_in.payment_terms is not None:
            quotation.payment_terms = obj_in.payment_terms
        if obj_in.notes is not None:
            quotation.notes = obj_in.notes

        await db.commit()
        await db.refresh(quotation)

        await audit_log_service.log_event(
            db=db,
            action="SUPPLIER_QUOTATION_UPDATE",
            entity_type="SupplierQuotation",
            entity_id=quotation.id,
            user_id=current_user_id,
        )

        return quotation

    async def submit_quotation(
        self, db: AsyncSession, quotation_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> SupplierQuotation:
        quotation = await self.get_quotation(db, quotation_id)
        if quotation.status != "Draft":
            raise ValidationException(f"Only Draft supplier quotations can be submitted. Current status: '{quotation.status}'.")

        quotation.status = "Submitted"

        # If linked to RFQ, update RFQSupplier invitation status to Quoted
        if quotation.rfq_id:
            rfq_sup = await rfq_supplier_repository.get_by_rfq_and_supplier(db, quotation.rfq_id, quotation.supplier_id)
            if rfq_sup:
                rfq_sup.status = "Quoted"

        await db.commit()
        await db.refresh(quotation)

        await audit_log_service.log_event(
            db=db,
            action="SUPPLIER_QUOTATION_SUBMIT",
            entity_type="SupplierQuotation",
            entity_id=quotation.id,
            user_id=current_user_id,
        )

        return quotation

    async def withdraw_quotation(
        self, db: AsyncSession, quotation_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> SupplierQuotation:
        quotation = await self.get_quotation(db, quotation_id)
        if quotation.status not in ("Draft", "Submitted", "Under Review"):
            raise ValidationException(f"Cannot withdraw quotation in '{quotation.status}' status.")

        quotation.status = "Withdrawn"
        await db.commit()
        await db.refresh(quotation)

        await audit_log_service.log_event(
            db=db,
            action="SUPPLIER_QUOTATION_WITHDRAW",
            entity_type="SupplierQuotation",
            entity_id=quotation.id,
            user_id=current_user_id,
        )

        return quotation

    async def approve_quotation(
        self, db: AsyncSession, quotation_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> SupplierQuotation:
        quotation = await self.get_quotation(db, quotation_id)
        if quotation.status not in ("Draft", "Submitted", "Under Review"):
            raise ValidationException(f"Cannot approve quotation in '{quotation.status}' status.")

        quotation.status = "Approved"
        await db.commit()
        await db.refresh(quotation)

        await audit_log_service.log_event(
            db=db,
            action="SUPPLIER_QUOTATION_AWARD",
            entity_type="SupplierQuotation",
            entity_id=quotation.id,
            user_id=current_user_id,
        )

        return quotation

    async def reject_quotation(
        self, db: AsyncSession, quotation_id: uuid.UUID, reason: Optional[str] = None, current_user_id: Optional[uuid.UUID] = None
    ) -> SupplierQuotation:
        quotation = await self.get_quotation(db, quotation_id)
        if quotation.status not in ("Draft", "Submitted", "Under Review"):
            raise ValidationException(f"Cannot reject quotation in '{quotation.status}' status.")

        quotation.status = "Rejected"
        if reason:
            quotation.notes = (quotation.notes or "") + f"\n[Rejected]: {reason}"
        await db.commit()
        await db.refresh(quotation)
        return quotation

    async def list_quotations(
        self,
        db: AsyncSession,
        rfq_id: Optional[uuid.UUID] = None,
        supplier_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SupplierQuotation], int]:
        return await supplier_quotation_repository.get_multi_paginated(
            db, rfq_id=rfq_id, supplier_id=supplier_id, status=status, search=search, skip=skip, limit=limit
        )


supplier_quotation_service = SupplierQuotationService()
