import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import and_, case, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

# Import models across domains
from app.models.attendance import Attendance
from app.models.batch import Batch
from app.models.crm import Activity, Lead, LeadSource, Opportunity, OpportunityStage
from app.models.customer import Customer
from app.models.department import Department
from app.models.employee import Employee
from app.models.finance import AccountGroup, ChartOfAccount, Company, FiscalPeriod, FiscalYear, Journal, JournalLine
from app.models.goods_receipt import GoodsReceipt
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType
from app.models.payroll_period import PayrollPeriod, PayrollRecord
from app.models.payroll_run import PayrollRun
from app.models.payslip import Payslip
from app.models.position import Position
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.purchase_return import PurchaseReturn
from app.models.sales_order import SalesOrder, SalesOrderItem
from app.models.sales_quotation import SalesQuotation
from app.models.stock_balance import StockBalance
from app.models.stock_ledger import StockLedger
from app.models.stock_reservation import StockReservation
from app.models.supplier import Supplier
from app.models.warehouse import Warehouse

from app.models.reporting import (
    AnalyticsSnapshot,
    ChartConfiguration,
    Dashboard,
    DashboardWidget,
    KPI,
    KPIMetric,
    ReportExecution,
    ReportTemplate,
    SavedReport,
    ScheduledReport,
)
from app.repositories.base_repository import BaseRepository


class ReportingRepository:
    """
    Centralized Read-Only Repository for high-performance database-side aggregations across all ERP domains.
    """

    # =========================================================================
    # 1. EXECUTIVE MANAGEMENT DASHBOARD
    # =========================================================================

    async def get_dashboard_metrics(self, db: AsyncSession, as_of_date: Optional[date] = None) -> Dict[str, Any]:
        cut_off = as_of_date or date.today()

        # HR
        emp_stmt = select(
            func.count(Employee.id).label("total"),
            func.count(case((Employee.employment_status.ilike("Active"), Employee.id))).label("active"),
        ).where(Employee.is_deleted == False)
        emp_res = (await db.execute(emp_stmt)).first()
        total_emp = emp_res.total if emp_res else 0
        active_emp = emp_res.active if emp_res else 0

        dept_count_stmt = select(func.count(Department.id)).where(Department.is_deleted == False)
        dept_count = (await db.execute(dept_count_stmt)).scalar() or 0

        # CRM
        leads_stmt = select(
            func.count(Lead.id).label("total"),
            func.count(case((Lead.is_converted == False, Lead.id))).label("open"),
        ).where(Lead.is_deleted == False)
        leads_res = (await db.execute(leads_stmt)).first()
        total_leads = leads_res.total if leads_res else 0
        open_leads = leads_res.open if leads_res else 0

        opp_stmt = select(
            func.count(Opportunity.id).label("total_active"),
            func.coalesce(func.sum(Opportunity.expected_revenue), Decimal("0.00")).label("pipeline_val"),
            func.coalesce(func.sum(Opportunity.expected_revenue * (Opportunity.probability / Decimal("100.00"))), Decimal("0.00")).label("weighted_val"),
        ).where(and_(Opportunity.is_deleted == False, Opportunity.status == "Open"))
        opp_res = (await db.execute(opp_stmt)).first()
        active_opps = opp_res.total_active if opp_res else 0
        pipeline_val = opp_res.pipeline_val if opp_res else Decimal("0.00")
        weighted_val = opp_res.weighted_val if opp_res else Decimal("0.00")

        # Sales
        sales_stmt = select(
            func.count(SalesOrder.id).label("total_orders"),
            func.coalesce(func.sum(SalesOrder.total_amount), Decimal("0.00")).label("total_rev"),
            func.count(case((SalesOrder.status.in_(["Draft", "Pending", "Submitted"]), SalesOrder.id))).label("pending_orders"),
        ).where(SalesOrder.status != "Cancelled")
        sales_res = (await db.execute(sales_stmt)).first()
        total_orders = sales_res.total_orders if sales_res else 0
        total_sales_rev = sales_res.total_rev if sales_res else Decimal("0.00")
        pending_orders = sales_res.pending_orders if sales_res else 0
        avg_order_val = (total_sales_rev / Decimal(total_orders)) if total_orders > 0 else Decimal("0.00")

        # Procurement
        po_stmt = select(
            func.count(PurchaseOrder.id).label("total_pos"),
            func.coalesce(func.sum(PurchaseOrder.total_amount), Decimal("0.00")).label("total_spend"),
            func.count(case((PurchaseOrder.status.in_(["Draft", "Pending", "Submitted"]), PurchaseOrder.id))).label("pending_pos"),
        ).where(PurchaseOrder.status != "Cancelled")
        po_res = (await db.execute(po_stmt)).first()
        total_pos = po_res.total_pos if po_res else 0
        total_po_spend = po_res.total_spend if po_res else Decimal("0.00")
        pending_pos = po_res.pending_pos if po_res else 0

        # Inventory
        prod_count_stmt = select(func.count(Product.id))
        prod_count = (await db.execute(prod_count_stmt)).scalar() or 0

        wh_count_stmt = select(func.count(Warehouse.id))
        wh_count = (await db.execute(wh_count_stmt)).scalar() or 0

        stock_stmt = (
            select(
                func.coalesce(func.sum(StockBalance.available_quantity), Decimal("0.00")).label("total_qty"),
                func.coalesce(func.sum(StockBalance.available_quantity * func.coalesce(Product.default_unit_price, Decimal("0.00"))), Decimal("0.00")).label("total_val"),
            )
            .join(Product, Product.id == StockBalance.product_id)
        )
        stock_res = (await db.execute(stock_stmt)).first()
        total_stock_qty = stock_res.total_qty if stock_res else Decimal("0.00")
        total_stock_val = stock_res.total_val if stock_res else Decimal("0.00")

        low_stock_stmt = (
            select(func.count(distinct(Product.id)))
            .join(StockBalance, StockBalance.product_id == Product.id)
            .where(
                StockBalance.available_quantity <= func.coalesce(Product.reorder_level, Decimal("0.00")),
            )
        )
        low_stock_count = (await db.execute(low_stock_stmt)).scalar() or 0

        # Finance
        fin_rev_stmt = (
            select(func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), Decimal("0.00")))
            .join(ChartOfAccount, ChartOfAccount.id == JournalLine.account_id)
            .join(Journal, Journal.id == JournalLine.journal_id)
            .where(and_(Journal.status == "Posted", ChartOfAccount.account_type.in_(["Revenue", "Income"])))
        )
        fin_rev = (await db.execute(fin_rev_stmt)).scalar() or Decimal("0.00")

        fin_exp_stmt = (
            select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), Decimal("0.00")))
            .join(ChartOfAccount, ChartOfAccount.id == JournalLine.account_id)
            .join(Journal, Journal.id == JournalLine.journal_id)
            .where(and_(Journal.status == "Posted", ChartOfAccount.account_type == "Expense"))
        )
        fin_exp = (await db.execute(fin_exp_stmt)).scalar() or Decimal("0.00")

        posted_j_stmt = select(func.count(Journal.id)).where(Journal.status == "Posted")
        posted_j_count = (await db.execute(posted_j_stmt)).scalar() or 0

        # Payroll
        pr_stmt = (
            select(
                func.count(distinct(PayrollRun.id)).label("runs_count"),
                func.coalesce(func.sum(Payslip.gross_salary), Decimal("0.00")).label("total_gross"),
                func.coalesce(func.sum(Payslip.net_salary), Decimal("0.00")).label("total_net"),
            )
            .select_from(PayrollRun)
            .join(Payslip, Payslip.payroll_period_id == PayrollRun.payroll_period_id, isouter=True)
        )
        pr_res = (await db.execute(pr_stmt)).first()
        pr_count = pr_res.runs_count if pr_res else 0
        pr_cost = pr_res.total_gross if pr_res else Decimal("0.00")
        pr_net = pr_res.total_net if pr_res else Decimal("0.00")

        return {
            "as_of_date": cut_off,
            "hr": {
                "total_employees": total_emp,
                "active_employees": active_emp,
                "total_departments": dept_count,
            },
            "crm": {
                "open_leads": open_leads,
                "total_leads": total_leads,
                "active_opportunities": active_opps,
                "pipeline_value": pipeline_val,
                "weighted_forecast_value": weighted_val,
            },
            "sales": {
                "total_orders_count": total_orders,
                "total_sales_revenue": total_sales_rev,
                "pending_orders_count": pending_orders,
                "average_order_value": round(avg_order_val, 2),
            },
            "procurement": {
                "total_pos_count": total_pos,
                "total_spend": total_po_spend,
                "pending_pos_count": pending_pos,
            },
            "inventory": {
                "total_products_count": prod_count,
                "total_warehouses_count": wh_count,
                "total_on_hand_quantity": total_stock_qty,
                "total_inventory_valuation": total_stock_val,
                "low_stock_items_count": low_stock_count,
            },
            "finance": {
                "total_revenue": fin_rev,
                "total_expenses": fin_exp,
                "net_operating_income": fin_rev - fin_exp,
                "posted_journals_count": posted_j_count,
            },
            "payroll": {
                "total_payroll_runs_count": pr_count,
                "total_payroll_cost": pr_cost,
                "total_net_disbursed": pr_net,
            },
        }

    # =========================================================================
    # 2. FINANCE REPORTS
    # =========================================================================

    async def get_profit_loss(
        self, db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None, company_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        filters = [Journal.status == "Posted"]
        if from_date:
            filters.append(Journal.posting_date >= from_date)
        if to_date:
            filters.append(Journal.posting_date <= to_date)

        # Revenue accounts
        rev_stmt = (
            select(
                ChartOfAccount.id.label("account_id"),
                ChartOfAccount.account_code,
                ChartOfAccount.name.label("account_name"),
                AccountGroup.name.label("group_name"),
                ChartOfAccount.account_type,
                func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), Decimal("0.00")).label("amount"),
            )
            .join(JournalLine, JournalLine.account_id == ChartOfAccount.id)
            .join(Journal, Journal.id == JournalLine.journal_id)
            .join(AccountGroup, AccountGroup.id == ChartOfAccount.account_group_id, isouter=True)
            .where(and_(*filters, ChartOfAccount.account_type.in_(["Revenue", "Income"])))
            .group_by(ChartOfAccount.id, ChartOfAccount.account_code, ChartOfAccount.name, AccountGroup.name, ChartOfAccount.account_type)
            .order_by(ChartOfAccount.account_code.asc())
        )
        rev_rows = (await db.execute(rev_stmt)).all()

        # Expense accounts
        exp_stmt = (
            select(
                ChartOfAccount.id.label("account_id"),
                ChartOfAccount.account_code,
                ChartOfAccount.name.label("account_name"),
                AccountGroup.name.label("group_name"),
                ChartOfAccount.account_type,
                func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), Decimal("0.00")).label("amount"),
            )
            .join(JournalLine, JournalLine.account_id == ChartOfAccount.id)
            .join(Journal, Journal.id == JournalLine.journal_id)
            .join(AccountGroup, AccountGroup.id == ChartOfAccount.account_group_id, isouter=True)
            .where(and_(*filters, ChartOfAccount.account_type == "Expense"))
            .group_by(ChartOfAccount.id, ChartOfAccount.account_code, ChartOfAccount.name, AccountGroup.name, ChartOfAccount.account_type)
            .order_by(ChartOfAccount.account_code.asc())
        )
        exp_rows = (await db.execute(exp_stmt)).all()

        rev_lines = []
        tot_rev = Decimal("0.00")
        for r in rev_rows:
            tot_rev += r.amount
            rev_lines.append(
                {
                    "account_id": r.account_id,
                    "account_code": r.account_code,
                    "account_name": r.account_name,
                    "account_group_name": r.group_name,
                    "account_type": r.account_type,
                    "amount": r.amount,
                }
            )

        exp_lines = []
        tot_exp = Decimal("0.00")
        for r in exp_rows:
            tot_exp += r.amount
            exp_lines.append(
                {
                    "account_id": r.account_id,
                    "account_code": r.account_code,
                    "account_name": r.account_name,
                    "account_group_name": r.group_name,
                    "account_type": r.account_type,
                    "amount": r.amount,
                }
            )

        return {
            "from_date": from_date,
            "to_date": to_date,
            "total_revenue": tot_rev,
            "total_expenses": tot_exp,
            "net_profit": tot_rev - tot_exp,
            "revenue_lines": rev_lines,
            "expense_lines": exp_lines,
        }

    async def get_balance_sheet(
        self, db: AsyncSession, as_of_date: Optional[date] = None, company_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        cut_off = as_of_date or date.today()

        stmt = (
            select(
                ChartOfAccount.id.label("account_id"),
                ChartOfAccount.account_code,
                ChartOfAccount.name.label("account_name"),
                AccountGroup.name.label("group_name"),
                ChartOfAccount.account_type,
                ChartOfAccount.current_balance,
            )
            .join(AccountGroup, AccountGroup.id == ChartOfAccount.account_group_id, isouter=True)
            .where(
                and_(
                    ChartOfAccount.is_deleted == False,
                    ChartOfAccount.account_type.in_(["Asset", "Liability", "Equity"]),
                )
            )
            .order_by(ChartOfAccount.account_code.asc())
        )
        rows = (await db.execute(stmt)).all()

        asset_lines = []
        liab_lines = []
        equity_lines = []
        tot_asset = Decimal("0.00")
        tot_liab = Decimal("0.00")
        tot_equity = Decimal("0.00")

        for r in rows:
            line = {
                "account_id": r.account_id,
                "account_code": r.account_code,
                "account_name": r.account_name,
                "account_group_name": r.group_name,
                "account_type": r.account_type,
                "balance": r.current_balance,
            }
            if r.account_type == "Asset":
                asset_lines.append(line)
                tot_asset += r.current_balance
            elif r.account_type == "Liability":
                liab_lines.append(line)
                tot_liab += r.current_balance
            elif r.account_type == "Equity":
                equity_lines.append(line)
                tot_equity += r.current_balance

        return {
            "as_of_date": cut_off,
            "total_assets": tot_asset,
            "total_liabilities": tot_liab,
            "total_equity": tot_equity,
            "is_balanced": bool(tot_asset == (tot_liab + tot_equity)),
            "asset_lines": asset_lines,
            "liability_lines": liab_lines,
            "equity_lines": equity_lines,
        }

    async def get_trial_balance(
        self, db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None, company_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        filters = [Journal.status == "Posted"]
        if from_date:
            filters.append(Journal.posting_date >= from_date)
        if to_date:
            filters.append(Journal.posting_date <= to_date)

        stmt = (
            select(
                ChartOfAccount.id.label("account_id"),
                ChartOfAccount.account_code,
                ChartOfAccount.name.label("account_name"),
                ChartOfAccount.account_type,
                ChartOfAccount.opening_balance,
                func.coalesce(func.sum(JournalLine.debit), Decimal("0.00")).label("period_debit"),
                func.coalesce(func.sum(JournalLine.credit), Decimal("0.00")).label("period_credit"),
            )
            .join(JournalLine, JournalLine.account_id == ChartOfAccount.id, isouter=True)
            .join(Journal, and_(Journal.id == JournalLine.journal_id, *filters), isouter=True)
            .where(ChartOfAccount.is_deleted == False)
            .group_by(ChartOfAccount.id, ChartOfAccount.account_code, ChartOfAccount.name, ChartOfAccount.account_type, ChartOfAccount.opening_balance)
            .order_by(ChartOfAccount.account_code.asc())
        )
        rows = (await db.execute(stmt)).all()

        lines = []
        tot_debit = Decimal("0.00")
        tot_credit = Decimal("0.00")

        for r in rows:
            debit = r.period_debit
            credit = r.period_credit
            tot_debit += debit
            tot_credit += credit

            closing = r.opening_balance + (debit - credit if r.account_type in ["Asset", "Expense"] else credit - debit)

            lines.append(
                {
                    "account_id": r.account_id,
                    "account_code": r.account_code,
                    "account_name": r.account_name,
                    "account_type": r.account_type,
                    "opening_balance": r.opening_balance,
                    "debit_total": debit,
                    "credit_total": credit,
                    "closing_balance": closing,
                }
            )

        return {
            "from_date": from_date,
            "to_date": to_date,
            "total_debit": tot_debit,
            "total_credit": tot_credit,
            "is_balanced": bool(tot_debit == tot_credit),
            "lines": lines,
        }

    async def get_account_balances(
        self, db: AsyncSession, account_type: Optional[str] = None, company_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        filters = [ChartOfAccount.is_deleted == False]
        if account_type:
            filters.append(ChartOfAccount.account_type == account_type)

        stmt = select(ChartOfAccount).where(and_(*filters)).order_by(ChartOfAccount.account_code.asc())
        accounts = (await db.execute(stmt)).scalars().all()

        items = []
        tot_dr = Decimal("0.00")
        tot_cr = Decimal("0.00")

        for a in accounts:
            bal = a.current_balance
            if a.account_type in ["Asset", "Expense"]:
                tot_dr += bal
            else:
                tot_cr += bal

            items.append(
                {
                    "account_id": a.id,
                    "account_code": a.account_code,
                    "account_name": a.name,
                    "account_type": a.account_type,
                    "currency_code": a.currency_code or "USD",
                    "current_balance": bal,
                    "is_active": a.is_active,
                }
            )

        return {
            "as_of_date": date.today(),
            "total_accounts": len(items),
            "total_debit_balance": tot_dr,
            "total_credit_balance": tot_cr,
            "accounts": items,
        }

    # =========================================================================
    # 3. SALES REPORTS
    # =========================================================================

    async def get_sales_order_summary(
        self, db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        filters = [SalesOrder.status != "Cancelled"]
        if from_date:
            filters.append(SalesOrder.created_at >= datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc))
        if to_date:
            filters.append(SalesOrder.created_at <= datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc))

        stmt = select(
            func.count(SalesOrder.id).label("total_orders"),
            func.coalesce(func.sum(SalesOrder.subtotal_amount), Decimal("0.00")).label("subtotal"),
            func.coalesce(func.sum(SalesOrder.discount_amount), Decimal("0.00")).label("discount"),
            func.coalesce(func.sum(SalesOrder.tax_amount), Decimal("0.00")).label("tax"),
            func.coalesce(func.sum(SalesOrder.total_amount), Decimal("0.00")).label("total"),
        ).where(and_(*filters))
        res = (await db.execute(stmt)).first()

        tot_orders = res.total_orders if res else 0
        tot_subtotal = res.subtotal if res else Decimal("0.00")
        tot_disc = res.discount if res else Decimal("0.00")
        tot_tax = res.tax if res else Decimal("0.00")
        tot_net = res.total if res else Decimal("0.00")
        avg_order = (tot_net / Decimal(tot_orders)) if tot_orders > 0 else Decimal("0.00")

        status_stmt = select(
            SalesOrder.status,
            func.count(SalesOrder.id).label("count"),
            func.coalesce(func.sum(SalesOrder.total_amount), Decimal("0.00")).label("total"),
        ).where(and_(*filters)).group_by(SalesOrder.status)
        status_res = (await db.execute(status_stmt)).all()
        status_items = [{"status": r.status, "order_count": r.count, "total_amount": r.total} for r in status_res]

        return {
            "from_date": from_date,
            "to_date": to_date,
            "total_orders": tot_orders,
            "total_gross_amount": tot_subtotal,
            "total_discount_amount": tot_disc,
            "total_tax_amount": tot_tax,
            "total_net_amount": tot_net,
            "average_order_value": round(avg_order, 2),
            "status_breakdown": status_items,
        }

    async def get_sales_by_customer(
        self, db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None, limit: int = 100
    ) -> Dict[str, Any]:
        filters = [SalesOrder.status != "Cancelled", Customer.is_deleted == False]
        if from_date:
            filters.append(SalesOrder.created_at >= datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc))
        if to_date:
            filters.append(SalesOrder.created_at <= datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc))

        stmt = (
            select(
                Customer.id.label("customer_id"),
                Customer.customer_code,
                Customer.name.label("customer_name"),
                func.count(SalesOrder.id).label("order_count"),
                func.coalesce(func.sum(SalesOrder.total_amount), Decimal("0.00")).label("total_spent"),
            )
            .join(Customer, Customer.id == SalesOrder.customer_id)
            .where(and_(*filters))
            .group_by(Customer.id, Customer.customer_code, Customer.name)
            .order_by(func.sum(SalesOrder.total_amount).desc())
            .limit(limit)
        )
        res = (await db.execute(stmt)).all()

        customers = []
        grand_total = Decimal("0.00")
        for r in res:
            avg_val = (r.total_spent / Decimal(r.order_count)) if r.order_count > 0 else Decimal("0.00")
            grand_total += r.total_spent
            customers.append(
                {
                    "customer_id": r.customer_id,
                    "customer_code": r.customer_code,
                    "customer_name": r.customer_name,
                    "order_count": r.order_count,
                    "total_spent": r.total_spent,
                    "average_order_value": round(avg_val, 2),
                    "outstanding_balance": Decimal("0.00"),
                }
            )

        return {
            "from_date": from_date,
            "to_date": to_date,
            "total_customers": len(customers),
            "total_revenue": grand_total,
            "customers": customers,
        }

    async def get_sales_by_product(
        self, db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None, limit: int = 100
    ) -> Dict[str, Any]:
        filters = [SalesOrder.status != "Cancelled"]
        if from_date:
            filters.append(SalesOrder.created_at >= datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc))
        if to_date:
            filters.append(SalesOrder.created_at <= datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc))

        stmt = (
            select(
                Product.id.label("product_id"),
                Product.sku.label("product_sku"),
                Product.name.label("product_name"),
                func.coalesce(func.sum(SalesOrderItem.quantity), Decimal("0.00")).label("units_sold"),
                func.coalesce(func.sum(SalesOrderItem.line_total), Decimal("0.00")).label("revenue"),
            )
            .join(SalesOrderItem, SalesOrderItem.product_id == Product.id)
            .join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id)
            .where(and_(*filters))
            .group_by(Product.id, Product.sku, Product.name)
            .order_by(func.sum(SalesOrderItem.line_total).desc())
            .limit(limit)
        )
        res = (await db.execute(stmt)).all()

        products = []
        tot_units = Decimal("0.00")
        tot_rev = Decimal("0.00")
        for r in res:
            avg_p = (r.revenue / r.units_sold) if r.units_sold > 0 else Decimal("0.00")
            tot_units += r.units_sold
            tot_rev += r.revenue
            products.append(
                {
                    "product_id": r.product_id,
                    "product_sku": r.product_sku,
                    "product_name": r.product_name,
                    "units_sold": r.units_sold,
                    "total_revenue": r.revenue,
                    "average_price": round(avg_p, 2),
                }
            )

        return {
            "from_date": from_date,
            "to_date": to_date,
            "total_products": len(products),
            "total_units_sold": tot_units,
            "total_revenue": tot_rev,
            "products": products,
        }

    async def get_sales_quotation_summary(
        self, db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        filters = [SalesQuotation.status != "Cancelled"]
        if from_date:
            filters.append(SalesQuotation.created_at >= datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc))
        if to_date:
            filters.append(SalesQuotation.created_at <= datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc))

        stmt = select(
            func.count(SalesQuotation.id).label("total"),
            func.coalesce(func.sum(SalesQuotation.total_amount), Decimal("0.00")).label("total_val"),
            func.count(case((SalesQuotation.status.in_(["Approved", "Converted"]), SalesQuotation.id))).label("converted"),
        ).where(and_(*filters))
        res = (await db.execute(stmt)).first()

        total = res.total if res else 0
        total_val = res.total_val if res else Decimal("0.00")
        converted = res.converted if res else 0
        conv_rate = float(converted / total * 100) if total > 0 else 0.0

        st_stmt = select(SalesQuotation.status, func.count(SalesQuotation.id)).where(and_(*filters)).group_by(SalesQuotation.status)
        st_rows = (await db.execute(st_stmt)).all()
        status_map = {r[0]: r[1] for r in st_rows}

        return {
            "from_date": from_date,
            "to_date": to_date,
            "total_quotations": total,
            "total_quotation_value": total_val,
            "converted_quotations_count": converted,
            "conversion_rate": round(conv_rate, 2),
            "status_breakdown": status_map,
        }

    # =========================================================================
    # 4. PROCUREMENT REPORTS
    # =========================================================================

    async def get_purchase_order_summary(
        self, db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        filters = [PurchaseOrder.status != "Cancelled"]
        if from_date:
            filters.append(PurchaseOrder.created_at >= datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc))
        if to_date:
            filters.append(PurchaseOrder.created_at <= datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc))

        stmt = select(
            func.count(PurchaseOrder.id).label("total_pos"),
            func.coalesce(func.sum(PurchaseOrder.total_amount), Decimal("0.00")).label("total_spend"),
        ).where(and_(*filters))
        res = (await db.execute(stmt)).first()

        total_pos = res.total_pos if res else 0
        total_spend = res.total_spend if res else Decimal("0.00")
        avg_val = (total_spend / Decimal(total_pos)) if total_pos > 0 else Decimal("0.00")

        status_stmt = select(
            PurchaseOrder.status,
            func.count(PurchaseOrder.id).label("count"),
            func.coalesce(func.sum(PurchaseOrder.total_amount), Decimal("0.00")).label("total"),
        ).where(and_(*filters)).group_by(PurchaseOrder.status)
        status_res = (await db.execute(status_stmt)).all()
        status_items = [{"status": r.status, "po_count": r.count, "total_amount": r.total} for r in status_res]

        return {
            "from_date": from_date,
            "to_date": to_date,
            "total_purchase_orders": total_pos,
            "total_spend": total_spend,
            "average_po_value": round(avg_val, 2),
            "status_breakdown": status_items,
        }

    async def get_purchases_by_supplier(
        self, db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None, limit: int = 100
    ) -> Dict[str, Any]:
        filters = [PurchaseOrder.status != "Cancelled", Supplier.is_deleted == False]
        if from_date:
            filters.append(PurchaseOrder.created_at >= datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc))
        if to_date:
            filters.append(PurchaseOrder.created_at <= datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc))

        stmt = (
            select(
                Supplier.id.label("supplier_id"),
                Supplier.code.label("supplier_code"),
                Supplier.name.label("supplier_name"),
                func.count(PurchaseOrder.id).label("po_count"),
                func.coalesce(func.sum(PurchaseOrder.total_amount), Decimal("0.00")).label("total_purchases"),
            )
            .join(Supplier, Supplier.id == PurchaseOrder.supplier_id)
            .where(and_(*filters))
            .group_by(Supplier.id, Supplier.code, Supplier.name)
            .order_by(func.sum(PurchaseOrder.total_amount).desc())
            .limit(limit)
        )
        res = (await db.execute(stmt)).all()

        suppliers = []
        grand_total = Decimal("0.00")
        for r in res:
            avg_val = (r.total_purchases / Decimal(r.po_count)) if r.po_count > 0 else Decimal("0.00")
            grand_total += r.total_purchases
            suppliers.append(
                {
                    "supplier_id": r.supplier_id,
                    "supplier_code": r.supplier_code,
                    "supplier_name": r.supplier_name,
                    "po_count": r.po_count,
                    "total_purchases": r.total_purchases,
                    "average_po_value": round(avg_val, 2),
                }
            )

        return {
            "from_date": from_date,
            "to_date": to_date,
            "total_suppliers": len(suppliers),
            "total_spend": grand_total,
            "suppliers": suppliers,
        }

    async def get_procurement_spend_summary(
        self, db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        return await self.get_purchase_order_summary(db, from_date=from_date, to_date=to_date)

    async def get_goods_received_summary(
        self, db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        filters = [GoodsReceipt.status != "Cancelled"]
        if from_date:
            filters.append(GoodsReceipt.receipt_date >= datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc))
        if to_date:
            filters.append(GoodsReceipt.receipt_date <= datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc))

        stmt = select(
            func.count(GoodsReceipt.id).label("total"),
            func.count(case((GoodsReceipt.status == "Received", GoodsReceipt.id))).label("received"),
            func.count(case((GoodsReceipt.status == "Draft", GoodsReceipt.id))).label("draft"),
        ).where(and_(*filters))
        res = (await db.execute(stmt)).first()

        total = res.total if res else 0
        received = res.received if res else 0
        draft = res.draft if res else 0

        return {
            "from_date": from_date,
            "to_date": to_date,
            "total_receipts": total,
            "received_count": received,
            "draft_count": draft,
        }

    async def get_purchase_return_summary(
        self, db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        filters = [PurchaseReturn.status != "Cancelled"]
        if from_date:
            filters.append(PurchaseReturn.created_at >= datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc))
        if to_date:
            filters.append(PurchaseReturn.created_at <= datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc))

        stmt = select(
            func.count(PurchaseReturn.id).label("total"),
            func.coalesce(func.sum(PurchaseReturn.total_amount), Decimal("0.00")).label("total_val"),
        ).where(and_(*filters))
        res = (await db.execute(stmt)).first()

        total = res.total if res else 0
        total_val = res.total_val if res else Decimal("0.00")

        return {
            "from_date": from_date,
            "to_date": to_date,
            "total_returns": total,
            "total_returned_amount": total_val,
        }

    # =========================================================================
    # 5. INVENTORY REPORTS
    # =========================================================================

    async def get_stock_by_warehouse(self, db: AsyncSession) -> Dict[str, Any]:
        stmt = (
            select(
                Warehouse.id.label("warehouse_id"),
                Warehouse.code.label("warehouse_code"),
                Warehouse.name.label("warehouse_name"),
                func.count(distinct(StockBalance.product_id)).label("unique_products"),
                func.coalesce(func.sum(StockBalance.available_quantity), Decimal("0.00")).label("total_on_hand"),
                func.coalesce(func.sum(StockBalance.reserved_quantity), Decimal("0.00")).label("total_reserved"),
                func.coalesce(func.sum(StockBalance.available_quantity * func.coalesce(Product.default_unit_price, Decimal("0.00"))), Decimal("0.00")).label("total_val"),
            )
            .join(StockBalance, StockBalance.warehouse_id == Warehouse.id, isouter=True)
            .join(Product, Product.id == StockBalance.product_id, isouter=True)
            .group_by(Warehouse.id, Warehouse.code, Warehouse.name)
            .order_by(Warehouse.name.asc())
        )
        res = (await db.execute(stmt)).all()

        warehouses = []
        tot_qty = Decimal("0.00")
        tot_val = Decimal("0.00")
        for r in res:
            tot_qty += r.total_on_hand
            tot_val += r.total_val
            warehouses.append(
                {
                    "warehouse_id": r.warehouse_id,
                    "warehouse_code": r.warehouse_code,
                    "warehouse_name": r.warehouse_name,
                    "products_count": r.unique_products,
                    "total_quantity": r.total_on_hand,
                    "total_valuation": r.total_val,
                }
            )

        return {
            "total_warehouses": len(warehouses),
            "total_inventory_quantity": tot_qty,
            "total_inventory_valuation": tot_val,
            "warehouses": warehouses,
        }

    async def get_stock_by_product(
        self, db: AsyncSession, category_id: Optional[uuid.UUID] = None, warehouse_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        filters = []
        if category_id:
            filters.append(Product.category_id == category_id)

        balance_filters = []
        if warehouse_id:
            balance_filters.append(StockBalance.warehouse_id == warehouse_id)

        stmt = (
            select(
                Product.id.label("product_id"),
                Product.sku.label("product_sku"),
                Product.name.label("product_name"),
                ProductCategory.name.label("category_name"),
                func.coalesce(func.sum(StockBalance.available_quantity), Decimal("0.00")).label("total_on_hand"),
                func.coalesce(func.sum(StockBalance.reserved_quantity), Decimal("0.00")).label("total_reserved"),
                Product.default_unit_price,
                func.coalesce(func.sum(StockBalance.available_quantity * func.coalesce(Product.default_unit_price, Decimal("0.00"))), Decimal("0.00")).label("total_val"),
            )
            .join(ProductCategory, ProductCategory.id == Product.category_id, isouter=True)
            .join(StockBalance, and_(StockBalance.product_id == Product.id, *balance_filters), isouter=True)
            .where(and_(*filters) if filters else True)
            .group_by(Product.id, Product.sku, Product.name, ProductCategory.name, Product.default_unit_price)
            .order_by(Product.sku.asc())
        )
        res = (await db.execute(stmt)).all()

        products = []
        tot_qty = Decimal("0.00")
        tot_val = Decimal("0.00")
        for r in res:
            tot_qty += r.total_on_hand
            tot_val += r.total_val
            products.append(
                {
                    "product_id": r.product_id,
                    "product_sku": r.product_sku,
                    "product_name": r.product_name,
                    "category_name": r.category_name,
                    "quantity_on_hand": r.total_on_hand,
                    "quantity_reserved": r.total_reserved,
                    "quantity_available": r.total_on_hand - r.total_reserved,
                    "valuation": r.total_val,
                }
            )

        return {
            "total_products": len(products),
            "total_quantity": tot_qty,
            "total_valuation": tot_val,
            "products": products,
        }

    async def get_low_stock_summary(self, db: AsyncSession) -> Dict[str, Any]:
        stmt = (
            select(
                Product.id.label("product_id"),
                Product.sku.label("product_sku"),
                Product.name.label("product_name"),
                Warehouse.name.label("warehouse_name"),
                StockBalance.available_quantity.label("current_stock"),
                func.coalesce(Product.reorder_level, Decimal("0.00")).label("reorder_level"),
                func.coalesce(Product.minimum_stock, Decimal("0.00")).label("minimum_stock"),
            )
            .join(StockBalance, StockBalance.product_id == Product.id)
            .join(Warehouse, Warehouse.id == StockBalance.warehouse_id)
            .where(
                StockBalance.available_quantity <= func.coalesce(Product.reorder_level, Decimal("0.00")),
            )
            .order_by(Product.sku.asc())
        )
        res = (await db.execute(stmt)).all()

        items = []
        for r in res:
            curr_stock = Decimal(str(r.current_stock or 0.0))
            shortage = r.reorder_level - curr_stock
            items.append(
                {
                    "product_id": r.product_id,
                    "product_sku": r.product_sku,
                    "product_name": r.product_name,
                    "warehouse_name": r.warehouse_name,
                    "current_stock": curr_stock,
                    "reorder_level": r.reorder_level,
                    "minimum_stock": r.minimum_stock,
                    "shortage_quantity": shortage if shortage > Decimal("0.00") else Decimal("0.00"),
                }
            )

        return {
            "total_low_stock_items": len(items),
            "items": items,
        }

    # =========================================================================
    # 6. HR & PAYROLL REPORTS
    # =========================================================================

    async def get_headcount_summary(self, db: AsyncSession) -> Dict[str, Any]:
        emp_stmt = select(
            func.count(Employee.id).label("total"),
            func.count(case((Employee.employment_status.ilike("Active"), Employee.id))).label("active"),
        ).where(Employee.is_deleted == False)
        emp_res = (await db.execute(emp_stmt)).first()
        total_emp = emp_res.total if emp_res else 0
        active_emp = emp_res.active if emp_res else 0

        # By Department
        dept_stmt = (
            select(
                Department.id.label("department_id"),
                Department.name.label("department_name"),
                func.count(case((Employee.employment_status.ilike("Active"), Employee.id))).label("active_count"),
                func.count(case((~Employee.employment_status.ilike("Active"), Employee.id))).label("inactive_count"),
                func.count(Employee.id).label("total_count"),
            )
            .join(Employee, Employee.department_id == Department.id)
            .where(and_(Department.is_deleted == False, Employee.is_deleted == False))
            .group_by(Department.id, Department.name)
            .order_by(Department.name.asc())
        )
        dept_res = (await db.execute(dept_stmt)).all()
        by_dept = [
            {
                "department_id": r.department_id,
                "department_name": r.department_name,
                "active_count": r.active_count,
                "inactive_count": r.inactive_count,
                "total_count": r.total_count,
            }
            for r in dept_res
        ]

        # By Position / Designation
        desig_stmt = (
            select(
                Position.title.label("designation_name"),
                func.count(Employee.id).label("employee_count"),
            )
            .join(Employee, Employee.position_id == Position.id)
            .where(and_(Position.is_deleted == False, Employee.is_deleted == False))
            .group_by(Position.title)
            .order_by(func.count(Employee.id).desc())
        )
        desig_res = (await db.execute(desig_stmt)).all()
        by_desig = [{"designation_name": r.designation_name, "employee_count": r.employee_count} for r in desig_res]

        # By Employment Type
        emp_type_stmt = (
            select(
                func.coalesce(Employee.employment_type, "Full-Time").label("emp_type"),
                func.count(Employee.id).label("count"),
            )
            .where(Employee.is_deleted == False)
            .group_by(Employee.employment_type)
        )
        emp_type_res = (await db.execute(emp_type_stmt)).all()
        by_emp_type = [{"employment_type": r.emp_type, "employee_count": r.count} for r in emp_type_res]

        return {
            "total_employees": total_emp,
            "total_active_employees": active_emp,
            "total_departments": len(by_dept),
            "by_department": by_dept,
            "by_designation": by_desig,
            "by_employment_type": by_emp_type,
        }

    async def get_attendance_summary(
        self, db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        filters = [Attendance.is_deleted == False]
        if from_date:
            filters.append(Attendance.attendance_date >= from_date)
        if to_date:
            filters.append(Attendance.attendance_date <= to_date)

        stmt = select(
            func.count(Attendance.id).label("total"),
            func.count(case((Attendance.attendance_status.ilike("Present"), Attendance.id))).label("present"),
            func.count(case((Attendance.attendance_status.ilike("Absent"), Attendance.id))).label("absent"),
            func.count(case((Attendance.attendance_status.ilike("Late"), Attendance.id))).label("late"),
            func.count(case((Attendance.attendance_status.ilike("On Leave"), Attendance.id))).label("leave"),
        ).where(and_(*filters))
        res = (await db.execute(stmt)).first()

        total = res.total if res else 0
        present = res.present if res else 0
        absent = res.absent if res else 0
        late = res.late if res else 0
        leave = res.leave if res else 0
        att_rate = float(present / total * 100) if total > 0 else 0.0

        dept_stmt = (
            select(
                Department.name.label("dept_name"),
                func.count(Attendance.id).label("total"),
                func.count(case((Attendance.attendance_status.ilike("Present"), Attendance.id))).label("present"),
                func.count(case((Attendance.attendance_status.ilike("Absent"), Attendance.id))).label("absent"),
                func.count(case((Attendance.attendance_status.ilike("Late"), Attendance.id))).label("late"),
                func.count(case((Attendance.attendance_status.ilike("On Leave"), Attendance.id))).label("leave"),
            )
            .join(Employee, Employee.id == Attendance.employee_id)
            .join(Department, Department.id == Employee.department_id)
            .where(and_(*filters, Department.is_deleted == False))
            .group_by(Department.name)
        )
        dept_rows = (await db.execute(dept_stmt)).all()
        by_dept = []
        for r in dept_rows:
            d_tot = r.total
            d_pres = r.present
            d_rate = float(d_pres / d_tot * 100) if d_tot > 0 else 0.0
            by_dept.append(
                {
                    "department_name": r.dept_name,
                    "total_records": d_tot,
                    "present_count": d_pres,
                    "absent_count": r.absent,
                    "late_count": r.late,
                    "leave_count": r.leave,
                    "attendance_rate": round(d_rate, 2),
                }
            )

        return {
            "from_date": from_date,
            "to_date": to_date,
            "total_attendance_records": total,
            "present_records": present,
            "absent_records": absent,
            "late_records": late,
            "leave_records": leave,
            "overall_attendance_rate": round(att_rate, 2),
            "by_department": by_dept,
        }

    async def get_leave_summary(
        self, db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        filters = [LeaveRequest.is_deleted == False]
        if from_date:
            filters.append(LeaveRequest.start_date >= from_date)
        if to_date:
            filters.append(LeaveRequest.end_date <= to_date)

        stmt = select(
            func.count(LeaveRequest.id).label("total"),
            func.count(case((LeaveRequest.status.ilike("Approved"), LeaveRequest.id))).label("approved"),
            func.count(case((LeaveRequest.status.ilike("Pending"), LeaveRequest.id))).label("pending"),
            func.count(case((LeaveRequest.status.ilike("Rejected"), LeaveRequest.id))).label("rejected"),
            func.coalesce(func.sum(case((LeaveRequest.status.ilike("Approved"), LeaveRequest.total_days))), 0.0).label("days_taken"),
        ).where(and_(*filters))
        res = (await db.execute(stmt)).first()

        total = res.total if res else 0
        approved = res.approved if res else 0
        pending = res.pending if res else 0
        rejected = res.rejected if res else 0
        days_taken = float(res.days_taken if res else 0.0)

        type_stmt = (
            select(
                LeaveType.name.label("leave_type_name"),
                func.count(LeaveRequest.id).label("req_count"),
                func.coalesce(func.sum(case((LeaveRequest.status.ilike("Approved"), LeaveRequest.total_days))), 0.0).label("days_app"),
            )
            .join(LeaveType, LeaveType.id == LeaveRequest.leave_type_id)
            .where(and_(*filters, LeaveType.is_deleted == False))
            .group_by(LeaveType.name)
        )
        type_rows = (await db.execute(type_stmt)).all()
        by_type = [
            {
                "leave_type_name": r.leave_type_name,
                "requests_count": r.req_count,
                "total_days_approved": float(r.days_app),
            }
            for r in type_rows
        ]

        return {
            "from_date": from_date,
            "to_date": to_date,
            "total_leave_requests": total,
            "approved_requests_count": approved,
            "pending_requests_count": pending,
            "rejected_requests_count": rejected,
            "total_leave_days_taken": days_taken,
            "by_leave_type": by_type,
        }

    async def get_payroll_summary(
        self, db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        filters = []
        if from_date:
            filters.append(PayrollPeriod.start_date >= from_date)
        if to_date:
            filters.append(PayrollPeriod.end_date <= to_date)

        stmt = (
            select(
                func.count(distinct(PayrollRun.id)).label("total_runs"),
                func.count(distinct(Payslip.id)).label("total_slips"),
                func.coalesce(func.sum(Payslip.gross_salary), Decimal("0.00")).label("total_gross"),
                func.coalesce(func.sum(Payslip.total_deductions), Decimal("0.00")).label("total_ded"),
                func.coalesce(func.sum(Payslip.net_salary), Decimal("0.00")).label("total_net"),
            )
            .select_from(PayrollPeriod)
            .join(PayrollRun, PayrollRun.payroll_period_id == PayrollPeriod.id, isouter=True)
            .join(Payslip, Payslip.payroll_period_id == PayrollPeriod.id, isouter=True)
            .where(and_(*filters) if filters else True)
        )
        res = (await db.execute(stmt)).first()

        tot_runs = res.total_runs if res else 0
        tot_slips = res.total_slips if res else 0
        tot_gross = Decimal(str(res.total_gross or 0.00)) if res else Decimal("0.00")
        tot_ded = Decimal(str(res.total_ded or 0.00)) if res else Decimal("0.00")
        tot_net = Decimal(str(res.total_net or 0.00)) if res else Decimal("0.00")

        # Cost by Department
        dept_cost_stmt = (
            select(
                Department.name.label("department_name"),
                func.count(distinct(Payslip.employee_id)).label("emp_count"),
                func.coalesce(func.sum(Payslip.gross_salary), Decimal("0.00")).label("dept_gross"),
                func.coalesce(func.sum(Payslip.total_deductions), Decimal("0.00")).label("dept_ded"),
                func.coalesce(func.sum(Payslip.net_salary), Decimal("0.00")).label("dept_net"),
            )
            .join(Employee, Employee.id == Payslip.employee_id)
            .join(Department, Department.id == Employee.department_id)
            .join(PayrollPeriod, PayrollPeriod.id == Payslip.payroll_period_id)
            .where(and_(*filters, Department.is_deleted == False) if filters else Department.is_deleted == False)
            .group_by(Department.name)
            .order_by(func.sum(Payslip.gross_salary).desc())
        )
        dept_rows = (await db.execute(dept_cost_stmt)).all()
        by_dept = [
            {
                "department_name": r.department_name,
                "employees_count": r.emp_count,
                "total_gross_pay": Decimal(str(r.dept_gross or 0.00)),
                "total_deductions": Decimal(str(r.dept_ded or 0.00)),
                "total_net_pay": Decimal(str(r.dept_net or 0.00)),
                "total_employer_cost": Decimal(str(r.dept_gross or 0.00)),
            }
            for r in dept_rows
        ]

        return {
            "from_date": from_date,
            "to_date": to_date,
            "total_payroll_runs": tot_runs,
            "total_payslips": tot_slips,
            "total_gross_pay": tot_gross,
            "total_deductions": tot_ded,
            "total_net_pay": tot_net,
            "total_employer_cost": tot_gross,
            "by_department": by_dept,
        }

    # =========================================================================
    # 7. CRM REPORTS
    # =========================================================================

    async def get_crm_leads_summary(
        self, db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        filters = [Lead.is_deleted == False]
        if from_date:
            filters.append(Lead.created_at >= datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc))
        if to_date:
            filters.append(Lead.created_at <= datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc))

        stmt = select(
            func.count(Lead.id).label("total"),
            func.count(case((Lead.is_converted == True, Lead.id))).label("converted"),
            func.coalesce(func.avg(Lead.score), 0.0).label("avg_score"),
        ).where(and_(*filters))
        res = (await db.execute(stmt)).first()

        total = res.total if res else 0
        converted = res.converted if res else 0
        avg_score = float(res.avg_score if res else 0.0)
        conv_rate = float(converted / total * 100) if total > 0 else 0.0

        # By status
        status_stmt = select(Lead.status, func.count(Lead.id)).where(and_(*filters)).group_by(Lead.status)
        status_rows = (await db.execute(status_stmt)).all()
        by_status = [
            {"status": r[0], "count": r[1], "percentage": round(float(r[1] / total * 100), 2) if total > 0 else 0.0}
            for r in status_rows
        ]

        # By source
        src_stmt = (
            select(func.coalesce(LeadSource.name, "Direct / None").label("source_name"), func.count(Lead.id))
            .join(LeadSource, LeadSource.id == Lead.source_id, isouter=True)
            .where(and_(*filters))
            .group_by(LeadSource.name)
        )
        src_rows = (await db.execute(src_stmt)).all()
        by_source = [
            {"source_name": r[0], "count": r[1], "percentage": round(float(r[1] / total * 100), 2) if total > 0 else 0.0}
            for r in src_rows
        ]

        return {
            "from_date": from_date,
            "to_date": to_date,
            "total_leads": total,
            "converted_leads_count": converted,
            "conversion_rate": round(conv_rate, 2),
            "average_lead_score": round(avg_score, 2),
            "by_status": by_status,
            "by_source": by_source,
        }

    async def get_opportunity_pipeline(
        self, db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        filters = [Opportunity.is_deleted == False]
        if from_date:
            filters.append(Opportunity.created_at >= datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc))
        if to_date:
            filters.append(Opportunity.created_at <= datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc))

        stmt = select(
            func.count(Opportunity.id).label("total"),
            func.coalesce(func.sum(Opportunity.expected_revenue), Decimal("0.00")).label("pipeline_val"),
            func.coalesce(func.sum(Opportunity.expected_revenue * (Opportunity.probability / Decimal("100.00"))), Decimal("0.00")).label("weighted_val"),
        ).where(and_(*filters))
        res = (await db.execute(stmt)).first()

        total = res.total if res else 0
        pipeline_val = res.pipeline_val if res else Decimal("0.00")
        weighted_val = res.weighted_val if res else Decimal("0.00")
        avg_deal = (pipeline_val / Decimal(total)) if total > 0 else Decimal("0.00")

        # By stage
        stage_stmt = (
            select(
                OpportunityStage.name.label("stage_name"),
                OpportunityStage.code.label("stage_code"),
                func.count(Opportunity.id).label("count"),
                func.coalesce(func.sum(Opportunity.expected_revenue), Decimal("0.00")).label("stage_val"),
                func.coalesce(func.sum(Opportunity.expected_revenue * (Opportunity.probability / Decimal("100.00"))), Decimal("0.00")).label("weighted_val"),
            )
            .join(OpportunityStage, OpportunityStage.id == Opportunity.stage_id)
            .where(and_(*filters))
            .group_by(OpportunityStage.name, OpportunityStage.code, OpportunityStage.display_order)
            .order_by(OpportunityStage.display_order.asc())
        )
        stage_rows = (await db.execute(stage_stmt)).all()
        by_stage = [
            {
                "stage_name": r.stage_name,
                "stage_code": r.stage_code,
                "opportunity_count": r.count,
                "total_value": r.stage_val,
                "weighted_value": r.weighted_val,
            }
            for r in stage_rows
        ]

        return {
            "from_date": from_date,
            "to_date": to_date,
            "total_opportunities": total,
            "total_pipeline_value": pipeline_val,
            "total_weighted_forecast": weighted_val,
            "average_deal_size": round(avg_deal, 2),
            "by_stage": by_stage,
        }

    async def get_opportunity_win_loss(
        self, db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        filters = [Opportunity.is_deleted == False, Opportunity.status.in_(["Won", "Lost"])]
        if from_date:
            filters.append(Opportunity.created_at >= datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc))
        if to_date:
            filters.append(Opportunity.created_at <= datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc))

        stmt = select(
            func.count(Opportunity.id).label("total_closed"),
            func.count(case((Opportunity.status == "Won", Opportunity.id))).label("won_cnt"),
            func.count(case((Opportunity.status == "Lost", Opportunity.id))).label("lost_cnt"),
            func.coalesce(func.sum(case((Opportunity.status == "Won", Opportunity.expected_revenue))), Decimal("0.00")).label("won_rev"),
            func.coalesce(func.sum(case((Opportunity.status == "Lost", Opportunity.expected_revenue))), Decimal("0.00")).label("lost_rev"),
        ).where(and_(*filters))
        res = (await db.execute(stmt)).first()

        total = res.total_closed if res else 0
        won = res.won_cnt if res else 0
        lost = res.lost_cnt if res else 0
        won_rev = res.won_rev if res else Decimal("0.00")
        lost_rev = res.lost_rev if res else Decimal("0.00")
        win_rate = float(won / total * 100) if total > 0 else 0.0

        return {
            "from_date": from_date,
            "to_date": to_date,
            "total_closed_deals": total,
            "won_count": won,
            "lost_count": lost,
            "win_rate": round(win_rate, 2),
            "total_won_revenue": won_rev,
            "total_lost_revenue": lost_rev,
        }

    async def get_crm_activity_summary(
        self, db: AsyncSession, from_date: Optional[date] = None, to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        filters = []
        if from_date:
            filters.append(Activity.created_at >= datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc))
        if to_date:
            filters.append(Activity.created_at <= datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc))

        stmt = select(
            func.count(Activity.id).label("total"),
            func.count(case((Activity.status == "Completed", Activity.id))).label("completed"),
            func.count(case((Activity.status != "Completed", Activity.id))).label("pending"),
        ).where(and_(*filters) if filters else True)
        res = (await db.execute(stmt)).first()

        total = res.total if res else 0
        completed = res.completed if res else 0
        pending = res.pending if res else 0
        comp_rate = float(completed / total * 100) if total > 0 else 0.0

        type_stmt = (
            select(
                Activity.activity_type,
                func.count(Activity.id).label("total"),
                func.count(case((Activity.status == "Completed", Activity.id))).label("completed"),
                func.count(case((Activity.status != "Completed", Activity.id))).label("pending"),
            )
            .where(and_(*filters) if filters else True)
            .group_by(Activity.activity_type)
        )
        type_rows = (await db.execute(type_stmt)).all()
        by_type = [
            {
                "activity_type": r.activity_type,
                "total_count": r.total,
                "completed_count": r.completed,
                "pending_count": r.pending,
            }
            for r in type_rows
        ]

        return {
            "from_date": from_date,
            "to_date": to_date,
            "total_activities": total,
            "total_completed": completed,
            "total_pending": pending,
            "completion_rate": round(comp_rate, 2),
            "by_type": by_type,
        }


reporting_repository = ReportingRepository()


# =========================================================================
# LEGACY DYNAMIC BI REPOSITORIES
# =========================================================================

class DashboardRepository(BaseRepository[Dashboard, Any, Any]):
    def __init__(self):
        super().__init__(Dashboard)

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[Dashboard]:
        stmt = select(Dashboard).where(Dashboard.code == code, Dashboard.is_deleted == False)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_type(self, db: AsyncSession, *, dashboard_type: str) -> Optional[Dashboard]:
        stmt = select(Dashboard).where(
            Dashboard.dashboard_type == dashboard_type,
            Dashboard.is_system == True,
            Dashboard.is_deleted == False,
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_dashboards(
        self, db: AsyncSession, *, owner_id: Optional[uuid.UUID] = None
    ) -> List[Dashboard]:
        conditions = [Dashboard.is_deleted == False]
        if owner_id:
            conditions.append(or_(Dashboard.owner_id == owner_id, Dashboard.is_shared == True, Dashboard.is_system == True))
        else:
            conditions.append(or_(Dashboard.is_shared == True, Dashboard.is_system == True))
        stmt = select(Dashboard).where(and_(*conditions)).order_by(Dashboard.name.asc())
        res = await db.execute(stmt)
        return list(res.scalars().all())


class DashboardWidgetRepository(BaseRepository[DashboardWidget, Any, Any]):
    def __init__(self):
        super().__init__(DashboardWidget)

    async def get_by_dashboard(self, db: AsyncSession, *, dashboard_id: uuid.UUID) -> List[DashboardWidget]:
        stmt = select(DashboardWidget).where(DashboardWidget.dashboard_id == dashboard_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())


class KPIRepository(BaseRepository[KPI, Any, Any]):
    def __init__(self):
        super().__init__(KPI)

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[KPI]:
        stmt = select(KPI).where(KPI.code == code, KPI.is_deleted == False)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_module(self, db: AsyncSession, *, module: str) -> List[KPI]:
        stmt = select(KPI).where(KPI.module == module, KPI.is_active == True, KPI.is_deleted == False)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_all_active(self, db: AsyncSession) -> List[KPI]:
        stmt = select(KPI).where(KPI.is_active == True, KPI.is_deleted == False)
        res = await db.execute(stmt)
        return list(res.scalars().all())


class KPIMetricRepository(BaseRepository[KPIMetric, Any, Any]):
    def __init__(self):
        super().__init__(KPIMetric)

    async def get_latest_by_kpi(self, db: AsyncSession, *, kpi_id: uuid.UUID) -> Optional[KPIMetric]:
        stmt = select(KPIMetric).where(KPIMetric.kpi_id == kpi_id).order_by(KPIMetric.recorded_at.desc())
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_history(self, db: AsyncSession, *, kpi_id: uuid.UUID, limit: int = 30) -> List[KPIMetric]:
        stmt = select(KPIMetric).where(KPIMetric.kpi_id == kpi_id).order_by(KPIMetric.recorded_at.desc()).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all())


class ReportTemplateRepository(BaseRepository[ReportTemplate, Any, Any]):
    def __init__(self):
        super().__init__(ReportTemplate)

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[ReportTemplate]:
        stmt = select(ReportTemplate).where(ReportTemplate.code == code, ReportTemplate.is_deleted == False)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_module(self, db: AsyncSession, *, module: str) -> List[ReportTemplate]:
        stmt = select(ReportTemplate).where(ReportTemplate.module == module, ReportTemplate.is_deleted == False)
        res = await db.execute(stmt)
        return list(res.scalars().all())


class SavedReportRepository(BaseRepository[SavedReport, Any, Any]):
    def __init__(self):
        super().__init__(SavedReport)

    async def get_user_saved_reports(
        self, db: AsyncSession, *, owner_id: Optional[uuid.UUID] = None
    ) -> List[SavedReport]:
        conditions = [SavedReport.is_deleted == False]
        if owner_id:
            conditions.append(or_(SavedReport.owner_id == owner_id, SavedReport.is_shared == True))
        else:
            conditions.append(SavedReport.is_shared == True)
        stmt = select(SavedReport).where(and_(*conditions)).order_by(SavedReport.name.asc())
        res = await db.execute(stmt)
        return list(res.scalars().all())


class ScheduledReportRepository(BaseRepository[ScheduledReport, Any, Any]):
    def __init__(self):
        super().__init__(ScheduledReport)

    async def get_due_schedules(self, db: AsyncSession) -> List[ScheduledReport]:
        stmt = select(ScheduledReport).where(
            ScheduledReport.is_active == True,
            ScheduledReport.is_deleted == False,
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


class ReportExecutionRepository(BaseRepository[ReportExecution, Any, Any]):
    def __init__(self):
        super().__init__(ReportExecution)

    async def get_recent(self, db: AsyncSession, *, limit: int = 50) -> List[ReportExecution]:
        stmt = select(ReportExecution).order_by(ReportExecution.created_at.desc()).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all())


class AnalyticsSnapshotRepository(BaseRepository[AnalyticsSnapshot, Any, Any]):
    def __init__(self):
        super().__init__(AnalyticsSnapshot)

    async def get_latest_by_type(
        self, db: AsyncSession, *, snapshot_type: str, module: str
    ) -> Optional[AnalyticsSnapshot]:
        stmt = (
            select(AnalyticsSnapshot)
            .where(AnalyticsSnapshot.snapshot_type == snapshot_type, AnalyticsSnapshot.module == module)
            .order_by(AnalyticsSnapshot.created_at.desc())
        )
        res = await db.execute(stmt)
        return res.scalars().first()


class ChartConfigurationRepository(BaseRepository[ChartConfiguration, Any, Any]):
    def __init__(self):
        super().__init__(ChartConfiguration)

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[ChartConfiguration]:
        stmt = select(ChartConfiguration).where(ChartConfiguration.code == code, ChartConfiguration.is_deleted == False)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_module(self, db: AsyncSession, *, module: str) -> List[ChartConfiguration]:
        stmt = select(ChartConfiguration).where(ChartConfiguration.module == module, ChartConfiguration.is_deleted == False)
        res = await db.execute(stmt)
        return list(res.scalars().all())
