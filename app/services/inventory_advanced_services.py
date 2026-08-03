from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_events import domain_event_publisher
from app.core.redis import redis_manager
from app.exceptions.base import DuplicateResourceException, NotFoundException, ValidationException


from app.models.batch import Batch
from app.models.cycle_count import CycleCount, CycleCountItem
from app.models.inventory_adjustment import InventoryAdjustment
from app.models.lot import Lot
from app.models.serial_number import SerialNumber
from app.models.stock_reservation import StockReservation
from app.repositories.inventory_advanced_repos import (
    batch_repository,
    cycle_count_repository,
    lot_repository,
    serial_number_repository,
    stock_reservation_repository,
)
from app.repositories.inventory_repos import product_repository, warehouse_repository
from app.schemas.stock_engine import InventoryAdjustmentCreate

from app.schemas.inventory_advanced import (
    BatchCreate,
    BatchUpdate,
    CycleCountCreate,
    CycleCountItemCreate,
    LotCreate,
    LotUpdate,
    SerialNumberCreate,
    SerialNumberUpdate,
    StockReservationCreate,
)
from app.services.stock_engine_services import inventory_adjustment_service, stock_balance_service, stock_ledger_service


# ============================================================================
# BATCH SERVICE
# ============================================================================
class BatchService:
    async def create_batch(self, db: AsyncSession, obj_in: BatchCreate) -> Batch:
        existing = await batch_repository.get_by_number(db, obj_in.batch_number)
        if existing:
            raise DuplicateResourceException(f"Batch with number '{obj_in.batch_number}' already exists.")


        product = await product_repository.get_by_id(db, obj_in.product_id)
        if not product:
            raise NotFoundException(f"Product with ID '{obj_in.product_id}' not found.")

        data = obj_in.model_dump()
        batch = await batch_repository.create(db, obj_in=data)

        # Invalidate Redis batch summary cache
        await redis_manager.delete_pattern("batch:*")
        return batch

    async def get_batch(self, db: AsyncSession, batch_id: uuid.UUID) -> Batch:
        batch = await batch_repository.get_by_id(db, batch_id)
        if not batch:
            raise NotFoundException(f"Batch with ID '{batch_id}' not found.")
        return batch

    async def update_batch(self, db: AsyncSession, batch_id: uuid.UUID, obj_in: BatchUpdate) -> Batch:
        batch = await self.get_batch(db, batch_id)
        update_data = obj_in.model_dump(exclude_unset=True)
        updated = await batch_repository.update(db, db_obj=batch, obj_in=update_data)
        await redis_manager.delete_pattern("batch:*")
        return updated

    async def list_batches(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Batch], int]:
        return await batch_repository.get_multi_paginated(
            db, product_id=product_id, status=status, search=search, skip=skip, limit=limit
        )

    async def allocate_batches(
        self,
        db: AsyncSession,
        product_id: uuid.UUID,
        required_qty: Decimal,
        strategy: str = "FEFO",
    ) -> List[Tuple[Batch, Decimal]]:
        """
        Selects available batches for product allocation using FEFO (First Expired, First Out)
        or FIFO (First In, First Out).
        """
        batches, _ = await batch_repository.get_multi_paginated(
            db, product_id=product_id, status="Active", limit=500
        )
        now = datetime.now(timezone.utc)

        # Filter non-expired active batches
        valid_batches = [
            b for b in batches
            if b.current_quantity > 0 and (b.expiry_date is None or b.expiry_date > now)
        ]

        if strategy.upper() == "FEFO":
            # Earliest expiry date first (None at the end)
            valid_batches.sort(key=lambda b: (b.expiry_date is None, b.expiry_date))
        else:  # FIFO
            valid_batches.sort(key=lambda b: (b.manufacturing_date is None, b.manufacturing_date, b.created_at))

        allocations: List[Tuple[Batch, Decimal]] = []
        remaining = Decimal(str(required_qty))

        for batch in valid_batches:
            if remaining <= Decimal("0.0"):
                break
            avail = Decimal(str(batch.current_quantity))
            allocated = min(avail, remaining)
            allocations.append((batch, allocated))
            remaining -= allocated

        return allocations


# ============================================================================
# SERIAL NUMBER SERVICE
# ============================================================================
class SerialNumberService:
    async def create_serial(self, db: AsyncSession, obj_in: SerialNumberCreate) -> SerialNumber:
        existing = await serial_number_repository.get_by_number(db, obj_in.serial_number)
        if existing:
            raise DuplicateResourceException(f"Serial number '{obj_in.serial_number}' already registered.")


        product = await product_repository.get_by_id(db, obj_in.product_id)
        if not product:
            raise NotFoundException(f"Product with ID '{obj_in.product_id}' not found.")

        data = obj_in.model_dump()
        initial_event = {
            "event": "REGISTERED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": data.get("status", "Available"),
            "warehouse_id": str(data.get("warehouse_id")) if data.get("warehouse_id") else None,
        }
        data["history"] = [initial_event]
        serial = await serial_number_repository.create(db, obj_in=data)
        return serial

    async def get_serial(self, db: AsyncSession, serial_id: uuid.UUID) -> SerialNumber:
        serial = await serial_number_repository.get_by_id(db, serial_id)
        if not serial:
            raise NotFoundException(f"Serial number with ID '{serial_id}' not found.")
        return serial

    async def update_serial_status(
        self,
        db: AsyncSession,
        serial_id: uuid.UUID,
        status: str,
        warehouse_id: Optional[uuid.UUID] = None,
        storage_location_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
    ) -> SerialNumber:
        serial = await self.get_serial(db, serial_id)
        history = list(serial.history or [])
        history.append({
            "event": "STATUS_CHANGE",
            "previous_status": serial.status,
            "new_status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "warehouse_id": str(warehouse_id) if warehouse_id else str(serial.warehouse_id),
            "remarks": remarks,
        })

        update_dict: Dict[str, Any] = {"status": status, "history": history}
        if warehouse_id is not None:
            update_dict["warehouse_id"] = warehouse_id
        if storage_location_id is not None:
            update_dict["storage_location_id"] = storage_location_id

        return await serial_number_repository.update(db, db_obj=serial, obj_in=update_dict)

    async def list_serials(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SerialNumber], int]:
        return await serial_number_repository.get_multi_paginated(
            db, product_id=product_id, warehouse_id=warehouse_id, status=status, search=search, skip=skip, limit=limit
        )


# ============================================================================
# LOT SERVICE
# ============================================================================
class LotService:
    async def create_lot(self, db: AsyncSession, obj_in: LotCreate) -> Lot:
        existing = await lot_repository.get_by_number(db, obj_in.lot_number)
        if existing:
            raise DuplicateResourceException(f"Lot number '{obj_in.lot_number}' already exists.")


        product = await product_repository.get_by_id(db, obj_in.product_id)
        if not product:
            raise NotFoundException(f"Product with ID '{obj_in.product_id}' not found.")

        return await lot_repository.create(db, obj_in=obj_in.model_dump())

    async def get_lot(self, db: AsyncSession, lot_id: uuid.UUID) -> Lot:
        lot = await lot_repository.get_by_id(db, lot_id)
        if not lot:
            raise NotFoundException(f"Lot with ID '{lot_id}' not found.")
        return lot

    async def list_lots(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Lot], int]:
        return await lot_repository.get_multi_paginated(
            db, product_id=product_id, search=search, skip=skip, limit=limit
        )


# ============================================================================
# STOCK RESERVATION SERVICE
# ============================================================================
class StockReservationService:
    async def create_reservation(
        self, db: AsyncSession, obj_in: StockReservationCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> StockReservation:
        """
        Creates a stock reservation.
        Reduces available stock projection without altering StockLedger physical stock.
        """
        # Validate Product & Warehouse
        product = await product_repository.get_by_id(db, obj_in.product_id)
        if not product or product.status == "Archived":
            raise NotFoundException(f"Product with ID '{obj_in.product_id}' not found or archived.")

        warehouse = await warehouse_repository.get_by_id(db, obj_in.warehouse_id)
        if not warehouse or not warehouse.is_active:
            raise NotFoundException(f"Warehouse with ID '{obj_in.warehouse_id}' not found or inactive.")

        # Check current stock balance available
        balance = await stock_balance_service.get_or_create_balance(
            db, product_id=obj_in.product_id, warehouse_id=obj_in.warehouse_id, storage_location_id=obj_in.storage_location_id
        )
        active_reserved = await stock_reservation_repository.get_active_reserved_quantity(
            db, product_id=obj_in.product_id, warehouse_id=obj_in.warehouse_id
        )

        available_qty = Decimal(str(balance.available_quantity)) - active_reserved
        req_qty = Decimal(str(obj_in.quantity))

        if req_qty > available_qty and not product.allow_negative_stock:
            raise ValidationException(
                f"Insufficient unreserved stock available ({available_qty}) for product SKU '{product.sku}' to reserve requested quantity ({req_qty})."
            )

        # Generate Reservation Number
        res_count = (await stock_reservation_repository.get_multi_paginated(db, limit=1))[1] + 1
        res_num = f"RES-{datetime.now().year}-{res_count:05d}"

        data = obj_in.model_dump()
        data["reservation_number"] = res_num
        data["created_by"] = current_user_id
        data["status"] = "Active"

        reservation = await stock_reservation_repository.create(db, obj_in=data)

        # Publish Domain Event
        domain_event_publisher.publish(
            "StockReserved",
            {
                "reservation_id": str(reservation.id),
                "reservation_number": reservation.reservation_number,
                "product_id": str(reservation.product_id),
                "warehouse_id": str(reservation.warehouse_id),
                "quantity": float(reservation.quantity),
                "reserved_for_type": reservation.reserved_for_type,
            },
        )

        # Invalidate Cache
        await redis_manager.delete_pattern("reservation:*")
        await redis_manager.delete_pattern("stock_balance:*")

        return reservation

    async def cancel_reservation(self, db: AsyncSession, reservation_id: uuid.UUID) -> StockReservation:
        res = await stock_reservation_repository.get_by_id(db, reservation_id)
        if not res:
            raise NotFoundException(f"Stock reservation with ID '{reservation_id}' not found.")
        if res.status != "Active":
            raise ValidationException(f"Only Active reservations can be cancelled. Current status is '{res.status}'.")

        res = await stock_reservation_repository.update(db, db_obj=res, obj_in={"status": "Cancelled"})
        await redis_manager.delete_pattern("reservation:*")
        await redis_manager.delete_pattern("stock_balance:*")
        return res

    async def list_reservations(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[StockReservation], int]:
        return await stock_reservation_repository.get_multi_paginated(
            db, product_id=product_id, warehouse_id=warehouse_id, status=status, skip=skip, limit=limit
        )


# ============================================================================
# CYCLE COUNT SERVICE
# ============================================================================
class CycleCountService:
    async def create_cycle_count(
        self, db: AsyncSession, obj_in: CycleCountCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> CycleCount:
        warehouse = await warehouse_repository.get_by_id(db, obj_in.warehouse_id)
        if not warehouse or not warehouse.is_active:
            raise NotFoundException(f"Warehouse with ID '{obj_in.warehouse_id}' not found or inactive.")

        cc_count = (await cycle_count_repository.get_multi_paginated(db, limit=1))[1] + 1
        count_num = f"CC-{datetime.now().year}-{cc_count:05d}"

        cycle_count = CycleCount(
            count_number=count_num,
            warehouse_id=obj_in.warehouse_id,
            storage_location_id=obj_in.storage_location_id,
            status="Draft",
            planned_date=obj_in.planned_date or datetime.now(timezone.utc),
            counted_by_id=current_user_id,
            notes=obj_in.notes,
        )
        db.add(cycle_count)
        await db.flush()

        for item_in in obj_in.items:
            # Query system quantity from StockBalance projection
            bal = await stock_balance_service.get_or_create_balance(
                db, product_id=item_in.product_id, warehouse_id=obj_in.warehouse_id, storage_location_id=obj_in.storage_location_id
            )
            sys_qty = Decimal(str(bal.available_quantity))
            cnt_qty = Decimal(str(item_in.counted_qty))
            variance = cnt_qty - sys_qty

            cc_item = CycleCountItem(
                cycle_count_id=cycle_count.id,
                product_id=item_in.product_id,
                batch_id=item_in.batch_id,
                system_qty=sys_qty,
                counted_qty=cnt_qty,
                variance_qty=variance,
                remarks=item_in.remarks,
            )
            db.add(cc_item)

        await db.commit()
        await db.refresh(cycle_count)
        return cycle_count

    async def approve_cycle_count(
        self, db: AsyncSession, cycle_count_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> CycleCount:
        cc = await cycle_count_repository.get_by_id(db, cycle_count_id)
        if not cc:
            raise NotFoundException(f"Cycle count document with ID '{cycle_count_id}' not found.")
        if cc.status in ("Approved", "Cancelled"):
            raise ValidationException(f"Cycle count is already in terminal state '{cc.status}'.")

        # For items with non-zero variance, generate automatic InventoryAdjustment
        for item in cc.items:
            var_qty = Decimal(str(item.variance_qty))
            if var_qty != Decimal("0.0"):
                adj_type = "Increase" if var_qty > Decimal("0.0") else "Decrease"
                adj_in = InventoryAdjustmentCreate(
                    product_id=item.product_id,
                    warehouse_id=cc.warehouse_id,
                    location_id=cc.storage_location_id,
                    adjustment_type=adj_type,
                    reason=f"Cycle count variance audit ({cc.count_number})",
                    actual_quantity=Decimal(str(item.counted_qty)),
                )
                adj = await inventory_adjustment_service.create_adjustment(db, obj_in=adj_in, current_user_id=current_user_id)
                approved_adj = await inventory_adjustment_service.approve_adjustment(db, id=adj.id, current_user_id=current_user_id)
                await inventory_adjustment_service.apply_adjustment(db, id=approved_adj.id, current_user_id=current_user_id)


        cc.status = "Approved"
        cc.approved_by_id = current_user_id
        await db.commit()
        await db.refresh(cc)

        # Publish Domain Event
        domain_event_publisher.publish(
            "StockCountCompleted",
            {
                "cycle_count_id": str(cc.id),
                "count_number": cc.count_number,
                "warehouse_id": str(cc.warehouse_id),
                "items_count": len(cc.items),
            },
        )

        return cc

    async def list_cycle_counts(
        self,
        db: AsyncSession,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[CycleCount], int]:
        return await cycle_count_repository.get_multi_paginated(
            db, warehouse_id=warehouse_id, status=status, skip=skip, limit=limit
        )


batch_service = BatchService()
serial_number_service = SerialNumberService()
lot_service = LotService()
stock_reservation_service = StockReservationService()
cycle_count_service = CycleCountService()
