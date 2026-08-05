from decimal import Decimal
from typing import List, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import DuplicateResourceException, NotFoundException
from app.models.pricing import PriceList, PricingRule, DiscountRule
from app.repositories.sales_repos import (
    price_list_repository,
    pricing_rule_repository,
    discount_rule_repository,
)
from app.repositories.inventory_repos import product_repository
from app.schemas.sales import (
    DiscountRuleCreate,
    PriceListCreate,
    PricingRuleCreate,
)


class PricingService:
    async def create_price_list(self, db: AsyncSession, obj_in: PriceListCreate) -> PriceList:
        existing = await price_list_repository.get_by_code(db, obj_in.code)
        if existing:
            raise DuplicateResourceException(f"Price List code '{obj_in.code}' already exists.")

        return await price_list_repository.create(db, obj_in=obj_in.model_dump())

    async def list_price_lists(self, db: AsyncSession) -> List[PriceList]:
        return await price_list_repository.get_multi(db, limit=100)

    async def get_price_list(self, db: AsyncSession, price_list_id: uuid.UUID) -> PriceList:
        pl = await price_list_repository.get_by_id(db, price_list_id)
        if not pl:
            raise NotFoundException(f"Price List ID '{price_list_id}' not found.")
        return pl

    async def create_pricing_rule(self, db: AsyncSession, obj_in: PricingRuleCreate) -> PricingRule:
        await self.get_price_list(db, obj_in.price_list_id)
        prod = await product_repository.get_by_id(db, obj_in.product_id)
        if not prod:
            raise NotFoundException(f"Product ID '{obj_in.product_id}' not found.")

        return await pricing_rule_repository.create(db, obj_in=obj_in.model_dump())

    async def get_effective_price(
        self, db: AsyncSession, price_list_id: uuid.UUID, product_id: uuid.UUID, quantity: Decimal, default_price: Decimal
    ) -> Decimal:
        rule = await pricing_rule_repository.get_effective_rule(db, price_list_id, product_id, quantity)
        if rule:
            return rule.unit_price
        return default_price


class DiscountService:
    async def create_discount_rule(self, db: AsyncSession, obj_in: DiscountRuleCreate) -> DiscountRule:
        existing = await discount_rule_repository.get_by_code(db, obj_in.code)
        if existing:
            raise DuplicateResourceException(f"Discount Rule code '{obj_in.code}' already exists.")

        return await discount_rule_repository.create(db, obj_in=obj_in.model_dump())

    async def list_discount_rules(self, db: AsyncSession) -> List[DiscountRule]:
        return await discount_rule_repository.get_multi(db, limit=100)

    async def calculate_line_discount(
        self, unit_price: Decimal, quantity: Decimal, discount_type: str, discount_value: Decimal
    ) -> Decimal:
        gross = unit_price * quantity
        if gross <= Decimal("0.00"):
            return Decimal("0.00")

        if discount_type == "Percentage":
            amt = gross * (discount_value / Decimal("100.00"))
        else:  # FixedAmount
            amt = discount_value

        return max(Decimal("0.00"), min(gross, round(amt, 2)))

    async def evaluate_document_discounts(
        self, db: AsyncSession, order_total: Decimal, total_quantity: Decimal
    ) -> Decimal:
        active_rules = await discount_rule_repository.get_active_rules(db, discount_type="Document")
        best_discount = Decimal("0.00")

        for r in active_rules:
            if order_total >= r.min_order_value and total_quantity >= r.min_quantity:
                if r.calculation_type == "Percentage":
                    disc = order_total * (r.discount_value / Decimal("100.00"))
                else:
                    disc = r.discount_value
                if disc > best_discount:
                    best_discount = disc

        return round(min(order_total, best_discount), 2)


pricing_service = PricingService()
discount_service = DiscountService()
