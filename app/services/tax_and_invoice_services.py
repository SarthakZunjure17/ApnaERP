from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import NotFoundException, ValidationException
from app.repositories.sales_repos import sales_order_repository
from app.schemas.sales import SalesInvoicePayload, SalesInvoicePayloadItem


class TaxEngineService:
    """
    Interface for Tax Groups and Category calculations.
    Ensures future Finance module compatibility by computing item tax lines.
    """
    async def calculate_item_tax(
        self, amount: Decimal, tax_rate: Decimal
    ) -> Decimal:
        if amount <= Decimal("0.00") or tax_rate <= Decimal("0.00"):
            return Decimal("0.00")
        return round(amount * (tax_rate / Decimal("100.00")), 2)


class InvoicePayloadService:
    """
    Exposes sales invoice data payload for consumption by future Finance / AR domain.
    Does NOT write any accounting entries into general ledger.
    """
    async def generate_invoice_payload(self, db: AsyncSession, sales_order_id: uuid.UUID) -> SalesInvoicePayload:
        order = await sales_order_repository.get_by_id(db, sales_order_id)
        if not order:
            raise NotFoundException(f"Sales Order ID '{sales_order_id}' not found.")

        if order.status not in ("Partially Delivered", "Fully Delivered", "Approved", "Closed"):
            raise ValidationException(f"Cannot generate invoice payload for Sales Order in status '{order.status}'.")

        items_payload = []
        for i in order.items:
            items_payload.append(
                SalesInvoicePayloadItem(
                    product_id=i.product_id,
                    product_sku=i.product.sku if i.product else "N/A",
                    product_name=i.product.name if i.product else (i.description or "Product"),
                    quantity=i.delivered_quantity if i.delivered_quantity > Decimal("0.00") else i.quantity,
                    unit_price=i.unit_price,
                    discount_amount=i.discount_amount,
                    tax_rate=i.tax_rate,
                    tax_amount=i.tax_amount,
                    line_total=i.line_total,
                )
            )

        return SalesInvoicePayload(
            sales_order_id=order.id,
            order_number=order.order_number,
            customer_id=order.customer_id,
            customer_name=order.customer.name if order.customer else "Unknown Customer",
            customer_tax_id=order.customer.tax_id if order.customer else None,
            currency=order.currency,
            order_date=order.order_date,
            subtotal_amount=order.subtotal_amount,
            discount_amount=order.discount_amount,
            tax_amount=order.tax_amount,
            total_amount=order.total_amount,
            payment_terms=order.payment_terms,
            items=items_payload,
            generated_at=datetime.now(timezone.utc),
        )


tax_engine_service = TaxEngineService()
invoice_payload_service = InvoicePayloadService()
