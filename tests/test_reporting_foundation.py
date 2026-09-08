from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.models.department import Department
from app.models.position import Position
from app.models.employee import Employee
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.unit_of_measure import UnitOfMeasure
from app.models.warehouse import Warehouse
from app.models.stock_balance import StockBalance
from app.models.sales_order import SalesOrder, SalesOrderItem
from app.models.sales_quotation import SalesQuotation, SalesQuotationItem
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.goods_receipt import GoodsReceipt
from app.models.crm import Activity, Lead, LeadSource, Opportunity, OpportunityStage
from app.models.finance import ChartOfAccount, FiscalYear, FiscalPeriod, Journal, JournalLine, JournalType
from app.models.salary_structure import SalaryStructure
from app.models.employee_compensation import EmployeeCompensation
from app.models.payroll_period import PayrollPeriod, PayrollRecord
from app.models.payroll_run import PayrollRun
from app.models.payslip import Payslip
from app.schemas.reporting import ReportTypeEnum
from app.services.reporting_services import reporting_service


@pytest.mark.asyncio
async def test_management_dashboard_aggregation():
    """Verify that the Executive Management Dashboard aggregates metrics across all 7 ERP domains."""
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]

        # 1. HR
        dept = Department(name=f"Reporting Dept {unique}", code=f"RD_{unique}")
        session.add(dept)
        await session.flush()

        emp = Employee(
            first_name="Alice",
            last_name="Reporter",
            work_email=f"alice_{unique}@test.com",
            employee_code=f"EMP-R-{unique}",
            department_id=dept.id,
            employment_status="Active",
            joining_date=date(2026, 1, 1),
        )
        session.add(emp)

        # 2. CRM
        src = LeadSource(code=f"SRC_{unique}", name=f"Website {unique}")
        session.add(src)
        await session.flush()

        lead = Lead(
            lead_code=f"LEAD-R-{unique}",
            first_name="Bob",
            last_name="Lead",
            email=f"bob_{unique}@test.com",
            source_id=src.id,
            status="New",
            is_converted=False,
        )
        session.add(lead)

        stage = OpportunityStage(code=f"STAGE_{unique}", name="Prospecting", probability_default=Decimal("10.00"), display_order=1)
        session.add(stage)
        await session.flush()

        opp = Opportunity(
            opportunity_code=f"OPP-R-{unique}",
            title=f"Dashboard Deal {unique}",
            stage_id=stage.id,
            status="Open",
            expected_revenue=Decimal("25000.00"),
            probability=Decimal("20.00"),
        )
        session.add(opp)

        # 3. Inventory
        cat = ProductCategory(name=f"Report Cat {unique}", code=f"RC_{unique}")
        uom = UnitOfMeasure(name=f"Pieces {unique}", code=f"PCS_{unique}", symbol=f"pcs_{unique}", category="Count")
        session.add_all([cat, uom])
        await session.flush()

        wh = Warehouse(code=f"WH-R-{unique}", name=f"Warehouse {unique}")
        session.add(wh)
        await session.flush()

        prod = Product(
            sku=f"SKU-R-{unique}",
            name=f"Report Product {unique}",
            category_id=cat.id,
            base_unit_id=uom.id,
            default_unit_price=Decimal("150.00"),
            reorder_level=Decimal("10.0000"),
        )
        session.add(prod)
        await session.flush()

        stock = StockBalance(
            product_id=prod.id,
            warehouse_id=wh.id,
            available_quantity=50.0,
            reserved_quantity=5.0,
        )
        session.add(stock)

        # 4. Sales
        cust = Customer(customer_code=f"CUST-R-{unique}", name=f"Client {unique}")
        session.add(cust)
        await session.flush()

        so = SalesOrder(
            order_number=f"SO-R-{unique}",
            customer_id=cust.id,
            status="Approved",
            subtotal_amount=Decimal("3000.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("300.00"),
            total_amount=Decimal("3300.00"),
        )
        session.add(so)

        # 5. Procurement
        supp = Supplier(code=f"SUP-R-{unique}", name=f"Vendor {unique}")
        session.add(supp)
        await session.flush()

        po = PurchaseOrder(
            po_number=f"PO-R-{unique}",
            supplier_id=supp.id,
            status="Approved",
            subtotal=Decimal("1500.00"),
            tax_amount=Decimal("150.00"),
            total_amount=Decimal("1650.00"),
        )
        session.add(po)

        # 6. Finance
        rev_acc = ChartOfAccount(
            account_code=f"4000_{unique}",
            name=f"Consulting Revenue {unique}",
            account_type="Revenue",
            is_active=True,
            current_balance=Decimal("12000.00"),
        )
        exp_acc = ChartOfAccount(
            account_code=f"5000_{unique}",
            name=f"Office Expense {unique}",
            account_type="Expense",
            is_active=True,
            current_balance=Decimal("4000.00"),
        )
        session.add_all([rev_acc, exp_acc])
        await session.flush()

        jt = JournalType(name=f"General Journal {unique}", code=f"GEN_{unique}", prefix="JV")
        session.add(jt)
        await session.flush()

        j = Journal(
            journal_number=f"JV-R-{unique}",
            journal_type_id=jt.id,
            posting_date=date.today(),
            description="Dashboard test journal",
            status="Posted",
            total_debit=Decimal("1000.00"),
            total_credit=Decimal("1000.00"),
        )
        session.add(j)
        await session.flush()

        jl1 = JournalLine(
            journal_id=j.id,
            account_id=exp_acc.id,
            line_number=1,
            debit=Decimal("1000.00"),
            credit=Decimal("0.00"),
        )
        jl2 = JournalLine(
            journal_id=j.id,
            account_id=rev_acc.id,
            line_number=2,
            debit=Decimal("0.00"),
            credit=Decimal("1000.00"),
        )
        session.add_all([jl1, jl2])

        # 7. Payroll
        struct = SalaryStructure(code=f"SS-DASH-{unique}", name=f"Structure {unique}", currency="USD", effective_from=date(2026, 1, 1))
        session.add(struct)
        await session.flush()

        comp = EmployeeCompensation(
            employee_id=emp.id,
            salary_structure_id=struct.id,
            effective_from=date(2026, 1, 1),
            annual_ctc=60000.00,
            monthly_gross_salary=5000.00,
            status="Active",
        )
        session.add(comp)
        await session.flush()

        period = PayrollPeriod(
            period_code=f"PR-DASH-{unique}",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 30),
            status="Completed",
        )
        session.add(period)
        await session.flush()

        prun = PayrollRun(
            payroll_period_id=period.id,
            run_number=f"RUN-R-{unique}",
            status="Approved",
        )
        session.add(prun)
        await session.flush()

        prec = PayrollRecord(
            payroll_period_id=period.id,
            employee_id=emp.id,
            employee_compensation_id=comp.id,
            gross_salary=Decimal("5000.00"),
            total_deductions=Decimal("500.00"),
            net_salary=Decimal("4500.00"),
            status="Paid",
        )
        session.add(prec)
        await session.flush()

        ps = Payslip(
            payroll_record_id=prec.id,
            payroll_period_id=period.id,
            employee_id=emp.id,
            payslip_number=f"PS-R-{unique}",
            gross_salary=Decimal("5000.00"),
            total_deductions=Decimal("500.00"),
            net_salary=Decimal("4500.00"),
        )
        session.add(ps)
        await session.commit()

        # Execute Dashboard Query
        dashboard = await reporting_service.get_dashboard(session)

        # Assertions across domains
        assert dashboard.hr.total_employees >= 1
        assert dashboard.hr.active_employees >= 1
        assert dashboard.crm.open_leads >= 1
        assert dashboard.crm.active_opportunities >= 1
        assert dashboard.crm.pipeline_value >= Decimal("25000.00")
        assert dashboard.sales.total_orders_count >= 1
        assert dashboard.sales.total_sales_revenue >= Decimal("3300.00")
        assert dashboard.procurement.total_pos_count >= 1
        assert dashboard.procurement.total_spend >= Decimal("1650.00")
        assert dashboard.inventory.total_products_count >= 1
        assert dashboard.finance.posted_journals_count >= 1
        assert dashboard.payroll.total_payroll_runs_count >= 1


@pytest.mark.asyncio
async def test_finance_reports_profit_loss_and_balance_sheet():
    """Verify Profit & Loss, Balance Sheet, and Trial Balance generation."""
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]

        asset_acc = ChartOfAccount(account_code=f"1010_{unique}", name=f"Operating Bank {unique}", account_type="Asset", is_active=True, current_balance=Decimal("50000.00"))
        liab_acc = ChartOfAccount(account_code=f"2010_{unique}", name=f"Trade Payables {unique}", account_type="Liability", is_active=True, current_balance=Decimal("20000.00"))
        equity_acc = ChartOfAccount(account_code=f"3010_{unique}", name=f"Retained Earnings {unique}", account_type="Equity", is_active=True, current_balance=Decimal("30000.00"))
        rev_acc = ChartOfAccount(account_code=f"4010_{unique}", name=f"Services Sales {unique}", account_type="Revenue", is_active=True, current_balance=Decimal("0.00"))
        exp_acc = ChartOfAccount(account_code=f"5010_{unique}", name=f"Marketing Expense {unique}", account_type="Expense", is_active=True, current_balance=Decimal("0.00"))

        session.add_all([asset_acc, liab_acc, equity_acc, rev_acc, exp_acc])
        await session.flush()

        jt = JournalType(name=f"General Journal {unique}", code=f"GEN_F_{unique}", prefix="JV")
        session.add(jt)
        await session.flush()

        j = Journal(
            journal_number=f"JV-FIN-{unique}",
            journal_type_id=jt.id,
            posting_date=date(2026, 9, 15),
            description="Finance test journal",
            status="Posted",
            total_debit=Decimal("8000.00"),
            total_credit=Decimal("8000.00"),
        )
        session.add(j)
        await session.flush()

        jl1 = JournalLine(journal_id=j.id, account_id=asset_acc.id, line_number=1, debit=Decimal("8000.00"), credit=Decimal("0.00"))
        jl2 = JournalLine(journal_id=j.id, account_id=rev_acc.id, line_number=2, debit=Decimal("0.00"), credit=Decimal("8000.00"))
        session.add_all([jl1, jl2])
        await session.commit()

        # 1. Profit & Loss
        pnl = await reporting_service.get_profit_loss(session, from_date=date(2026, 9, 1), to_date=date(2026, 9, 30))
        assert pnl.total_revenue >= Decimal("8000.00")
        assert len(pnl.revenue_lines) >= 1

        # 2. Balance Sheet
        bs = await reporting_service.get_balance_sheet(session)
        assert bs.total_assets >= Decimal("50000.00")
        assert bs.total_liabilities >= Decimal("20000.00")
        assert bs.total_equity >= Decimal("30000.00")

        # 3. Trial Balance
        tb = await reporting_service.get_trial_balance(session, from_date=date(2026, 9, 1), to_date=date(2026, 9, 30))
        assert tb.total_debit >= Decimal("8000.00")
        assert tb.total_credit >= Decimal("8000.00")


@pytest.mark.asyncio
async def test_sales_reports_summary_customers_products():
    """Verify Sales Order Summary, Sales by Customer, and Sales by Product reports."""
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]

        cust1 = Customer(customer_code=f"CUST-S1-{unique}", name=f"MegaCorp {unique}")
        cust2 = Customer(customer_code=f"CUST-S2-{unique}", name=f"TechCorp {unique}")
        session.add_all([cust1, cust2])

        cat = ProductCategory(name=f"Tech Cat {unique}", code=f"TC_{unique}")
        uom = UnitOfMeasure(name=f"Units {unique}", code=f"U_{unique}", symbol=f"u_{unique}", category="Count")
        session.add_all([cat, uom])
        await session.flush()

        prod1 = Product(sku=f"SKU-S1-{unique}", name="Enterprise Server", category_id=cat.id, base_unit_id=uom.id, default_unit_price=Decimal("1000.00"))
        prod2 = Product(sku=f"SKU-S2-{unique}", name="Support License", category_id=cat.id, base_unit_id=uom.id, default_unit_price=Decimal("200.00"))
        session.add_all([prod1, prod2])
        await session.flush()

        so1 = SalesOrder(order_number=f"SO-S1-{unique}", customer_id=cust1.id, status="Approved", subtotal_amount=Decimal("5000.00"), discount_amount=Decimal("0.00"), tax_amount=Decimal("500.00"), total_amount=Decimal("5500.00"))
        so2 = SalesOrder(order_number=f"SO-S2-{unique}", customer_id=cust2.id, status="Closed", subtotal_amount=Decimal("2000.00"), discount_amount=Decimal("0.00"), tax_amount=Decimal("200.00"), total_amount=Decimal("2200.00"))
        session.add_all([so1, so2])
        await session.flush()

        item1 = SalesOrderItem(sales_order_id=so1.id, product_id=prod1.id, quantity=Decimal("5.0000"), unit_price=Decimal("1000.00"), line_total=Decimal("5000.00"))
        item2 = SalesOrderItem(sales_order_id=so2.id, product_id=prod2.id, quantity=Decimal("10.0000"), unit_price=Decimal("200.00"), line_total=Decimal("2000.00"))
        session.add_all([item1, item2])
        await session.commit()

        # Test Sales Summary
        summary = await reporting_service.get_sales_summary(session)
        assert summary.total_orders >= 2
        assert summary.total_net_amount >= Decimal("7700.00")

        # Test Sales by Customer
        by_cust = await reporting_service.get_sales_by_customer(session)
        assert by_cust.total_customers >= 2
        assert any(c.customer_code == f"CUST-S1-{unique}" for c in by_cust.customers)

        # Test Sales by Product
        by_prod = await reporting_service.get_sales_by_product(session)
        assert by_prod.total_products >= 2
        assert any(p.product_sku == f"SKU-S1-{unique}" for p in by_prod.products)


@pytest.mark.asyncio
async def test_procurement_reports_summary_and_suppliers():
    """Verify Purchase Order Summary and Purchases by Supplier reports."""
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]

        supp1 = Supplier(code=f"SUP-P1-{unique}", name=f"Global Silicon {unique}")
        supp2 = Supplier(code=f"SUP-P2-{unique}", name=f"Fast Logistics {unique}")
        session.add_all([supp1, supp2])
        await session.flush()

        po1 = PurchaseOrder(po_number=f"PO-P1-{unique}", supplier_id=supp1.id, status="Approved", subtotal=Decimal("8000.00"), tax_amount=Decimal("800.00"), total_amount=Decimal("8800.00"))
        po2 = PurchaseOrder(po_number=f"PO-P2-{unique}", supplier_id=supp2.id, status="Closed", subtotal=Decimal("1200.00"), tax_amount=Decimal("120.00"), total_amount=Decimal("1320.00"))
        session.add_all([po1, po2])
        await session.commit()

        po_summary = await reporting_service.get_procurement_summary(session)
        assert po_summary.total_purchase_orders >= 2
        assert po_summary.total_spend >= Decimal("10120.00")

        by_supp = await reporting_service.get_purchases_by_supplier(session)
        assert by_supp.total_suppliers >= 2
        assert any(s.supplier_code == f"SUP-P1-{unique}" for s in by_supp.suppliers)


@pytest.mark.asyncio
async def test_inventory_reports_warehouses_products_low_stock():
    """Verify Stock by Warehouse, Stock by Product, and Low Stock Alerts reports."""
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]

        cat = ProductCategory(name=f"Hardware {unique}", code=f"HW_{unique}")
        uom = UnitOfMeasure(name=f"Items {unique}", code=f"IT_{unique}", symbol=f"it_{unique}", category="Count")
        session.add_all([cat, uom])
        await session.flush()

        wh_central = Warehouse(code=f"WH-C-{unique}", name=f"Central Hub {unique}")
        session.add(wh_central)
        await session.flush()

        p_ok = Product(sku=f"SKU-OK-{unique}", name="Plentiful Item", category_id=cat.id, base_unit_id=uom.id, default_unit_price=Decimal("20.00"), reorder_level=Decimal("10.0000"))
        p_low = Product(sku=f"SKU-LOW-{unique}", name="Scarce Component", category_id=cat.id, base_unit_id=uom.id, default_unit_price=Decimal("100.00"), reorder_level=Decimal("25.0000"))
        session.add_all([p_ok, p_low])
        await session.flush()

        sb_ok = StockBalance(product_id=p_ok.id, warehouse_id=wh_central.id, available_quantity=100.0, reserved_quantity=10.0)
        sb_low = StockBalance(product_id=p_low.id, warehouse_id=wh_central.id, available_quantity=5.0, reserved_quantity=0.0)
        session.add_all([sb_ok, sb_low])
        await session.commit()

        # Stock by warehouse
        by_wh = await reporting_service.get_stock_by_warehouse(session)
        assert any(w.warehouse_code == f"WH-C-{unique}" for w in by_wh.warehouses)

        # Stock by product
        by_prod = await reporting_service.get_stock_by_product(session)
        assert any(p.product_sku == f"SKU-OK-{unique}" for p in by_prod.products)

        # Low stock report
        low_rep = await reporting_service.get_low_stock_summary(session)
        assert any(item.product_sku == f"SKU-LOW-{unique}" for item in low_rep.items)


@pytest.mark.asyncio
async def test_hr_and_payroll_reports():
    """Verify Headcount Summary and Payroll Cost breakdown reports."""
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]

        dept_eng = Department(name=f"Engineering {unique}", code=f"ENG_{unique}")
        dept_mkt = Department(name=f"Marketing {unique}", code=f"MKT_{unique}")
        session.add_all([dept_eng, dept_mkt])
        await session.flush()

        pos_lead = Position(title=f"Lead Architect {unique}", code=f"ARCH_{unique}", department_id=dept_eng.id)
        session.add(pos_lead)
        await session.flush()

        e1 = Employee(first_name="John", last_name="Doe", work_email=f"john_{unique}@corp.com", employee_code=f"EMP-H1-{unique}", department_id=dept_eng.id, position_id=pos_lead.id, employment_status="Active", employment_type="Full-Time", joining_date=date(2026, 1, 1))
        e2 = Employee(first_name="Jane", last_name="Smith", work_email=f"jane_{unique}@corp.com", employee_code=f"EMP-H2-{unique}", department_id=dept_eng.id, employment_status="Active", employment_type="Full-Time", joining_date=date(2026, 2, 1))
        e3 = Employee(first_name="Mark", last_name="Taylor", work_email=f"mark_{unique}@corp.com", employee_code=f"EMP-H3-{unique}", department_id=dept_mkt.id, employment_status="Inactive", employment_type="Contract", joining_date=date(2026, 3, 1))
        session.add_all([e1, e2, e3])
        await session.flush()

        struct = SalaryStructure(code=f"SS-HR-{unique}", name=f"HR Structure {unique}", currency="USD", effective_from=date(2026, 1, 1))
        session.add(struct)
        await session.flush()

        comp1 = EmployeeCompensation(employee_id=e1.id, salary_structure_id=struct.id, effective_from=date(2026, 1, 1), annual_ctc=108000.00, monthly_gross_salary=9000.00, status="Active")
        comp2 = EmployeeCompensation(employee_id=e2.id, salary_structure_id=struct.id, effective_from=date(2026, 1, 1), annual_ctc=72000.00, monthly_gross_salary=6000.00, status="Active")
        session.add_all([comp1, comp2])
        await session.flush()

        period = PayrollPeriod(
            period_code=f"PAY-P-{unique}",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 30),
            status="Completed",
        )
        session.add(period)
        await session.flush()

        prun = PayrollRun(
            payroll_period_id=period.id,
            run_number=f"PAY-HR-{unique}",
            status="Approved",
        )
        session.add(prun)
        await session.flush()

        prec1 = PayrollRecord(payroll_period_id=period.id, employee_id=e1.id, employee_compensation_id=comp1.id, gross_salary=Decimal("9000.00"), total_deductions=Decimal("1200.00"), net_salary=Decimal("7800.00"), status="Paid")
        prec2 = PayrollRecord(payroll_period_id=period.id, employee_id=e2.id, employee_compensation_id=comp2.id, gross_salary=Decimal("6000.00"), total_deductions=Decimal("800.00"), net_salary=Decimal("5200.00"), status="Paid")
        session.add_all([prec1, prec2])
        await session.flush()

        ps1 = Payslip(payroll_record_id=prec1.id, payroll_period_id=period.id, employee_id=e1.id, payslip_number=f"PS1-{unique}", gross_salary=Decimal("9000.00"), total_deductions=Decimal("1200.00"), net_salary=Decimal("7800.00"))
        ps2 = Payslip(payroll_record_id=prec2.id, payroll_period_id=period.id, employee_id=e2.id, payslip_number=f"PS2-{unique}", gross_salary=Decimal("6000.00"), total_deductions=Decimal("800.00"), net_salary=Decimal("5200.00"))
        session.add_all([ps1, ps2])
        await session.commit()

        # Headcount report
        headcount = await reporting_service.get_hr_headcount(session)
        assert headcount.total_employees >= 3
        assert headcount.total_active_employees >= 2

        # Payroll summary
        payroll = await reporting_service.get_payroll_summary(session, from_date=date(2026, 9, 1), to_date=date(2026, 9, 30))
        assert payroll.total_gross_pay >= Decimal("15000.00")
        assert payroll.total_net_pay >= Decimal("13000.00")
        assert len(payroll.by_department) >= 1


@pytest.mark.asyncio
async def test_crm_reports_leads_and_pipeline():
    """Verify CRM Lead summary and Opportunity Pipeline conversion reports."""
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]

        src_ad = LeadSource(code=f"ADS_{unique}", name=f"Google Ads {unique}")
        stage_prop = OpportunityStage(code=f"PROP_{unique}", name=f"Proposal {unique}", probability_default=Decimal("50.00"), display_order=2)
        session.add_all([src_ad, stage_prop])
        await session.flush()

        l1 = Lead(lead_code=f"L-C1-{unique}", first_name="Chris", last_name="Evans", email=f"chris_{unique}@gmail.com", status="Contacted", is_converted=True, source_id=src_ad.id, score=85)
        l2 = Lead(lead_code=f"L-C2-{unique}", first_name="Scarlett", last_name="Johansson", email=f"scarlett_{unique}@gmail.com", status="New", is_converted=False, source_id=src_ad.id, score=40)
        session.add_all([l1, l2])

        opp1 = Opportunity(opportunity_code=f"OPP-C1-{unique}", title=f"Cloud Migration {unique}", stage_id=stage_prop.id, status="Open", expected_revenue=Decimal("40000.00"), probability=Decimal("50.00"))
        opp2 = Opportunity(opportunity_code=f"OPP-C2-{unique}", title=f"Legacy Upgrade {unique}", stage_id=stage_prop.id, status="Won", expected_revenue=Decimal("15000.00"), probability=Decimal("100.00"))
        session.add_all([opp1, opp2])
        await session.commit()

        # Leads report
        leads = await reporting_service.get_crm_leads(session)
        assert leads.total_leads >= 2
        assert leads.converted_leads_count >= 1

        # Pipeline report
        pipeline = await reporting_service.get_crm_pipeline(session)
        assert pipeline.total_opportunities >= 1
        assert pipeline.total_pipeline_value >= Decimal("40000.00")


@pytest.mark.asyncio
async def test_report_csv_exports():
    """Verify CSV export formatting and RFC 4180 headers across multiple report types."""
    async with AsyncSessionLocal() as session:
        # Dashboard CSV
        dash_csv = await reporting_service.export_report(session, report_type=ReportTypeEnum.DASHBOARD.value)
        assert "Domain,Metric,Value" in dash_csv
        assert "HR,Total Employees" in dash_csv

        # Sales by customer CSV
        sales_csv = await reporting_service.export_report(session, report_type=ReportTypeEnum.SALES_BY_CUSTOMER.value)
        assert "Customer Code,Customer Name,Orders Count,Total Spent" in sales_csv

        # Procurement CSV
        proc_csv = await reporting_service.export_report(session, report_type=ReportTypeEnum.PROCUREMENT_BY_SUPPLIER.value)
        assert "Supplier Code,Supplier Name,PO Count,Total Purchases" in proc_csv

        # Headcount CSV
        hr_csv = await reporting_service.export_report(session, report_type=ReportTypeEnum.HR_HEADCOUNT.value)
        assert "Total Employees" in hr_csv


@pytest.mark.asyncio
async def test_reporting_read_only_and_domain_isolation():
    """Ensure reporting operations do not mutate or create records in underlying domain tables."""
    async with AsyncSessionLocal() as session:
        # Capture initial counts
        emp_count_before = (await session.execute(select(func.count(Employee.id)))).scalar()
        so_count_before = (await session.execute(select(func.count(SalesOrder.id)))).scalar()
        po_count_before = (await session.execute(select(func.count(PurchaseOrder.id)))).scalar()
        lead_count_before = (await session.execute(select(func.count(Lead.id)))).scalar()
        journal_count_before = (await session.execute(select(func.count(Journal.id)))).scalar()

        # Run multiple reporting methods
        await reporting_service.get_dashboard(session)
        await reporting_service.get_profit_loss(session)
        await reporting_service.get_balance_sheet(session)
        await reporting_service.get_sales_summary(session)
        await reporting_service.get_procurement_summary(session)
        await reporting_service.get_stock_by_warehouse(session)
        await reporting_service.get_hr_headcount(session)
        await reporting_service.get_crm_leads(session)

        # Assert post counts remain strictly unchanged
        emp_count_after = (await session.execute(select(func.count(Employee.id)))).scalar()
        so_count_after = (await session.execute(select(func.count(SalesOrder.id)))).scalar()
        po_count_after = (await session.execute(select(func.count(PurchaseOrder.id)))).scalar()
        lead_count_after = (await session.execute(select(func.count(Lead.id)))).scalar()
        journal_count_after = (await session.execute(select(func.count(Journal.id)))).scalar()

        assert emp_count_after == emp_count_before
        assert so_count_after == so_count_before
        assert po_count_after == po_count_before
        assert lead_count_after == lead_count_before
        assert journal_count_after == journal_count_before


@pytest.mark.asyncio
async def test_empty_database_handling():
    """Verify that reporting methods execute cleanly with graceful defaults on out-of-range dates."""
    async with AsyncSessionLocal() as session:
        future_start = date(2099, 1, 1)
        future_end = date(2099, 12, 31)

        pnl = await reporting_service.get_profit_loss(session, from_date=future_start, to_date=future_end)
        assert pnl.total_revenue == Decimal("0.00")
        assert pnl.total_expenses == Decimal("0.00")
        assert pnl.net_profit == Decimal("0.00")
        assert pnl.revenue_lines == []

        sales = await reporting_service.get_sales_summary(session, from_date=future_start, to_date=future_end)
        assert sales.total_orders == 0
        assert sales.total_net_amount == Decimal("0.00")

        po = await reporting_service.get_procurement_summary(session, from_date=future_start, to_date=future_end)
        assert po.total_purchase_orders == 0
        assert po.total_spend == Decimal("0.00")

        payroll = await reporting_service.get_payroll_summary(session, from_date=future_start, to_date=future_end)
        assert payroll.total_gross_pay == Decimal("0.00")
        assert payroll.total_net_pay == Decimal("0.00")

        crm = await reporting_service.get_crm_leads(session, from_date=future_start, to_date=future_end)
        assert crm.total_leads == 0
        assert crm.conversion_rate == 0.0
