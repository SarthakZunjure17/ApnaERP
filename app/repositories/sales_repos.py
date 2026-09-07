from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.customer import (
    CustomerCategory,
    Customer,
    CustomerContact,
    CustomerAddress,
    CustomerDocument,
)
from app.models.pricing import PriceList, PricingRule, DiscountRule
from app.models.sales_quotation import SalesQuotation, SalesQuotationItem
from app.models.sales_order import SalesOrder, SalesOrderItem
from app.models.delivery_order import DeliveryOrder, DeliveryOrderItem
from app.models.sales_return import SalesReturn, SalesReturnItem
from app.models.sales_report_snapshot import SalesReportSnapshot
from app.repositories.base import BaseRepository


class CustomerCategoryRepository(BaseRepository[CustomerCategory, Any, Any]):
    def __init__(self):
        super().__init__(CustomerCategory)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[CustomerCategory]:
        stmt = select(CustomerCategory).where(CustomerCategory.code == code)
        res = await db.execute(stmt)
        return res.scalars().first()


class CustomerRepository(BaseRepository[Customer, Any, Any]):
    def __init__(self):
        super().__init__(Customer)

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[Customer]:
        stmt = (
            select(Customer)
            .options(
                selectinload(Customer.contacts),
                selectinload(Customer.addresses),
                selectinload(Customer.category),
            )
            .where(and_(Customer.id == id, Customer.is_deleted.is_(False)))
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_by_code(self, db: AsyncSession, customer_code: str) -> Optional[Customer]:
        stmt = (
            select(Customer)
            .options(
                selectinload(Customer.contacts),
                selectinload(Customer.addresses),
                selectinload(Customer.category),
            )
            .where(and_(Customer.customer_code == customer_code, Customer.is_deleted.is_(False)))
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    async def search_customers(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        status: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        is_preferred: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Customer], int]:
        filters = [Customer.is_deleted.is_(False)]
        if status:
            filters.append(Customer.status == status)
        if category_id:
            filters.append(Customer.category_id == category_id)
        if is_preferred is not None:
            filters.append(Customer.is_preferred.is_(is_preferred))
        if query:
            q = f"%{query}%"
            filters.append(
                or_(
                    Customer.customer_code.ilike(q),
                    Customer.name.ilike(q),
                    Customer.email.ilike(q),
                    Customer.phone.ilike(q),
                    Customer.tax_id.ilike(q),
                )
            )

        count_stmt = select(func.count(Customer.id)).where(and_(*filters))
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Customer)
            .where(and_(*filters))
            .order_by(Customer.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all()), total

    async def get_max_number_suffix(self, db: AsyncSession, prefix: str = "CUST-") -> int:
        stmt = select(Customer.customer_code).where(Customer.customer_code.like(f"{prefix}%"))
        res = await db.execute(stmt)
        codes = res.scalars().all()
        max_num = 0
        for code_str in codes:
            suffix = code_str[len(prefix):]
            if suffix.isdigit():
                val = int(suffix)
                if val > max_num:
                    max_num = val
        return max_num


class CustomerContactRepository(BaseRepository[CustomerContact, Any, Any]):
    def __init__(self):
        super().__init__(CustomerContact)

    async def get_by_customer_id(self, db: AsyncSession, customer_id: uuid.UUID) -> List[CustomerContact]:
        stmt = select(CustomerContact).where(CustomerContact.customer_id == customer_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())


class CustomerAddressRepository(BaseRepository[CustomerAddress, Any, Any]):
    def __init__(self):
        super().__init__(CustomerAddress)

    async def get_by_customer_id(self, db: AsyncSession, customer_id: uuid.UUID) -> List[CustomerAddress]:
        stmt = select(CustomerAddress).where(CustomerAddress.customer_id == customer_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())


class CustomerDocumentRepository(BaseRepository[CustomerDocument, Any, Any]):
    def __init__(self):
        super().__init__(CustomerDocument)

    async def get_by_customer_id(self, db: AsyncSession, customer_id: uuid.UUID) -> List[CustomerDocument]:
        stmt = select(CustomerDocument).where(CustomerDocument.customer_id == customer_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())


class PriceListRepository(BaseRepository[PriceList, Any, Any]):
    def __init__(self):
        super().__init__(PriceList)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[PriceList]:
        stmt = select(PriceList).where(PriceList.code == code)
        res = await db.execute(stmt)
        return res.scalars().first()


class PricingRuleRepository(BaseRepository[PricingRule, Any, Any]):
    def __init__(self):
        super().__init__(PricingRule)

    async def get_effective_rule(
        self, db: AsyncSession, price_list_id: uuid.UUID, product_id: uuid.UUID, quantity: Decimal
    ) -> Optional[PricingRule]:
        now = datetime.now()
        stmt = (
            select(PricingRule)
            .where(
                and_(
                    PricingRule.price_list_id == price_list_id,
                    PricingRule.product_id == product_id,
                    PricingRule.min_quantity <= quantity,
                    or_(PricingRule.valid_from.is_(None), PricingRule.valid_from <= now),
                    or_(PricingRule.valid_to.is_(None), PricingRule.valid_to >= now),
                )
            )
            .order_by(PricingRule.min_quantity.desc())
        )
        res = await db.execute(stmt)
        return res.scalars().first()


class DiscountRuleRepository(BaseRepository[DiscountRule, Any, Any]):
    def __init__(self):
        super().__init__(DiscountRule)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[DiscountRule]:
        stmt = select(DiscountRule).where(DiscountRule.code == code)
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_active_rules(self, db: AsyncSession, discount_type: Optional[str] = None) -> List[DiscountRule]:
        now = datetime.now()
        filters = [
            DiscountRule.is_active.is_(True),
            or_(DiscountRule.valid_from.is_(None), DiscountRule.valid_from <= now),
            or_(DiscountRule.valid_to.is_(None), DiscountRule.valid_to >= now),
        ]
        if discount_type:
            filters.append(DiscountRule.discount_type == discount_type)
        stmt = select(DiscountRule).where(and_(*filters))
        res = await db.execute(stmt)
        return list(res.scalars().all())


class SalesQuotationRepository(BaseRepository[SalesQuotation, Any, Any]):
    def __init__(self):
        super().__init__(SalesQuotation)

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[SalesQuotation]:
        stmt = select(SalesQuotation).where(SalesQuotation.id == id).options(selectinload(SalesQuotation.items))
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_for_update(self, db: AsyncSession, id: uuid.UUID) -> Optional[SalesQuotation]:
        stmt = (
            select(SalesQuotation)
            .options(selectinload(SalesQuotation.items))
            .where(SalesQuotation.id == id)
            .with_for_update()
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_number(self, db: AsyncSession, quotation_number: str) -> Optional[SalesQuotation]:
        stmt = select(SalesQuotation).where(SalesQuotation.quotation_number == quotation_number).options(selectinload(SalesQuotation.items))
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_max_number_suffix(self, db: AsyncSession, prefix: str = "SQ-") -> int:
        stmt = select(SalesQuotation.quotation_number).where(SalesQuotation.quotation_number.like(f"{prefix}%"))
        res = await db.execute(stmt)
        numbers = res.scalars().all()
        max_num = 0
        for num_str in numbers:
            suffix = num_str[len(prefix):]
            if suffix.isdigit():
                val = int(suffix)
                if val > max_num:
                    max_num = val
        return max_num

    async def search_quotations(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        status: Optional[str] = None,
        customer_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SalesQuotation], int]:
        filters = []
        if status:
            filters.append(SalesQuotation.status == status)
        if customer_id:
            filters.append(SalesQuotation.customer_id == customer_id)
        if query:
            q = f"%{query}%"
            filters.append(or_(SalesQuotation.quotation_number.ilike(q), SalesQuotation.remarks.ilike(q)))

        count_stmt = select(func.count(SalesQuotation.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = select(SalesQuotation).options(selectinload(SalesQuotation.items)).order_by(SalesQuotation.created_at.desc()).offset(skip).limit(limit)
        if filters:
            stmt = stmt.where(and_(*filters))
        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class SalesOrderRepository(BaseRepository[SalesOrder, Any, Any]):
    def __init__(self):
        super().__init__(SalesOrder)

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[SalesOrder]:
        stmt = select(SalesOrder).where(SalesOrder.id == id).options(selectinload(SalesOrder.items))
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_for_update(self, db: AsyncSession, id: uuid.UUID) -> Optional[SalesOrder]:
        stmt = (
            select(SalesOrder)
            .options(selectinload(SalesOrder.items))
            .where(SalesOrder.id == id)
            .with_for_update()
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_number(self, db: AsyncSession, order_number: str) -> Optional[SalesOrder]:
        stmt = select(SalesOrder).where(SalesOrder.order_number == order_number).options(selectinload(SalesOrder.items))
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_max_number_suffix(self, db: AsyncSession, prefix: str = "SO-") -> int:
        stmt = select(SalesOrder.order_number).where(SalesOrder.order_number.like(f"{prefix}%"))
        res = await db.execute(stmt)
        numbers = res.scalars().all()
        max_num = 0
        for num_str in numbers:
            suffix = num_str[len(prefix):]
            if suffix.isdigit():
                val = int(suffix)
                if val > max_num:
                    max_num = val
        return max_num

    async def search_orders(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        status: Optional[str] = None,
        delivery_status: Optional[str] = None,
        customer_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SalesOrder], int]:
        filters = []
        if status:
            filters.append(SalesOrder.status == status)
        if delivery_status:
            filters.append(SalesOrder.delivery_status == delivery_status)
        if customer_id:
            filters.append(SalesOrder.customer_id == customer_id)
        if query:
            q = f"%{query}%"
            filters.append(or_(SalesOrder.order_number.ilike(q), SalesOrder.remarks.ilike(q)))

        count_stmt = select(func.count(SalesOrder.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = select(SalesOrder).options(selectinload(SalesOrder.items)).order_by(SalesOrder.created_at.desc()).offset(skip).limit(limit)
        if filters:
            stmt = stmt.where(and_(*filters))
        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class DeliveryOrderRepository(BaseRepository[DeliveryOrder, Any, Any]):
    def __init__(self):
        super().__init__(DeliveryOrder)

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[DeliveryOrder]:
        stmt = select(DeliveryOrder).where(DeliveryOrder.id == id).options(selectinload(DeliveryOrder.items))
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_by_number(self, db: AsyncSession, delivery_number: str) -> Optional[DeliveryOrder]:
        stmt = select(DeliveryOrder).where(DeliveryOrder.delivery_number == delivery_number).options(selectinload(DeliveryOrder.items))
        res = await db.execute(stmt)
        return res.scalars().first()

    async def search_deliveries(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        status: Optional[str] = None,
        sales_order_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[DeliveryOrder], int]:
        filters = []
        if status:
            filters.append(DeliveryOrder.status == status)
        if sales_order_id:
            filters.append(DeliveryOrder.sales_order_id == sales_order_id)
        if warehouse_id:
            filters.append(DeliveryOrder.warehouse_id == warehouse_id)
        if query:
            q = f"%{query}%"
            filters.append(
                or_(
                    DeliveryOrder.delivery_number.ilike(q),
                    DeliveryOrder.tracking_number.ilike(q),
                    DeliveryOrder.carrier.ilike(q),
                )
            )

        count_stmt = select(func.count(DeliveryOrder.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = select(DeliveryOrder).options(selectinload(DeliveryOrder.items)).order_by(DeliveryOrder.created_at.desc()).offset(skip).limit(limit)
        if filters:
            stmt = stmt.where(and_(*filters))
        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class SalesReturnRepository(BaseRepository[SalesReturn, Any, Any]):
    def __init__(self):
        super().__init__(SalesReturn)

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[SalesReturn]:
        stmt = select(SalesReturn).where(SalesReturn.id == id).options(selectinload(SalesReturn.items))
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_by_number(self, db: AsyncSession, return_number: str) -> Optional[SalesReturn]:
        stmt = select(SalesReturn).where(SalesReturn.return_number == return_number).options(selectinload(SalesReturn.items))
        res = await db.execute(stmt)
        return res.scalars().first()

    async def search_returns(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        status: Optional[str] = None,
        sales_order_id: Optional[uuid.UUID] = None,
        customer_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SalesReturn], int]:
        filters = []
        if status:
            filters.append(SalesReturn.status == status)
        if sales_order_id:
            filters.append(SalesReturn.sales_order_id == sales_order_id)
        if customer_id:
            filters.append(SalesReturn.customer_id == customer_id)
        if query:
            q = f"%{query}%"
            filters.append(or_(SalesReturn.return_number.ilike(q), SalesReturn.remarks.ilike(q)))

        count_stmt = select(func.count(SalesReturn.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = select(SalesReturn).options(selectinload(SalesReturn.items)).order_by(SalesReturn.created_at.desc()).offset(skip).limit(limit)
        if filters:
            stmt = stmt.where(and_(*filters))
        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class SalesReportSnapshotRepository(BaseRepository[SalesReportSnapshot, Any, Any]):
    def __init__(self):
        super().__init__(SalesReportSnapshot)


customer_category_repository = CustomerCategoryRepository()
customer_repository = CustomerRepository()
customer_contact_repository = CustomerContactRepository()
customer_address_repository = CustomerAddressRepository()
customer_document_repository = CustomerDocumentRepository()
price_list_repository = PriceListRepository()
pricing_rule_repository = PricingRuleRepository()
discount_rule_repository = DiscountRuleRepository()
sales_quotation_repository = SalesQuotationRepository()
sales_order_repository = SalesOrderRepository()
delivery_order_repository = DeliveryOrderRepository()
sales_return_repository = SalesReturnRepository()
sales_report_snapshot_repository = SalesReportSnapshotRepository()
