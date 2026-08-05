from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.sales_repos import (
    customer_repository,
    delivery_order_repository,
    sales_order_repository,
    sales_quotation_repository,
)
from app.repositories.inventory_repos import product_repository
from app.schemas.sales import SalesSearchResult


class SalesSearchService:
    async def global_sales_search(
        self, db: AsyncSession, query: str, limit: int = 50
    ) -> List[SalesSearchResult]:
        results: List[SalesSearchResult] = []
        if not query or len(query.strip()) < 2:
            return results

        q = query.strip()

        # 1. Search Customers
        custs, _ = await customer_repository.search_customers(db, query=q, limit=10)
        for c in custs:
            results.append(
                SalesSearchResult(
                    entity_type="Customer",
                    entity_id=str(c.id),
                    title=c.name,
                    subtitle=f"Code: {c.customer_code} | Tax ID: {c.tax_id or 'N/A'}",
                    status=c.status,
                    details={"email": c.email, "phone": c.phone, "credit_limit": float(c.credit_limit)},
                )
            )

        # 2. Search Sales Orders
        orders, _ = await sales_order_repository.search_orders(db, query=q, limit=10)
        for o in orders:
            results.append(
                SalesSearchResult(
                    entity_type="SalesOrder",
                    entity_id=str(o.id),
                    title=o.order_number,
                    subtitle=f"Customer: {o.customer.name if o.customer else 'N/A'}",
                    status=o.status,
                    details={"total_amount": float(o.total_amount), "delivery_status": o.delivery_status},
                )
            )

        # 3. Search Quotations
        quots, _ = await sales_quotation_repository.search_quotations(db, query=q, limit=10)
        for sq in quots:
            results.append(
                SalesSearchResult(
                    entity_type="SalesQuotation",
                    entity_id=str(sq.id),
                    title=sq.quotation_number,
                    subtitle=f"Customer: {sq.customer.name if sq.customer else 'N/A'}",
                    status=sq.status,
                    details={"total_amount": float(sq.total_amount)},
                )
            )

        # 4. Search Delivery Orders (tracking number, carrier, delivery number)
        dels, _ = await delivery_order_repository.search_deliveries(db, query=q, limit=10)
        for d in dels:
            results.append(
                SalesSearchResult(
                    entity_type="DeliveryOrder",
                    entity_id=str(d.id),
                    title=d.delivery_number,
                    subtitle=f"Tracking: {d.tracking_number or 'N/A'} | Carrier: {d.carrier or 'N/A'}",
                    status=d.status,
                    details={"sales_order_id": str(d.sales_order_id)},
                )
            )

        # 5. Search Products
        prods, _ = await product_repository.search_and_filter(db, search_term=q, limit=10)
        for p in prods:
            results.append(
                SalesSearchResult(
                    entity_type="Product",
                    entity_id=str(p.id),
                    title=p.name,
                    subtitle=f"SKU: {p.sku}",
                    status=p.status,
                    details={"category_id": str(p.category_id)},
                )
            )

        return results[:limit]


sales_search_service = SalesSearchService()
