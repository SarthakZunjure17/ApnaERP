import calendar
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.audit_log import AuditLog
from app.models.finance import (
    AccountGroup,
    ChartOfAccount,
    Company,
    FiscalPeriod,
    FiscalYear,
    Journal,
    JournalLine,
    JournalType,
)
from app.models.user import User
from app.schemas.finance import (
    AccountGroupCreate,
    ChartOfAccountCreate,
    ChartOfAccountUpdate,
    CompanyCreate,
    CompanyUpdate,
    FiscalPeriodCreate,
    FiscalYearCreate,
    JournalCreate,
    JournalLineCreate,
    JournalTypeCreate,
    JournalUpdate,
)
from app.services.finance_services import (
    ChartOfAccountsService,
    CompanyService,
    FiscalService,
    GeneralLedgerService,
    JournalService,
    PostingEngineService,
)


@pytest.mark.asyncio
async def test_company_configuration_and_lifecycle():
    """Test Company configuration, defaults, update, and audit logging."""
    async with AsyncSessionLocal() as session:
        company_service = CompanyService()
        test_user_id = uuid.uuid4()

        # 1. Create company
        code = f"CMP_{uuid.uuid4().hex[:6].upper()}"
        company_in = CompanyCreate(
            code=code,
            name="Apna Global Technologies",
            legal_name="Apna Global Technologies Private Limited",
            tax_id="GSTIN99887766A1Z5",
            base_currency_code="INR",
            fiscal_year_start_month=4,
            address_line1="123 Tech Park, Phase 1",
            city="Pune",
            state="Maharashtra",
            postal_code="411057",
            country="India",
            email="finance@apnaglobal.com",
            phone="+91-20-12345678",
            is_active=True,
        )
        company = await company_service.create_company(session, company_in, current_user_id=test_user_id)
        assert company.id is not None
        assert company.code == code
        assert company.base_currency_code == "INR"
        assert company.fiscal_year_start_month == 4

        # Duplicate code rejection
        with pytest.raises(ValueError, match="already exists"):
            await company_service.create_company(session, company_in, current_user_id=test_user_id)

        # 2. Get and list companies
        fetched = await company_service.get_company(session, company.id)
        assert fetched is not None
        assert fetched.name == "Apna Global Technologies"

        companies, total = await company_service.list_companies(session, query="Apna Global")
        assert total >= 1
        assert any(c.code == code for c in companies)

        # 3. Update company
        updated = await company_service.update_company(
            session, company.id, CompanyUpdate(name="Apna Global Tech Ltd"), current_user_id=test_user_id
        )
        assert updated.name == "Apna Global Tech Ltd"

        # Verify audit log
        stmt = select(AuditLog).where(AuditLog.entity_id == str(company.id)).order_by(AuditLog.created_at.desc())
        audit_res = await session.execute(stmt)
        audits = audit_res.scalars().all()
        assert len(audits) >= 2  # CREATE and UPDATE
        assert any(a.action == "CREATE" for a in audits)
        assert any(a.action == "UPDATE" for a in audits)


@pytest.mark.asyncio
async def test_chart_of_accounts_hierarchy_and_circular_prevention():
    """Test Chart of Accounts CRUD, hierarchy, active flag, and circular parent prevention."""
    async with AsyncSessionLocal() as session:
        coa_service = ChartOfAccountsService()
        test_user_id = uuid.uuid4()

        # 1. Create root asset account
        root_acc = await coa_service.create_account(
            session,
            ChartOfAccountCreate(
                account_code=f"1000-{uuid.uuid4().hex[:4]}",
                name="Current Assets Root",
                account_type="Asset",
                opening_balance=Decimal("0.00"),
            ),
            current_user_id=test_user_id,
        )

        # 2. Create child bank account
        child_acc = await coa_service.create_account(
            session,
            ChartOfAccountCreate(
                account_code=f"1010-{uuid.uuid4().hex[:4]}",
                name="HDFC Bank Operating",
                account_type="Asset",
                parent_id=root_acc.id,
                opening_balance=Decimal("50000.00"),
            ),
            current_user_id=test_user_id,
        )

        # 3. Create sub-child account
        sub_child_acc = await coa_service.create_account(
            session,
            ChartOfAccountCreate(
                account_code=f"1011-{uuid.uuid4().hex[:4]}",
                name="HDFC Petty Cash Sub",
                account_type="Asset",
                parent_id=child_acc.id,
                opening_balance=Decimal("2000.00"),
            ),
            current_user_id=test_user_id,
        )

        # 4. Circular hierarchy validation: Account cannot be its own parent
        with pytest.raises(ValueError, match="account cannot be its own parent"):
            await coa_service.update_account(
                session,
                root_acc.id,
                ChartOfAccountUpdate(parent_id=root_acc.id),
                current_user_id=test_user_id,
            )

        # 5. Circular hierarchy validation: Root cannot set descendant as parent
        with pytest.raises(ValueError, match="cannot set a descendant as parent"):
            await coa_service.update_account(
                session,
                root_acc.id,
                ChartOfAccountUpdate(parent_id=sub_child_acc.id),
                current_user_id=test_user_id,
            )

        # 6. Non-circular update succeeds
        updated_child = await coa_service.update_account(
            session,
            child_acc.id,
            ChartOfAccountUpdate(name="HDFC Bank Operating Main"),
            current_user_id=test_user_id,
        )
        assert updated_child.name == "HDFC Bank Operating Main"


@pytest.mark.asyncio
async def test_fiscal_calendar_period_and_year_closing():
    """Test Fiscal year, period date validations, overlap checks, locking and closing."""
    async with AsyncSessionLocal() as session:
        fiscal_service = FiscalService()
        test_user_id = uuid.uuid4()

        fy_code = f"FY2027_{uuid.uuid4().hex[:4]}"
        fy = await fiscal_service.create_fiscal_year(
            session,
            FiscalYearCreate(
                code=fy_code,
                name="Fiscal Year 2027-2028",
                start_date=date(2027, 4, 1),
                end_date=date(2028, 3, 31),
            ),
            current_user_id=test_user_id,
        )
        assert fy.id is not None

        # Verify automatic period generation (12 periods)
        periods = await fiscal_service.period_repo.get_periods_for_year(session, fy.id)
        assert len(periods) == 12

        # Overlapping period validation check
        with pytest.raises(ValueError, match="overlap"):
            await fiscal_service.create_fiscal_period(
                session,
                FiscalPeriodCreate(
                    fiscal_year_id=fy.id,
                    period_number=13,
                    name="Overlapping Period",
                    start_date=date(2027, 4, 15),
                    end_date=date(2027, 5, 15),
                ),
                current_user_id=test_user_id,
            )

        # Close period
        p1 = periods[0]
        closed_p1 = await fiscal_service.close_period(session, p1.id, current_user_id=test_user_id)
        assert closed_p1.is_closed is True
        assert closed_p1.is_locked is True

        # Unlocking closed period is disallowed directly
        with pytest.raises(ValueError, match="Closed fiscal periods cannot be unlocked"):
            await fiscal_service.lock_period(session, p1.id, is_locked=False, current_user_id=test_user_id)

        # Close fiscal year
        closed_fy = await fiscal_service.close_fiscal_year(session, fy.id, current_user_id=test_user_id)
        assert closed_fy.status == "Closed"

        all_periods = await fiscal_service.period_repo.get_periods_for_year(session, fy.id)
        assert all(p.is_closed and p.is_locked for p in all_periods)


@pytest.mark.asyncio
async def test_journal_validation_rules():
    """Test all journal validation rules: line counts, unbalanced debits/credits, inactive accounts, negative values."""
    async with AsyncSessionLocal() as session:
        coa_service = ChartOfAccountsService()
        journal_service = JournalService()

        jtype = await journal_service.create_journal_type(
            session,
            JournalTypeCreate(code=f"JV_{uuid.uuid4().hex[:4]}", name="General Journal", prefix="JV"),
        )
        acc_dr = await coa_service.create_account(
            session,
            ChartOfAccountCreate(account_code=f"1030-{uuid.uuid4().hex[:4]}", name="Bank Account DR", account_type="Asset"),
        )
        acc_cr = await coa_service.create_account(
            session,
            ChartOfAccountCreate(account_code=f"4020-{uuid.uuid4().hex[:4]}", name="Sales Account CR", account_type="Income"),
        )
        acc_inactive = await coa_service.create_account(
            session,
            ChartOfAccountCreate(
                account_code=f"5020-{uuid.uuid4().hex[:4]}",
                name="Inactive Expense",
                account_type="Expense",
                is_active=False,
            ),
        )

        today = date(2035, 5, 1)

        # 1. Less than two lines
        with pytest.raises((ValueError, Exception), match="(?i)at least 2 line items|at least two lines"):
            await journal_service.create_journal(
                session,
                JournalCreate(
                    journal_type_id=jtype.id,
                    posting_date=today,
                    description="Single line test",
                    lines=[JournalLineCreate(account_id=acc_dr.id, debit=Decimal("100.00"), credit=Decimal("0.00"))],
                ),
            )

        # 2. Unbalanced debit and credit
        with pytest.raises((ValueError, Exception), match="(?i)must equal total credit"):
            await journal_service.create_journal(
                session,
                JournalCreate(
                    journal_type_id=jtype.id,
                    posting_date=today,
                    description="Unbalanced test",
                    lines=[
                        JournalLineCreate(account_id=acc_dr.id, debit=Decimal("100.00"), credit=Decimal("0.00")),
                        JournalLineCreate(account_id=acc_cr.id, debit=Decimal("0.00"), credit=Decimal("90.00")),
                    ],
                ),
            )

        # 3. Line with both debit and credit
        with pytest.raises((ValueError, Exception), match="(?i)cannot have both debit and credit"):
            await journal_service.create_journal(
                session,
                JournalCreate(
                    journal_type_id=jtype.id,
                    posting_date=today,
                    description="Both Dr and Cr test",
                    lines=[
                        JournalLineCreate(account_id=acc_dr.id, debit=Decimal("100.00"), credit=Decimal("50.00")),
                        JournalLineCreate(account_id=acc_cr.id, debit=Decimal("0.00"), credit=Decimal("50.00")),
                    ],
                ),
            )

        # 4. Inactive account
        with pytest.raises((ValueError, Exception), match="(?i)inactive and cannot be used"):
            await journal_service.create_journal(
                session,
                JournalCreate(
                    journal_type_id=jtype.id,
                    posting_date=today,
                    description="Inactive account test",
                    lines=[
                        JournalLineCreate(account_id=acc_inactive.id, debit=Decimal("100.00"), credit=Decimal("0.00")),
                        JournalLineCreate(account_id=acc_cr.id, debit=Decimal("0.00"), credit=Decimal("100.00")),
                    ],
                ),
            )


@pytest.mark.asyncio
async def test_journal_posting_immutability_and_reversal():
    """Test transactional posting, balance math, immutability of posted journals, deletion block, and reversal."""
    async with AsyncSessionLocal() as session:
        coa_service = ChartOfAccountsService()
        journal_service = JournalService()
        posting_engine = PostingEngineService()
        fiscal_service = FiscalService()
        test_user_id = uuid.uuid4()

        # 1. Setup Open Fiscal Year & Period for 2029
        fy = await fiscal_service.create_fiscal_year(
            session,
            FiscalYearCreate(
                code=f"FY2029_{uuid.uuid4().hex[:4]}",
                name="2029",
                start_date=date(2029, 1, 1),
                end_date=date(2029, 12, 31),
            ),
        )

        # 2. Setup Accounts (Asset & Revenue)
        cash_acc = await coa_service.create_account(
            session,
            ChartOfAccountCreate(
                account_code=f"1050-{uuid.uuid4().hex[:4]}",
                name="Petty Cash",
                account_type="Asset",
                opening_balance=Decimal("1000.00"),
            ),
        )
        sales_acc = await coa_service.create_account(
            session,
            ChartOfAccountCreate(
                account_code=f"4050-{uuid.uuid4().hex[:4]}",
                name="Consulting Revenue",
                account_type="Revenue",
                opening_balance=Decimal("0.00"),
            ),
        )

        jtype = await journal_service.create_journal_type(
            session,
            JournalTypeCreate(code=f"JV_{uuid.uuid4().hex[:4]}", name="Sales Journal", prefix="SJ"),
        )

        # 3. Create Draft Journal
        post_dt = date(2029, 2, 15)
        journal = await journal_service.create_journal(
            session,
            JournalCreate(
                journal_type_id=jtype.id,
                posting_date=post_dt,
                description="Consulting fee received",
                reference_module="Sales",
                reference_id="INV-2029-001",
                lines=[
                    JournalLineCreate(account_id=cash_acc.id, debit=Decimal("5000.00"), credit=Decimal("0.00")),
                    JournalLineCreate(account_id=sales_acc.id, debit=Decimal("0.00"), credit=Decimal("5000.00")),
                ],
            ),
            current_user_id=test_user_id,
        )
        assert journal.status == "Draft"
        assert journal.total_debit == Decimal("5000.00")
        assert journal.total_credit == Decimal("5000.00")

        # 4. Draft Journal can be updated
        updated_journal = await journal_service.update_journal(
            session,
            journal.id,
            JournalUpdate(description="Consulting fee received - updated description"),
            current_user_id=test_user_id,
        )
        assert updated_journal.description == "Consulting fee received - updated description"

        # 5. Post Journal
        posted_journal = await posting_engine.post_journal(session, journal.id, current_user_id=test_user_id)
        assert posted_journal.status == "Posted"
        assert posted_journal.posted_at is not None

        # Verify Account Balances:
        # Asset: 1000 + 5000 = 6000
        # Revenue: 0 + 5000 = 5000
        cash_refreshed = await coa_service.account_repo.get_by_id(session, cash_acc.id)
        sales_refreshed = await coa_service.account_repo.get_by_id(session, sales_acc.id)
        assert cash_refreshed.current_balance == Decimal("6000.00")
        assert sales_refreshed.current_balance == Decimal("5000.00")

        # 6. IMMUTABILITY: Posted journal cannot be updated
        with pytest.raises(ValueError, match="Cannot update journal in 'Posted' status"):
            await journal_service.update_journal(
                session,
                journal.id,
                JournalUpdate(description="Illegal edit on posted journal"),
                current_user_id=test_user_id,
            )

        # 7. IMMUTABILITY: Posted journal cannot be deleted
        with pytest.raises(ValueError, match="Posted journals cannot be deleted"):
            await journal_service.delete_journal(session, journal.id, current_user_id=test_user_id)

        # 8. IMMUTABILITY: Posted journal cannot be cancelled
        with pytest.raises(ValueError, match="Posted journals cannot be cancelled"):
            await journal_service.cancel_journal(session, journal.id, current_user_id=test_user_id)

        # 9. Account with posted transactions cannot be deleted
        with pytest.raises(ValueError, match="Cannot delete account with posted transactions"):
            await coa_service.delete_account(session, cash_acc.id, current_user_id=test_user_id)

        # 10. Reversal
        rev_journal = await posting_engine.reverse_journal(
            session, journal.id, reversal_reason="Client billing dispute refund", current_user_id=test_user_id
        )
        assert rev_journal.status == "Posted"
        assert rev_journal.journal_number.startswith("REV-")

        # Verify Original Journal marked Reversed
        orig_journal = await journal_service.journal_repo.get_by_id(session, journal.id)
        assert orig_journal.status == "Reversed"

        # Verify Balances restored to initial opening balances
        cash_rev = await coa_service.account_repo.get_by_id(session, cash_acc.id)
        sales_rev = await coa_service.account_repo.get_by_id(session, sales_acc.id)
        assert cash_rev.current_balance == Decimal("1000.00")
        assert sales_rev.current_balance == Decimal("0.00")


@pytest.mark.asyncio
async def test_general_ledger_and_trial_balance():
    """Test General Ledger extraction, Account Ledger running balances, and balanced Trial Balance."""
    async with AsyncSessionLocal() as session:
        coa_service = ChartOfAccountsService()
        journal_service = JournalService()
        posting_engine = PostingEngineService()
        gl_service = GeneralLedgerService()
        fiscal_service = FiscalService()

        # 1. Setup Fiscal Year 2030
        await fiscal_service.create_fiscal_year(
            session,
            FiscalYearCreate(
                code=f"FY2030_{uuid.uuid4().hex[:4]}",
                name="2030",
                start_date=date(2030, 1, 1),
                end_date=date(2030, 12, 31),
            ),
        )

        jtype = await journal_service.create_journal_type(
            session,
            JournalTypeCreate(code=f"GEN_{uuid.uuid4().hex[:4]}", name="GL Journal", prefix="GL"),
        )

        # Setup 4 distinct accounts: Asset, Liability, Equity, Expense
        acc_bank = await coa_service.create_account(
            session,
            ChartOfAccountCreate(
                account_code=f"1090-{uuid.uuid4().hex[:4]}",
                name="Checking Account",
                account_type="Asset",
                opening_balance=Decimal("20000.00"),
            ),
        )
        acc_loan = await coa_service.create_account(
            session,
            ChartOfAccountCreate(
                account_code=f"2090-{uuid.uuid4().hex[:4]}",
                name="Bank Loan Payable",
                account_type="Liability",
                opening_balance=Decimal("15000.00"),
            ),
        )
        acc_equity = await coa_service.create_account(
            session,
            ChartOfAccountCreate(
                account_code=f"3090-{uuid.uuid4().hex[:4]}",
                name="Owner Equity",
                account_type="Equity",
                opening_balance=Decimal("5000.00"),
            ),
        )
        acc_rent = await coa_service.create_account(
            session,
            ChartOfAccountCreate(
                account_code=f"5090-{uuid.uuid4().hex[:4]}",
                name="Office Rent Expense",
                account_type="Expense",
                opening_balance=Decimal("0.00"),
            ),
        )

        # Post Journal 1: Pay Rent $2,000 from Bank
        j1 = await journal_service.create_journal(
            session,
            JournalCreate(
                journal_type_id=jtype.id,
                posting_date=date(2030, 1, 10),
                description="Jan 2030 Office Rent Payment",
                reference_module="Procurement",
                reference_id="RENT-JAN-2030",
                lines=[
                    JournalLineCreate(account_id=acc_rent.id, debit=Decimal("2000.00"), credit=Decimal("0.00")),
                    JournalLineCreate(account_id=acc_bank.id, debit=Decimal("0.00"), credit=Decimal("2000.00")),
                ],
            ),
        )
        await posting_engine.post_journal(session, j1.id)

        # Post Journal 2: Repay Loan $3,000 from Bank
        j2 = await journal_service.create_journal(
            session,
            JournalCreate(
                journal_type_id=jtype.id,
                posting_date=date(2030, 1, 20),
                description="Principal Loan Repayment",
                reference_module="Finance",
                reference_id="LOAN-REPAY-01",
                lines=[
                    JournalLineCreate(account_id=acc_loan.id, debit=Decimal("3000.00"), credit=Decimal("0.00")),
                    JournalLineCreate(account_id=acc_bank.id, debit=Decimal("0.00"), credit=Decimal("3000.00")),
                ],
            ),
        )
        await posting_engine.post_journal(session, j2.id)

        # 2. Query Specific Account Ledger for Bank Account
        bank_ledger = await gl_service.get_account_ledger(
            session,
            account_id=acc_bank.id,
            from_date=date(2030, 1, 1),
            to_date=date(2030, 1, 31),
        )
        assert bank_ledger["account_id"] == acc_bank.id
        assert bank_ledger["opening_balance"] == Decimal("20000.00")
        assert bank_ledger["period_credit"] == Decimal("5000.00")
        assert bank_ledger["closing_balance"] == Decimal("15000.00")
        assert len(bank_ledger["entries"]) == 2

        # 3. Query All Transactions Ledger
        all_txs, total_count = await gl_service.get_all_transactions(
            session,
            from_date=date(2030, 1, 1),
            to_date=date(2030, 1, 31),
        )
        assert total_count >= 4  # 4 lines total across 2 journals

        # 4. Query Trial Balance Report
        tb = await gl_service.get_trial_balance(session, as_of_date=date(2030, 1, 31))
        assert tb["is_balanced"] is True
        assert tb["total_debit"] == tb["total_credit"]
        assert tb["total_debit"] > Decimal("0.00")

        # Verify each account line is present
        tb_account_ids = [line["account_id"] for line in tb["lines"]]
        assert acc_bank.id in tb_account_ids
        assert acc_loan.id in tb_account_ids
        assert acc_equity.id in tb_account_ids
        assert acc_rent.id in tb_account_ids
