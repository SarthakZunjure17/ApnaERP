from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.delivery_order import DeliveryOrder
from app.models.sales_order import SalesOrder, SalesOrderItem
from app.models.sales_quotation import SalesQuotation
from app.models.sales_report_snapshot import SalesReportSnapshot
from app.models.sales_return import SalesReturn
from app.repositories.sales_repos import (
    customer_repository,
    delivery_order_repository,
    sales_order_repository,
    sales_quotation_repository,
    sales_report_snapshot_repository,
    sales_return_repository,
)
from app.schemas.sales import CustomerLedgerEntry, SalesAnalyticsResponse


class SalesAnalyticsService:
    async def get_analytics_summary(self, db: AsyncSession) -> SalesAnalyticsResponse:
        orders, total_orders = await sales_order_repository.search_orders(db, limit=1000)
        completed_orders = [o for o in orders if o.status in ("Approved", "Partially Delivered", "Fully Delivered", "Closed")]

        total_rev = sum((o.total_amount for o in completed_orders), Decimal("0.00"))
        avg_aov = round(total_rev / Decimal(len(completed_orders)), 2) if completed_orders else Decimal("0.00")

        custs, total_custs = await customer_repository.search_customers(db, limit=1000)

        # Top customers by spend
        cust_spend: Dict[str, Dict[str, Any]] = {}
        for o in completed_orders:
            cid = str(o.customer_id)
            cname = o.customer.name if o.customer else "Customer"
            cust_spend.setdefault(cid, {"customer_id": cid, "customer_name": cname, "spent": Decimal("0.00"), "order_count": 0})
            cust_spend[cid]["spent"] += o.total_amount
            cust_spend[cid]["order_count"] += 1

        top_custs = sorted(cust_spend.values(), key=lambda x: x["spent"], reverse=True)[:5]
        for tc in top_custs:
            tc["spent"] = float(tc["spent"])

        # Top products by quantity
        prod_sales: Dict[str, Dict[str, Any]] = {}
        for o in completed_orders:
            for item in o.items:
                pid = str(item.product_id)
                pname = item.product.name if item.product else "Product"
                prod_sales.setdefault(pid, {"product_id": pid, "product_name": pname, "quantity": Decimal("0.00"), "revenue": Decimal("0.00")})
                prod_sales[pid]["quantity"] += item.quantity
                prod_sales[pid]["revenue"] += item.line_total

        top_prods = sorted(prod_sales.values(), key=lambda x: x["revenue"], reverse=True)[:5]
        for tp in top_prods:
            tp["quantity"] = float(tp["quantity"])
            tp["revenue"] = float(tp["revenue"])

        # Monthly sales breakdown
        monthly_map: Dict[str, Dict[str, Any]] = {}
        for o in completed_orders:
            m_key = o.order_date.strftime("%Y-%m")
            monthly_map.setdefault(m_key, {"month": m_key, "revenue": Decimal("0.00"), "orders": 0})
            monthly_map[m_key]["revenue"] += o.total_amount
            monthly_map[m_key]["orders"] += 1

        monthly_list = sorted(monthly_map.values(), key=lambda x: x["month"])
        for m in monthly_list:
            m["revenue"] = float(m["revenue"])

        # Warehouse sales breakdown
        wh_map: Dict[str, Dict[str, Any]] = {}
        for o in completed_orders:
            for item in o.items:
                if item.warehouse_id:
                    w_id = str(item.warehouse_id)
                    w_name = item.warehouse.name if item.warehouse else "Warehouse"
                    wh_map.setdefault(w_id, {"warehouse_id": w_id, "warehouse_name": w_name, "revenue": Decimal("0.00")})
                    wh_map[w_id]["revenue"] += item.line_total

        wh_list = list(wh_map.values())
        for w in wh_list:
            w["revenue"] = float(w["revenue"])

        return SalesAnalyticsResponse(
            total_revenue=total_rev,
            total_orders=len(completed_orders),
            avg_order_value=avg_aov,
            total_customers=total_custs,
            top_customers=top_custs,
            top_products=top_prods,
            monthly_sales=monthly_list,
            warehouse_sales=wh_list,
        )

    async def refresh_sales_analytics_snapshot(self, db: AsyncSession) -> SalesReportSnapshot:
        analytics = await self.get_analytics_summary(db)
        snapshot = await sales_report_snapshot_repository.create(
            db,
            obj_in={
                "snapshot_date": datetime.now(timezone.utc),
                "period_type": "Daily",
                "total_revenue": analytics.total_revenue,
                "total_orders": analytics.total_orders,
                "avg_order_value": analytics.avg_order_value,
                "metrics_json": analytics.model_dump(mode="json"),
            },
        )
        return snapshot


class SalesReportService:
    async def get_quotation_report(self, db: AsyncSession, status: Optional[str] = None) -> List[Dict[str, Any]]:
        quots, _ = await sales_quotation_repository.search_quotations(db, status=status, limit=500)
        return [
            {
                "quotation_number": q.quotation_number,
                "customer_name": q.customer.name if q.customer else "N/A",
                "quotation_date": q.quotation_date.isoformat(),
                "validity_date": q.validity_date.isoformat(),
                "status": q.status,
                "total_amount": float(q.total_amount),
            }
            for q in quots
        ]

    async def get_order_report(self, db: AsyncSession, status: Optional[str] = None) -> List[Dict[str, Any]]:
        orders, _ = await sales_order_repository.search_orders(db, status=status, limit=500)
        return [
            {
                "order_number": o.order_number,
                "customer_name": o.customer.name if o.customer else "N/A",
                "order_date": o.order_date.isoformat(),
                "status": o.status,
                "delivery_status": o.delivery_status,
                "total_amount": float(o.total_amount),
            }
            for o in orders
        ]

    async def get_delivery_report(self, db: AsyncSession, status: Optional[str] = None) -> List[Dict[str, Any]]:
        dels, _ = await delivery_order_repository.search_deliveries(db, status=status, limit=500)
        return [
            {
                "delivery_number": d.delivery_number,
                "sales_order_number": d.sales_order.order_number if d.sales_order else "N/A",
                "warehouse_name": d.warehouse.name if d.warehouse else "N/A",
                "dispatch_date": d.dispatch_date.isoformat(),
                "carrier": d.carrier,
                "tracking_number": d.tracking_number,
                "status": d.status,
            }
            for d in dels
        ]

    async def get_sales_register(self, db: AsyncSession) -> List[Dict[str, Any]]:
        orders, _ = await sales_order_repository.search_orders(db, limit=1000)
        return [
            {
                "order_number": o.order_number,
                "customer_name": o.customer.name if o.customer else "N/A",
                "tax_id": o.customer.tax_id if o.customer else None,
                "date": o.order_date.isoformat(),
                "subtotal": float(o.subtotal_amount),
                "discount": float(o.discount_amount),
                "tax": float(o.tax_amount),
                "total": float(o.total_amount),
                "status": o.status,
            }
            for o in orders
        ]

    async def get_customer_ledger(self, db: AsyncSession, customer_id: uuid.UUID) -> List[CustomerLedgerEntry]:
        orders, _ = await sales_order_repository.search_orders(db, customer_id=customer_id, limit=500)
        returns, _ = await sales_return_repository.search_returns(db, customer_id=customer_id, limit=500)

        entries: List[CustomerLedgerEntry] = []
        running_bal = Decimal("0.00")

        # Combine orders (debit/sales) and returns (credit/returns)
        events = []
        for o in orders:
            if o.status in ("Approved", "Partially Delivered", "Fully Delivered", "Closed"):
                events.append((o.order_date, o.order_number, "Sales Order", o.total_amount, f"Order booking {o.order_number}"))
        for r in returns:
            if r.status in ("Approved", "Completed"):
                events.append((r.return_date, r.return_number, "Sales Return", -r.total_refund_amount, f"Return credit {r.return_number}"))

        events.sort(key=lambda x: x[0])

        for dt, doc_num, doc_type, amt, notes in events:
            running_bal += amt
            entries.append(
                CustomerLedgerEntry(
                    date=dt,
                    document_number=doc_num,
                    document_type=doc_type,
                    amount=amt,
                    balance=running_bal,
                    notes=notes,
                )
            )

        return entries

    async def get_return_report(self, db: AsyncSession) -> List[Dict[str, Any]]:
        returns, _ = await sales_return_repository.search_returns(db, limit=500)
        return [
            {
                "return_number": r.return_number,
                "sales_order_number": r.sales_order.order_number if r.sales_order else "N/A",
                "customer_name": r.customer.name if r.customer else "N/A",
                "return_date": r.return_date.isoformat(),
                "reason_code": r.reason_code,
                "refund_amount": float(r.total_refund_amount),
                "status": r.status,
            }
            for r in returns
        ]


sales_analytics_service = SalesAnalyticsService()
sales_report_service = SalesReportService()
