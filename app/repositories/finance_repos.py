from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.finance import (
    AccountGroup,
    AccountingDimension,
    AccountingEvent,
    ChartOfAccount,
    Company,
    CostCenter,
    Currency,
    ExchangeRate,
    FiscalPeriod,
    FiscalYear,
    Journal,
    JournalLine,
    JournalType,
    PostingRule,
    TaxCategory,
    TaxRate,
)
from app.repositories.base_repository import BaseRepository


class AccountGroupRepository(BaseRepository[AccountGroup, Any, Any]):
    def __init__(self):
        super().__init__(AccountGroup)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[AccountGroup]:
        stmt = select(AccountGroup).where(AccountGroup.code == code).options(selectinload(AccountGroup.children))
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_hierarchy(self, db: AsyncSession) -> List[AccountGroup]:
        stmt = select(AccountGroup).where(AccountGroup.parent_id == None).options(
            selectinload(AccountGroup.children)
        ).order_by(AccountGroup.display_order.asc())
        res = await db.execute(stmt)
        return list(res.scalars().all())


class ChartOfAccountRepository(BaseRepository[ChartOfAccount, Any, Any]):
    def __init__(self):
        super().__init__(ChartOfAccount)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[ChartOfAccount]:
        stmt = select(ChartOfAccount).where(
            and_(ChartOfAccount.account_code == code, ChartOfAccount.is_deleted == False)
        ).options(selectinload(ChartOfAccount.account_group))
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_ancestor_ids(self, db: AsyncSession, account_id: uuid.UUID) -> List[uuid.UUID]:
        """Traverse ancestor hierarchy to detect cycles."""
        ancestors: List[uuid.UUID] = []
        current_id: Optional[uuid.UUID] = account_id
        visited = set()
        while current_id and current_id not in visited:
            visited.add(current_id)
            stmt = select(ChartOfAccount.parent_id).where(ChartOfAccount.id == current_id)
            res = await db.execute(stmt)
            parent_id = res.scalar()
            if parent_id:
                ancestors.append(parent_id)
                current_id = parent_id
            else:
                break
        return ancestors

    async def get_descendant_ids(self, db: AsyncSession, account_id: uuid.UUID) -> List[uuid.UUID]:
        """Traverse descendant hierarchy to detect cycles."""
        descendants: List[uuid.UUID] = []
        queue = [account_id]
        visited = {account_id}
        while queue:
            curr = queue.pop(0)
            stmt = select(ChartOfAccount.id).where(
                and_(ChartOfAccount.parent_id == curr, ChartOfAccount.is_deleted == False)
            )
            res = await db.execute(stmt)
            children = res.scalars().all()
            for ch in children:
                if ch not in visited:
                    visited.add(ch)
                    descendants.append(ch)
                    queue.append(ch)
        return descendants

    async def has_posted_transactions(self, db: AsyncSession, account_id: uuid.UUID) -> bool:
        stmt = (
            select(func.count(JournalLine.id))
            .join(Journal, Journal.id == JournalLine.journal_id)
            .where(and_(JournalLine.account_id == account_id, Journal.status == "Posted", Journal.is_deleted == False))
        )
        count = (await db.execute(stmt)).scalar() or 0
        return count > 0

    async def search_accounts(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        account_type: Optional[str] = None,
        group_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ChartOfAccount], int]:
        filters = [ChartOfAccount.is_deleted == False]
        if account_type:
            filters.append(ChartOfAccount.account_type.ilike(account_type))
        if group_id:
            filters.append(ChartOfAccount.account_group_id == group_id)
        if is_active is not None:
            filters.append(ChartOfAccount.is_active == is_active)
        if query:
            q = f"%{query}%"
            filters.append(or_(ChartOfAccount.name.ilike(q), ChartOfAccount.account_code.ilike(q)))

        count_stmt = select(func.count(ChartOfAccount.id)).where(and_(*filters))
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = select(ChartOfAccount).where(and_(*filters)).options(
            selectinload(ChartOfAccount.account_group)
        ).order_by(ChartOfAccount.account_code.asc()).offset(skip).limit(limit)

        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class FiscalYearRepository(BaseRepository[FiscalYear, Any, Any]):
    def __init__(self):
        super().__init__(FiscalYear)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[FiscalYear]:
        stmt = select(FiscalYear).where(FiscalYear.code == code).options(selectinload(FiscalYear.periods))
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_active_year_for_date(self, db: AsyncSession, dt: date) -> Optional[FiscalYear]:
        stmt = select(FiscalYear).where(
            and_(FiscalYear.start_date <= dt, FiscalYear.end_date >= dt, FiscalYear.status == "Open")
        ).options(selectinload(FiscalYear.periods))
        res = await db.execute(stmt)
        return res.scalars().first()


class FiscalPeriodRepository(BaseRepository[FiscalPeriod, Any, Any]):
    def __init__(self):
        super().__init__(FiscalPeriod)

    async def get_period_for_date(self, db: AsyncSession, dt: date) -> Optional[FiscalPeriod]:
        stmt = (
            select(FiscalPeriod)
            .join(FiscalYear, FiscalYear.id == FiscalPeriod.fiscal_year_id)
            .where(and_(FiscalPeriod.start_date <= dt, FiscalPeriod.end_date >= dt))
            .options(selectinload(FiscalPeriod.fiscal_year))
            .order_by(FiscalPeriod.created_at.desc())
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_periods_for_year(self, db: AsyncSession, fiscal_year_id: uuid.UUID) -> List[FiscalPeriod]:
        stmt = select(FiscalPeriod).where(FiscalPeriod.fiscal_year_id == fiscal_year_id).order_by(FiscalPeriod.period_number.asc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def check_overlap(
        self,
        db: AsyncSession,
        fiscal_year_id: uuid.UUID,
        start_date: date,
        end_date: date,
        exclude_period_id: Optional[uuid.UUID] = None,
    ) -> bool:
        filters = [
            FiscalPeriod.fiscal_year_id == fiscal_year_id,
            FiscalPeriod.start_date <= end_date,
            FiscalPeriod.end_date >= start_date,
        ]
        if exclude_period_id:
            filters.append(FiscalPeriod.id != exclude_period_id)
        stmt = select(func.count(FiscalPeriod.id)).where(and_(*filters))
        count = (await db.execute(stmt)).scalar() or 0
        return count > 0


class CurrencyRepository(BaseRepository[Currency, Any, Any]):
    def __init__(self):
        super().__init__(Currency)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[Currency]:
        stmt = select(Currency).where(Currency.code == code)
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_base_currency(self, db: AsyncSession) -> Optional[Currency]:
        stmt = select(Currency).where(Currency.is_base == True)
        res = await db.execute(stmt)
        return res.scalars().first()


class ExchangeRateRepository(BaseRepository[ExchangeRate, Any, Any]):
    def __init__(self):
        super().__init__(ExchangeRate)

    async def get_latest_rate(
        self, db: AsyncSession, from_currency: str, to_currency: str, dt: Optional[date] = None
    ) -> Optional[ExchangeRate]:
        if from_currency == to_currency:
            return ExchangeRate(
                from_currency_code=from_currency,
                to_currency_code=to_currency,
                rate=Decimal("1.000000"),
                effective_date=dt or date.today(),
            )
        stmt = select(ExchangeRate).where(
            and_(
                ExchangeRate.from_currency_code == from_currency,
                ExchangeRate.to_currency_code == to_currency,
                ExchangeRate.is_active == True,
            )
        )
        if dt:
            stmt = stmt.where(ExchangeRate.effective_date <= dt)
        stmt = stmt.order_by(ExchangeRate.effective_date.desc())
        res = await db.execute(stmt)
        return res.scalars().first()


class CostCenterRepository(BaseRepository[CostCenter, Any, Any]):
    def __init__(self):
        super().__init__(CostCenter)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[CostCenter]:
        stmt = select(CostCenter).where(CostCenter.code == code).options(selectinload(CostCenter.children))
        res = await db.execute(stmt)
        return res.scalars().first()


class AccountingDimensionRepository(BaseRepository[AccountingDimension, Any, Any]):
    def __init__(self):
        super().__init__(AccountingDimension)

    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[AccountingDimension]:
        stmt = select(AccountingDimension).where(AccountingDimension.name == name)
        res = await db.execute(stmt)
        return res.scalars().first()


class JournalTypeRepository(BaseRepository[JournalType, Any, Any]):
    def __init__(self):
        super().__init__(JournalType)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[JournalType]:
        stmt = select(JournalType).where(JournalType.code == code)
        res = await db.execute(stmt)
        return res.scalars().first()


class JournalRepository(BaseRepository[Journal, Any, Any]):
    def __init__(self):
        super().__init__(Journal)

    async def get_by_number(self, db: AsyncSession, number: str) -> Optional[Journal]:
        stmt = select(Journal).where(and_(Journal.journal_number == number, Journal.is_deleted == False)).options(
            selectinload(Journal.lines).selectinload(JournalLine.account),
            selectinload(Journal.journal_type),
            selectinload(Journal.fiscal_period),
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_by_id_with_details(self, db: AsyncSession, id: uuid.UUID) -> Optional[Journal]:
        stmt = select(Journal).where(and_(Journal.id == id, Journal.is_deleted == False)).options(
            selectinload(Journal.lines).selectinload(JournalLine.account),
            selectinload(Journal.journal_type),
            selectinload(Journal.fiscal_period),
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    async def search_journals(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        journal_type_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Journal], int]:
        filters = [Journal.is_deleted == False]
        if journal_type_id:
            filters.append(Journal.journal_type_id == journal_type_id)
        if status:
            filters.append(Journal.status == status)
        if from_date:
            filters.append(Journal.posting_date >= from_date)
        if to_date:
            filters.append(Journal.posting_date <= to_date)
        if query:
            q = f"%{query}%"
            filters.append(or_(Journal.journal_number.ilike(q), Journal.description.ilike(q), Journal.reference_id.ilike(q)))

        count_stmt = select(func.count(Journal.id)).where(and_(*filters))
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = select(Journal).where(and_(*filters)).options(
            selectinload(Journal.lines).selectinload(JournalLine.account),
            selectinload(Journal.journal_type),
        ).order_by(Journal.posting_date.desc(), Journal.created_at.desc()).offset(skip).limit(limit)

        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class JournalLineRepository(BaseRepository[JournalLine, Any, Any]):
    def __init__(self):
        super().__init__(JournalLine)


class TaxCategoryRepository(BaseRepository[TaxCategory, Any, Any]):
    def __init__(self):
        super().__init__(TaxCategory)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[TaxCategory]:
        stmt = select(TaxCategory).where(TaxCategory.code == code).options(selectinload(TaxCategory.rates))
        res = await db.execute(stmt)
        return res.scalars().first()


class TaxRateRepository(BaseRepository[TaxRate, Any, Any]):
    def __init__(self):
        super().__init__(TaxRate)

    async def get_effective_rate(self, db: AsyncSession, category_id: uuid.UUID, dt: date) -> Optional[TaxRate]:
        stmt = select(TaxRate).where(
            and_(
                TaxRate.tax_category_id == category_id,
                TaxRate.is_active == True,
                TaxRate.effective_from <= dt,
                or_(TaxRate.effective_to == None, TaxRate.effective_to >= dt),
            )
        ).order_by(TaxRate.effective_from.desc())
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[TaxRate]:
        stmt = select(TaxRate).where(TaxRate.code == code)
        res = await db.execute(stmt)
        return res.scalars().first()



class PostingRuleRepository(BaseRepository[PostingRule, Any, Any]):
    def __init__(self):
        super().__init__(PostingRule)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[PostingRule]:
        stmt = select(PostingRule).where(PostingRule.rule_code == code).options(
            selectinload(PostingRule.debit_account),
            selectinload(PostingRule.credit_account),
            selectinload(PostingRule.journal_type),
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_by_event(self, db: AsyncSession, event_name: str) -> List[PostingRule]:
        stmt = select(PostingRule).where(
            and_(PostingRule.event_name == event_name, PostingRule.is_active == True)
        ).options(
            selectinload(PostingRule.debit_account),
            selectinload(PostingRule.credit_account),
            selectinload(PostingRule.journal_type),
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


class AccountingEventRepository(BaseRepository[AccountingEvent, Any, Any]):
    def __init__(self):
        super().__init__(AccountingEvent)


class CompanyRepository(BaseRepository[Company, Any, Any]):
    def __init__(self):
        super().__init__(Company)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[Company]:
        stmt = select(Company).where(and_(Company.code == code, Company.is_deleted == False))
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_default_company(self, db: AsyncSession) -> Optional[Company]:
        stmt = select(Company).where(and_(Company.is_active == True, Company.is_deleted == False)).order_by(Company.created_at.asc())
        res = await db.execute(stmt)
        return res.scalars().first()

    async def search_companies(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Company], int]:
        filters = [Company.is_deleted == False]
        if is_active is not None:
            filters.append(Company.is_active == is_active)
        if query:
            q = f"%{query}%"
            filters.append(or_(Company.name.ilike(q), Company.code.ilike(q), Company.legal_name.ilike(q)))

        count_stmt = select(func.count(Company.id)).where(and_(*filters))
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = select(Company).where(and_(*filters)).order_by(Company.code.asc()).offset(skip).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class GeneralLedgerRepository:
    """
    Read-only General Ledger & Trial Balance Repository.
    Executes database-safe, Decimal-precision financial queries across posted double-entry journals.
    """
    async def get_account_ledger(
        self,
        db: AsyncSession,
        account_id: uuid.UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        acc_stmt = select(ChartOfAccount).where(and_(ChartOfAccount.id == account_id, ChartOfAccount.is_deleted == False))
        res = await db.execute(acc_stmt)
        account = res.scalars().first()
        if not account:
            return {}

        opening_balance = Decimal(str(account.opening_balance or "0.00"))
        if from_date:
            prior_stmt = (
                select(
                    func.coalesce(func.sum(JournalLine.debit), Decimal("0.00")),
                    func.coalesce(func.sum(JournalLine.credit), Decimal("0.00")),
                )
                .join(Journal, Journal.id == JournalLine.journal_id)
                .where(
                    and_(
                        JournalLine.account_id == account_id,
                        Journal.status == "Posted",
                        Journal.is_deleted == False,
                        Journal.posting_date < from_date,
                    )
                )
            )
            prior_res = await db.execute(prior_stmt)
            prior_debit, prior_credit = prior_res.first() or (Decimal("0.00"), Decimal("0.00"))
            if account.account_type.upper() in ("ASSET", "EXPENSE"):
                opening_balance += prior_debit - prior_credit
            else:
                opening_balance += prior_credit - prior_debit

        entry_filters = [
            JournalLine.account_id == account_id,
            Journal.status == "Posted",
            Journal.is_deleted == False,
        ]
        if from_date:
            entry_filters.append(Journal.posting_date >= from_date)
        if to_date:
            entry_filters.append(Journal.posting_date <= to_date)

        count_stmt = (
            select(func.count(JournalLine.id))
            .join(Journal, Journal.id == JournalLine.journal_id)
            .where(and_(*entry_filters))
        )
        total_count = (await db.execute(count_stmt)).scalar() or 0

        entries_stmt = (
            select(JournalLine, Journal)
            .join(Journal, Journal.id == JournalLine.journal_id)
            .where(and_(*entry_filters))
            .order_by(Journal.posting_date.asc(), Journal.created_at.asc(), JournalLine.line_number.asc())
            .offset(skip)
            .limit(limit)
        )
        entries_res = await db.execute(entries_stmt)
        raw_rows = entries_res.all()

        running = opening_balance
        entries_data = []
        period_debit = Decimal("0.00")
        period_credit = Decimal("0.00")

        for line, journal in raw_rows:
            d = line.debit
            c = line.credit
            period_debit += d
            period_credit += c
            if account.account_type.upper() in ("ASSET", "EXPENSE"):
                running += d - c
            else:
                running += c - d

            entries_data.append(
                {
                    "id": line.id,
                    "journal_id": journal.id,
                    "journal_number": journal.journal_number,
                    "posting_date": journal.posting_date,
                    "line_number": line.line_number,
                    "account_id": account.id,
                    "account_code": account.account_code,
                    "account_name": account.name,
                    "account_type": account.account_type,
                    "debit": d,
                    "credit": c,
                    "running_balance": running,
                    "description": line.description or journal.description,
                    "reference_module": journal.reference_module,
                    "reference_id": journal.reference_id,
                    "cost_center_id": line.cost_center_id,
                    "created_at": line.created_at,
                }
            )

        closing_balance = running

        return {
            "account_id": account.id,
            "account_code": account.account_code,
            "account_name": account.name,
            "account_type": account.account_type,
            "currency_code": account.currency_code,
            "opening_balance": opening_balance,
            "period_debit": period_debit,
            "period_credit": period_credit,
            "closing_balance": closing_balance,
            "from_date": from_date,
            "to_date": to_date,
            "entries": entries_data,
            "total_entries": total_count,
        }

    async def get_all_transactions(
        self,
        db: AsyncSession,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        account_id: Optional[uuid.UUID] = None,
        account_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Dict[str, Any]], int]:
        filters = [Journal.status == "Posted", Journal.is_deleted == False]
        if from_date:
            filters.append(Journal.posting_date >= from_date)
        if to_date:
            filters.append(Journal.posting_date <= to_date)
        if account_id:
            filters.append(JournalLine.account_id == account_id)
        if account_type:
            filters.append(ChartOfAccount.account_type.ilike(account_type))

        count_stmt = (
            select(func.count(JournalLine.id))
            .join(Journal, Journal.id == JournalLine.journal_id)
            .join(ChartOfAccount, ChartOfAccount.id == JournalLine.account_id)
            .where(and_(*filters))
        )
        total_count = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(JournalLine, Journal, ChartOfAccount)
            .join(Journal, Journal.id == JournalLine.journal_id)
            .join(ChartOfAccount, ChartOfAccount.id == JournalLine.account_id)
            .where(and_(*filters))
            .order_by(Journal.posting_date.desc(), Journal.created_at.desc(), JournalLine.line_number.asc())
            .offset(skip)
            .limit(limit)
        )
        res = await db.execute(stmt)
        rows = res.all()

        results = []
        for line, journal, account in rows:
            results.append(
                {
                    "id": line.id,
                    "journal_id": journal.id,
                    "journal_number": journal.journal_number,
                    "posting_date": journal.posting_date,
                    "line_number": line.line_number,
                    "account_id": account.id,
                    "account_code": account.account_code,
                    "account_name": account.name,
                    "account_type": account.account_type,
                    "debit": line.debit,
                    "credit": line.credit,
                    "description": line.description or journal.description,
                    "reference_module": journal.reference_module,
                    "reference_id": journal.reference_id,
                    "cost_center_id": line.cost_center_id,
                    "created_at": line.created_at,
                }
            )

        return results, total_count

    async def get_trial_balance(
        self,
        db: AsyncSession,
        as_of_date: date,
    ) -> Dict[str, Any]:
        acc_stmt = (
            select(ChartOfAccount)
            .where(and_(ChartOfAccount.is_deleted == False, ChartOfAccount.is_active == True))
            .order_by(ChartOfAccount.account_code.asc())
        )
        res = await db.execute(acc_stmt)
        accounts = list(res.scalars().all())

        lines = []
        grand_total_debit = Decimal("0.00")
        grand_total_credit = Decimal("0.00")

        for acc in accounts:
            tot_stmt = (
                select(
                    func.coalesce(func.sum(JournalLine.debit), Decimal("0.00")),
                    func.coalesce(func.sum(JournalLine.credit), Decimal("0.00")),
                )
                .join(Journal, Journal.id == JournalLine.journal_id)
                .where(
                    and_(
                        JournalLine.account_id == acc.id,
                        Journal.status == "Posted",
                        Journal.is_deleted == False,
                        Journal.posting_date <= as_of_date,
                    )
                )
            )
            tot_res = await db.execute(tot_stmt)
            period_debit, period_credit = tot_res.first() or (Decimal("0.00"), Decimal("0.00"))

            opening = Decimal(str(acc.opening_balance or "0.00"))
            acc_type = acc.account_type.upper()
            if acc_type in ("ASSET", "EXPENSE"):
                net = period_debit - period_credit
                debit_bal = net if net >= 0 else Decimal("0.00")
                credit_bal = abs(net) if net < 0 else Decimal("0.00")
            else:
                net = period_credit - period_debit
                credit_bal = net if net >= 0 else Decimal("0.00")
                debit_bal = abs(net) if net < 0 else Decimal("0.00")

            grand_total_debit += debit_bal
            grand_total_credit += credit_bal

            lines.append(
                {
                    "account_id": acc.id,
                    "account_code": acc.account_code,
                    "account_name": acc.name,
                    "account_type": acc.account_type,
                    "opening_balance": opening,
                    "period_debit": period_debit,
                    "period_credit": period_credit,
                    "debit_balance": debit_bal,
                    "credit_balance": credit_bal,
                    "net_balance": net,
                }
            )

        return {
            "as_of_date": as_of_date,
            "total_debit": grand_total_debit,
            "total_credit": grand_total_credit,
            "is_balanced": grand_total_debit == grand_total_credit,
            "lines": lines,
        }

