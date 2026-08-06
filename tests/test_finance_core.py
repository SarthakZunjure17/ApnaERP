from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest

from app.db.session import AsyncSessionLocal
from app.models.financial_posting_queue import FinancialPostingQueue
from app.schemas.finance import (
    AccountGroupCreate,
    AccountingDimensionCreate,
    ChartOfAccountCreate,
    CostCenterCreate,
    CurrencyCreate,
    ExchangeRateCreate,
    FiscalYearCreate,
    JournalCreate,
    JournalLineCreate,
    JournalReverseRequest,
    JournalTypeCreate,
    PostingRuleCreate,
    TaxCategoryCreate,
    TaxRateCreate,
)
from app.services.finance_services import (
    ChartOfAccountsService,
    CostCenterService,
    CurrencyService,
    FiscalService,
    JournalService,
    PostingEngineService,
    PostingRuleService,
    TaxService,
)
from app.tasks.finance_tasks import process_financial_posting_queue_task


@pytest.mark.asyncio
async def test_chart_of_accounts_hierarchy_and_balances():
    async with AsyncSessionLocal() as session:
        coa_service = ChartOfAccountsService()

        # 1. Create Account Group
        grp_code = f"GRP_{uuid.uuid4().hex[:6].upper()}"
        grp = await coa_service.create_account_group(
            session, AccountGroupCreate(code=grp_code, name="Current Assets", category="Asset")
        )
        assert grp.id is not None
        assert grp.code == grp_code

        # 2. Create Account
        acc_code1 = f"1010-{uuid.uuid4().hex[:4].upper()}"
        acc1 = await coa_service.create_account(
            session,
            ChartOfAccountCreate(
                account_code=acc_code1,
                name="Main Operating Bank Account",
                account_type="Asset",
                account_group_id=grp.id,
                opening_balance=Decimal("10000.00"),
            ),
        )
        assert acc1.id is not None
        assert acc1.current_balance == Decimal("10000.00")

        # Duplicate account code error check
        with pytest.raises(ValueError, match="already exists"):
            await coa_service.create_account(
                session,
                ChartOfAccountCreate(
                    account_code=acc_code1,
                    name="Duplicate Account",
                    account_type="Asset",
                ),
            )


@pytest.mark.asyncio
async def test_fiscal_calendar_and_period_lock():
    async with AsyncSessionLocal() as session:
        fiscal_service = FiscalService()
        journal_service = JournalService()
        posting_engine = PostingEngineService()
        coa_service = ChartOfAccountsService()

        # Setup Accounts & Journal Type
        jtype = await journal_service.create_journal_type(
            session, JournalTypeCreate(code=f"GEN_{uuid.uuid4().hex[:4]}", name="General Journal", prefix="GJ")
        )
        acc1 = await coa_service.create_account(
            session,
            ChartOfAccountCreate(account_code=f"1100-{uuid.uuid4().hex[:4]}", name="Cash", account_type="Asset"),
        )
        acc2 = await coa_service.create_account(
            session,
            ChartOfAccountCreate(account_code=f"4100-{uuid.uuid4().hex[:4]}", name="Sales", account_type="Income"),
        )

        # 1. Create Fiscal Year
        fy_code = f"FY2026_{uuid.uuid4().hex[:4]}"
        fy = await fiscal_service.create_fiscal_year(
            session,
            FiscalYearCreate(
                code=fy_code,
                name="Fiscal Year 2026",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                status="Open",
            ),
        )
        periods = await fiscal_service.period_repo.get_periods_for_year(session, fy.id)
        assert len(periods) == 12

        # Lock period 1
        p1 = periods[0]
        await fiscal_service.lock_period(session, p1.id, is_locked=True)

        # 2. Attempt to create journal in locked period
        with pytest.raises(ValueError, match="locked fiscal period"):
            await journal_service.create_journal(
                session,
                JournalCreate(
                    journal_type_id=jtype.id,
                    posting_date=p1.start_date,
                    description="Locked period test",
                    lines=[
                        JournalLineCreate(account_id=acc1.id, debit=Decimal("500.00")),
                        JournalLineCreate(account_id=acc2.id, credit=Decimal("500.00")),
                    ],
                ),
            )


@pytest.mark.asyncio
async def test_double_entry_engine_and_journal_posting():
    async with AsyncSessionLocal() as session:
        coa_service = ChartOfAccountsService()
        journal_service = JournalService()
        posting_engine = PostingEngineService()

        # 1. Setup Accounts
        bank_acc = await coa_service.create_account(
            session,
            ChartOfAccountCreate(account_code=f"1020-{uuid.uuid4().hex[:4]}", name="Bank Account", account_type="Asset"),
        )
        rev_acc = await coa_service.create_account(
            session,
            ChartOfAccountCreate(account_code=f"4010-{uuid.uuid4().hex[:4]}", name="Service Revenue", account_type="Income"),
        )

        jtype = await journal_service.create_journal_type(
            session, JournalTypeCreate(code=f"SJ_{uuid.uuid4().hex[:4]}", name="Sales Journal", prefix="SJ")
        )

        # 2. Unbalanced Journal validation error check
        with pytest.raises(ValueError, match="Total Debit"):
            JournalCreate(
                journal_type_id=jtype.id,
                posting_date=date.today(),
                description="Unbalanced",
                lines=[
                    JournalLineCreate(account_id=bank_acc.id, debit=Decimal("1000.00")),
                    JournalLineCreate(account_id=rev_acc.id, credit=Decimal("800.00")),
                ],
            )

        # 3. Create Balanced Journal
        j_in = JournalCreate(
            journal_type_id=jtype.id,
            posting_date=date.today(),
            description="Service Fee Income Receipt",
            lines=[
                JournalLineCreate(account_id=bank_acc.id, debit=Decimal("2500.00")),
                JournalLineCreate(account_id=rev_acc.id, credit=Decimal("2500.00")),
            ],
        )
        journal = await journal_service.create_journal(session, j_in)
        assert journal.status == "Draft"
        assert journal.total_debit == Decimal("2500.00")

        # 4. Post Journal to General Ledger
        posted_journal = await posting_engine.post_journal(session, journal.id)
        assert posted_journal.status == "Posted"
        assert posted_journal.posted_at is not None

        # Verify Account Balances updated
        b_acc = await coa_service.account_repo.get_by_id(session, bank_acc.id)
        r_acc = await coa_service.account_repo.get_by_id(session, rev_acc.id)

        assert b_acc.current_balance == Decimal("2500.00")  # Asset increases with Debit
        assert r_acc.current_balance == Decimal("2500.00")  # Income increases with Credit


@pytest.mark.asyncio
async def test_journal_reversal_immutability():
    async with AsyncSessionLocal() as session:
        coa_service = ChartOfAccountsService()
        journal_service = JournalService()
        posting_engine = PostingEngineService()

        acc_exp = await coa_service.create_account(
            session,
            ChartOfAccountCreate(account_code=f"5010-{uuid.uuid4().hex[:4]}", name="Rent Expense", account_type="Expense"),
        )
        acc_cash = await coa_service.create_account(
            session,
            ChartOfAccountCreate(account_code=f"1005-{uuid.uuid4().hex[:4]}", name="Petty Cash", account_type="Asset"),
        )
        jtype = await journal_service.create_journal_type(
            session, JournalTypeCreate(code=f"EX_{uuid.uuid4().hex[:4]}", name="Expense Journal", prefix="EJ")
        )

        # 1. Post Original Journal
        j_in = JournalCreate(
            journal_type_id=jtype.id,
            posting_date=date.today(),
            description="Office Rent Payment",
            lines=[
                JournalLineCreate(account_id=acc_exp.id, debit=Decimal("1200.00")),
                JournalLineCreate(account_id=acc_cash.id, credit=Decimal("1200.00")),
            ],
        )
        orig_j = await journal_service.create_journal(session, j_in)
        await posting_engine.post_journal(session, orig_j.id)

        # 2. Reverse Journal
        rev_j = await posting_engine.reverse_journal(session, orig_j.id, reversal_reason="Duplicate payment entry")

        # Verify Immutability & Audit Tracking
        orig_db = await journal_service.journal_repo.get_by_id(session, orig_j.id)
        assert orig_db.status == "Reversed"
        assert orig_db.reversed_journal_id == rev_j.id

        assert rev_j.status == "Posted"
        assert rev_j.total_debit == Decimal("1200.00")
        assert rev_j.journal_number.startswith("REV-")

        # Verify Balances restored to initial
        exp_acc = await coa_service.account_repo.get_by_id(session, acc_exp.id)
        cash_acc = await coa_service.account_repo.get_by_id(session, acc_cash.id)
        assert exp_acc.current_balance == Decimal("0.00")
        assert cash_acc.current_balance == Decimal("0.00")


@pytest.mark.asyncio
async def test_posting_rules_and_queue_processing():
    async with AsyncSessionLocal() as session:
        coa_service = ChartOfAccountsService()
        journal_service = JournalService()
        rule_service = PostingRuleService()

        # Setup Accounts & Rule
        payroll_exp = await coa_service.create_account(
            session,
            ChartOfAccountCreate(account_code=f"5100-{uuid.uuid4().hex[:4]}", name="Salaries & Wages", account_type="Expense"),
        )
        payroll_payable = await coa_service.create_account(
            session,
            ChartOfAccountCreate(account_code=f"2100-{uuid.uuid4().hex[:4]}", name="Payroll Payable", account_type="Liability"),
        )
        jtype = await journal_service.create_journal_type(
            session, JournalTypeCreate(code=f"PJ_{uuid.uuid4().hex[:4]}", name="Payroll Journal", prefix="PJ")
        )

        rule_in = PostingRuleCreate(
            event_name="PayrollCompleted",
            rule_code=f"RULE_PAY_{uuid.uuid4().hex[:4]}",
            name="Automated Payroll Posting Rule",
            journal_type_id=jtype.id,
            debit_account_id=payroll_exp.id,
            credit_account_id=payroll_payable.id,
        )
        rule = await rule_service.create_posting_rule(session, rule_in)
        assert rule.id is not None

        # Add payload to FinancialPostingQueue
        ref_id = f"PAY-RUN-{uuid.uuid4().hex[:6]}"
        q_item = FinancialPostingQueue(
            payroll_period_id=None,
            posting_status="Pending",
            payload={
                "event_name": "PayrollCompleted",
                "reference_module": "Payroll",
                "reference_id": ref_id,
                "amount": "15000.00",
                "description": "Monthly Employee Salaries Payroll Run",
            },
        )
        session.add(q_item)
        await session.commit()

        # Process Posting Queue
        res = process_financial_posting_queue_task()
        assert res["status"] == "success"


@pytest.mark.asyncio
async def test_currencies_tax_and_cost_centers():
    async with AsyncSessionLocal() as session:
        curr_service = CurrencyService()
        cc_service = CostCenterService()
        tax_service = TaxService()

        # 1. Currency & Exchange Rate
        usd = await curr_service.create_currency(
            session, CurrencyCreate(code=f"USD_{uuid.uuid4().hex[:2]}", name="US Dollar", symbol="$", is_base=True)
        )
        eur = await curr_service.create_currency(
            session, CurrencyCreate(code=f"EUR_{uuid.uuid4().hex[:2]}", name="Euro", symbol="€")
        )

        rate = await curr_service.set_exchange_rate(
            session,
            ExchangeRateCreate(
                from_currency_code=usd.code,
                to_currency_code=eur.code,
                rate=Decimal("0.920000"),
                effective_date=date.today(),
            ),
        )
        assert rate.rate == Decimal("0.920000")

        converted = await curr_service.convert_amount(session, usd.code, eur.code, Decimal("100.00"))
        assert converted == Decimal("92.00")

        # 2. Cost Center & Dimension
        cc = await cc_service.create_cost_center(
            session, CostCenterCreate(code=f"CC_IT_{uuid.uuid4().hex[:4]}", name="IT Department Cost Center")
        )
        dim = await cc_service.create_dimension(
            session, AccountingDimensionCreate(name=f"Branch_{uuid.uuid4().hex[:4]}", dimension_type="Branch")
        )
        assert cc.id is not None
        assert dim.id is not None

        # 3. Tax Category & Rate
        tax_cat = await tax_service.create_tax_category(
            session, TaxCategoryCreate(code=f"VAT_{uuid.uuid4().hex[:4]}", name="Value Added Tax", tax_type="Output")
        )
        tax_rate = await tax_service.create_tax_rate(
            session,
            TaxRateCreate(
                tax_category_id=tax_cat.id,
                code=f"VAT18_{uuid.uuid4().hex[:4]}",
                name="Standard VAT 18%",
                rate_percentage=Decimal("18.00"),
                effective_from=date(2026, 1, 1),
            ),
        )
        assert tax_rate.rate_percentage == Decimal("18.00")
