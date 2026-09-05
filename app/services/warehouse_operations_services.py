from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import (
    DuplicateResourceException,
    NotFoundException,
    ValidationException,
)
from app.models.goods_issue import GoodsIssue, GoodsIssueItem
from app.models.goods_receipt import GoodsReceipt, GoodsReceiptItem
from app.models.stock_transfer import StockTransfer, StockTransferItem
from app.repositories.inventory_repos import (
    product_repository,
    storage_location_repository,
    warehouse_repository,
)
from app.repositories.stock_engine_repos import stock_balance_repository
from app.repositories.warehouse_operations_repos import (
    goods_issue_repository,
    goods_receipt_repository,
    stock_transfer_repository,
)
from app.schemas.warehouse_operations import (
    GoodsIssueCreate,
    GoodsIssueUpdate,
    GoodsReceiptCreate,
    GoodsReceiptUpdate,
    StockTransferCreate,
    StockTransferUpdate,
)
from app.services.audit_log import audit_log_service
from app.services.stock_engine_services import stock_movement_service
from app.tasks.warehouse_operations_tasks import send_warehouse_notification_task

logger = logging.getLogger("app.services.warehouse_operations")


class WarehouseExecutionService:
    """
    Orchestration service responsible for executing warehouse operations and generating
    immutable StockLedger entries and updating StockBalance via the authoritative StockMovementService.
    Does NOT directly modify StockBalance.available_quantity.
    """

    async def execute_goods_receipt(
        self, db: AsyncSession, receipt: GoodsReceipt, current_user_id: Optional[uuid.UUID] = None
    ) -> None:
        """
        Executes a GoodsReceipt by creating STOCK_IN movements for each line item.
        Uses commit=False to allow atomic multi-line transaction grouping.
        """
        for item in receipt.items:
            await stock_movement_service.stock_in(
                db,
                product_id=item.product_id,
                warehouse_id=receipt.warehouse_id,
                quantity=Decimal(str(item.quantity)),
                storage_location_id=item.storage_location_id,
                reference_type="GoodsReceipt",
                reference_id=receipt.id,
                reason=f"Goods Receipt #{receipt.receipt_number}",
                notes=item.remarks or item.notes or receipt.remarks or receipt.notes,
                current_user_id=current_user_id,
                commit=False,
            )

    async def execute_goods_issue(
        self, db: AsyncSession, issue: GoodsIssue, current_user_id: Optional[uuid.UUID] = None
    ) -> None:
        """
        Executes a GoodsIssue by creating STOCK_OUT movements for each line item (validating negative stock rules).
        Uses commit=False to allow atomic multi-line transaction grouping.
        """
        for item in issue.items:
            await stock_movement_service.stock_out(
                db,
                product_id=item.product_id,
                warehouse_id=issue.warehouse_id,
                quantity=Decimal(str(item.quantity)),
                storage_location_id=item.storage_location_id,
                reference_type="GoodsIssue",
                reference_id=issue.id,
                reason=f"Goods Issue #{issue.issue_number} ({issue.issue_reason})",
                notes=item.remarks or item.notes or issue.remarks or issue.notes,
                current_user_id=current_user_id,
                commit=False,
            )

    async def execute_stock_transfer_atomic(
        self, db: AsyncSession, transfer: StockTransfer, current_user_id: Optional[uuid.UUID] = None
    ) -> None:
        """
        Executes an atomic StockTransfer (Source OUT + Destination IN) within a single database transaction.
        Implements deterministic lock ordering across all involved balances to prevent PostgreSQL deadlocks.
        """
        # 1. Collect all distinct balance coordinates across source and destination
        balance_keys = set()
        for item in transfer.items:
            s_key = (str(item.product_id), str(transfer.source_warehouse_id), str(transfer.source_location_id or ""))
            d_key = (str(item.product_id), str(transfer.destination_warehouse_id), str(transfer.destination_location_id or ""))
            balance_keys.add(s_key)
            balance_keys.add(d_key)

        # 2. Sort lexicographically to enforce deterministic lock acquisition order
        sorted_keys = sorted(list(balance_keys))

        # 3. Acquire row-level locks on PostgreSQL StockBalance rows in sorted order
        for (pid_str, wid_str, lid_str) in sorted_keys:
            pid = uuid.UUID(pid_str)
            wid = uuid.UUID(wid_str)
            lid = uuid.UUID(lid_str) if lid_str else None
            await stock_balance_repository.get_or_create_for_update(
                db,
                product_id=pid,
                warehouse_id=wid,
                storage_location_id=lid,
            )

        # 4. Execute Source OUT movements
        for item in transfer.items:
            await stock_movement_service.stock_out(
                db,
                product_id=item.product_id,
                warehouse_id=transfer.source_warehouse_id,
                quantity=Decimal(str(item.quantity)),
                storage_location_id=transfer.source_location_id,
                reference_type="StockTransfer",
                reference_id=transfer.id,
                reason=f"Stock Transfer #{transfer.transfer_number} (Source OUT)",
                notes=item.remarks or item.notes or transfer.remarks or transfer.notes,
                current_user_id=current_user_id,
                commit=False,
            )

        # 5. Execute Destination IN movements
        for item in transfer.items:
            await stock_movement_service.stock_in(
                db,
                product_id=item.product_id,
                warehouse_id=transfer.destination_warehouse_id,
                quantity=Decimal(str(item.quantity)),
                storage_location_id=transfer.destination_location_id,
                reference_type="StockTransfer",
                reference_id=transfer.id,
                reason=f"Stock Transfer #{transfer.transfer_number} (Destination IN)",
                notes=item.remarks or item.notes or transfer.remarks or transfer.notes,
                current_user_id=current_user_id,
                commit=False,
            )

    async def execute_stock_transfer_dispatch(
        self, db: AsyncSession, transfer: StockTransfer, current_user_id: Optional[uuid.UUID] = None
    ) -> None:
        """
        Executes Stock Transfer Dispatch by creating STOCK_OUT movements from source warehouse.
        """
        for item in transfer.items:
            await stock_movement_service.stock_out(
                db,
                product_id=item.product_id,
                warehouse_id=transfer.source_warehouse_id,
                quantity=Decimal(str(item.quantity)),
                storage_location_id=transfer.source_location_id,
                reference_type="StockTransfer",
                reference_id=transfer.id,
                reason=f"Stock Transfer Dispatch #{transfer.transfer_number} (Out of source WH)",
                notes=item.remarks or item.notes or transfer.remarks or transfer.notes,
                current_user_id=current_user_id,
                commit=False,
            )

    async def execute_stock_transfer_receive(
        self, db: AsyncSession, transfer: StockTransfer, current_user_id: Optional[uuid.UUID] = None
    ) -> None:
        """
        Executes Stock Transfer Completion/Receipt by creating STOCK_IN movements at destination warehouse.
        """
        for item in transfer.items:
            await stock_movement_service.stock_in(
                db,
                product_id=item.product_id,
                warehouse_id=transfer.destination_warehouse_id,
                quantity=Decimal(str(item.quantity)),
                storage_location_id=transfer.destination_location_id,
                reference_type="StockTransfer",
                reference_id=transfer.id,
                reason=f"Stock Transfer Completion #{transfer.transfer_number} (Into dest WH)",
                notes=item.remarks or item.notes or transfer.remarks or transfer.notes,
                current_user_id=current_user_id,
                commit=False,
            )


class GoodsReceiptService:
    """
    Domain service for managing GoodsReceipt documents and posting workflows.
    """

    def __init__(self, execution_service: WarehouseExecutionService):
        self.execution_service = execution_service

    async def _validate_warehouse_and_items(
        self, db: AsyncSession, warehouse_id: uuid.UUID, items: List[Any]
    ) -> None:
        if not items:
            raise ValidationException("Goods receipt must have at least one line item.")

        wh = await warehouse_repository.get_by_id(db, warehouse_id)
        if not wh or not wh.is_active:
            raise NotFoundException(f"Warehouse with ID '{warehouse_id}' not found or inactive.")

        for item in items:
            qty = Decimal(str(item.quantity))
            if qty <= Decimal("0.0"):
                raise ValidationException("Receipt line quantity must be strictly positive.")

            prod = await product_repository.get_by_id(db, item.product_id)
            if not prod:
                raise NotFoundException(f"Product with ID '{item.product_id}' not found.")
            if hasattr(prod, "is_active") and not prod.is_active:
                raise ValidationException(f"Product SKU '{prod.sku}' is inactive.")
            if prod.status == "Archived":
                raise ValidationException(f"Product SKU '{prod.sku}' is archived and read-only.")
            if hasattr(prod, "is_stockable") and not prod.is_stockable:
                raise ValidationException(f"Product SKU '{prod.sku}' is not configured as stockable inventory.")
            if hasattr(prod, "track_inventory") and not prod.track_inventory:
                raise ValidationException(f"Product SKU '{prod.sku}' does not track inventory.")

            if item.storage_location_id:
                loc = await storage_location_repository.get_by_id(db, item.storage_location_id)
                if not loc:
                    raise NotFoundException(f"Storage location with ID '{item.storage_location_id}' not found.")
                if hasattr(loc, "is_active") and not loc.is_active:
                    raise ValidationException(f"Storage location '{loc.code}' is inactive.")
                if loc.warehouse_id != warehouse_id:
                    raise ValidationException("Storage location does not belong to the target warehouse.")

    async def create_receipt(
        self, db: AsyncSession, obj_in: GoodsReceiptCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> GoodsReceipt:
        if await goods_receipt_repository.exists_by_number(db, obj_in.receipt_number):
            raise DuplicateResourceException(f"Goods receipt number '{obj_in.receipt_number}' already exists.")

        await self._validate_warehouse_and_items(db, obj_in.warehouse_id, obj_in.items)

        remarks_val = obj_in.remarks or obj_in.notes
        receipt = GoodsReceipt(
            receipt_number=obj_in.receipt_number,
            warehouse_id=obj_in.warehouse_id,
            supplier_reference=obj_in.supplier_reference,
            external_reference=obj_in.external_reference,
            receipt_date=obj_in.receipt_date or datetime.now(timezone.utc),
            status="Draft",
            remarks=remarks_val,
            created_by=current_user_id,
        )
        for item in obj_in.items:
            item_remarks = item.remarks or item.notes
            receipt.items.append(
                GoodsReceiptItem(
                    product_id=item.product_id,
                    storage_location_id=item.storage_location_id,
                    quantity=item.quantity,
                    unit_id=item.unit_id,
                    unit_cost=item.unit_cost,
                    remarks=item_remarks,
                )
            )

        db.add(receipt)
        await db.commit()
        await db.refresh(receipt)

        await audit_log_service.log_event(
            db,
            action="GOODS_RECEIPT_CREATE",
            entity_type="GoodsReceipt",
            entity_id=receipt.id,
            user_id=current_user_id,
            new_data={"receipt_number": receipt.receipt_number, "warehouse_id": str(receipt.warehouse_id)},
        )
        return receipt

    async def update_receipt(
        self, db: AsyncSession, id: uuid.UUID, obj_in: GoodsReceiptUpdate, current_user_id: Optional[uuid.UUID] = None
    ) -> GoodsReceipt:
        receipt = await goods_receipt_repository.get_by_id(db, id)
        if not receipt:
            raise NotFoundException(f"Goods receipt with ID '{id}' not found.")
        if receipt.status != "Draft":
            raise ValidationException(f"Only Draft goods receipts can be modified. Current status: '{receipt.status}'.")

        if obj_in.supplier_reference is not None:
            receipt.supplier_reference = obj_in.supplier_reference
        if obj_in.external_reference is not None:
            receipt.external_reference = obj_in.external_reference
        if obj_in.remarks is not None or obj_in.notes is not None:
            receipt.remarks = obj_in.remarks or obj_in.notes

        if obj_in.items is not None:
            await self._validate_warehouse_and_items(db, receipt.warehouse_id, obj_in.items)
            receipt.items.clear()
            for item in obj_in.items:
                receipt.items.append(
                    GoodsReceiptItem(
                        product_id=item.product_id,
                        storage_location_id=item.storage_location_id,
                        quantity=item.quantity,
                        unit_id=item.unit_id,
                        unit_cost=item.unit_cost,
                        remarks=item.remarks or item.notes,
                    )
                )

        await db.commit()
        await db.refresh(receipt)

        await audit_log_service.log_event(
            db,
            action="GOODS_RECEIPT_UPDATE",
            entity_type="GoodsReceipt",
            entity_id=receipt.id,
            user_id=current_user_id,
        )
        return receipt

    async def approve_receipt(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> GoodsReceipt:
        receipt = await goods_receipt_repository.get_by_id(db, id)
        if not receipt:
            raise NotFoundException(f"Goods receipt with ID '{id}' not found.")
        if receipt.status != "Draft":
            raise ValidationException(f"Only Draft receipts can be approved. Current status: '{receipt.status}'.")

        receipt.status = "Approved"
        receipt.approved_by = current_user_id
        receipt.approved_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(receipt)

        await audit_log_service.log_event(
            db,
            action="GOODS_RECEIPT_APPROVE",
            entity_type="GoodsReceipt",
            entity_id=receipt.id,
            user_id=current_user_id,
        )
        return receipt

    async def post_receipt(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None, target_status: str = "Posted"
    ) -> GoodsReceipt:
        """
        Atomically posts a GoodsReceipt document:
        1. Validates document state and business rules.
        2. Executes STOCK_IN movements for each line item via StockMovementService.
        3. Updates document status to Posted (or Received).
        4. Commits all ledger mutations and status changes atomically in a single PostgreSQL transaction.
        """
        receipt = await goods_receipt_repository.get_by_id(db, id)
        if not receipt:
            raise NotFoundException(f"Goods receipt with ID '{id}' not found.")
        if receipt.status in ("Posted", "Received"):
            raise ValidationException(f"Goods receipt is already posted. Current status: '{receipt.status}'.")
        if receipt.status == "Cancelled":
            raise ValidationException(f"Cannot post goods receipt in terminal status '{receipt.status}'.")

        # Full re-validation of warehouse and lines before posting
        await self._validate_warehouse_and_items(db, receipt.warehouse_id, receipt.items)

        try:
            # Execute stock IN via StockMovementService under current transaction
            await self.execution_service.execute_goods_receipt(db, receipt, current_user_id=current_user_id)

            now = datetime.now(timezone.utc)
            receipt.status = target_status
            if not receipt.approved_by:
                receipt.approved_by = current_user_id
                receipt.approved_at = now

            await db.commit()
            await db.refresh(receipt)
        except Exception:
            await db.rollback()
            raise

        try:
            await redis_manager.delete_pattern("stock_balance:*")
            await redis_manager.delete_pattern("warehouse_summary:*")
            await redis_manager.delete_pattern("product_stock:*")
        except Exception:
            pass

        await audit_log_service.log_event(
            db,
            action="GOODS_RECEIPT_POST",
            entity_type="GoodsReceipt",
            entity_id=receipt.id,
            user_id=current_user_id,
            new_data={"receipt_number": receipt.receipt_number, "status": receipt.status, "item_count": len(receipt.items)},
        )

        try:
            send_warehouse_notification_task.delay(
                event_type="GOODS_RECEIPT_POSTED",
                payload={"receipt_id": str(receipt.id), "number": receipt.receipt_number},
            )
        except Exception as e:
            logger.warning(f"Failed to dispatch warehouse notification task: {e}")

        return receipt

    async def receive_receipt(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> GoodsReceipt:
        """
        Legacy/alias method that delegates to post_receipt with Received status.
        """
        return await self.post_receipt(db, id, current_user_id=current_user_id, target_status="Received")

    async def cancel_receipt(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> GoodsReceipt:
        receipt = await goods_receipt_repository.get_by_id(db, id)
        if not receipt:
            raise NotFoundException(f"Goods receipt with ID '{id}' not found.")
        if receipt.status in ("Posted", "Received", "Cancelled"):
            raise ValidationException(f"Cannot cancel goods receipt in terminal status '{receipt.status}'.")

        receipt.status = "Cancelled"
        await db.commit()
        await db.refresh(receipt)

        await audit_log_service.log_event(
            db,
            action="GOODS_RECEIPT_CANCEL",
            entity_type="GoodsReceipt",
            entity_id=receipt.id,
            user_id=current_user_id,
        )
        return receipt

    async def delete_receipt(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> None:
        """
        Deletes a draft GoodsReceipt. Prohibits deleting posted documents.
        """
        receipt = await goods_receipt_repository.get_by_id(db, id)
        if not receipt:
            raise NotFoundException(f"Goods receipt with ID '{id}' not found.")
        if receipt.status != "Draft":
            raise ValidationException(f"Only Draft goods receipts can be deleted. Current status: '{receipt.status}'.")

        await goods_receipt_repository.delete(db, id=id)
        await audit_log_service.log_event(
            db,
            action="GOODS_RECEIPT_DELETE",
            entity_type="GoodsReceipt",
            entity_id=id,
            user_id=current_user_id,
        )

    async def get_receipts(
        self,
        db: AsyncSession,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[GoodsReceipt], int]:
        return await goods_receipt_repository.get_goods_receipts_paginated(
            db, warehouse_id=warehouse_id, status=status, start_date=start_date, end_date=end_date, search_term=search, skip=skip, limit=limit
        )

    async def get_receipt(self, db: AsyncSession, id: uuid.UUID) -> GoodsReceipt:
        gr = await goods_receipt_repository.get_by_id(db, id)
        if not gr:
            raise NotFoundException(f"Goods receipt with ID '{id}' not found.")
        return gr


class GoodsIssueService:
    """
    Domain service for managing GoodsIssue documents and posting workflows.
    """

    def __init__(self, execution_service: WarehouseExecutionService):
        self.execution_service = execution_service

    async def _validate_warehouse_and_items(
        self, db: AsyncSession, warehouse_id: uuid.UUID, items: List[Any]
    ) -> None:
        if not items:
            raise ValidationException("Goods issue must have at least one line item.")

        wh = await warehouse_repository.get_by_id(db, warehouse_id)
        if not wh or not wh.is_active:
            raise NotFoundException(f"Warehouse with ID '{warehouse_id}' not found or inactive.")

        for item in items:
            qty = Decimal(str(item.quantity))
            if qty <= Decimal("0.0"):
                raise ValidationException("Issue line quantity must be strictly positive.")

            prod = await product_repository.get_by_id(db, item.product_id)
            if not prod:
                raise NotFoundException(f"Product with ID '{item.product_id}' not found.")
            if hasattr(prod, "is_active") and not prod.is_active:
                raise ValidationException(f"Product SKU '{prod.sku}' is inactive.")
            if prod.status == "Archived":
                raise ValidationException(f"Product SKU '{prod.sku}' is archived and read-only.")
            if hasattr(prod, "is_stockable") and not prod.is_stockable:
                raise ValidationException(f"Product SKU '{prod.sku}' is not configured as stockable inventory.")
            if hasattr(prod, "track_inventory") and not prod.track_inventory:
                raise ValidationException(f"Product SKU '{prod.sku}' does not track inventory.")

            if item.storage_location_id:
                loc = await storage_location_repository.get_by_id(db, item.storage_location_id)
                if not loc:
                    raise NotFoundException(f"Storage location with ID '{item.storage_location_id}' not found.")
                if hasattr(loc, "is_active") and not loc.is_active:
                    raise ValidationException(f"Storage location '{loc.code}' is inactive.")
                if loc.warehouse_id != warehouse_id:
                    raise ValidationException("Storage location does not belong to the target warehouse.")

    async def create_issue(
        self, db: AsyncSession, obj_in: GoodsIssueCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> GoodsIssue:
        if await goods_issue_repository.exists_by_number(db, obj_in.issue_number):
            raise DuplicateResourceException(f"Goods issue number '{obj_in.issue_number}' already exists.")

        await self._validate_warehouse_and_items(db, obj_in.warehouse_id, obj_in.items)

        remarks_val = obj_in.remarks or obj_in.notes
        issue = GoodsIssue(
            issue_number=obj_in.issue_number,
            warehouse_id=obj_in.warehouse_id,
            issue_date=obj_in.issue_date or datetime.now(timezone.utc),
            issue_reason=obj_in.issue_reason,
            status="Draft",
            remarks=remarks_val,
            created_by=current_user_id,
        )
        for item in obj_in.items:
            item_remarks = item.remarks or item.notes
            issue.items.append(
                GoodsIssueItem(
                    product_id=item.product_id,
                    storage_location_id=item.storage_location_id,
                    quantity=item.quantity,
                    unit_id=item.unit_id,
                    remarks=item_remarks,
                )
            )

        db.add(issue)
        await db.commit()
        await db.refresh(issue)

        await audit_log_service.log_event(
            db,
            action="GOODS_ISSUE_CREATE",
            entity_type="GoodsIssue",
            entity_id=issue.id,
            user_id=current_user_id,
            new_data={"issue_number": issue.issue_number, "warehouse_id": str(issue.warehouse_id)},
        )
        return issue

    async def update_issue(
        self, db: AsyncSession, id: uuid.UUID, obj_in: GoodsIssueUpdate, current_user_id: Optional[uuid.UUID] = None
    ) -> GoodsIssue:
        issue = await goods_issue_repository.get_by_id(db, id)
        if not issue:
            raise NotFoundException(f"Goods issue with ID '{id}' not found.")
        if issue.status != "Draft":
            raise ValidationException(f"Only Draft goods issues can be modified. Current status: '{issue.status}'.")

        if obj_in.issue_reason is not None:
            issue.issue_reason = obj_in.issue_reason
        if obj_in.remarks is not None or obj_in.notes is not None:
            issue.remarks = obj_in.remarks or obj_in.notes

        if obj_in.items is not None:
            await self._validate_warehouse_and_items(db, issue.warehouse_id, obj_in.items)
            issue.items.clear()
            for item in obj_in.items:
                issue.items.append(
                    GoodsIssueItem(
                        product_id=item.product_id,
                        storage_location_id=item.storage_location_id,
                        quantity=item.quantity,
                        unit_id=item.unit_id,
                        remarks=item.remarks or item.notes,
                    )
                )

        await db.commit()
        await db.refresh(issue)

        await audit_log_service.log_event(
            db,
            action="GOODS_ISSUE_UPDATE",
            entity_type="GoodsIssue",
            entity_id=issue.id,
            user_id=current_user_id,
        )
        return issue

    async def approve_issue(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> GoodsIssue:
        issue = await goods_issue_repository.get_by_id(db, id)
        if not issue:
            raise NotFoundException(f"Goods issue with ID '{id}' not found.")
        if issue.status != "Draft":
            raise ValidationException(f"Only Draft issues can be approved. Current status: '{issue.status}'.")

        issue.status = "Approved"
        issue.approved_by = current_user_id
        issue.approved_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(issue)

        await audit_log_service.log_event(
            db,
            action="GOODS_ISSUE_APPROVE",
            entity_type="GoodsIssue",
            entity_id=issue.id,
            user_id=current_user_id,
        )
        return issue

    async def post_issue(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None, target_status: str = "Posted"
    ) -> GoodsIssue:
        """
        Atomically posts a GoodsIssue document:
        1. Validates document state and items.
        2. Executes STOCK_OUT movements for each line item via StockMovementService (with negative stock policy enforcement).
        3. Updates document status to Posted (or Issued).
        4. Commits all ledger mutations and status changes atomically in a single PostgreSQL transaction.
        """
        issue = await goods_issue_repository.get_by_id(db, id)
        if not issue:
            raise NotFoundException(f"Goods issue with ID '{id}' not found.")
        if issue.status in ("Posted", "Issued"):
            raise ValidationException(f"Goods issue is already posted. Current status: '{issue.status}'.")
        if issue.status == "Cancelled":
            raise ValidationException(f"Cannot post goods issue in terminal status '{issue.status}'.")

        # Full re-validation of warehouse and lines before posting
        await self._validate_warehouse_and_items(db, issue.warehouse_id, issue.items)

        try:
            # Execute stock OUT via StockMovementService under current transaction
            await self.execution_service.execute_goods_issue(db, issue, current_user_id=current_user_id)

            now = datetime.now(timezone.utc)
            issue.status = target_status
            if not issue.approved_by:
                issue.approved_by = current_user_id
                issue.approved_at = now

            await db.commit()
            await db.refresh(issue)
        except Exception:
            await db.rollback()
            raise

        try:
            await redis_manager.delete_pattern("stock_balance:*")
            await redis_manager.delete_pattern("warehouse_summary:*")
            await redis_manager.delete_pattern("product_stock:*")
        except Exception:
            pass

        await audit_log_service.log_event(
            db,
            action="GOODS_ISSUE_POST",
            entity_type="GoodsIssue",
            entity_id=issue.id,
            user_id=current_user_id,
            new_data={"issue_number": issue.issue_number, "status": issue.status, "item_count": len(issue.items)},
        )

        try:
            send_warehouse_notification_task.delay(
                event_type="GOODS_ISSUE_POSTED",
                payload={"issue_id": str(issue.id), "number": issue.issue_number},
            )
        except Exception as e:
            logger.warning(f"Failed to dispatch warehouse notification task: {e}")

        return issue

    async def issue_issue(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> GoodsIssue:
        """
        Legacy/alias method that delegates to post_issue with Issued status.
        """
        return await self.post_issue(db, id, current_user_id=current_user_id, target_status="Issued")

    async def cancel_issue(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> GoodsIssue:
        issue = await goods_issue_repository.get_by_id(db, id)
        if not issue:
            raise NotFoundException(f"Goods issue with ID '{id}' not found.")
        if issue.status in ("Posted", "Issued", "Cancelled"):
            raise ValidationException(f"Cannot cancel goods issue in terminal status '{issue.status}'.")

        issue.status = "Cancelled"
        await db.commit()
        await db.refresh(issue)

        await audit_log_service.log_event(
            db,
            action="GOODS_ISSUE_CANCEL",
            entity_type="GoodsIssue",
            entity_id=issue.id,
            user_id=current_user_id,
        )
        return issue

    async def delete_issue(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> None:
        """
        Deletes a draft GoodsIssue. Prohibits deleting posted documents.
        """
        issue = await goods_issue_repository.get_by_id(db, id)
        if not issue:
            raise NotFoundException(f"Goods issue with ID '{id}' not found.")
        if issue.status != "Draft":
            raise ValidationException(f"Only Draft goods issues can be deleted. Current status: '{issue.status}'.")

        await goods_issue_repository.delete(db, id=id)
        await audit_log_service.log_event(
            db,
            action="GOODS_ISSUE_DELETE",
            entity_type="GoodsIssue",
            entity_id=id,
            user_id=current_user_id,
        )

    async def get_issues(
        self,
        db: AsyncSession,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        issue_reason: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[GoodsIssue], int]:
        return await goods_issue_repository.get_goods_issues_paginated(
            db, warehouse_id=warehouse_id, status=status, issue_reason=issue_reason, start_date=start_date, end_date=end_date, search_term=search, skip=skip, limit=limit
        )

    async def get_issue(self, db: AsyncSession, id: uuid.UUID) -> GoodsIssue:
        gi = await goods_issue_repository.get_by_id(db, id)
        if not gi:
            raise NotFoundException(f"Goods issue with ID '{id}' not found.")
        return gi


class StockTransferService:
    """
    Domain service for managing StockTransfer documents and posting workflows.
    """

    def __init__(self, execution_service: WarehouseExecutionService):
        self.execution_service = execution_service

    async def _validate_transfer_details(
        self, db: AsyncSession, source_wh_id: uuid.UUID, dest_wh_id: uuid.UUID, source_loc_id: Optional[uuid.UUID], dest_loc_id: Optional[uuid.UUID], items: List[Any]
    ) -> None:
        if not items:
            raise ValidationException("Stock transfer must have at least one line item.")

        if source_wh_id == dest_wh_id and source_loc_id == dest_loc_id:
            raise ValidationException("Source warehouse and location must not be identical to destination warehouse and location.")

        s_wh = await warehouse_repository.get_by_id(db, source_wh_id)
        if not s_wh or not s_wh.is_active:
            raise NotFoundException(f"Source warehouse with ID '{source_wh_id}' not found or inactive.")

        d_wh = await warehouse_repository.get_by_id(db, dest_wh_id)
        if not d_wh or not d_wh.is_active:
            raise NotFoundException(f"Destination warehouse with ID '{dest_wh_id}' not found or inactive.")

        if source_loc_id:
            s_loc = await storage_location_repository.get_by_id(db, source_loc_id)
            if not s_loc:
                raise NotFoundException(f"Source storage location with ID '{source_loc_id}' not found.")
            if hasattr(s_loc, "is_active") and not s_loc.is_active:
                raise ValidationException(f"Source storage location '{s_loc.code}' is inactive.")
            if s_loc.warehouse_id != source_wh_id:
                raise ValidationException("Source storage location does not belong to source warehouse.")

        if dest_loc_id:
            d_loc = await storage_location_repository.get_by_id(db, dest_loc_id)
            if not d_loc:
                raise NotFoundException(f"Destination storage location with ID '{dest_loc_id}' not found.")
            if hasattr(d_loc, "is_active") and not d_loc.is_active:
                raise ValidationException(f"Destination storage location '{d_loc.code}' is inactive.")
            if d_loc.warehouse_id != dest_wh_id:
                raise ValidationException("Destination storage location does not belong to destination warehouse.")

        for item in items:
            qty = Decimal(str(item.quantity))
            if qty <= Decimal("0.0"):
                raise ValidationException("Transfer line quantity must be strictly positive.")

            prod = await product_repository.get_by_id(db, item.product_id)
            if not prod:
                raise NotFoundException(f"Product with ID '{item.product_id}' not found.")
            if hasattr(prod, "is_active") and not prod.is_active:
                raise ValidationException(f"Product SKU '{prod.sku}' is inactive.")
            if prod.status == "Archived":
                raise ValidationException(f"Product SKU '{prod.sku}' is archived and read-only.")
            if hasattr(prod, "is_stockable") and not prod.is_stockable:
                raise ValidationException(f"Product SKU '{prod.sku}' is not configured as stockable inventory.")
            if hasattr(prod, "track_inventory") and not prod.track_inventory:
                raise ValidationException(f"Product SKU '{prod.sku}' does not track inventory.")

    async def create_transfer(
        self, db: AsyncSession, obj_in: StockTransferCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> StockTransfer:
        if await stock_transfer_repository.exists_by_number(db, obj_in.transfer_number):
            raise DuplicateResourceException(f"Stock transfer number '{obj_in.transfer_number}' already exists.")

        await self._validate_transfer_details(
            db, obj_in.source_warehouse_id, obj_in.destination_warehouse_id, obj_in.source_location_id, obj_in.destination_location_id, obj_in.items
        )

        remarks_val = obj_in.remarks or obj_in.notes
        transfer = StockTransfer(
            transfer_number=obj_in.transfer_number,
            source_warehouse_id=obj_in.source_warehouse_id,
            destination_warehouse_id=obj_in.destination_warehouse_id,
            source_location_id=obj_in.source_location_id,
            destination_location_id=obj_in.destination_location_id,
            transfer_date=obj_in.transfer_date or datetime.now(timezone.utc),
            status="Draft",
            remarks=remarks_val,
            created_by=current_user_id,
        )
        for item in obj_in.items:
            item_remarks = item.remarks or item.notes
            transfer.items.append(
                StockTransferItem(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_id=item.unit_id,
                    remarks=item_remarks,
                )
            )

        db.add(transfer)
        await db.commit()
        await db.refresh(transfer)

        await audit_log_service.log_event(
            db,
            action="STOCK_TRANSFER_CREATE",
            entity_type="StockTransfer",
            entity_id=transfer.id,
            user_id=current_user_id,
            new_data={"transfer_number": transfer.transfer_number, "source_wh": str(transfer.source_warehouse_id), "dest_wh": str(transfer.destination_warehouse_id)},
        )
        return transfer

    async def update_transfer(
        self, db: AsyncSession, id: uuid.UUID, obj_in: StockTransferUpdate, current_user_id: Optional[uuid.UUID] = None
    ) -> StockTransfer:
        transfer = await stock_transfer_repository.get_by_id(db, id)
        if not transfer:
            raise NotFoundException(f"Stock transfer with ID '{id}' not found.")
        if transfer.status != "Draft":
            raise ValidationException(f"Only Draft stock transfers can be modified. Current status: '{transfer.status}'.")

        if obj_in.source_location_id is not None:
            transfer.source_location_id = obj_in.source_location_id
        if obj_in.destination_location_id is not None:
            transfer.destination_location_id = obj_in.destination_location_id
        if obj_in.remarks is not None or obj_in.notes is not None:
            transfer.remarks = obj_in.remarks or obj_in.notes

        if obj_in.items is not None:
            await self._validate_transfer_details(
                db, transfer.source_warehouse_id, transfer.destination_warehouse_id, transfer.source_location_id, transfer.destination_location_id, obj_in.items
            )
            transfer.items.clear()
            for item in obj_in.items:
                transfer.items.append(
                    StockTransferItem(
                        product_id=item.product_id,
                        quantity=item.quantity,
                        unit_id=item.unit_id,
                        remarks=item.remarks or item.notes,
                    )
                )

        await db.commit()
        await db.refresh(transfer)

        await audit_log_service.log_event(
            db,
            action="STOCK_TRANSFER_UPDATE",
            entity_type="StockTransfer",
            entity_id=transfer.id,
            user_id=current_user_id,
        )
        return transfer

    async def approve_transfer(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> StockTransfer:
        transfer = await stock_transfer_repository.get_by_id(db, id)
        if not transfer:
            raise NotFoundException(f"Stock transfer with ID '{id}' not found.")
        if transfer.status != "Draft":
            raise ValidationException(f"Only Draft transfers can be approved. Current status: '{transfer.status}'.")

        transfer.status = "Approved"
        transfer.approved_by = current_user_id
        await db.commit()
        await db.refresh(transfer)

        await audit_log_service.log_event(
            db,
            action="STOCK_TRANSFER_APPROVE",
            entity_type="StockTransfer",
            entity_id=transfer.id,
            user_id=current_user_id,
        )
        return transfer

    async def post_transfer(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> StockTransfer:
        """
        Atomically posts a StockTransfer document:
        1. Validates document state and rules.
        2. Implements deterministic deadlock-free lock ordering across all balances.
        3. Executes Source STOCK_OUT and Destination STOCK_IN movements via StockMovementService.
        4. Updates document status to Posted.
        5. Commits all mutations atomically in a single PostgreSQL transaction.
        """
        transfer = await stock_transfer_repository.get_by_id(db, id)
        if not transfer:
            raise NotFoundException(f"Stock transfer with ID '{id}' not found.")
        if transfer.status in ("Posted", "Completed", "In Transit"):
            raise ValidationException(f"Stock transfer is already posted or in progress. Current status: '{transfer.status}'.")
        if transfer.status == "Cancelled":
            raise ValidationException(f"Cannot post stock transfer in terminal status '{transfer.status}'.")

        # Full re-validation of transfer details
        await self._validate_transfer_details(
            db, transfer.source_warehouse_id, transfer.destination_warehouse_id, transfer.source_location_id, transfer.destination_location_id, transfer.items
        )

        try:
            # Atomic transfer execution with deterministic lock acquisition
            await self.execution_service.execute_stock_transfer_atomic(db, transfer, current_user_id=current_user_id)

            now = datetime.now(timezone.utc)
            transfer.status = "Posted"
            if not transfer.approved_by:
                transfer.approved_by = current_user_id
            transfer.completed_by = current_user_id

            await db.commit()
            await db.refresh(transfer)
        except Exception:
            await db.rollback()
            raise

        try:
            await redis_manager.delete_pattern("stock_balance:*")
            await redis_manager.delete_pattern("warehouse_summary:*")
            await redis_manager.delete_pattern("product_stock:*")
        except Exception:
            pass

        await audit_log_service.log_event(
            db,
            action="STOCK_TRANSFER_POST",
            entity_type="StockTransfer",
            entity_id=transfer.id,
            user_id=current_user_id,
            new_data={"transfer_number": transfer.transfer_number, "status": transfer.status, "item_count": len(transfer.items)},
        )

        try:
            send_warehouse_notification_task.delay(
                event_type="STOCK_TRANSFER_POSTED",
                payload={"transfer_id": str(transfer.id), "number": transfer.transfer_number},
            )
        except Exception as e:
            logger.warning(f"Failed to dispatch warehouse notification task: {e}")

        return transfer

    async def dispatch_transfer(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> StockTransfer:
        """
        Dispatches a StockTransfer proposal (two-phase workflow), creating STOCK_OUT movements at source warehouse.
        """
        transfer = await stock_transfer_repository.get_by_id(db, id)
        if not transfer:
            raise NotFoundException(f"Stock transfer with ID '{id}' not found.")
        if transfer.status not in ("Draft", "Approved"):
            raise ValidationException(f"Stock transfer with status '{transfer.status}' cannot be dispatched.")

        await self._validate_transfer_details(
            db, transfer.source_warehouse_id, transfer.destination_warehouse_id, transfer.source_location_id, transfer.destination_location_id, transfer.items
        )

        # Execute dispatch (OUT from source WH)
        await self.execution_service.execute_stock_transfer_dispatch(db, transfer, current_user_id=current_user_id)

        transfer.status = "In Transit"
        if not transfer.approved_by:
            transfer.approved_by = current_user_id

        await db.commit()
        await db.refresh(transfer)

        try:
            await redis_manager.delete_pattern("stock_balance:*")
            await redis_manager.delete_pattern("warehouse_summary:*")
            await redis_manager.delete_pattern("product_stock:*")
        except Exception:
            pass

        await audit_log_service.log_event(
            db,
            action="STOCK_TRANSFER_DISPATCH",
            entity_type="StockTransfer",
            entity_id=transfer.id,
            user_id=current_user_id,
        )

        try:
            send_warehouse_notification_task.delay(
                event_type="STOCK_TRANSFER_DISPATCHED",
                payload={"transfer_id": str(transfer.id), "number": transfer.transfer_number},
            )
        except Exception as e:
            logger.warning(f"Failed to dispatch warehouse notification task: {e}")

        return transfer

    async def complete_transfer(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> StockTransfer:
        """
        Completes/receives an 'In Transit' StockTransfer (two-phase workflow), creating STOCK_IN movements at destination warehouse.
        """
        transfer = await stock_transfer_repository.get_by_id(db, id)
        if not transfer:
            raise NotFoundException(f"Stock transfer with ID '{id}' not found.")
        if transfer.status != "In Transit":
            raise ValidationException(f"Only 'In Transit' transfers can be completed/received. Current status: '{transfer.status}'.")

        # Execute receipt (IN at destination WH)
        await self.execution_service.execute_stock_transfer_receive(db, transfer, current_user_id=current_user_id)

        transfer.status = "Completed"
        transfer.completed_by = current_user_id

        await db.commit()
        await db.refresh(transfer)

        try:
            await redis_manager.delete_pattern("stock_balance:*")
            await redis_manager.delete_pattern("warehouse_summary:*")
            await redis_manager.delete_pattern("product_stock:*")
        except Exception:
            pass

        await audit_log_service.log_event(
            db,
            action="STOCK_TRANSFER_COMPLETE",
            entity_type="StockTransfer",
            entity_id=transfer.id,
            user_id=current_user_id,
        )

        try:
            send_warehouse_notification_task.delay(
                event_type="STOCK_TRANSFER_COMPLETED",
                payload={"transfer_id": str(transfer.id), "number": transfer.transfer_number},
            )
        except Exception as e:
            logger.warning(f"Failed to dispatch warehouse notification task: {e}")

        return transfer

    async def cancel_transfer(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> StockTransfer:
        transfer = await stock_transfer_repository.get_by_id(db, id)
        if not transfer:
            raise NotFoundException(f"Stock transfer with ID '{id}' not found.")
        if transfer.status in ("Posted", "Completed", "Cancelled"):
            raise ValidationException(f"Cannot cancel stock transfer in terminal status '{transfer.status}'.")

        transfer.status = "Cancelled"
        await db.commit()
        await db.refresh(transfer)

        await audit_log_service.log_event(
            db,
            action="STOCK_TRANSFER_CANCEL",
            entity_type="StockTransfer",
            entity_id=transfer.id,
            user_id=current_user_id,
        )
        return transfer

    async def delete_transfer(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> None:
        """
        Deletes a draft StockTransfer. Prohibits deleting posted or in-transit documents.
        """
        transfer = await stock_transfer_repository.get_by_id(db, id)
        if not transfer:
            raise NotFoundException(f"Stock transfer with ID '{id}' not found.")
        if transfer.status != "Draft":
            raise ValidationException(f"Only Draft stock transfers can be deleted. Current status: '{transfer.status}'.")

        await stock_transfer_repository.delete(db, id=id)
        await audit_log_service.log_event(
            db,
            action="STOCK_TRANSFER_DELETE",
            entity_type="StockTransfer",
            entity_id=id,
            user_id=current_user_id,
        )

    async def get_transfers(
        self,
        db: AsyncSession,
        source_warehouse_id: Optional[uuid.UUID] = None,
        destination_warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[StockTransfer], int]:
        return await stock_transfer_repository.get_stock_transfers_paginated(
            db, source_warehouse_id=source_warehouse_id, destination_warehouse_id=destination_warehouse_id, status=status, start_date=start_date, end_date=end_date, search_term=search, skip=skip, limit=limit
        )

    async def get_transfer(self, db: AsyncSession, id: uuid.UUID) -> StockTransfer:
        st = await stock_transfer_repository.get_by_id(db, id)
        if not st:
            raise NotFoundException(f"Stock transfer with ID '{id}' not found.")
        return st


# Singleton Services
warehouse_execution_service = WarehouseExecutionService()
goods_receipt_service = GoodsReceiptService(warehouse_execution_service)
goods_issue_service = GoodsIssueService(warehouse_execution_service)
stock_transfer_service = StockTransferService(warehouse_execution_service)
