import calendar
from datetime import date, datetime, timezone
from decimal import Decimal
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import select, and_, or_, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.domain_events import (
    FINANCE_ACCOUNT_CREATED,
    FINANCE_EXCHANGE_RATE_UPDATED,
    FINANCE_FISCAL_PERIOD_CLOSED,
    FINANCE_JOURNAL_POSTED,
    FINANCE_JOURNAL_REVERSED,
    FINANCE_POSTING_RULE_CHANGED,
    domain_event_publisher,
)
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
from app.models.financial_posting_queue import FinancialPostingQueue
from app.repositories.finance_repos import (
    AccountGroupRepository,
    AccountingDimensionRepository,
    AccountingEventRepository,
    ChartOfAccountRepository,
    CompanyRepository,
    CostCenterRepository,
    CurrencyRepository,
    ExchangeRateRepository,
    FiscalPeriodRepository,
    FiscalYearRepository,
    GeneralLedgerRepository,
    JournalLineRepository,
    JournalRepository,
    JournalTypeRepository,
    PostingRuleRepository,
    TaxCategoryRepository,
    TaxRateRepository,
)
from app.schemas.finance import (
    AccountGroupCreate,
    AccountGroupUpdate,
    AccountingDimensionCreate,
    ChartOfAccountCreate,
    ChartOfAccountUpdate,
    CompanyCreate,
    CompanyUpdate,
    CostCenterCreate,
    CurrencyCreate,
    ExchangeRateCreate,
    FiscalPeriodCreate,
    FiscalYearCreate,
    JournalCreate,
    JournalLineCreate,
    JournalTypeCreate,
    JournalUpdate,
    PostingRuleCreate,
    TaxCategoryCreate,
    TaxRateCreate,
)
from app.services.audit_log import audit_log_service

logger = logging.getLogger("app.services.finance")

# Setup Redis client connection if available
redis_client = None
try:
    import redis

    redis_client = redis.Redis(
        host=getattr(settings, "REDIS_HOST", "localhost"),
        port=getattr(settings, "REDIS_PORT", 6379),
        db=getattr(settings, "REDIS_DB", 0),
        decode_responses=True,
    )
except Exception:
    redis_client = None


class AccountingEventService:
    def __init__(self):
        self.event_repo = AccountingEventRepository()

    async def log_event(
        self,
        db: AsyncSession,
        event_type: str,
        event_name: str,
        entity_type: str,
        entity_id: uuid.UUID,
        payload: Dict[str, Any],
        user_id: Optional[uuid.UUID] = None,
    ) -> AccountingEvent:
        event = AccountingEvent(
            event_type=event_type,
            event_name=event_name,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
        )
        db.add(event)
        await db.commit()
        return event


class CompanyService:
    def __init__(self):
        self.company_repo = CompanyRepository()
        self.account_repo = ChartOfAccountRepository()

    async def create_company(
        self, db: AsyncSession, obj_in: CompanyCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> Company:
        existing = await self.company_repo.get_by_code(db, obj_in.code)
        if existing:
            raise ValueError(f"Company with code '{obj_in.code}' already exists")

        company = Company(**obj_in.model_dump())
        db.add(company)
        await db.commit()
        await db.refresh(company)

        await audit_log_service.log_event(
            db,
            action="CREATE",
            entity_type="Company",
            entity_id=str(company.id),
            user_id=current_user_id,
            new_data={"code": company.code, "name": company.name, "currency": company.base_currency_code},
        )
        return company

    async def get_company(self, db: AsyncSession, company_id: uuid.UUID) -> Optional[Company]:
        company = await self.company_repo.get_by_id(db, company_id)
        if not company or company.is_deleted:
            return None
        return company

    async def get_default_company(self, db: AsyncSession) -> Optional[Company]:
        return await self.company_repo.get_default_company(db)

    async def list_companies(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Company], int]:
        return await self.company_repo.search_companies(db, query=query, is_active=is_active, skip=skip, limit=limit)

    async def update_company(
        self, db: AsyncSession, company_id: uuid.UUID, obj_in: CompanyUpdate, current_user_id: Optional[uuid.UUID] = None
    ) -> Company:
        company = await self.company_repo.get_by_id(db, company_id)
        if not company or company.is_deleted:
            raise ValueError("Company not found")

        prev_data = {"name": company.name, "is_active": company.is_active}
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(company, field, value)

        await db.commit()
        await db.refresh(company)

        await audit_log_service.log_event(
            db,
            action="UPDATE",
            entity_type="Company",
            entity_id=str(company.id),
            user_id=current_user_id,
            previous_data=prev_data,
            new_data=update_data,
        )
        return company

    async def delete_company(
        self, db: AsyncSession, company_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> bool:
        company = await self.company_repo.get_by_id(db, company_id)
        if not company or company.is_deleted:
            raise ValueError("Company not found")

        company.is_deleted = True
        company.deleted_at = datetime.now(timezone.utc)
        await db.commit()

        await audit_log_service.log_event(
            db,
            action="DELETE",
            entity_type="Company",
            entity_id=str(company.id),
            user_id=current_user_id,
            previous_data={"code": company.code, "name": company.name},
        )
        return True



class ChartOfAccountsService:
    def __init__(self):
        self.group_repo = AccountGroupRepository()
        self.account_repo = ChartOfAccountRepository()
        self.event_service = AccountingEventService()

    async def create_account_group(self, db: AsyncSession, obj_in: AccountGroupCreate) -> AccountGroup:
        existing = await self.group_repo.get_by_code(db, obj_in.code)
        if existing:
            raise ValueError(f"Account Group with code '{obj_in.code}' already exists")
        group = AccountGroup(**obj_in.model_dump())
        db.add(group)
        await db.commit()
        await db.refresh(group)
        return group

    async def get_hierarchy(self, db: AsyncSession) -> List[AccountGroup]:
        return await self.group_repo.get_hierarchy(db)

    async def create_account(
        self, db: AsyncSession, obj_in: ChartOfAccountCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> ChartOfAccount:
        existing = await self.account_repo.get_by_code(db, obj_in.account_code)
        if existing:
            raise ValueError(f"Chart of Account with code '{obj_in.account_code}' already exists")

        if obj_in.parent_id:
            parent = await self.account_repo.get_by_id(db, obj_in.parent_id)
            if not parent:
                raise ValueError("Parent account not found")

        account_data = obj_in.model_dump()
        account = ChartOfAccount(**account_data, current_balance=obj_in.opening_balance)
        db.add(account)
        await db.commit()
        await db.refresh(account)

        domain_event_publisher.publish(
            FINANCE_ACCOUNT_CREATED,
            {
                "account_id": str(account.id),
                "account_code": account.account_code,
                "name": account.name,
                "account_type": account.account_type,
            },
        )

        await audit_log_service.log_event(
            db,
            action="CREATE",
            entity_type="ChartOfAccount",
            entity_id=str(account.id),
            user_id=current_user_id,
            new_data={"account_code": account.account_code, "name": account.name, "account_type": account.account_type},
        )

        await self.event_service.log_event(
            db,
            event_type="AccountCreated",
            event_name=FINANCE_ACCOUNT_CREATED,
            entity_type="ChartOfAccount",
            entity_id=account.id,
            payload={"account_code": account.account_code, "name": account.name},
            user_id=current_user_id,
        )

        return account

    async def update_account(
        self, db: AsyncSession, account_id: uuid.UUID, obj_in: ChartOfAccountUpdate, current_user_id: Optional[uuid.UUID] = None
    ) -> ChartOfAccount:
        account = await self.account_repo.get_by_id(db, account_id)
        if not account or account.is_deleted:
            raise ValueError("Account not found")

        if account.is_system:
            if obj_in.account_group_id is not None or obj_in.is_active is False:
                raise ValueError("System reserved accounts cannot be disabled or moved")

        # Circular hierarchy validation
        if obj_in.parent_id is not None:
            if obj_in.parent_id == account_id:
                raise ValueError("Circular reference detected in account hierarchy: account cannot be its own parent")
            descendants = await self.account_repo.get_descendant_ids(db, account_id)
            if obj_in.parent_id in descendants:
                raise ValueError("Circular reference detected in account hierarchy: cannot set a descendant as parent")

        prev_data = {
            "name": account.name,
            "account_type": account.account_type,
            "is_active": account.is_active,
            "parent_id": str(account.parent_id) if account.parent_id else None,
        }
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(account, field, value)

        await db.commit()
        await db.refresh(account)

        await audit_log_service.log_event(
            db,
            action="UPDATE",
            entity_type="ChartOfAccount",
            entity_id=str(account.id),
            user_id=current_user_id,
            previous_data=prev_data,
            new_data=update_data,
        )
        return account

    async def delete_account(
        self, db: AsyncSession, account_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> bool:
        account = await self.account_repo.get_by_id(db, account_id)
        if not account or account.is_deleted:
            raise ValueError("Account not found")
        if account.is_system:
            raise ValueError("System reserved accounts cannot be deleted")

        has_tx = await self.account_repo.has_posted_transactions(db, account_id)
        if has_tx:
            raise ValueError("Cannot delete account with posted transactions")

        account.is_deleted = True
        account.deleted_at = datetime.now(timezone.utc)
        await db.commit()

        await audit_log_service.log_event(
            db,
            action="DELETE",
            entity_type="ChartOfAccount",
            entity_id=str(account.id),
            user_id=current_user_id,
            previous_data={"account_code": account.account_code, "name": account.name},
        )
        return True


class FiscalService:
    def __init__(self):
        self.year_repo = FiscalYearRepository()
        self.period_repo = FiscalPeriodRepository()
        self.event_service = AccountingEventService()

    async def create_fiscal_year(
        self, db: AsyncSession, obj_in: FiscalYearCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> FiscalYear:
        if obj_in.start_date > obj_in.end_date:
            raise ValueError("Fiscal Year start_date cannot be after end_date")

        existing = await self.year_repo.get_by_code(db, obj_in.code)
        if existing:
            raise ValueError(f"Fiscal Year with code '{obj_in.code}' already exists")

        fy = FiscalYear(**obj_in.model_dump())
        db.add(fy)
        await db.commit()
        await db.refresh(fy)

        # Generate 12 monthly fiscal periods automatically
        start_year = fy.start_date.year
        for month in range(1, 13):
            _, last_day = calendar.monthrange(start_year, month)
            p_start = date(start_year, month, 1)
            p_end = date(start_year, month, last_day)
            p_name = f"P{month:02d}-{start_year}"
            period = FiscalPeriod(
                fiscal_year_id=fy.id,
                period_number=month,
                name=p_name,
                start_date=p_start,
                end_date=p_end,
                is_locked=False,
                is_closed=False,
            )
            db.add(period)

        await db.commit()
        await db.refresh(fy)

        await audit_log_service.log_event(
            db,
            action="CREATE",
            entity_type="FiscalYear",
            entity_id=str(fy.id),
            user_id=current_user_id,
            new_data={"code": fy.code, "name": fy.name, "start_date": str(fy.start_date), "end_date": str(fy.end_date)},
        )
        return fy

    async def create_fiscal_period(
        self, db: AsyncSession, obj_in: FiscalPeriodCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> FiscalPeriod:
        if obj_in.start_date > obj_in.end_date:
            raise ValueError("Fiscal Period start_date cannot be after end_date")

        fy = await self.year_repo.get_by_id(db, obj_in.fiscal_year_id)
        if not fy:
            raise ValueError("Fiscal Year not found")

        has_overlap = await self.period_repo.check_overlap(db, obj_in.fiscal_year_id, obj_in.start_date, obj_in.end_date)
        if has_overlap:
            raise ValueError("Fiscal Period dates overlap with an existing period in the same fiscal year")

        period = FiscalPeriod(**obj_in.model_dump())
        db.add(period)
        await db.commit()
        await db.refresh(period)

        await audit_log_service.log_event(
            db,
            action="CREATE",
            entity_type="FiscalPeriod",
            entity_id=str(period.id),
            user_id=current_user_id,
            new_data={"name": period.name, "period_number": period.period_number},
        )
        return period

    async def lock_period(
        self, db: AsyncSession, period_id: uuid.UUID, is_locked: bool, current_user_id: Optional[uuid.UUID] = None
    ) -> FiscalPeriod:
        period = await self.period_repo.get_by_id(db, period_id)
        if not period:
            raise ValueError("Fiscal period not found")

        if period.is_closed and not is_locked:
            raise ValueError("Closed fiscal periods cannot be unlocked directly")

        period.is_locked = is_locked
        await db.commit()
        await db.refresh(period)

        if is_locked:
            domain_event_publisher.publish(
                FINANCE_FISCAL_PERIOD_CLOSED,
                {"period_id": str(period.id), "name": period.name, "start_date": str(period.start_date)},
            )
            await self.event_service.log_event(
                db,
                event_type="FiscalPeriodLocked",
                event_name=FINANCE_FISCAL_PERIOD_CLOSED,
                entity_type="FiscalPeriod",
                entity_id=period.id,
                payload={"period_name": period.name, "is_locked": True},
                user_id=current_user_id,
            )

        await audit_log_service.log_event(
            db,
            action="LOCK" if is_locked else "UNLOCK",
            entity_type="FiscalPeriod",
            entity_id=str(period.id),
            user_id=current_user_id,
            new_data={"name": period.name, "is_locked": is_locked},
        )
        return period

    async def close_period(
        self, db: AsyncSession, period_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> FiscalPeriod:
        period = await self.period_repo.get_by_id(db, period_id)
        if not period:
            raise ValueError("Fiscal period not found")

        period.is_closed = True
        period.is_locked = True
        await db.commit()
        await db.refresh(period)

        domain_event_publisher.publish(
            FINANCE_FISCAL_PERIOD_CLOSED,
            {"period_id": str(period.id), "name": period.name, "start_date": str(period.start_date)},
        )

        await audit_log_service.log_event(
            db,
            action="CLOSE",
            entity_type="FiscalPeriod",
            entity_id=str(period.id),
            user_id=current_user_id,
            new_data={"name": period.name, "is_closed": True, "is_locked": True},
        )
        return period

    async def close_fiscal_year(
        self, db: AsyncSession, year_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> FiscalYear:
        fy = await self.year_repo.get_by_id(db, year_id)
        if not fy:
            raise ValueError("Fiscal Year not found")

        periods = await self.period_repo.get_periods_for_year(db, year_id)
        for p in periods:
            p.is_closed = True
            p.is_locked = True

        fy.status = "Closed"
        await db.commit()
        await db.refresh(fy)

        await audit_log_service.log_event(
            db,
            action="CLOSE",
            entity_type="FiscalYear",
            entity_id=str(fy.id),
            user_id=current_user_id,
            new_data={"code": fy.code, "status": "Closed"},
        )
        return fy


class CurrencyService:
    def __init__(self):
        self.curr_repo = CurrencyRepository()
        self.rate_repo = ExchangeRateRepository()
        self.event_service = AccountingEventService()

    async def create_currency(self, db: AsyncSession, obj_in: CurrencyCreate) -> Currency:
        existing = await self.curr_repo.get_by_code(db, obj_in.code)
        if existing:
            raise ValueError(f"Currency with code '{obj_in.code}' already exists")

        if obj_in.is_base:
            # Reset any existing base currency
            base = await self.curr_repo.get_base_currency(db)
            if base:
                base.is_base = False

        currency = Currency(**obj_in.model_dump())
        db.add(currency)
        await db.commit()
        await db.refresh(currency)
        return currency

    async def set_exchange_rate(
        self, db: AsyncSession, obj_in: ExchangeRateCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> ExchangeRate:
        rate = ExchangeRate(**obj_in.model_dump())
        db.add(rate)
        await db.commit()
        await db.refresh(rate)

        # Cache in Redis if available
        if redis_client:
            try:
                cache_key = f"finance:rate:{obj_in.from_currency_code}:{obj_in.to_currency_code}"
                redis_client.set(cache_key, str(obj_in.rate))
            except Exception:
                pass

        domain_event_publisher.publish(
            FINANCE_EXCHANGE_RATE_UPDATED,
            {
                "from_currency": obj_in.from_currency_code,
                "to_currency": obj_in.to_currency_code,
                "rate": float(obj_in.rate),
                "effective_date": str(obj_in.effective_date),
            },
        )

        await self.event_service.log_event(
            db,
            event_type="ExchangeRateUpdated",
            event_name=FINANCE_EXCHANGE_RATE_UPDATED,
            entity_type="ExchangeRate",
            entity_id=rate.id,
            payload={
                "from_currency": obj_in.from_currency_code,
                "to_currency": obj_in.to_currency_code,
                "rate": float(obj_in.rate),
            },
            user_id=current_user_id,
        )

        return rate

    async def get_exchange_rate(
        self, db: AsyncSession, from_currency: str, to_currency: str, dt: Optional[date] = None
    ) -> Decimal:
        if from_currency == to_currency:
            return Decimal("1.000000")

        # Try Redis cache first
        cache_key = f"finance:rate:{from_currency}:{to_currency}"
        if redis_client and not dt:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    return Decimal(cached)
            except Exception:
                pass

        rate_obj = await self.rate_repo.get_latest_rate(db, from_currency, to_currency, dt)
        if not rate_obj:
            raise ValueError(f"Exchange rate from '{from_currency}' to '{to_currency}' not found")

        return rate_obj.rate

    async def convert_amount(
        self, db: AsyncSession, from_currency: str, to_currency: str, amount: Decimal, dt: Optional[date] = None
    ) -> Decimal:
        rate = await self.get_exchange_rate(db, from_currency, to_currency, dt)
        return round(amount * rate, 2)


class CostCenterService:
    def __init__(self):
        self.cost_repo = CostCenterRepository()
        self.dim_repo = AccountingDimensionRepository()

    async def create_cost_center(self, db: AsyncSession, obj_in: CostCenterCreate) -> CostCenter:
        existing = await self.cost_repo.get_by_code(db, obj_in.code)
        if existing:
            raise ValueError(f"Cost Center with code '{obj_in.code}' already exists")
        cc = CostCenter(**obj_in.model_dump())
        db.add(cc)
        await db.commit()
        await db.refresh(cc)
        return cc

    async def create_dimension(self, db: AsyncSession, obj_in: AccountingDimensionCreate) -> AccountingDimension:
        existing = await self.dim_repo.get_by_name(db, obj_in.name)
        if existing:
            raise ValueError(f"Accounting Dimension '{obj_in.name}' already exists")
        dim = AccountingDimension(**obj_in.model_dump())
        db.add(dim)
        await db.commit()
        await db.refresh(dim)
        return dim


class TaxService:
    def __init__(self):
        self.cat_repo = TaxCategoryRepository()
        self.rate_repo = TaxRateRepository()

    async def create_tax_category(self, db: AsyncSession, obj_in: TaxCategoryCreate) -> TaxCategory:
        existing = await self.cat_repo.get_by_code(db, obj_in.code)
        if existing:
            raise ValueError(f"Tax Category with code '{obj_in.code}' already exists")
        cat = TaxCategory(**obj_in.model_dump())
        db.add(cat)
        await db.commit()
        await db.refresh(cat)
        return cat

    async def create_tax_rate(self, db: AsyncSession, obj_in: TaxRateCreate) -> TaxRate:
        existing = await self.rate_repo.get_by_code(db, obj_in.code)
        if existing:
            raise ValueError(f"Tax Rate with code '{obj_in.code}' already exists")
        rate = TaxRate(**obj_in.model_dump())
        db.add(rate)
        await db.commit()
        await db.refresh(rate)
        return rate

    async def get_effective_tax_rate(
        self, db: AsyncSession, category_id: uuid.UUID, dt: Optional[date] = None
    ) -> Optional[TaxRate]:
        target_date = dt or date.today()
        return await self.rate_repo.get_effective_rate(db, category_id, target_date)


class PostingRuleService:
    def __init__(self):
        self.rule_repo = PostingRuleRepository()
        self.event_service = AccountingEventService()

    async def create_posting_rule(
        self, db: AsyncSession, obj_in: PostingRuleCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> PostingRule:
        existing = await self.rule_repo.get_by_code(db, obj_in.rule_code)
        if existing:
            raise ValueError(f"Posting Rule with code '{obj_in.rule_code}' already exists")

        rule = PostingRule(**obj_in.model_dump())
        db.add(rule)
        await db.commit()
        await db.refresh(rule)

        domain_event_publisher.publish(
            FINANCE_POSTING_RULE_CHANGED,
            {"rule_code": rule.rule_code, "event_name": rule.event_name, "action": "created"},
        )

        await self.event_service.log_event(
            db,
            event_type="PostingRuleCreated",
            event_name=FINANCE_POSTING_RULE_CHANGED,
            entity_type="PostingRule",
            entity_id=rule.id,
            payload={"rule_code": rule.rule_code, "event_name": rule.event_name},
            user_id=current_user_id,
        )

        return rule

    async def generate_journal_from_event(
        self, db: AsyncSession, event_name: str, payload: Dict[str, Any]
    ) -> Optional[JournalCreate]:
        rules = await self.rule_repo.get_by_event(db, event_name)
        if not rules:
            logger.warning(f"No active posting rules found for event '{event_name}'")
            return None

        rule = rules[0]  # Select primary rule
        amount = Decimal(str(payload.get("amount", payload.get("total_amount", "0.00"))))
        if amount <= 0:
            return None

        description = payload.get("description", f"Automated posting for event '{event_name}'")
        posting_date_str = payload.get("posting_date", str(date.today()))
        posting_dt = date.fromisoformat(posting_date_str) if isinstance(posting_date_str, str) else posting_date_str

        lines = [
            JournalLineCreate(
                account_id=rule.debit_account_id,
                debit=amount,
                credit=Decimal("0.00"),
                description=f"Debit line for {event_name}",
            ),
            JournalLineCreate(
                account_id=rule.credit_account_id,
                debit=Decimal("0.00"),
                credit=amount,
                description=f"Credit line for {event_name}",
            ),
        ]

        return JournalCreate(
            journal_type_id=rule.journal_type_id,
            posting_date=posting_dt,
            currency_code=payload.get("currency_code", "USD"),
            exchange_rate=Decimal(str(payload.get("exchange_rate", "1.000000"))),
            description=description,
            reference_module=payload.get("reference_module", event_name),
            reference_id=str(payload.get("reference_id", payload.get("id", ""))),
            lines=lines,
        )


class JournalService:
    def __init__(self):
        self.journal_repo = JournalRepository()
        self.line_repo = JournalLineRepository()
        self.type_repo = JournalTypeRepository()
        self.period_repo = FiscalPeriodRepository()
        self.account_repo = ChartOfAccountRepository()
        self.event_service = AccountingEventService()

    async def create_journal_type(self, db: AsyncSession, obj_in: JournalTypeCreate) -> JournalType:
        existing = await self.type_repo.get_by_code(db, obj_in.code)
        if existing:
            raise ValueError(f"Journal Type with code '{obj_in.code}' already exists")
        jtype = JournalType(**obj_in.model_dump())
        db.add(jtype)
        await db.commit()
        await db.refresh(jtype)
        return jtype

    async def create_journal(
        self, db: AsyncSession, obj_in: JournalCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> Journal:
        jtype = await self.type_repo.get_by_id(db, obj_in.journal_type_id)
        if not jtype:
            raise ValueError("Journal Type not found")

        # Resolve Fiscal Period
        period = await self.period_repo.get_period_for_date(db, obj_in.posting_date)
        if period and (period.is_locked or period.is_closed):
            raise ValueError(f"Posting Date {obj_in.posting_date} falls in closed or locked fiscal period '{period.name}'")

        # Line validation
        if not obj_in.lines or len(obj_in.lines) < 2:
            raise ValueError("Every journal entry must contain at least two lines")

        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")

        for line_in in obj_in.lines:
            if line_in.debit < 0 or line_in.credit < 0:
                raise ValueError("Journal line debit and credit amounts must be non-negative")
            if line_in.debit > 0 and line_in.credit > 0:
                raise ValueError("A journal line cannot have both debit and credit amounts")
            if line_in.debit == 0 and line_in.credit == 0:
                raise ValueError("A journal line must have either a debit or credit amount greater than zero")

            acc = await self.account_repo.get_by_id(db, line_in.account_id)
            if not acc or acc.is_deleted:
                raise ValueError(f"Account {line_in.account_id} not found")
            if not acc.is_active:
                raise ValueError(f"Account '{acc.account_code} - {acc.name}' is inactive and cannot be used in journal entries")

            total_debit += line_in.debit
            total_credit += line_in.credit

        if total_debit != total_credit:
            raise ValueError(f"Total debit ({total_debit}) must equal total credit ({total_credit})")
        if total_debit <= Decimal("0.00"):
            raise ValueError("Journal entry total amount must be greater than zero")

        journal_num = f"{jtype.prefix}-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        status = "Draft"
        if jtype.requires_approval and total_debit >= jtype.approval_threshold:
            status = "PendingApproval"

        journal = Journal(
            journal_number=journal_num,
            journal_type_id=jtype.id,
            posting_date=obj_in.posting_date,
            fiscal_period_id=period.id if period else None,
            currency_code=obj_in.currency_code,
            exchange_rate=obj_in.exchange_rate,
            description=obj_in.description,
            reference_module=obj_in.reference_module,
            reference_id=obj_in.reference_id,
            status=status,
            total_debit=total_debit,
            total_credit=total_credit,
        )
        db.add(journal)
        await db.commit()
        await db.refresh(journal)

        # Create lines
        for idx, l_in in enumerate(obj_in.lines, start=1):
            line = JournalLine(
                journal_id=journal.id,
                line_number=idx,
                account_id=l_in.account_id,
                cost_center_id=l_in.cost_center_id,
                debit=l_in.debit,
                credit=l_in.credit,
                description=l_in.description,
                dimensions=l_in.dimensions,
            )
            db.add(line)

        await db.commit()

        await audit_log_service.log_event(
            db,
            action="CREATE",
            entity_type="Journal",
            entity_id=str(journal.id),
            user_id=current_user_id,
            new_data={"journal_number": journal.journal_number, "total_debit": str(total_debit), "status": status},
        )

        # Route to Approval Workflow if PendingApproval
        if status == "PendingApproval":
            try:
                from app.services.approval_engine import ApprovalEngineService
                engine = ApprovalEngineService(db)
                from app.schemas.approval_workflow import ApprovalRequestCreate
                req_in = ApprovalRequestCreate(
                    document_type="WF_JOURNAL",
                    document_id=journal.id,
                    document_number=journal.journal_number,
                )
                await engine.create_approval_request(req_in, current_user_id)
            except Exception as exc:
                logger.warning(f"Approval workflow creation skipped: {exc}")

        return await self.journal_repo.get_by_id_with_details(db, journal.id)

    async def update_journal(
        self,
        db: AsyncSession,
        journal_id: uuid.UUID,
        obj_in: JournalUpdate,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> Journal:
        journal = await self.journal_repo.get_by_id_with_details(db, journal_id)
        if not journal or journal.is_deleted:
            raise ValueError("Journal not found")

        if journal.status in ("Posted", "Cancelled", "Reversed"):
            raise ValueError(f"Cannot update journal in '{journal.status}' status. Only Draft or PendingApproval journals may be modified.")

        prev_data = {
            "journal_number": journal.journal_number,
            "status": journal.status,
            "total_debit": str(journal.total_debit),
            "description": journal.description,
        }

        # Validate date change with fiscal period
        if obj_in.posting_date is not None:
            period = await self.period_repo.get_period_for_date(db, obj_in.posting_date)
            if period and (period.is_locked or period.is_closed):
                raise ValueError(f"Posting Date {obj_in.posting_date} falls in closed or locked fiscal period '{period.name}'")
            journal.posting_date = obj_in.posting_date
            journal.fiscal_period_id = period.id if period else None

        if obj_in.journal_type_id is not None:
            jtype = await self.type_repo.get_by_id(db, obj_in.journal_type_id)
            if not jtype:
                raise ValueError("Journal Type not found")
            journal.journal_type_id = jtype.id

        if obj_in.currency_code is not None:
            journal.currency_code = obj_in.currency_code
        if obj_in.exchange_rate is not None:
            journal.exchange_rate = obj_in.exchange_rate
        if obj_in.description is not None:
            journal.description = obj_in.description
        if obj_in.reference_module is not None:
            journal.reference_module = obj_in.reference_module
        if obj_in.reference_id is not None:
            journal.reference_id = obj_in.reference_id

        # Update lines if provided
        if obj_in.lines is not None:
            if len(obj_in.lines) < 2:
                raise ValueError("Every journal entry must contain at least two lines")

            total_debit = Decimal("0.00")
            total_credit = Decimal("0.00")

            for line_in in obj_in.lines:
                if line_in.debit < 0 or line_in.credit < 0:
                    raise ValueError("Journal line debit and credit amounts must be non-negative")
                if line_in.debit > 0 and line_in.credit > 0:
                    raise ValueError("A journal line cannot have both debit and credit amounts")
                if line_in.debit == 0 and line_in.credit == 0:
                    raise ValueError("A journal line must have either a debit or credit amount greater than zero")

                acc = await self.account_repo.get_by_id(db, line_in.account_id)
                if not acc or acc.is_deleted:
                    raise ValueError(f"Account {line_in.account_id} not found")
                if not acc.is_active:
                    raise ValueError(f"Account '{acc.account_code} - {acc.name}' is inactive and cannot be used in journal entries")

                total_debit += line_in.debit
                total_credit += line_in.credit

            if total_debit != total_credit:
                raise ValueError(f"Total debit ({total_debit}) must equal total credit ({total_credit})")
            if total_debit <= Decimal("0.00"):
                raise ValueError("Journal entry total amount must be greater than zero")

            # Remove existing lines and add new lines
            await db.execute(delete(JournalLine).where(JournalLine.journal_id == journal.id))
            journal.total_debit = total_debit
            journal.total_credit = total_credit

            for idx, l_in in enumerate(obj_in.lines, start=1):
                line = JournalLine(
                    journal_id=journal.id,
                    line_number=idx,
                    account_id=l_in.account_id,
                    cost_center_id=l_in.cost_center_id,
                    debit=l_in.debit,
                    credit=l_in.credit,
                    description=l_in.description,
                    dimensions=l_in.dimensions,
                )
                db.add(line)

        await db.commit()
        await db.refresh(journal)

        await audit_log_service.log_event(
            db,
            action="UPDATE",
            entity_type="Journal",
            entity_id=str(journal.id),
            user_id=current_user_id,
            previous_data=prev_data,
            new_data={"journal_number": journal.journal_number, "total_debit": str(journal.total_debit), "status": journal.status},
        )

        return await self.journal_repo.get_by_id_with_details(db, journal.id)

    async def delete_journal(
        self, db: AsyncSession, journal_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> bool:
        journal = await self.journal_repo.get_by_id(db, journal_id)
        if not journal or journal.is_deleted:
            raise ValueError("Journal not found")

        if journal.status == "Posted":
            raise ValueError("Posted journals cannot be deleted")

        journal.is_deleted = True
        journal.deleted_at = datetime.now(timezone.utc)
        await db.commit()

        await audit_log_service.log_event(
            db,
            action="DELETE",
            entity_type="Journal",
            entity_id=str(journal.id),
            user_id=current_user_id,
            previous_data={"journal_number": journal.journal_number, "status": journal.status},
        )
        return True

    async def cancel_journal(
        self, db: AsyncSession, journal_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> Journal:
        journal = await self.journal_repo.get_by_id(db, journal_id)
        if not journal or journal.is_deleted:
            raise ValueError("Journal not found")
        if journal.status == "Posted":
            raise ValueError("Posted journals cannot be cancelled. Use reverse_journal instead.")

        prev_status = journal.status
        journal.status = "Cancelled"
        await db.commit()
        await db.refresh(journal)

        await audit_log_service.log_event(
            db,
            action="CANCEL",
            entity_type="Journal",
            entity_id=str(journal.id),
            user_id=current_user_id,
            previous_data={"status": prev_status},
            new_data={"status": "Cancelled"},
        )
        return journal


class PostingEngineService:
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.journal_repo = JournalRepository()
        self.account_repo = ChartOfAccountRepository()
        self.period_repo = FiscalPeriodRepository()
        self.event_service = AccountingEventService()

    async def post_journal(
        self, db: AsyncSession, journal_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> Journal:
        journal = await self.journal_repo.get_by_id_with_details(db, journal_id)
        if not journal or journal.is_deleted:
            raise ValueError("Journal not found")
        if journal.status == "Posted":
            raise ValueError("Journal is already posted")
        if journal.status not in ("Draft", "Approved"):
            raise ValueError(f"Journal status is '{journal.status}'. Only Draft or Approved journals may be posted.")

        # Fiscal period validation
        period = None
        if journal.fiscal_period_id:
            period = await self.period_repo.get_by_id(db, journal.fiscal_period_id)
        else:
            period = await self.period_repo.get_period_for_date(db, journal.posting_date)

        if period and (period.is_locked or period.is_closed):
            raise ValueError(f"Cannot post journal: Fiscal Period '{period.name}' is closed or locked")

        # Double entry balance check
        if journal.total_debit != journal.total_credit or journal.total_debit <= 0:
            raise ValueError("Unbalanced journal entries cannot be posted into General Ledger")

        # Verify lines exist and at least 2
        if not journal.lines or len(journal.lines) < 2:
            raise ValueError("Every journal entry must contain at least two lines to be posted")

        # Update Account Balances
        for line in journal.lines:
            account = await self.account_repo.get_by_id(db, line.account_id)
            if not account or account.is_deleted:
                raise ValueError(f"Account {line.account_id} not found")
            if not account.is_active:
                raise ValueError(f"Account '{account.account_code} - {account.name}' is inactive and cannot be posted to")

            # Normal Balance Convention:
            # Assets / Expenses increase with Debit, decrease with Credit
            # Liabilities / Equity / Revenue increase with Credit, decrease with Debit
            acc_type = account.account_type.upper()
            if acc_type in ("ASSET", "EXPENSE"):
                account.current_balance += line.debit - line.credit
            else:
                account.current_balance += line.credit - line.debit

        journal.status = "Posted"
        journal.posted_at = datetime.now(timezone.utc)
        journal.posted_by_id = current_user_id

        # Update FinancialPostingQueue if linked by reference
        if journal.reference_id:
            try:
                from sqlalchemy import update
                stmt = (
                    update(FinancialPostingQueue)
                    .where(FinancialPostingQueue.payload["reference_id"].astext == journal.reference_id)
                    .values(posting_status="Posted", posted_at=datetime.now(timezone.utc))
                )
                await db.execute(stmt)
            except Exception:
                pass

        await db.commit()
        await db.refresh(journal)

        await audit_log_service.log_event(
            db,
            action="POST",
            entity_type="Journal",
            entity_id=str(journal.id),
            user_id=current_user_id,
            new_data={"journal_number": journal.journal_number, "total_debit": str(journal.total_debit), "status": "Posted"},
        )

        domain_event_publisher.publish(
            FINANCE_JOURNAL_POSTED,
            {
                "journal_id": str(journal.id),
                "journal_number": journal.journal_number,
                "amount": float(journal.total_debit),
                "posting_date": str(journal.posting_date),
            },
        )

        await self.event_service.log_event(
            db,
            event_type="JournalPosted",
            event_name=FINANCE_JOURNAL_POSTED,
            entity_type="Journal",
            entity_id=journal.id,
            payload={"journal_number": journal.journal_number, "total_amount": float(journal.total_debit)},
            user_id=current_user_id,
        )

        return journal

    async def post_double_entry_journal(
        self,
        db: AsyncSession,
        entry_date: date,
        description: str,
        lines: List[Dict[str, Any]],
        reference_number: Optional[str] = None,
        user: Optional[Any] = None,
    ) -> Journal:
        type_stmt = select(JournalType).limit(1)
        res = await db.execute(type_stmt)
        jtype = res.scalars().first()
        if not jtype:
            jtype = JournalType(code="GEN", name="General Journal", prefix="JV", requires_approval=False)
            db.add(jtype)
            await db.flush()

        # Check fiscal period
        period = await self.period_repo.get_period_for_date(db, entry_date)
        if period and (period.is_locked or period.is_closed):
            raise ValueError(f"Cannot post journal: Fiscal Period '{period.name}' is closed or locked")

        j_num = f"{jtype.prefix}-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        total_debit = Decimal(str(sum(line.get("debit", 0.0) for line in lines)))
        total_credit = Decimal(str(sum(line.get("credit", 0.0) for line in lines)))

        if total_debit != total_credit or total_debit <= 0:
            raise ValueError("Unbalanced journal entries cannot be posted into General Ledger")

        journal = Journal(
            journal_number=j_num,
            journal_type_id=jtype.id,
            posting_date=entry_date,
            fiscal_period_id=period.id if period else None,
            description=description,
            reference_id=reference_number,
            status="Posted",
            total_debit=total_debit,
            total_credit=total_credit,
            posted_at=datetime.now(timezone.utc),
            posted_by_id=user.id if user and hasattr(user, "id") else None,
        )
        db.add(journal)
        await db.flush()

        for idx, line in enumerate(lines, start=1):
            account_id = uuid.UUID(line["account_id"]) if isinstance(line["account_id"], str) else line["account_id"]
            debit_amt = Decimal(str(line.get("debit", 0.0)))
            credit_amt = Decimal(str(line.get("credit", 0.0)))

            jline = JournalLine(
                journal_id=journal.id,
                line_number=idx,
                account_id=account_id,
                debit=debit_amt,
                credit=credit_amt,
                description=line.get("description"),
            )
            db.add(jline)

            acc_stmt = select(ChartOfAccount).where(ChartOfAccount.id == account_id)
            acc_res = await db.execute(acc_stmt)
            account = acc_res.scalar_one_or_none()
            if account:
                if not account.is_active or account.is_deleted:
                    raise ValueError(f"Account '{account.account_code} - {account.name}' is inactive or deleted")
                acc_type = account.account_type.upper()
                if acc_type in ("ASSET", "EXPENSE"):
                    account.current_balance += debit_amt - credit_amt
                else:
                    account.current_balance += credit_amt - debit_amt

        await db.commit()
        await db.refresh(journal)

        await audit_log_service.log_event(
            db,
            action="POST",
            entity_type="Journal",
            entity_id=str(journal.id),
            user_id=user.id if user and hasattr(user, "id") else None,
            new_data={"journal_number": journal.journal_number, "total_debit": str(total_debit), "status": "Posted"},
        )
        return journal

    async def reverse_journal(
        self,
        db: AsyncSession,
        journal_id: uuid.UUID,
        reversal_reason: str,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> Journal:
        orig = await self.journal_repo.get_by_id_with_details(db, journal_id)
        if not orig or orig.is_deleted:
            raise ValueError("Original journal not found")
        if orig.status != "Posted":
            raise ValueError("Only Posted journals can be reversed")

        rev_date = orig.posting_date
        period = None
        if orig.fiscal_period_id:
            period = await self.period_repo.get_by_id(db, orig.fiscal_period_id)
        else:
            period = await self.period_repo.get_period_for_date(db, rev_date)

        if period and (period.is_locked or period.is_closed):
            raise ValueError(f"Cannot reverse journal: Fiscal Period '{period.name}' is closed or locked")

        rev_number = f"REV-{orig.journal_number}"

        # Create Reversal Journal Header
        rev_journal = Journal(
            journal_number=rev_number,
            journal_type_id=orig.journal_type_id,
            posting_date=rev_date,
            fiscal_period_id=period.id if period else orig.fiscal_period_id,
            currency_code=orig.currency_code,
            exchange_rate=orig.exchange_rate,
            description=f"Reversal of {orig.journal_number}: {reversal_reason}",
            reference_module=orig.reference_module,
            reference_id=orig.reference_id,
            status="Posted",
            total_debit=orig.total_credit,
            total_credit=orig.total_debit,
            posted_at=datetime.now(timezone.utc),
            posted_by_id=current_user_id,
            reversed_journal_id=orig.id,
            reversal_reason=reversal_reason,
        )
        db.add(rev_journal)
        await db.commit()
        await db.refresh(rev_journal)

        # Create counter-balancing lines (Swap Debit and Credit)
        for idx, line in enumerate(orig.lines, start=1):
            rev_line = JournalLine(
                journal_id=rev_journal.id,
                line_number=idx,
                account_id=line.account_id,
                cost_center_id=line.cost_center_id,
                debit=line.credit,  # Swap
                credit=line.debit,  # Swap
                description=f"Reversal line for line {line.line_number}",
                dimensions=line.dimensions,
            )
            db.add(rev_line)

            # Reverse account balance
            account = await self.account_repo.get_by_id(db, line.account_id)
            if account:
                acc_type = account.account_type.upper()
                if acc_type in ("ASSET", "EXPENSE"):
                    account.current_balance += line.credit - line.debit
                else:
                    account.current_balance += line.debit - line.credit

        # Mark original journal as Reversed
        orig.status = "Reversed"
        orig.reversed_journal_id = rev_journal.id
        orig.reversal_reason = reversal_reason

        await db.commit()

        await audit_log_service.log_event(
            db,
            action="REVERSE",
            entity_type="Journal",
            entity_id=str(orig.id),
            user_id=current_user_id,
            new_data={"reversal_journal_id": str(rev_journal.id), "reason": reversal_reason},
        )

        domain_event_publisher.publish(
            FINANCE_JOURNAL_REVERSED,
            {
                "original_journal_id": str(orig.id),
                "reversal_journal_id": str(rev_journal.id),
                "reversal_number": rev_journal.journal_number,
                "reason": reversal_reason,
            },
        )

        await self.event_service.log_event(
            db,
            event_type="JournalReversed",
            event_name=FINANCE_JOURNAL_REVERSED,
            entity_type="Journal",
            entity_id=rev_journal.id,
            payload={"original_journal": orig.journal_number, "reversal_reason": reversal_reason},
            user_id=current_user_id,
        )

        return await self.journal_repo.get_by_id_with_details(db, rev_journal.id)


class GeneralLedgerService:
    def __init__(self):
        self.gl_repo = GeneralLedgerRepository()

    async def get_account_ledger(
        self,
        db: AsyncSession,
        account_id: uuid.UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        return await self.gl_repo.get_account_ledger(
            db,
            account_id=account_id,
            from_date=from_date,
            to_date=to_date,
            skip=skip,
            limit=limit,
        )

    async def get_all_transactions(
        self,
        db: AsyncSession,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        account_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        return await self.gl_repo.get_all_transactions(
            db,
            from_date=from_date,
            to_date=to_date,
            account_id=account_id,
            skip=skip,
            limit=limit,
        )

    async def get_trial_balance(
        self,
        db: AsyncSession,
        as_of_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        target_date = as_of_date or date.today()
        return await self.gl_repo.get_trial_balance(db, as_of_date=target_date)

