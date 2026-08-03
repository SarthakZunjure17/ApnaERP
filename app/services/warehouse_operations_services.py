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
from app.services.stock_engine_services import stock_ledger_service
from app.tasks.warehouse_operations_tasks import send_warehouse_notification_task

logger = logging.getLogger("app.services.warehouse_operations")


class WarehouseExecutionService:
    """
    Orchestration service responsible for executing warehouse operations and generating
    immutable StockLedger entries via StockLedgerService.
    """
    async def execute_goods_receipt(
        self, db: AsyncSession, receipt: GoodsReceipt, current_user_id: Optional[uuid.UUID] = None
    ) -> None:
        """
        Executes a GoodsReceipt by creating IN ledger entries for each line item.
        """
        for item in receipt.items:
            await stock_ledger_service.create_ledger_entry(
                db,
                product_id=item.product_id,
                warehouse_id=receipt.warehouse_id,
                storage_location_id=item.storage_location_id,
                transaction_type_code="PURCHASE_RECEIPT",
                quantity=Decimal(str(item.quantity)),
                direction="IN",
                unit_id=item.unit_id,
                reference_type="GoodsReceipt",
                reference_id=receipt.id,
                remarks=f"Goods Receipt #{receipt.receipt_number}",
                current_user_id=current_user_id,
            )

    async def execute_goods_issue(
        self, db: AsyncSession, issue: GoodsIssue, current_user_id: Optional[uuid.UUID] = None
    ) -> None:
        """
        Executes a GoodsIssue by creating OUT ledger entries for each line item (validating negative stock rules).
        """
        transaction_type_code = "PRODUCTION_CONSUMPTION" if issue.issue_reason == "Consumption" else "SALES_ISSUE"
        for item in issue.items:
            await stock_ledger_service.create_ledger_entry(
                db,
                product_id=item.product_id,
                warehouse_id=issue.warehouse_id,
                storage_location_id=item.storage_location_id,
                transaction_type_code=transaction_type_code,
                quantity=Decimal(str(item.quantity)),
                direction="OUT",
                unit_id=item.unit_id,
                reference_type="GoodsIssue",
                reference_id=issue.id,
                remarks=f"Goods Issue #{issue.issue_number} ({issue.issue_reason})",
                current_user_id=current_user_id,
            )

    async def execute_stock_transfer_dispatch(
        self, db: AsyncSession, transfer: StockTransfer, current_user_id: Optional[uuid.UUID] = None
    ) -> None:
        """
        Executes Stock Transfer Dispatch by creating TRANSFER_OUT ledger entries from source warehouse.
        """
        for item in transfer.items:
            await stock_ledger_service.create_ledger_entry(
                db,
                product_id=item.product_id,
                warehouse_id=transfer.source_warehouse_id,
                storage_location_id=transfer.source_location_id,
                transaction_type_code="TRANSFER_OUT",
                quantity=Decimal(str(item.quantity)),
                direction="OUT",
                unit_id=item.unit_id,
                reference_type="StockTransfer",
                reference_id=transfer.id,
                remarks=f"Stock Transfer Dispatch #{transfer.transfer_number} (Out of source WH)",
                current_user_id=current_user_id,
            )

    async def execute_stock_transfer_receive(
        self, db: AsyncSession, transfer: StockTransfer, current_user_id: Optional[uuid.UUID] = None
    ) -> None:
        """
        Executes Stock Transfer Completion/Receipt by creating TRANSFER_IN ledger entries at destination warehouse.
        """
        for item in transfer.items:
            await stock_ledger_service.create_ledger_entry(
                db,
                product_id=item.product_id,
                warehouse_id=transfer.destination_warehouse_id,
                storage_location_id=transfer.destination_location_id,
                transaction_type_code="TRANSFER_IN",
                quantity=Decimal(str(item.quantity)),
                direction="IN",
                unit_id=item.unit_id,
                reference_type="StockTransfer",
                reference_id=transfer.id,
                remarks=f"Stock Transfer Completion #{transfer.transfer_number} (Into dest WH)",
                current_user_id=current_user_id,
            )


class GoodsReceiptService:
    """
    Domain service for managing GoodsReceipt documents.
    """
    def __init__(self, execution_service: WarehouseExecutionService):
        self.execution_service = execution_service

    async def _validate_warehouse_and_items(
        self, db: AsyncSession, warehouse_id: uuid.UUID, items: List[Any]
    ) -> None:
        wh = await warehouse_repository.get_by_id(db, warehouse_id)
        if not wh or not wh.is_active:
            raise NotFoundException(f"Warehouse with ID '{warehouse_id}' not found or inactive.")

        for item in items:
            prod = await product_repository.get_by_id(db, item.product_id)
            if not prod:
                raise NotFoundException(f"Product with ID '{item.product_id}' not found.")
            if not prod.track_inventory:
                raise ValidationException(f"Product SKU '{prod.sku}' is not configured for inventory tracking.")
            if prod.status == "Archived":
                raise ValidationException(f"Product SKU '{prod.sku}' is archived and read-only.")

            if item.storage_location_id:
                loc = await storage_location_repository.get_by_id(db, item.storage_location_id)
                if not loc:
                    raise NotFoundException(f"Storage location with ID '{item.storage_location_id}' not found.")
                if loc.warehouse_id != warehouse_id:
                    raise ValidationException("Storage location does not belong to the target warehouse.")

    async def create_receipt(
        self, db: AsyncSession, obj_in: GoodsReceiptCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> GoodsReceipt:
        if await goods_receipt_repository.exists_by_number(db, obj_in.receipt_number):
            raise DuplicateResourceException(f"Goods receipt number '{obj_in.receipt_number}' already exists.")

        await self._validate_warehouse_and_items(db, obj_in.warehouse_id, obj_in.items)

        receipt = GoodsReceipt(
            receipt_number=obj_in.receipt_number,
            warehouse_id=obj_in.warehouse_id,
            supplier_reference=obj_in.supplier_reference,
            external_reference=obj_in.external_reference,
            receipt_date=obj_in.receipt_date or datetime.now(timezone.utc),
            status="Draft",
            remarks=obj_in.remarks,
            created_by=current_user_id,
        )
        for item in obj_in.items:
            receipt.items.append(
                GoodsReceiptItem(
                    product_id=item.product_id,
                    storage_location_id=item.storage_location_id,
                    quantity=item.quantity,
                    unit_id=item.unit_id,
                    unit_cost=item.unit_cost,
                    remarks=item.remarks,
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
        if obj_in.remarks is not None:
            receipt.remarks = obj_in.remarks

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
                        remarks=item.remarks,
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

    async def receive_receipt(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> GoodsReceipt:
        """
        Executes and receives a GoodsReceipt document, generating immutable StockLedger IN entries.
        """
        receipt = await goods_receipt_repository.get_by_id(db, id)
        if not receipt:
            raise NotFoundException(f"Goods receipt with ID '{id}' not found.")
        if receipt.status not in ("Draft", "Approved"):
            raise ValidationException(f"Goods receipt with status '{receipt.status}' cannot be received.")

        # Execute stock ledger generation
        await self.execution_service.execute_goods_receipt(db, receipt, current_user_id=current_user_id)

        receipt.status = "Received"
        if not receipt.approved_by:
            receipt.approved_by = current_user_id
            receipt.approved_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(receipt)

        await audit_log_service.log_event(
            db,
            action="GOODS_RECEIPT_RECEIVE",
            entity_type="GoodsReceipt",
            entity_id=receipt.id,
            user_id=current_user_id,
        )

        try:
            send_warehouse_notification_task.delay(
                event_type="GOODS_RECEIPT_RECEIVED",
                payload={"receipt_id": str(receipt.id), "number": receipt.receipt_number},
            )
        except Exception as e:
            logger.warning(f"Failed to dispatch warehouse notification task: {e}")

        return receipt

    async def cancel_receipt(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> GoodsReceipt:
        receipt = await goods_receipt_repository.get_by_id(db, id)
        if not receipt:
            raise NotFoundException(f"Goods receipt with ID '{id}' not found.")
        if receipt.status in ("Received", "Cancelled"):
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
    Domain service for managing GoodsIssue documents.
    """
    def __init__(self, execution_service: WarehouseExecutionService):
        self.execution_service = execution_service

    async def _validate_warehouse_and_items(
        self, db: AsyncSession, warehouse_id: uuid.UUID, items: List[Any]
    ) -> None:
        wh = await warehouse_repository.get_by_id(db, warehouse_id)
        if not wh or not wh.is_active:
            raise NotFoundException(f"Warehouse with ID '{warehouse_id}' not found or inactive.")

        for item in items:
            prod = await product_repository.get_by_id(db, item.product_id)
            if not prod:
                raise NotFoundException(f"Product with ID '{item.product_id}' not found.")
            if not prod.track_inventory:
                raise ValidationException(f"Product SKU '{prod.sku}' is not configured for inventory tracking.")
            if prod.status == "Archived":
                raise ValidationException(f"Product SKU '{prod.sku}' is archived and read-only.")

            if item.storage_location_id:
                loc = await storage_location_repository.get_by_id(db, item.storage_location_id)
                if not loc:
                    raise NotFoundException(f"Storage location with ID '{item.storage_location_id}' not found.")
                if loc.warehouse_id != warehouse_id:
                    raise ValidationException("Storage location does not belong to the target warehouse.")

    async def create_issue(
        self, db: AsyncSession, obj_in: GoodsIssueCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> GoodsIssue:
        if await goods_issue_repository.exists_by_number(db, obj_in.issue_number):
            raise DuplicateResourceException(f"Goods issue number '{obj_in.issue_number}' already exists.")

        await self._validate_warehouse_and_items(db, obj_in.warehouse_id, obj_in.items)

        issue = GoodsIssue(
            issue_number=obj_in.issue_number,
            warehouse_id=obj_in.warehouse_id,
            issue_date=obj_in.issue_date or datetime.now(timezone.utc),
            issue_reason=obj_in.issue_reason,
            status="Draft",
            remarks=obj_in.remarks,
            created_by=current_user_id,
        )
        for item in obj_in.items:
            issue.items.append(
                GoodsIssueItem(
                    product_id=item.product_id,
                    storage_location_id=item.storage_location_id,
                    quantity=item.quantity,
                    unit_id=item.unit_id,
                    remarks=item.remarks,
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
        if obj_in.remarks is not None:
            issue.remarks = obj_in.remarks

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
                        remarks=item.remarks,
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

    async def issue_issue(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> GoodsIssue:
        """
        Executes and issues a GoodsIssue document, validating negative stock rules and generating StockLedger OUT entries.
        """
        issue = await goods_issue_repository.get_by_id(db, id)
        if not issue:
            raise NotFoundException(f"Goods issue with ID '{id}' not found.")
        if issue.status not in ("Draft", "Approved"):
            raise ValidationException(f"Goods issue with status '{issue.status}' cannot be issued.")

        # Execute stock ledger generation with negative stock checks
        await self.execution_service.execute_goods_issue(db, issue, current_user_id=current_user_id)

        issue.status = "Issued"
        if not issue.approved_by:
            issue.approved_by = current_user_id
            issue.approved_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(issue)

        await audit_log_service.log_event(
            db,
            action="GOODS_ISSUE_EXECUTE",
            entity_type="GoodsIssue",
            entity_id=issue.id,
            user_id=current_user_id,
        )

        try:
            send_warehouse_notification_task.delay(
                event_type="GOODS_ISSUE_ISSUED",
                payload={"issue_id": str(issue.id), "number": issue.issue_number},
            )
        except Exception as e:
            logger.warning(f"Failed to dispatch warehouse notification task: {e}")

        return issue

    async def cancel_issue(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> GoodsIssue:
        issue = await goods_issue_repository.get_by_id(db, id)
        if not issue:
            raise NotFoundException(f"Goods issue with ID '{id}' not found.")
        if issue.status in ("Issued", "Cancelled"):
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
    Domain service for managing StockTransfer documents across warehouses and locations.
    """
    def __init__(self, execution_service: WarehouseExecutionService):
        self.execution_service = execution_service

    async def _validate_transfer_details(
        self, db: AsyncSession, source_wh_id: uuid.UUID, dest_wh_id: uuid.UUID, source_loc_id: Optional[uuid.UUID], dest_loc_id: Optional[uuid.UUID], items: List[Any]
    ) -> None:
        if source_wh_id == dest_wh_id and (source_loc_id is None or source_loc_id == dest_loc_id):
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
            if s_loc.warehouse_id != source_wh_id:
                raise ValidationException("Source storage location does not belong to source warehouse.")

        if dest_loc_id:
            d_loc = await storage_location_repository.get_by_id(db, dest_loc_id)
            if not d_loc:
                raise NotFoundException(f"Destination storage location with ID '{dest_loc_id}' not found.")
            if d_loc.warehouse_id != dest_wh_id:
                raise ValidationException("Destination storage location does not belong to destination warehouse.")

        for item in items:
            prod = await product_repository.get_by_id(db, item.product_id)
            if not prod:
                raise NotFoundException(f"Product with ID '{item.product_id}' not found.")
            if not prod.track_inventory:
                raise ValidationException(f"Product SKU '{prod.sku}' is not configured for inventory tracking.")
            if prod.status == "Archived":
                raise ValidationException(f"Product SKU '{prod.sku}' is archived and read-only.")

    async def create_transfer(
        self, db: AsyncSession, obj_in: StockTransferCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> StockTransfer:
        if await stock_transfer_repository.exists_by_number(db, obj_in.transfer_number):
            raise DuplicateResourceException(f"Stock transfer number '{obj_in.transfer_number}' already exists.")

        await self._validate_transfer_details(
            db, obj_in.source_warehouse_id, obj_in.destination_warehouse_id, obj_in.source_location_id, obj_in.destination_location_id, obj_in.items
        )

        transfer = StockTransfer(
            transfer_number=obj_in.transfer_number,
            source_warehouse_id=obj_in.source_warehouse_id,
            destination_warehouse_id=obj_in.destination_warehouse_id,
            source_location_id=obj_in.source_location_id,
            destination_location_id=obj_in.destination_location_id,
            transfer_date=obj_in.transfer_date or datetime.now(timezone.utc),
            status="Draft",
            remarks=obj_in.remarks,
            created_by=current_user_id,
        )
        for item in obj_in.items:
            transfer.items.append(
                StockTransferItem(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_id=item.unit_id,
                    remarks=item.remarks,
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
        if obj_in.remarks is not None:
            transfer.remarks = obj_in.remarks

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
                        remarks=item.remarks,
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

    async def dispatch_transfer(
        self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> StockTransfer:
        """
        Dispatches a StockTransfer proposal, creating TRANSFER_OUT stock ledger entries at source warehouse.
        """
        transfer = await stock_transfer_repository.get_by_id(db, id)
        if not transfer:
            raise NotFoundException(f"Stock transfer with ID '{id}' not found.")
        if transfer.status not in ("Draft", "Approved"):
            raise ValidationException(f"Stock transfer with status '{transfer.status}' cannot be dispatched.")

        # Execute dispatch (OUT from source WH)
        await self.execution_service.execute_stock_transfer_dispatch(db, transfer, current_user_id=current_user_id)

        transfer.status = "In Transit"
        if not transfer.approved_by:
            transfer.approved_by = current_user_id

        await db.commit()
        await db.refresh(transfer)

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
        Completes/receives an 'In Transit' StockTransfer, creating TRANSFER_IN stock ledger entries at destination warehouse.
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
        if transfer.status in ("Completed", "Cancelled"):
            raise ValidationException(f"Cannot cancel stock transfer in terminal status '{transfer.status}'.")

        # Note: If cancelled while In Transit, in a production system an offsetting reversal would be created.
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
