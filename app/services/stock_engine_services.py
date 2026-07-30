from datetime import datetime, timezone
from decimal import Decimal
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import (
    DuplicateResourceException,
    NotFoundException,
    ValidationException,
)
from app.models.inventory_adjustment import InventoryAdjustment
from app.models.inventory_transaction_type import InventoryTransactionType
from app.models.opening_stock import OpeningStock
from app.models.product import Product
from app.models.stock_balance import StockBalance
from app.models.stock_ledger import StockLedger
from app.models.warehouse import Warehouse
from app.repositories.inventory_repos import (
    product_repository,
    storage_location_repository,
    warehouse_repository,
)
from app.repositories.stock_engine_repos import (
    inventory_adjustment_repository,
    inventory_transaction_type_repository,
    opening_stock_repository,
    stock_balance_repository,
    stock_ledger_repository,
)
from app.schemas.stock_engine import (
    InventoryAdjustmentCreate,
    InventoryAdjustmentUpdate,
    OpeningStockCreate,
    ProductStockSummaryResponse,
    StockBalanceResponse,
    WarehouseStockSummaryResponse,
)
from app.services.audit_log import audit_log_service
from app.tasks.stock_engine_tasks import send_stock_notification_task

logger = logging.getLogger("app.services.stock_engine")


class InventoryTransactionTypeService:
    """
    Service for managing InventoryTransactionType records.
    """
    async def get_all_active_types(self, db: AsyncSession) -> List[InventoryTransactionType]:
        return await inventory_transaction_type_repository.get_all_active(db)

    async def get_type_by_code(self, db: AsyncSession, code: str) -> InventoryTransactionType:
        ttype = await inventory_transaction_type_repository.get_by_code(db, code)
        if not ttype:
            raise NotFoundException(f"Inventory transaction type code '{code}' not found.")
        return ttype


class StockLedgerService:
    """
    Service for executing immutable stock ledger entries, running balance calculations,
    and negative stock validation.
    """
    async def create_ledger_entry(
        self,
        db: AsyncSession,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        transaction_type_code: str,
        quantity: Decimal,
        direction: str,
        storage_location_id: Optional[uuid.UUID] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
        unit_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
        current_user_id: Optional[uuid.UUID] = None,
        transaction_date: Optional[datetime] = None,
    ) -> StockLedger:
        """
        Creates an immutable stock ledger entry, evaluates negative stock limits, computes
        running balance, invalidates cache, and dispatches projection refresh task.
        """
        # 1. Validate Product
        product = await product_repository.get_by_id(db, product_id)
        if not product:
            raise NotFoundException(f"Product with ID '{product_id}' not found.")
        if not product.track_inventory:
            raise ValidationException(f"Product SKU '{product.sku}' is not configured for inventory tracking.")
        if product.status == "Archived":
            raise ValidationException(f"Product SKU '{product.sku}' is archived and read-only.")

        # 2. Validate Warehouse
        warehouse = await warehouse_repository.get_by_id(db, warehouse_id)
        if not warehouse or not warehouse.is_active:
            raise NotFoundException(f"Warehouse with ID '{warehouse_id}' not found or inactive.")

        # 3. Validate Storage Location if provided
        if storage_location_id:
            location = await storage_location_repository.get_by_id(db, storage_location_id)
            if not location:
                raise NotFoundException(f"Storage location with ID '{storage_location_id}' not found.")
            if location.warehouse_id != warehouse_id:
                raise ValidationException("Storage location does not belong to the specified warehouse.")

        # 4. Lookup Transaction Type
        ttype = await inventory_transaction_type_repository.get_by_code(db, transaction_type_code)
        if not ttype:
            raise NotFoundException(f"Transaction type code '{transaction_type_code}' not found.")

        # 5. Fetch previous running balance
        prev_balance = await stock_ledger_repository.get_latest_running_balance(
            db, product_id=product_id, warehouse_id=warehouse_id, storage_location_id=storage_location_id
        )

        qty = Decimal(str(quantity))
        if qty <= Decimal("0.0"):
            raise ValidationException("Transaction quantity must be strictly positive.")

        # Determine net delta
        if direction.upper() in ("IN", "PRODUCTION_RECEIPT", "RETURN_IN"):
            new_running_balance = prev_balance + qty
        elif direction.upper() in ("OUT", "SALES_ISSUE", "PRODUCTION_CONSUMPTION", "RETURN_OUT"):
            new_running_balance = prev_balance - qty
        elif direction.upper() in ("ADJUSTMENT", "SYSTEM", "TRANSFER"):
            # If direction is explicitly provided or adjustment delta
            new_running_balance = prev_balance + qty  # caller specifies positive or negative qty
        else:
            new_running_balance = prev_balance + qty

        # 6. Negative Stock Validation
        if new_running_balance < Decimal("0.0") and not product.allow_negative_stock:
            raise ValidationException(
                f"Negative stock is disabled for product SKU '{product.sku}'. Proposed transaction would result in negative balance ({new_running_balance})."
            )

        # 7. Insert Immutable Ledger Entry
        entry_data = {
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "storage_location_id": storage_location_id,
            "transaction_type_id": ttype.id,
            "reference_type": reference_type,
            "reference_id": reference_id,
            "quantity": qty,
            "unit_id": unit_id or product.base_unit_id,
            "direction": direction.upper(),
            "running_balance": new_running_balance,
            "transaction_date": transaction_date or datetime.now(timezone.utc),
            "remarks": remarks,
            "created_by": current_user_id,
        }
        ledger_entry = await stock_ledger_repository.create_ledger_entry(db, entry_data)

        # 8. Synchronous StockBalance projection update & Redis cache invalidation
        await stock_balance_repository.upsert_balance(
            db,
            product_id=product_id,
            warehouse_id=warehouse_id,
            storage_location_id=storage_location_id,
            available_quantity=new_running_balance,
        )

        await redis_manager.delete_pattern("stock_balance:*")
        await redis_manager.delete_pattern("warehouse_summary:*")
        await redis_manager.delete_pattern("product_stock:*")

        # 9. Audit event logging
        await audit_log_service.log_event(
            db,
            action="STOCK_LEDGER_CREATE",
            entity_type="StockLedger",
            entity_id=ledger_entry.id,
            user_id=current_user_id,
        )

        return ledger_entry

    async def get_ledger_entries(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        storage_location_id: Optional[uuid.UUID] = None,
        transaction_type_id: Optional[uuid.UUID] = None,
        reference_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search_term: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[StockLedger], int]:
        return await stock_ledger_repository.get_ledger_entries_paginated(
            db,
            product_id=product_id,
            warehouse_id=warehouse_id,
            storage_location_id=storage_location_id,
            transaction_type_id=transaction_type_id,
            reference_type=reference_type,
            start_date=start_date,
            end_date=end_date,
            search_term=search_term,
            skip=skip,
            limit=limit,
        )


class StockBalanceService:
    """
    Service for querying and recalculating StockBalance projections.
    """
    async def recalculate_balance_projection(
        self,
        db: AsyncSession,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        storage_location_id: Optional[uuid.UUID] = None,
    ) -> StockBalance:
        """
        Recalculates StockBalance projection directly from StockLedger history.
        """
        calculated_balance = await stock_ledger_repository.calculate_derived_balance_from_history(
            db, product_id=product_id, warehouse_id=warehouse_id, storage_location_id=storage_location_id
        )
        bal = await stock_balance_repository.upsert_balance(
            db,
            product_id=product_id,
            warehouse_id=warehouse_id,
            storage_location_id=storage_location_id,
            available_quantity=calculated_balance,
        )
        await redis_manager.delete_pattern("stock_balance:*")
        return bal

    async def get_balances(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        location_id: Optional[uuid.UUID] = None,
    ) -> List[StockBalance]:
        if product_id:
            return await stock_balance_repository.get_balances_by_product(db, product_id)
        if warehouse_id:
            return await stock_balance_repository.get_balances_by_warehouse(db, warehouse_id)
        if location_id:
            return await stock_balance_repository.get_balances_by_location(db, location_id)
        
        result = await db.execute(select(StockBalance))
        return list(result.scalars().all())

    async def get_warehouse_stock_summary(
        self, db: AsyncSession, warehouse_id: uuid.UUID
    ) -> WarehouseStockSummaryResponse:
        cache_key = f"warehouse_summary:{warehouse_id}"
        cached = await redis_manager.get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                return WarehouseStockSummaryResponse(**data)
            except Exception:
                pass

        warehouse = await warehouse_repository.get_by_id(db, warehouse_id)
        if not warehouse:
            raise NotFoundException(f"Warehouse with ID '{warehouse_id}' not found.")

        balances = await stock_balance_repository.get_balances_by_warehouse(db, warehouse_id)
        total_avail = sum(Decimal(str(b.available_quantity)) for b in balances)
        total_res = sum(Decimal(str(b.reserved_quantity)) for b in balances)
        total_dam = sum(Decimal(str(b.damaged_quantity)) for b in balances)

        res = WarehouseStockSummaryResponse(
            warehouse_id=warehouse.id,
            warehouse_code=warehouse.code,
            warehouse_name=warehouse.name,
            total_products=len(balances),
            total_available_stock=total_avail,
            total_reserved_stock=total_res,
            total_damaged_stock=total_dam,
        )
        await redis_manager.set(cache_key, res.model_dump_json(), ex=300)
        return res

    async def get_product_stock_summary(
        self, db: AsyncSession, product_id: uuid.UUID
    ) -> ProductStockSummaryResponse:
        cache_key = f"product_stock:{product_id}"
        cached = await redis_manager.get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                return ProductStockSummaryResponse(**data)
            except Exception:
                pass

        product = await product_repository.get_by_id(db, product_id)
        if not product:
            raise NotFoundException(f"Product with ID '{product_id}' not found.")

        balances = await stock_balance_repository.get_balances_by_product(db, product_id)
        total_avail = sum(Decimal(str(b.available_quantity)) for b in balances)
        total_res = sum(Decimal(str(b.reserved_quantity)) for b in balances)
        total_dam = sum(Decimal(str(b.damaged_quantity)) for b in balances)

        bal_responses = [StockBalanceResponse.model_validate(b) for b in balances]

        res = ProductStockSummaryResponse(
            product_id=product.id,
            sku=product.sku,
            product_name=product.name,
            total_available_stock=total_avail,
            total_reserved_stock=total_res,
            total_damaged_stock=total_dam,
            warehouse_balances=bal_responses,
        )
        await redis_manager.set(cache_key, res.model_dump_json(), ex=300)
        return res


class OpeningStockService:
    """
    Service for managing Opening Stock initialization.
    """
    def __init__(self, ledger_service: StockLedgerService):
        self.ledger_service = ledger_service

    async def create_opening_stock(
        self, db: AsyncSession, obj_in: OpeningStockCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> OpeningStock:
        """
        Creates OpeningStock record and executes corresponding StockLedger entry.
        """
        # Duplicate Reference Number Check
        if await opening_stock_repository.exists_by_reference(db, obj_in.reference_number):
            raise DuplicateResourceException(f"Opening stock reference number '{obj_in.reference_number}' already exists.")

        # Duplicate Product/Warehouse/Location Opening Stock Check
        if await opening_stock_repository.exists_by_product_warehouse_location(
            db, product_id=obj_in.product_id, warehouse_id=obj_in.warehouse_id, location_id=obj_in.location_id
        ):
            raise DuplicateResourceException("Opening stock has already been initialized for this product and warehouse location.")

        opening = OpeningStock(
            product_id=obj_in.product_id,
            warehouse_id=obj_in.warehouse_id,
            location_id=obj_in.location_id,
            quantity=obj_in.quantity,
            reference_number=obj_in.reference_number,
            created_by=current_user_id,
            approved_by=current_user_id,
        )
        db.add(opening)
        await db.commit()
        await db.refresh(opening)

        # Generate Stock Ledger Entry
        await self.ledger_service.create_ledger_entry(
            db,
            product_id=obj_in.product_id,
            warehouse_id=obj_in.warehouse_id,
            storage_location_id=obj_in.location_id,
            transaction_type_code="OPENING_STOCK",
            quantity=obj_in.quantity,
            direction="IN",
            reference_type="OpeningStock",
            reference_id=opening.id,
            remarks=f"Opening stock reference #{obj_in.reference_number}",
            current_user_id=current_user_id,
        )

        await audit_log_service.log_event(
            db,
            action="OPENING_STOCK_CREATE",
            entity_type="OpeningStock",
            entity_id=opening.id,
            user_id=current_user_id,
        )

        try:
            send_stock_notification_task.delay(
                event_name="OPENING_STOCK_CREATED",
                details=f"Opening stock ref #{opening.reference_number} created for product ID {opening.product_id}.",
            )
        except Exception as e:
            logger.warning(f"Failed to dispatch stock notification Celery task: {e}")

        return opening

    async def get_opening_stocks(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[OpeningStock]:
        result = await db.execute(select(OpeningStock).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_opening_stock(self, db: AsyncSession, id: uuid.UUID) -> OpeningStock:
        op = await opening_stock_repository.get_by_id(db, id)
        if not op:
            raise NotFoundException(f"Opening stock record with ID '{id}' not found.")
        return op


class InventoryAdjustmentService:
    """
    Service for managing Inventory Adjustments (Draft -> Approved -> Applied).
    """
    def __init__(self, ledger_service: StockLedgerService):
        self.ledger_service = ledger_service

    async def create_adjustment(
        self, db: AsyncSession, obj_in: InventoryAdjustmentCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> InventoryAdjustment:
        product = await product_repository.get_by_id(db, obj_in.product_id)
        if not product:
            raise NotFoundException(f"Product with ID '{obj_in.product_id}' not found.")
        if product.status == "Archived":
            raise ValidationException(f"Product SKU '{product.sku}' is archived and read-only.")

        warehouse = await warehouse_repository.get_by_id(db, obj_in.warehouse_id)
        if not warehouse or not warehouse.is_active:
            raise NotFoundException(f"Warehouse with ID '{obj_in.warehouse_id}' not found or inactive.")

        if obj_in.location_id:
            loc = await storage_location_repository.get_by_id(db, obj_in.location_id)
            if not loc:
                raise NotFoundException(f"Storage location with ID '{obj_in.location_id}' not found.")
            if loc.warehouse_id != obj_in.warehouse_id:
                raise ValidationException("Storage location does not belong to the specified warehouse.")

        # Calculate current expected balance
        expected_qty = await stock_ledger_repository.get_latest_running_balance(
            db, product_id=obj_in.product_id, warehouse_id=obj_in.warehouse_id, storage_location_id=obj_in.location_id
        )

        diff = Decimal(str(obj_in.actual_quantity)) - expected_qty

        # Verify adjustment type consistency
        if obj_in.adjustment_type == "Increase" and diff < Decimal("0.0"):
            raise ValidationException("Adjustment type is 'Increase' but actual quantity is lower than expected quantity.")
        if obj_in.adjustment_type == "Decrease" and diff > Decimal("0.0"):
            raise ValidationException("Adjustment type is 'Decrease' but actual quantity is higher than expected quantity.")

        adj = InventoryAdjustment(
            product_id=obj_in.product_id,
            warehouse_id=obj_in.warehouse_id,
            location_id=obj_in.location_id,
            adjustment_type=obj_in.adjustment_type,
            reason=obj_in.reason,
            expected_quantity=expected_qty,
            actual_quantity=obj_in.actual_quantity,
            difference=diff,
            status="Draft",
            created_by=current_user_id,
        )
        db.add(adj)
        await db.commit()
        await db.refresh(adj)

        await audit_log_service.log_event(
            db,
            action="INVENTORY_ADJUSTMENT_CREATE",
            entity_type="InventoryAdjustment",
            entity_id=adj.id,
            user_id=current_user_id,
        )
        return adj

    async def update_adjustment(
        self, db: AsyncSession, id: uuid.UUID, obj_in: InventoryAdjustmentUpdate, current_user_id: Optional[uuid.UUID] = None
    ) -> InventoryAdjustment:
        adj = await inventory_adjustment_repository.get_by_id(db, id)
        if not adj:
            raise NotFoundException(f"Inventory adjustment with ID '{id}' not found.")
        if adj.status != "Draft":
            raise ValidationException(f"Only Draft adjustments can be modified. Current status: '{adj.status}'.")

        if obj_in.reason is not None:
            adj.reason = obj_in.reason

        if obj_in.actual_quantity is not None:
            adj.actual_quantity = obj_in.actual_quantity
            adj.difference = Decimal(str(obj_in.actual_quantity)) - Decimal(str(adj.expected_quantity))

        await db.commit()
        await db.refresh(adj)

        await audit_log_service.log_event(
            db,
            action="INVENTORY_ADJUSTMENT_UPDATE",
            entity_type="InventoryAdjustment",
            entity_id=adj.id,
            user_id=current_user_id,
        )
        return adj

    async def approve_adjustment(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> InventoryAdjustment:
        adj = await inventory_adjustment_repository.get_by_id(db, id)
        if not adj:
            raise NotFoundException(f"Inventory adjustment with ID '{id}' not found.")
        if adj.status != "Draft":
            raise ValidationException(f"Only Draft adjustments can be approved. Current status: '{adj.status}'.")

        adj.status = "Approved"
        adj.approved_by = current_user_id
        adj.approved_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(adj)

        await audit_log_service.log_event(
            db,
            action="INVENTORY_ADJUSTMENT_APPROVE",
            entity_type="InventoryAdjustment",
            entity_id=adj.id,
            user_id=current_user_id,
        )

        try:
            send_stock_notification_task.delay(
                event_name="INVENTORY_ADJUSTMENT_APPROVED",
                details=f"Inventory adjustment ID {adj.id} was approved by user {current_user_id}.",
            )
        except Exception as e:
            logger.warning(f"Failed to dispatch stock notification task: {e}")

        return adj

    async def apply_adjustment(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> InventoryAdjustment:
        """
        Applies an Approved inventory adjustment, generating an immutable StockLedger entry.
        """
        adj = await inventory_adjustment_repository.get_by_id(db, id)
        if not adj:
            raise NotFoundException(f"Inventory adjustment with ID '{id}' not found.")
        if adj.status != "Approved":
            raise ValidationException(f"Only Approved adjustments can be applied. Current status: '{adj.status}'.")

        diff = Decimal(str(adj.difference))
        if diff == Decimal("0.0"):
            adj.status = "Applied"
            await db.commit()
            return adj

        direction = "IN" if diff > Decimal("0.0") else "OUT"
        qty = abs(diff)

        # Generate Stock Ledger entry
        await self.ledger_service.create_ledger_entry(
            db,
            product_id=adj.product_id,
            warehouse_id=adj.warehouse_id,
            storage_location_id=adj.location_id,
            transaction_type_code="STOCK_ADJUSTMENT",
            quantity=qty,
            direction=direction,
            reference_type="InventoryAdjustment",
            reference_id=adj.id,
            remarks=f"Stock adjustment: {adj.reason}",
            current_user_id=current_user_id,
        )

        adj.status = "Applied"
        await db.commit()
        await db.refresh(adj)

        await audit_log_service.log_event(
            db,
            action="INVENTORY_ADJUSTMENT_APPLY",
            entity_type="InventoryAdjustment",
            entity_id=adj.id,
            user_id=current_user_id,
        )

        try:
            send_stock_notification_task.delay(
                event_name="INVENTORY_ADJUSTMENT_APPLIED",
                details=f"Inventory adjustment ID {adj.id} was successfully applied to stock ledger.",
            )
        except Exception as e:
            logger.warning(f"Failed to dispatch stock notification task: {e}")

        return adj

    async def get_adjustments(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[InventoryAdjustment]:
        result = await db.execute(select(InventoryAdjustment).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_adjustment(self, db: AsyncSession, id: uuid.UUID) -> InventoryAdjustment:
        adj = await inventory_adjustment_repository.get_by_id(db, id)
        if not adj:
            raise NotFoundException(f"Inventory adjustment with ID '{id}' not found.")
        return adj


# Singleton Service Instances
inventory_transaction_type_service = InventoryTransactionTypeService()
stock_ledger_service = StockLedgerService()
stock_balance_service = StockBalanceService()
opening_stock_service = OpeningStockService(stock_ledger_service)
inventory_adjustment_service = InventoryAdjustmentService(stock_ledger_service)
