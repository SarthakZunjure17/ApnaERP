import datetime
from decimal import Decimal
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.customer import Customer
from app.models.finance import AccountGroup, ChartOfAccount, FiscalPeriod, FiscalYear
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.finance_ops import (
    AssetCategoryCreate,
    BankAccountCreate,
    BankStatementImportCreate,
    BankStatementLineDTO,
    BudgetCreate,
    BudgetLineCreate,
    CustomerInvoiceCreate,
    CustomerInvoiceLineCreate,
    FixedAssetCreate,
    PaymentVoucherCreate,
    ReceiptVoucherCreate,
    SupplierBillCreate,
    SupplierBillLineCreate,
)
from app.services.finance_ops_services import (
    AccountsPayableService,
    AccountsReceivableService,
    AnalyticsService,
    AssetService,
    BankService,
    BudgetService,
    DepreciationService,
    FinancialStatementService,
    PaymentService,
    ReconciliationService,
)


async def helper_setup_test_accounts(session: AsyncSession):
    grp_stmt = select(AccountGroup).where(AccountGroup.code == "AG-TEST-OPS")
    grp_res = await session.execute(grp_stmt)
    grp = grp_res.scalar_one_or_none()

    if not grp:
        grp = AccountGroup(
            code="AG-TEST-OPS",
            name="Test Group Ops",
            category="Asset",
        )
        session.add(grp)
        await session.flush()

    ar_acc = ChartOfAccount(
        account_code=f"1200-{uuid.uuid4().hex[:4]}",
        name="Accounts Receivable",
        account_type="Asset",
        account_group_id=grp.id,
        current_balance=Decimal("0.00"),
    )
    bank_acc = ChartOfAccount(
        account_code=f"1020-{uuid.uuid4().hex[:4]}",
        name="Main Bank Account GL",
        account_type="Asset",
        account_group_id=grp.id,
        current_balance=Decimal("10000.00"),
    )
    asset_acc = ChartOfAccount(
        account_code=f"1500-{uuid.uuid4().hex[:4]}",
        name="Machinery Fixed Asset",
        account_type="Asset",
        account_group_id=grp.id,
        current_balance=Decimal("0.00"),
    )

    ap_acc = ChartOfAccount(
        account_code=f"2100-{uuid.uuid4().hex[:4]}",
        name="Accounts Payable",
        account_type="Liability",
        account_group_id=grp.id,
        current_balance=Decimal("0.00"),
    )
    accum_depr_acc = ChartOfAccount(
        account_code=f"1510-{uuid.uuid4().hex[:4]}",
        name="Accumulated Depreciation",
        account_type="Asset",
        account_group_id=grp.id,
        current_balance=Decimal("0.00"),
    )

    sales_acc = ChartOfAccount(
        account_code=f"4000-{uuid.uuid4().hex[:4]}",
        name="Sales Revenue",
        account_type="Income",
        account_group_id=grp.id,
        current_balance=Decimal("0.00"),
    )

    exp_acc = ChartOfAccount(
        account_code=f"5000-{uuid.uuid4().hex[:4]}",
        name="Operating Expenses",
        account_type="Expense",
        account_group_id=grp.id,
        current_balance=Decimal("0.00"),
    )
    depr_exp_acc = ChartOfAccount(
        account_code=f"5100-{uuid.uuid4().hex[:4]}",
        name="Depreciation Expense",
        account_type="Expense",
        account_group_id=grp.id,
        current_balance=Decimal("0.00"),
    )

    session.add_all([ar_acc, bank_acc, asset_acc, ap_acc, accum_depr_acc, sales_acc, exp_acc, depr_exp_acc])
    await session.flush()

    fy = FiscalYear(
        code=f"FY-{uuid.uuid4().hex[:4]}",
        name="2026",
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 12, 31),
        status="Open",
    )
    session.add(fy)
    await session.flush()

    fp = FiscalPeriod(
        fiscal_year_id=fy.id,
        period_number=1,
        name="Jan-2026",
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 1, 31),
        is_closed=False,
        is_locked=False,
    )
    session.add(fp)
    await session.flush()

    customer = Customer(
        customer_code=f"CUST-OPS-{uuid.uuid4().hex[:4]}",
        name="Acme Corp Ops",
        email=f"acme-{uuid.uuid4().hex[:4]}@example.com",
        phone="555-0199",
    )
    supplier = Supplier(
        code=f"SUPP-OPS-{uuid.uuid4().hex[:4]}",
        name="Global Vendor Ops",
    )
    session.add_all([customer, supplier])
    await session.flush()

    return {
        "ar_acc": ar_acc,
        "bank_acc": bank_acc,
        "asset_acc": asset_acc,
        "ap_acc": ap_acc,
        "accum_depr_acc": accum_depr_acc,
        "sales_acc": sales_acc,
        "exp_acc": exp_acc,
        "depr_exp_acc": depr_exp_acc,
        "customer": customer,
        "supplier": supplier,
        "fiscal_year": fy,
    }


def get_mock_user():
    return User(
        id=uuid.uuid4(),
        email="accountant@apnaerp.com",
        full_name="Chief Accountant",
        is_active=True,
    )


@pytest.mark.asyncio
async def test_accounts_receivable_and_invoice_posting():
    async with AsyncSessionLocal() as session:
        ar_service = AccountsReceivableService(session)
        data = await helper_setup_test_accounts(session)
        mock_user = get_mock_user()

        inv_create = CustomerInvoiceCreate(
            customer_id=data["customer"].id,
            invoice_date=datetime.date(2026, 1, 15),
            due_date=datetime.date(2026, 2, 15),
            lines=[
                CustomerInvoiceLineCreate(
                    account_id=data["sales_acc"].id,
                    description="Consulting Services",
                    quantity=Decimal("10.00"),
                    unit_price=Decimal("150.00"),
                    tax_amount=Decimal("0.00"),
                )
            ],
        )

        invoice = await ar_service.create_invoice(inv_create, mock_user)
        assert invoice.status == "Draft"
        assert invoice.total_amount == Decimal("1500.00")

        posted_invoice = await ar_service.post_invoice(invoice.id, mock_user)
        assert posted_invoice.status == "Posted"
        assert posted_invoice.journal_id is not None

        statement = await ar_service.get_customer_statement(data["customer"].id)
        assert statement.total_outstanding == Decimal("1500.00")
        assert len(statement.entries) == 1


@pytest.mark.asyncio
async def test_accounts_payable_and_bill_posting():
    async with AsyncSessionLocal() as session:
        ap_service = AccountsPayableService(session)
        data = await helper_setup_test_accounts(session)
        mock_user = get_mock_user()

        bill_create = SupplierBillCreate(
            supplier_id=data["supplier"].id,
            vendor_bill_number="VEND-1001",
            bill_date=datetime.date(2026, 1, 10),
            due_date=datetime.date(2026, 2, 10),
            lines=[
                SupplierBillLineCreate(
                    account_id=data["exp_acc"].id,
                    description="Office Rent Expense",
                    quantity=Decimal("1.00"),
                    unit_price=Decimal("2000.00"),
                    tax_amount=Decimal("0.00"),
                )
            ],
        )

        bill = await ap_service.create_bill(bill_create, mock_user)
        assert bill.status == "Draft"
        assert bill.total_amount == Decimal("2000.00")

        posted_bill = await ap_service.post_bill(bill.id, mock_user)
        assert posted_bill.status == "Posted"
        assert posted_bill.journal_id is not None

        statement = await ap_service.get_vendor_statement(data["supplier"].id)
        assert statement.total_outstanding == Decimal("2000.00")


@pytest.mark.asyncio
async def test_payment_and_receipt_vouchers():
    async with AsyncSessionLocal() as session:
        payment_service = PaymentService(session)
        bank_service = BankService(session)
        data = await helper_setup_test_accounts(session)
        mock_user = get_mock_user()

        b_acc = await bank_service.create_bank_account(
            BankAccountCreate(
                account_name="Operating Bank Account",
                account_number=f"ACC-{uuid.uuid4().hex[:6]}",
                bank_name="First National Bank",
                gl_account_id=data["bank_acc"].id,
            )
        )

        rct = await payment_service.create_receipt_voucher(
            ReceiptVoucherCreate(
                customer_id=data["customer"].id,
                payment_mode="Bank",
                bank_account_id=b_acc.id,
                receipt_date=datetime.date(2026, 1, 20),
                amount=Decimal("500.00"),
            ),
            mock_user,
        )
        assert rct.status == "Draft"

        posted_rct = await payment_service.post_receipt_voucher(rct.id, mock_user)
        assert posted_rct.status == "Posted"
        assert b_acc.current_balance == Decimal("500.00")

        pmt = await payment_service.create_payment_voucher(
            PaymentVoucherCreate(
                supplier_id=data["supplier"].id,
                payment_mode="Bank",
                bank_account_id=b_acc.id,
                payment_date=datetime.date(2026, 1, 22),
                amount=Decimal("200.00"),
            ),
            mock_user,
        )

        posted_pmt = await payment_service.post_payment_voucher(pmt.id, mock_user)
        assert posted_pmt.status == "Posted"
        assert b_acc.current_balance == Decimal("300.00")


@pytest.mark.asyncio
async def test_fixed_assets_and_depreciation():
    async with AsyncSessionLocal() as session:
        asset_service = AssetService(session)
        depr_service = DepreciationService(session)
        data = await helper_setup_test_accounts(session)
        mock_user = get_mock_user()

        cat = await asset_service.create_category(
            AssetCategoryCreate(
                code=f"CAT-{uuid.uuid4().hex[:4]}",
                name="Plant & Machinery",
                depreciation_method="StraightLine",
                useful_life_years=5,
                asset_account_id=data["asset_acc"].id,
                accumulated_depreciation_account_id=data["accum_depr_acc"].id,
                depreciation_expense_account_id=data["depr_exp_acc"].id,
            )
        )

        asset = await asset_service.create_asset(
            FixedAssetCreate(
                asset_code=f"AST-{uuid.uuid4().hex[:4]}",
                name="CNC Laser Cutter",
                category_id=cat.id,
                acquisition_date=datetime.date(2026, 1, 1),
                purchase_cost=Decimal("12000.00"),
                salvage_value=Decimal("0.00"),
            ),
            mock_user,
        )
        assert asset.current_book_value == Decimal("12000.00")

        schedules = await depr_service.generate_schedule(asset.id)
        assert len(schedules) == 60
        assert schedules[0].depreciation_amount == Decimal("200.00")

        posted_sched = await depr_service.post_depreciation(schedules[0].id, mock_user)
        assert posted_sched.status == "Posted"
        assert asset.current_book_value == Decimal("11800.00")


@pytest.mark.asyncio
async def test_budget_creation_and_approval():
    async with AsyncSessionLocal() as session:
        budget_service = BudgetService(session)
        data = await helper_setup_test_accounts(session)

        budget = await budget_service.create_budget(
            BudgetCreate(
                code=f"BDG-{uuid.uuid4().hex[:4]}",
                name="Annual OPEX 2026",
                fiscal_year_id=data["fiscal_year"].id,
                lines=[
                    BudgetLineCreate(
                        account_id=data["exp_acc"].id,
                        budgeted_amount=Decimal("50000.00"),
                    )
                ],
            )
        )
        assert budget.status == "Draft"
        assert budget.total_budgeted_amount == Decimal("50000.00")

        approved_budget = await budget_service.approve_budget(budget.id)
        assert approved_budget.status == "Approved"


@pytest.mark.asyncio
async def test_financial_statements_and_analytics():
    async with AsyncSessionLocal() as session:
        stmt_service = FinancialStatementService(session)
        analytics_service = AnalyticsService(session)
        await helper_setup_test_accounts(session)

        tb = await stmt_service.generate_trial_balance(datetime.date.today())
        assert tb["total_debit"] >= 0
        assert tb["total_credit"] >= 0

        bs = await stmt_service.generate_balance_sheet(datetime.date.today())
        assert "total_assets" in bs

        pnl = await stmt_service.generate_profit_and_loss(datetime.date(2026, 1, 1), datetime.date(2026, 12, 31))
        assert "net_profit" in pnl

        analytics = await analytics_service.get_financial_analytics()
        assert "net_margin_percentage" in analytics
