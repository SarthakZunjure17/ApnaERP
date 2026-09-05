import asyncio
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
from app.models.batch import Batch
from app.models.inventory_adjustment import InventoryAdjustment
from app.models.inventory_policy import InventoryPolicy
from app.models.inventory_transaction_type import InventoryTransactionType
from app.models.opening_stock import OpeningStock
from app.models.product import Product
from app.models.serial_number import SerialNumber
from app.models.stock_balance import StockBalance
from app.models.stock_ledger import StockLedger
from app.models.warehouse import Warehouse
from app.repositories.inventory_advanced_repos import (
    batch_repository,
    serial_number_repository,
)
from app.repositories.inventory_repos import (
    inventory_policy_repository,
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
    StockMovementCreate,
    StorageLocationStockSummaryResponse,
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


class StockMovementService:
    """
    Authoritative Inventory Quantity and Movement Engine for ApnaERP.
    Coordinates immutable StockLedger transaction logs and row-locked StockBalance quantity updates
    inside a single atomic database transaction.
    """
    def __init__(self):
        self._lock = asyncio.Lock()

    async def resolve_negative_stock_policy(
        self, db: AsyncSession, warehouse_id: uuid.UUID, product: Product
    ) -> bool:
        """
        Resolves whether negative stock is allowed using the canonical policy hierarchy:
        1. Warehouse-specific InventoryPolicy (if active)
        2. Global InventoryPolicy (where warehouse_id is NULL, if active)
        3. Product master allow_negative_stock fallback
        """
        # 1. Warehouse Policy
        wh_policy = await inventory_policy_repository.get_by_warehouse_id(db, warehouse_id)
        if wh_policy and wh_policy.is_active:
            return bool(wh_policy.negative_stock_allowed)

        # 2. Global Policy
        global_policy = await inventory_policy_repository.get_global_policy(db)
        if global_policy and global_policy.is_active:
            return bool(global_policy.negative_stock_allowed)

        # 3. Product fallback
        return bool(getattr(product, "allow_negative_stock", False))

    async def process_movement(
        self,
        db: AsyncSession,
        movement_in: StockMovementCreate,
        current_user_id: Optional[uuid.UUID] = None,
        commit: bool = True,
    ) -> StockLedger:
        """
        Executes an atomic, concurrency-safe, idempotent stock movement.
        Updates StockBalance under a row-level lock and records an immutable StockLedger entry.
        """
        async with self._lock:
            # 1. Idempotency Check
            if movement_in.idempotency_key:
                existing = await stock_ledger_repository.find_by_idempotency_key(db, movement_in.idempotency_key)
                if existing:
                    logger.info(f"Duplicate stock movement ignored due to idempotency_key: {movement_in.idempotency_key}")
                    return existing

            # 2. Validate Product
            product = await product_repository.get_by_id(db, movement_in.product_id)
            if not product:
                raise NotFoundException(f"Product with ID '{movement_in.product_id}' not found.")
            if hasattr(product, "is_active") and not product.is_active:
                raise ValidationException(f"Product SKU '{product.sku}' is inactive.")
            if product.status == "Archived":
                raise ValidationException(f"Product SKU '{product.sku}' is archived and read-only.")
            if hasattr(product, "is_stockable") and not product.is_stockable:
                raise ValidationException(f"Product SKU '{product.sku}' is not configured as stockable inventory.")
            if hasattr(product, "track_inventory") and not product.track_inventory:
                raise ValidationException(f"Product SKU '{product.sku}' does not track inventory.")

            # 3. Validate Warehouse
            warehouse = await warehouse_repository.get_by_id(db, movement_in.warehouse_id)
            if not warehouse or not warehouse.is_active:
                raise NotFoundException(f"Warehouse with ID '{movement_in.warehouse_id}' not found or inactive.")

            # 4. Validate Storage Location if provided
            if movement_in.storage_location_id:
                location = await storage_location_repository.get_by_id(db, movement_in.storage_location_id)
                if not location:
                    raise NotFoundException(f"Storage location with ID '{movement_in.storage_location_id}' not found.")
                if hasattr(location, "is_active") and not location.is_active:
                    raise ValidationException(f"Storage location '{location.code}' is inactive.")
                if location.warehouse_id != movement_in.warehouse_id:
                    raise ValidationException("Storage location does not belong to the specified warehouse.")

            # 5. Validate Quantity
            qty = Decimal(str(movement_in.quantity))
            if qty <= Decimal("0.0"):
                raise ValidationException("Movement quantity must be strictly positive.")

            # 6. Normalize Movement Type & Direction
            movement_type = (movement_in.movement_type or "STOCK_IN").upper()
            if movement_type not in ("STOCK_IN", "STOCK_OUT", "ADJUSTMENT"):
                movement_type = "STOCK_IN"

            direction = movement_in.direction.upper() if movement_in.direction else None
            if not direction:
                if movement_type == "STOCK_IN":
                    direction = "IN"
                elif movement_type == "STOCK_OUT":
                    direction = "OUT"
                elif movement_type == "ADJUSTMENT":
                    direction = "IN"
                else:
                    direction = "IN"

            if direction not in ("IN", "OUT"):
                raise ValidationException(f"Movement direction must be 'IN' or 'OUT', received '{direction}'.")

            # 7. Tracking Validations & Mutex Logic
            # A. Batch Tracking Validation
            batch = None
            if product.is_batch_tracked or movement_in.batch_id:
                if product.is_batch_tracked and not movement_in.batch_id:
                    raise ValidationException(f"Product SKU '{product.sku}' is batch-tracked; batch_id is required.")

                if movement_in.batch_id:
                    batch = await batch_repository.get_by_id(db, movement_in.batch_id)
                    if not batch:
                        raise NotFoundException(f"Batch with ID '{movement_in.batch_id}' not found.")
                    if batch.product_id != product.id:
                        raise ValidationException(
                            f"Batch '{batch.batch_number}' does not belong to product SKU '{product.sku}'."
                        )

                    now = datetime.now(timezone.utc)
                    if direction == "OUT":
                        # Expiry Validation
                        if batch.expiry_date:
                            exp_dt = batch.expiry_date if batch.expiry_date.tzinfo else batch.expiry_date.replace(tzinfo=timezone.utc)
                            if exp_dt <= now:
                                raise ValidationException(
                                    f"Batch '{batch.batch_number}' expired on {batch.expiry_date.strftime('%Y-%m-%d')} and cannot be issued."
                                )

                        # Batch Quantity Availability Validation
                        batch_qty = Decimal(str(batch.current_quantity))
                        if qty > batch_qty:
                            raise ValidationException(
                                f"Insufficient stock in batch '{batch.batch_number}' for product SKU '{product.sku}'. "
                                f"Available in batch: {batch_qty}, requested: {qty}."
                            )
                        batch.current_quantity = float(batch_qty - qty)
                        if batch.current_quantity <= 0:
                            batch.status = "Consumed"
                    elif direction == "IN":
                        batch_qty = Decimal(str(batch.current_quantity))
                        batch.current_quantity = float(batch_qty + qty)
                        if batch.status == "Consumed" and batch.current_quantity > 0:
                            batch.status = "Active"

            # B. Serial Number Tracking Validation
            if product.is_serial_tracked or movement_in.serial_numbers:
                if product.is_serial_tracked and not movement_in.serial_numbers:
                    raise ValidationException(
                        f"Product SKU '{product.sku}' is serial-tracked; serial_numbers list is required."
                    )

                if movement_in.serial_numbers:
                    sn_list = list(movement_in.serial_numbers)
                    if int(qty) != len(sn_list) or qty != Decimal(str(len(sn_list))):
                        raise ValidationException(
                            f"Quantity ({qty}) does not match the count of serial numbers provided ({len(sn_list)})."
                        )
                    if len(set(sn_list)) != len(sn_list):
                        raise ValidationException("Duplicate serial numbers found in the supplied list.")

                    now = datetime.now(timezone.utc)
                    if direction == "IN":
                        for sn_str in sn_list:
                            existing_sn = await serial_number_repository.get_by_number(db, sn_str)
                            if existing_sn:
                                if existing_sn.product_id != product.id:
                                    raise ValidationException(
                                        f"Serial number '{sn_str}' belongs to a different product."
                                    )
                                if existing_sn.status == "Available":
                                    raise ValidationException(
                                        f"Serial number '{sn_str}' is already active and available in stock."
                                    )
                                existing_sn.status = "Available"
                                existing_sn.warehouse_id = movement_in.warehouse_id
                                existing_sn.storage_location_id = movement_in.storage_location_id
                                if movement_in.batch_id:
                                    existing_sn.batch_id = movement_in.batch_id
                                hist = list(existing_sn.history or [])
                                hist.append({
                                    "event": "STOCK_IN",
                                    "movement_type": movement_type,
                                    "warehouse_id": str(movement_in.warehouse_id),
                                    "storage_location_id": str(movement_in.storage_location_id) if movement_in.storage_location_id else None,
                                    "timestamp": now.isoformat(),
                                })
                                existing_sn.history = hist
                            else:
                                new_sn = SerialNumber(
                                    serial_number=sn_str,
                                    product_id=product.id,
                                    warehouse_id=movement_in.warehouse_id,
                                    storage_location_id=movement_in.storage_location_id,
                                    batch_id=movement_in.batch_id,
                                    status="Available",
                                    history=[{
                                        "event": "INITIAL_RECEIPT",
                                        "movement_type": movement_type,
                                        "warehouse_id": str(movement_in.warehouse_id),
                                        "storage_location_id": str(movement_in.storage_location_id) if movement_in.storage_location_id else None,
                                        "timestamp": now.isoformat(),
                                    }],
                                )
                                db.add(new_sn)
                    elif direction == "OUT":
                        for sn_str in sn_list:
                            existing_sn = await serial_number_repository.get_by_number(db, sn_str)
                            if not existing_sn:
                                raise NotFoundException(f"Serial number '{sn_str}' not found.")
                            if existing_sn.product_id != product.id:
                                raise ValidationException(
                                    f"Serial number '{sn_str}' does not belong to product SKU '{product.sku}'."
                                )
                            if existing_sn.status not in ("Available", "Reserved"):
                                raise ValidationException(
                                    f"Serial number '{sn_str}' is not available for issue (current status: '{existing_sn.status}')."
                                )
                            if existing_sn.warehouse_id != movement_in.warehouse_id:
                                raise ValidationException(
                                    f"Serial number '{sn_str}' is located at a different warehouse."
                                )
                            existing_sn.status = "Issued"
                            hist = list(existing_sn.history or [])
                            hist.append({
                                "event": "STOCK_OUT",
                                "movement_type": movement_type,
                                "warehouse_id": str(movement_in.warehouse_id),
                                "timestamp": now.isoformat(),
                            })
                            existing_sn.history = hist

            # 8. Row-level Lock on StockBalance
            balance = await stock_balance_repository.get_or_create_for_update(
                db,
                product_id=movement_in.product_id,
                warehouse_id=movement_in.warehouse_id,
                storage_location_id=movement_in.storage_location_id,
            )

            qty_before = Decimal(str(balance.available_quantity))
            if direction == "IN":
                qty_after = qty_before + qty
            else:  # OUT
                qty_after = qty_before - qty

            # 9. Negative Stock Enforcement
            if qty_after < Decimal("0.0"):
                allow_negative = await self.resolve_negative_stock_policy(db, movement_in.warehouse_id, product)
                if not allow_negative:
                    raise ValidationException(
                        f"Insufficient stock for product SKU '{product.sku}' at warehouse '{warehouse.code}'. "
                        f"Current available: {qty_before}, requested deduction: {qty}. Negative stock is disabled."
                    )

            # 10. Atomic Transaction: Update Balance + Insert Ledger Record
            now = datetime.now(timezone.utc)
            balance.available_quantity = qty_after
            balance.last_calculated = now

            meta_data = dict(movement_in.metadata_json or {})
            if movement_in.serial_numbers:
                meta_data["serial_numbers"] = list(movement_in.serial_numbers)

            entry_data = {
                "product_id": movement_in.product_id,
                "warehouse_id": movement_in.warehouse_id,
                "storage_location_id": movement_in.storage_location_id,
                "batch_id": movement_in.batch_id,
                "movement_type": movement_type,
                "direction": direction,
                "quantity": qty,
                "quantity_before": qty_before,
                "quantity_after": qty_after,
                "running_balance": qty_after,
                "unit_id": product.base_unit_id,
                "reference_type": movement_in.reference_type or "ManualMovement",
                "reference_id": movement_in.reference_id,
                "idempotency_key": movement_in.idempotency_key,
                "reason": movement_in.reason,
                "notes": movement_in.notes,
                "remarks": movement_in.notes or movement_in.reason,
                "metadata_json": meta_data if meta_data else None,
                "transaction_date": now,
                "created_by": current_user_id,
                "created_at": now,
            }

            ledger_entry = await stock_ledger_repository.create_ledger_entry(db, entry_data, commit=False)

            if commit:
                # Commit both balance update and ledger entry together atomically
                await db.commit()
                await db.refresh(ledger_entry)
                await db.refresh(balance)

                # Invalidate Cache if Redis configured
                try:
                    await redis_manager.delete_pattern("stock_balance:*")
                    await redis_manager.delete_pattern("warehouse_summary:*")
                    await redis_manager.delete_pattern("product_stock:*")
                    await redis_manager.delete_pattern("batch:*")
                except Exception:
                    pass

                # 11. Audit Logging
                try:
                    await audit_log_service.log_event(
                        db,
                        action=f"STOCK_{movement_type}_{direction}",
                        entity_type="StockLedger",
                        entity_id=str(ledger_entry.id),
                        user_id=current_user_id,
                        previous_data={"quantity_before": float(qty_before)},
                        new_data={
                            "quantity": float(qty),
                            "quantity_before": float(qty_before),
                            "quantity_after": float(qty_after),
                            "warehouse_id": str(movement_in.warehouse_id),
                            "product_id": str(movement_in.product_id),
                            "batch_id": str(movement_in.batch_id) if movement_in.batch_id else None,
                        },
                    )
                except Exception as e:
                    logger.warning(f"Audit log failed for stock movement {ledger_entry.id}: {e}")
            else:
                await db.flush()
                await db.refresh(ledger_entry)

            return ledger_entry

    async def stock_in(
        self,
        db: AsyncSession,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        quantity: Decimal,
        storage_location_id: Optional[uuid.UUID] = None,
        batch_id: Optional[uuid.UUID] = None,
        serial_numbers: Optional[List[str]] = None,
        idempotency_key: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
        reason: Optional[str] = None,
        notes: Optional[str] = None,
        current_user_id: Optional[uuid.UUID] = None,
        commit: bool = True,
    ) -> StockLedger:
        if quantity <= Decimal("0.0"):
            raise ValidationException("Movement quantity must be strictly positive.")
        movement_in = StockMovementCreate(
            product_id=product_id,
            warehouse_id=warehouse_id,
            storage_location_id=storage_location_id,
            batch_id=batch_id,
            serial_numbers=serial_numbers,
            movement_type="STOCK_IN",
            direction="IN",
            quantity=quantity,
            idempotency_key=idempotency_key,
            reference_type=reference_type,
            reference_id=reference_id,
            reason=reason,
            notes=notes,
        )
        return await self.process_movement(db, movement_in, current_user_id=current_user_id, commit=commit)

    async def stock_out(
        self,
        db: AsyncSession,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        quantity: Decimal,
        storage_location_id: Optional[uuid.UUID] = None,
        batch_id: Optional[uuid.UUID] = None,
        serial_numbers: Optional[List[str]] = None,
        idempotency_key: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
        reason: Optional[str] = None,
        notes: Optional[str] = None,
        current_user_id: Optional[uuid.UUID] = None,
        commit: bool = True,
    ) -> StockLedger:
        if quantity <= Decimal("0.0"):
            raise ValidationException("Movement quantity must be strictly positive.")
        movement_in = StockMovementCreate(
            product_id=product_id,
            warehouse_id=warehouse_id,
            storage_location_id=storage_location_id,
            batch_id=batch_id,
            serial_numbers=serial_numbers,
            movement_type="STOCK_OUT",
            direction="OUT",
            quantity=quantity,
            idempotency_key=idempotency_key,
            reference_type=reference_type,
            reference_id=reference_id,
            reason=reason,
            notes=notes,
        )
        return await self.process_movement(db, movement_in, current_user_id=current_user_id, commit=commit)

    async def adjustment(
        self,
        db: AsyncSession,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        quantity: Decimal,
        direction: str,
        storage_location_id: Optional[uuid.UUID] = None,
        batch_id: Optional[uuid.UUID] = None,
        serial_numbers: Optional[List[str]] = None,
        idempotency_key: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
        reason: Optional[str] = None,
        notes: Optional[str] = None,
        current_user_id: Optional[uuid.UUID] = None,
        commit: bool = True,
    ) -> StockLedger:
        if quantity <= Decimal("0.0"):
            raise ValidationException("Movement quantity must be strictly positive.")
        movement_in = StockMovementCreate(
            product_id=product_id,
            warehouse_id=warehouse_id,
            storage_location_id=storage_location_id,
            batch_id=batch_id,
            serial_numbers=serial_numbers,
            movement_type="ADJUSTMENT",
            direction=direction,
            quantity=quantity,
            idempotency_key=idempotency_key,
            reference_type=reference_type,
            reference_id=reference_id,
            reason=reason,
            notes=notes,
        )
        return await self.process_movement(db, movement_in, current_user_id=current_user_id, commit=commit)



class StockLedgerService:
    """
    Service for querying and viewing immutable stock ledger entries.
    """
    async def get_ledger_entries(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        storage_location_id: Optional[uuid.UUID] = None,
        transaction_type_id: Optional[uuid.UUID] = None,
        movement_type: Optional[str] = None,
        direction: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
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
            movement_type=movement_type,
            direction=direction,
            reference_type=reference_type,
            reference_id=reference_id,
            start_date=start_date,
            end_date=end_date,
            search_term=search_term,
            skip=skip,
            limit=limit,
        )

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> StockLedger:
        entry = await stock_ledger_repository.get_by_id(db, id)
        if not entry:
            raise NotFoundException(f"Stock ledger entry with ID '{id}' not found.")
        return entry

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
        Legacy adapter executing via StockMovementService or directly maintaining atomic consistency.
        """
        # Validate Product
        product = await product_repository.get_by_id(db, product_id)
        if not product:
            raise NotFoundException(f"Product with ID '{product_id}' not found.")
        if product.status == "Archived":
            raise ValidationException(f"Product SKU '{product.sku}' is archived and read-only.")

        # Validate Warehouse
        warehouse = await warehouse_repository.get_by_id(db, warehouse_id)
        if not warehouse or not warehouse.is_active:
            raise NotFoundException(f"Warehouse with ID '{warehouse_id}' not found or inactive.")

        # Validate Storage Location
        if storage_location_id:
            location = await storage_location_repository.get_by_id(db, storage_location_id)
            if not location:
                raise NotFoundException(f"Storage location with ID '{storage_location_id}' not found.")
            if location.warehouse_id != warehouse_id:
                raise ValidationException("Storage location does not belong to the specified warehouse.")

        # Transaction Type
        ttype = await inventory_transaction_type_repository.get_by_code(db, transaction_type_code)

        # Row-locked Balance
        balance = await stock_balance_repository.get_or_create_for_update(
            db, product_id=product_id, warehouse_id=warehouse_id, storage_location_id=storage_location_id
        )

        qty = Decimal(str(quantity))
        if qty <= Decimal("0.0"):
            raise ValidationException("Transaction quantity must be strictly positive.")

        qty_before = Decimal(str(balance.available_quantity))
        dir_upper = direction.upper()

        if dir_upper in ("IN", "PRODUCTION_RECEIPT", "RETURN_IN"):
            qty_after = qty_before + qty
            norm_dir = "IN"
        elif dir_upper in ("OUT", "SALES_ISSUE", "PRODUCTION_CONSUMPTION", "RETURN_OUT"):
            qty_after = qty_before - qty
            norm_dir = "OUT"
        else:
            qty_after = qty_before + qty
            norm_dir = "IN"

        # Negative Stock Validation
        if qty_after < Decimal("0.0"):
            wh_policy = await inventory_policy_repository.get_by_warehouse_id(db, warehouse_id)
            global_policy = await inventory_policy_repository.get_global_policy(db)
            allow_neg = False
            if wh_policy and wh_policy.is_active:
                allow_neg = bool(wh_policy.negative_stock_allowed)
            elif global_policy and global_policy.is_active:
                allow_neg = bool(global_policy.negative_stock_allowed)
            else:
                allow_neg = bool(getattr(product, "allow_negative_stock", False))

            if not allow_neg:
                raise ValidationException(
                    f"Negative stock is disabled for product SKU '{product.sku}'. Proposed transaction would result in negative balance ({qty_after})."
                )

        now = datetime.now(timezone.utc)
        balance.available_quantity = qty_after
        balance.last_calculated = now

        entry_data = {
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "storage_location_id": storage_location_id,
            "transaction_type_id": ttype.id if ttype else None,
            "movement_type": "STOCK_IN" if norm_dir == "IN" else "STOCK_OUT",
            "direction": norm_dir,
            "quantity": qty,
            "quantity_before": qty_before,
            "quantity_after": qty_after,
            "running_balance": qty_after,
            "unit_id": unit_id or product.base_unit_id,
            "reference_type": reference_type,
            "reference_id": reference_id,
            "remarks": remarks,
            "notes": remarks,
            "transaction_date": transaction_date or now,
            "created_by": current_user_id,
            "created_at": now,
        }
        ledger_entry = await stock_ledger_repository.create_ledger_entry(db, entry_data, commit=False)
        await db.commit()
        await db.refresh(ledger_entry)
        await db.refresh(balance)

        try:
            await redis_manager.delete_pattern("stock_balance:*")
            await redis_manager.delete_pattern("warehouse_summary:*")
            await redis_manager.delete_pattern("product_stock:*")
        except Exception:
            pass

        try:
            await audit_log_service.log_event(
                db,
                action="STOCK_LEDGER_CREATE",
                entity_type="StockLedger",
                entity_id=ledger_entry.id,
                user_id=current_user_id,
            )
        except Exception:
            pass

        return ledger_entry


class StockBalanceService:
    """
    Service for querying and verifying StockBalance current state.
    """
    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> StockBalance:
        bal = await stock_balance_repository.get_by_id(db, id)
        if not bal:
            raise NotFoundException(f"Stock balance record with ID '{id}' not found.")
        return bal

    async def recalculate_balance_projection(
        self,
        db: AsyncSession,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        storage_location_id: Optional[uuid.UUID] = None,
    ) -> StockBalance:
        """
        Recalculates StockBalance state directly from StockLedger historical entries.
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
        try:
            await redis_manager.delete_pattern("stock_balance:*")
        except Exception:
            pass
        return bal

    async def get_or_create_balance(
        self,
        db: AsyncSession,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        storage_location_id: Optional[uuid.UUID] = None,
    ) -> StockBalance:
        bal = await stock_balance_repository.get_by_keys(
            db, product_id=product_id, warehouse_id=warehouse_id, storage_location_id=storage_location_id
        )
        if not bal:
            bal = await stock_balance_repository.upsert_balance(
                db,
                product_id=product_id,
                warehouse_id=warehouse_id,
                storage_location_id=storage_location_id,
                available_quantity=Decimal("0.0"),
            )
        return bal

    async def get_balances(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        location_id: Optional[uuid.UUID] = None,
    ) -> List[StockBalance]:
        if product_id and warehouse_id and location_id:
            bal = await stock_balance_repository.get_by_keys(
                db, product_id=product_id, warehouse_id=warehouse_id, storage_location_id=location_id
            )
            return [bal] if bal else []
        if product_id and warehouse_id:
            stmt = select(StockBalance).where(
                StockBalance.product_id == product_id,
                StockBalance.warehouse_id == warehouse_id,
            )
            res = await db.execute(stmt)
            return list(res.scalars().all())
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
        warehouse = await warehouse_repository.get_by_id(db, warehouse_id)
        if not warehouse:
            raise NotFoundException(f"Warehouse with ID '{warehouse_id}' not found.")

        balances = await stock_balance_repository.get_balances_by_warehouse(db, warehouse_id)
        total_avail = sum(Decimal(str(b.available_quantity)) for b in balances)
        total_res = sum(Decimal(str(b.reserved_quantity)) for b in balances)
        total_dam = sum(Decimal(str(b.damaged_quantity)) for b in balances)

        return WarehouseStockSummaryResponse(
            warehouse_id=warehouse.id,
            warehouse_code=warehouse.code,
            warehouse_name=warehouse.name,
            total_products=len(balances),
            total_available_stock=total_avail,
            total_reserved_stock=total_res,
            total_damaged_stock=total_dam,
        )

    async def get_product_stock_summary(
        self, db: AsyncSession, product_id: uuid.UUID
    ) -> ProductStockSummaryResponse:
        product = await product_repository.get_by_id(db, product_id)
        if not product:
            raise NotFoundException(f"Product with ID '{product_id}' not found.")

        balances = await stock_balance_repository.get_balances_by_product(db, product_id)
        total_avail = sum(Decimal(str(b.available_quantity)) for b in balances)
        total_res = sum(Decimal(str(b.reserved_quantity)) for b in balances)
        total_dam = sum(Decimal(str(b.damaged_quantity)) for b in balances)

        bal_responses = []
        for b in balances:
            item = StockBalanceResponse.model_validate(b)
            item.quantity_on_hand = b.available_quantity
            item.total_quantity = b.available_quantity + b.reserved_quantity + b.damaged_quantity + b.in_transit_quantity
            if b.product:
                item.product_sku = b.product.sku
                item.product_name = b.product.name
            if b.warehouse:
                item.warehouse_code = b.warehouse.code
                item.warehouse_name = b.warehouse.name
            if b.storage_location:
                item.storage_location_code = b.storage_location.code
            bal_responses.append(item)

        return ProductStockSummaryResponse(
            product_id=product.id,
            sku=product.sku,
            product_name=product.name,
            total_available_stock=total_avail,
            total_reserved_stock=total_res,
            total_damaged_stock=total_dam,
            warehouse_balances=bal_responses,
        )

    async def get_location_stock_summary(
        self, db: AsyncSession, location_id: uuid.UUID
    ) -> StorageLocationStockSummaryResponse:
        location = await storage_location_repository.get_by_id(db, location_id)
        if not location:
            raise NotFoundException(f"Storage location with ID '{location_id}' not found.")

        warehouse = await warehouse_repository.get_by_id(db, location.warehouse_id)
        balances = await stock_balance_repository.get_balances_by_location(db, location_id)
        total_avail = sum(Decimal(str(b.available_quantity)) for b in balances)

        bal_responses = []
        for b in balances:
            item = StockBalanceResponse.model_validate(b)
            item.quantity_on_hand = b.available_quantity
            item.total_quantity = b.available_quantity + b.reserved_quantity + b.damaged_quantity + b.in_transit_quantity
            if b.product:
                item.product_sku = b.product.sku
                item.product_name = b.product.name
            if b.warehouse:
                item.warehouse_code = b.warehouse.code
                item.warehouse_name = b.warehouse.name
            if b.storage_location:
                item.storage_location_code = b.storage_location.code
            bal_responses.append(item)

        return StorageLocationStockSummaryResponse(
            storage_location_id=location.id,
            storage_location_code=location.code,
            warehouse_id=location.warehouse_id,
            warehouse_code=warehouse.code if warehouse else "",
            total_products=len(balances),
            total_available_stock=total_avail,
            balances=bal_responses,
        )


class OpeningStockService:
    """
    Service for managing Opening Stock initialization.
    """
    def __init__(self, ledger_service: StockLedgerService):
        self.ledger_service = ledger_service

    async def create_opening_stock(
        self, db: AsyncSession, obj_in: OpeningStockCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> OpeningStock:
        if await opening_stock_repository.exists_by_reference(db, obj_in.reference_number):
            raise DuplicateResourceException(f"Opening stock reference number '{obj_in.reference_number}' already exists.")

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

        try:
            await audit_log_service.log_event(
                db,
                action="OPENING_STOCK_CREATE",
                entity_type="OpeningStock",
                entity_id=opening.id,
                user_id=current_user_id,
            )
        except Exception:
            pass

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

        # Calculate current expected balance from StockBalance
        bal = await stock_balance_repository.get_by_keys(
            db, product_id=obj_in.product_id, warehouse_id=obj_in.warehouse_id, storage_location_id=obj_in.location_id
        )
        expected_qty = Decimal(str(bal.available_quantity)) if bal else Decimal("0.0")

        diff = Decimal(str(obj_in.actual_quantity)) - expected_qty

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

        try:
            await audit_log_service.log_event(
                db,
                action="INVENTORY_ADJUSTMENT_CREATE",
                entity_type="InventoryAdjustment",
                entity_id=adj.id,
                user_id=current_user_id,
            )
        except Exception:
            pass
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

        try:
            await audit_log_service.log_event(
                db,
                action="INVENTORY_ADJUSTMENT_UPDATE",
                entity_type="InventoryAdjustment",
                entity_id=adj.id,
                user_id=current_user_id,
            )
        except Exception:
            pass
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

        try:
            await audit_log_service.log_event(
                db,
                action="INVENTORY_ADJUSTMENT_APPROVE",
                entity_type="InventoryAdjustment",
                entity_id=adj.id,
                user_id=current_user_id,
            )
        except Exception:
            pass

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

        try:
            await audit_log_service.log_event(
                db,
                action="INVENTORY_ADJUSTMENT_APPLY",
                entity_type="InventoryAdjustment",
                entity_id=adj.id,
                user_id=current_user_id,
            )
        except Exception:
            pass

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
stock_movement_service = StockMovementService()
stock_ledger_service = StockLedgerService()
stock_balance_service = StockBalanceService()
opening_stock_service = OpeningStockService(stock_ledger_service)
inventory_adjustment_service = InventoryAdjustmentService(stock_ledger_service)
