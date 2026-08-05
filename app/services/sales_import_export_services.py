import csv
import io
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.sales import CustomerCreate, CustomerContactCreate, CustomerAddressCreate
from app.services.customer_services import customer_service
from app.repositories.sales_repos import (
    customer_repository,
    sales_order_repository,
    sales_quotation_repository,
)


class SalesImportExportService:
    async def export_customers_csv(self, db: AsyncSession) -> str:
        custs, _ = await customer_repository.search_customers(db, limit=1000)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["customer_code", "name", "email", "phone", "tax_id", "credit_limit", "payment_terms", "status", "rating"])
        for c in custs:
            writer.writerow([c.customer_code, c.name, c.email or "", c.phone or "", c.tax_id or "", float(c.credit_limit), c.payment_terms, c.status, float(c.rating)])
        return output.getvalue()

    async def export_quotations_csv(self, db: AsyncSession) -> str:
        quots, _ = await sales_quotation_repository.search_quotations(db, limit=1000)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["quotation_number", "customer_name", "date", "validity_date", "currency", "status", "total_amount"])
        for q in quots:
            writer.writerow([q.quotation_number, q.customer.name if q.customer else "", q.quotation_date.strftime("%Y-%m-%d"), q.validity_date.strftime("%Y-%m-%d"), q.currency, q.status, float(q.total_amount)])
        return output.getvalue()

    async def export_orders_csv(self, db: AsyncSession) -> str:
        orders, _ = await sales_order_repository.search_orders(db, limit=1000)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["order_number", "customer_name", "order_date", "status", "delivery_status", "currency", "total_amount"])
        for o in orders:
            writer.writerow([o.order_number, o.customer.name if o.customer else "", o.order_date.strftime("%Y-%m-%d"), o.status, o.delivery_status, o.currency, float(o.total_amount)])
        return output.getvalue()

    async def import_customers_csv(self, db: AsyncSession, csv_content: str) -> List[str]:
        reader = csv.DictReader(io.StringIO(csv_content))
        created_codes = []
        for row in reader:
            code = row.get("customer_code")
            name = row.get("name")
            if not code or not name:
                continue
            existing = await customer_repository.get_by_code(db, code)
            if existing:
                continue
            cust_in = CustomerCreate(
                customer_code=code,
                name=name,
                email=row.get("email"),
                phone=row.get("phone"),
                tax_id=row.get("tax_id"),
                payment_terms=row.get("payment_terms") or "Net 30",
            )
            cust = await customer_service.create_customer(db, obj_in=cust_in)
            created_codes.append(cust.customer_code)
        return created_codes


sales_import_export_service = SalesImportExportService()
