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
            filters.append(ChartOfAccount.account_type == account_type)
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
        stmt = select(FiscalPeriod).where(
            and_(FiscalPeriod.start_date <= dt, FiscalPeriod.end_date >= dt)
        ).options(selectinload(FiscalPeriod.fiscal_year))
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_periods_for_year(self, db: AsyncSession, fiscal_year_id: uuid.UUID) -> List[FiscalPeriod]:
        stmt = select(FiscalPeriod).where(FiscalPeriod.fiscal_year_id == fiscal_year_id).order_by(FiscalPeriod.period_number.asc())
        res = await db.execute(stmt)
        return list(res.scalars().all())


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
