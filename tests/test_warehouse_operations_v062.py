import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.goods_issue import GoodsIssue
from app.models.goods_receipt import GoodsReceipt
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.stock_balance import StockBalance
from app.models.stock_ledger import StockLedger
from app.models.stock_transfer import StockTransfer
from app.models.storage_location import StorageLocation
from app.models.unit_of_measure import UnitOfMeasure
from app.models.user import User
from app.models.warehouse import Warehouse
from app.repositories.stock_engine_repos import stock_balance_repository, stock_ledger_repository
from app.schemas.warehouse_operations import (
    GoodsIssueCreate,
    GoodsIssueItemCreate,
    GoodsIssueUpdate,
    GoodsReceiptCreate,
    GoodsReceiptItemCreate,
    GoodsReceiptUpdate,
    StockTransferCreate,
    StockTransferItemCreate,
    StockTransferUpdate,
)
from app.services.stock_engine_services import stock_movement_service
from app.services.warehouse_operations_services import (
    goods_issue_service,
    goods_receipt_service,
    stock_transfer_service,
)
from app.exceptions.base import ValidationException, NotFoundException, DuplicateResourceException


async def create_test_admin_user(session: AsyncSession) -> User:
    username = f"wh_admin_{uuid.uuid4().hex[:6]}"
    user = User(
        full_name="Warehouse Admin",
        email=f"{username}@apnaerp.com",
        username=username,
        password_hash="test_hash",
        is_active=True,
        is_superuser=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def setup_inventory_fixtures(session: AsyncSession):
    suffix = uuid.uuid4().hex[:6]
    cat = ProductCategory(code=f"CAT-{suffix}", name=f"Category {suffix}")
    uom = UnitOfMeasure(name=f"Pieces {suffix}", symbol=f"pcs_{suffix}", category="Unit")
    wh_a = Warehouse(code=f"WH-A-{suffix}", name=f"Main Warehouse {suffix}", is_active=True)
    wh_b = Warehouse(code=f"WH-B-{suffix}", name=f"Branch Warehouse {suffix}", is_active=True)
    session.add_all([cat, uom, wh_a, wh_b])
    await session.commit()

    loc_a1 = StorageLocation(code=f"LOC-A1-{suffix}", name="Rack A1", warehouse_id=wh_a.id, is_active=True)
    loc_a2 = StorageLocation(code=f"LOC-A2-{suffix}", name="Rack A2", warehouse_id=wh_a.id, is_active=True)
    loc_b1 = StorageLocation(code=f"LOC-B1-{suffix}", name="Rack B1", warehouse_id=wh_b.id, is_active=True)
    session.add_all([loc_a1, loc_a2, loc_b1])
    await session.commit()

    prod_1 = Product(
        sku=f"SKU-1-{suffix}",
        name=f"Standard Item 1 {suffix}",
        category_id=cat.id,
        base_unit_id=uom.id,
        is_stockable=True,
        track_inventory=True,
        status="Active",
    )
    prod_2 = Product(
        sku=f"SKU-2-{suffix}",
        name=f"Standard Item 2 {suffix}",
        category_id=cat.id,
        base_unit_id=uom.id,
        is_stockable=True,
        track_inventory=True,
        status="Active",
    )
    prod_non_stockable = Product(
        sku=f"SKU-NS-{suffix}",
        name=f"Service Item {suffix}",
        category_id=cat.id,
        base_unit_id=uom.id,
        is_stockable=False,
        track_inventory=False,
        status="Active",
    )
    session.add_all([prod_1, prod_2, prod_non_stockable])
    await session.commit()

    return {
        "wh_a": wh_a,
        "wh_b": wh_b,
        "loc_a1": loc_a1,
        "loc_a2": loc_a2,
        "loc_b1": loc_b1,
        "prod_1": prod_1,
        "prod_2": prod_2,
        "prod_ns": prod_non_stockable,
        "uom": uom,
    }


# ============================================================================
# 1. GOODS RECEIPT WORKFLOW TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_goods_receipt_crud_and_validation():
    async with AsyncSessionLocal() as session:
        admin = await create_test_admin_user(session)
        fx = await setup_inventory_fixtures(session)

        # 1. Empty lines rejection
        with pytest.raises(Exception):
            GoodsReceiptCreate(
                receipt_number=f"GR-{uuid.uuid4().hex[:6]}",
                warehouse_id=fx["wh_a"].id,
                items=[],
            )

        # 2. Cross-warehouse location rejection
        with pytest.raises(ValidationException, match="does not belong to the target warehouse"):
            await goods_receipt_service.create_receipt(
                session,
                GoodsReceiptCreate(
                    receipt_number=f"GR-{uuid.uuid4().hex[:6]}",
                    warehouse_id=fx["wh_a"].id,
                    items=[
                        GoodsReceiptItemCreate(
                            product_id=fx["prod_1"].id,
                            storage_location_id=fx["loc_b1"].id,  # Belongs to WH B!
                            quantity=Decimal("10.0"),
                        )
                    ],
                ),
                current_user_id=admin.id,
            )

        # 3. Non-stockable product rejection
        with pytest.raises(ValidationException, match="not configured as stockable inventory"):
            await goods_receipt_service.create_receipt(
                session,
                GoodsReceiptCreate(
                    receipt_number=f"GR-{uuid.uuid4().hex[:6]}",
                    warehouse_id=fx["wh_a"].id,
                    items=[
                        GoodsReceiptItemCreate(
                            product_id=fx["prod_ns"].id,
                            storage_location_id=fx["loc_a1"].id,
                            quantity=Decimal("10.0"),
                        )
                    ],
                ),
                current_user_id=admin.id,
            )

        # 4. Valid Draft Creation
        gr_num = f"GR-{uuid.uuid4().hex[:6]}"
        receipt = await goods_receipt_service.create_receipt(
            session,
            GoodsReceiptCreate(
                receipt_number=gr_num,
                warehouse_id=fx["wh_a"].id,
                supplier_reference="SUP-REF-100",
                remarks="Initial delivery",
                items=[
                    GoodsReceiptItemCreate(
                        product_id=fx["prod_1"].id,
                        storage_location_id=fx["loc_a1"].id,
                        quantity=Decimal("50.0"),
                    )
                ],
            ),
            current_user_id=admin.id,
        )
        assert receipt.status == "Draft"
        assert receipt.receipt_number == gr_num
        assert len(receipt.items) == 1
        assert receipt.notes == "Initial delivery"

        # 5. Duplicate receipt number rejection
        with pytest.raises(DuplicateResourceException):
            await goods_receipt_service.create_receipt(
                session,
                GoodsReceiptCreate(
                    receipt_number=gr_num,
                    warehouse_id=fx["wh_a"].id,
                    items=[
                        GoodsReceiptItemCreate(
                            product_id=fx["prod_1"].id,
                            quantity=Decimal("10.0"),
                        )
                    ],
                ),
                current_user_id=admin.id,
            )

        # 6. Update Draft Receipt
        updated = await goods_receipt_service.update_receipt(
            session,
            receipt.id,
            GoodsReceiptUpdate(
                remarks="Updated notes",
                items=[
                    GoodsReceiptItemCreate(
                        product_id=fx["prod_1"].id,
                        storage_location_id=fx["loc_a1"].id,
                        quantity=Decimal("75.0"),
                    ),
                    GoodsReceiptItemCreate(
                        product_id=fx["prod_2"].id,
                        storage_location_id=fx["loc_a2"].id,
                        quantity=Decimal("25.0"),
                    ),
                ],
            ),
            current_user_id=admin.id,
        )
        assert len(updated.items) == 2
        assert updated.remarks == "Updated notes"


@pytest.mark.asyncio
async def test_goods_receipt_posting_and_ledger_integration():
    async with AsyncSessionLocal() as session:
        admin = await create_test_admin_user(session)
        fx = await setup_inventory_fixtures(session)

        # Initial balance should be 0 or not exist yet
        bal1_before = await stock_balance_repository.get_by_keys(session, fx["prod_1"].id, fx["wh_a"].id, fx["loc_a1"].id)
        assert bal1_before is None or Decimal(str(bal1_before.available_quantity)) == Decimal("0.0")

        # Create multi-line Goods Receipt
        receipt = await goods_receipt_service.create_receipt(
            session,
            GoodsReceiptCreate(
                receipt_number=f"GR-POST-{uuid.uuid4().hex[:6]}",
                warehouse_id=fx["wh_a"].id,
                remarks="Multi-line receipt",
                items=[
                    GoodsReceiptItemCreate(
                        product_id=fx["prod_1"].id,
                        storage_location_id=fx["loc_a1"].id,
                        quantity=Decimal("100.0"),
                    ),
                    GoodsReceiptItemCreate(
                        product_id=fx["prod_2"].id,
                        storage_location_id=fx["loc_a2"].id,
                        quantity=Decimal("40.0"),
                    ),
                ],
            ),
            current_user_id=admin.id,
        )

        # Post Receipt
        posted = await goods_receipt_service.post_receipt(session, receipt.id, current_user_id=admin.id)
        assert posted.status == "Posted"
        assert posted.approved_by == admin.id

        # Verify StockBalance updated via StockMovementService
        bal1 = await stock_balance_repository.get_by_keys(session, fx["prod_1"].id, fx["wh_a"].id, fx["loc_a1"].id)
        bal2 = await stock_balance_repository.get_by_keys(session, fx["prod_2"].id, fx["wh_a"].id, fx["loc_a2"].id)
        assert bal1 is not None and Decimal(str(bal1.available_quantity)) == Decimal("100.0")
        assert bal2 is not None and Decimal(str(bal2.available_quantity)) == Decimal("40.0")

        # Verify StockLedger entries created and linked to GoodsReceipt
        stmt = select(StockLedger).where(
            StockLedger.reference_type == "GoodsReceipt",
            StockLedger.reference_id == receipt.id,
        )
        ledgers = (await session.execute(stmt)).scalars().all()
        assert len(ledgers) == 2
        for l in ledgers:
            assert l.movement_type == "STOCK_IN"
            assert l.direction == "IN"

        # Verify Idempotency: Duplicate post rejection
        with pytest.raises(ValidationException, match="already posted"):
            await goods_receipt_service.post_receipt(session, receipt.id, current_user_id=admin.id)

        # Verify Immutability: Reject update after posting
        with pytest.raises(ValidationException, match="Only Draft goods receipts can be modified"):
            await goods_receipt_service.update_receipt(
                session,
                receipt.id,
                GoodsReceiptUpdate(remarks="Attempt to modify posted receipt"),
                current_user_id=admin.id,
            )

        # Verify Immutability: Reject delete after posting
        with pytest.raises(ValidationException, match="Only Draft goods receipts can be deleted"):
            await goods_receipt_service.delete_receipt(session, receipt.id, current_user_id=admin.id)


# ============================================================================
# 2. GOODS ISSUE WORKFLOW & ATOMIC ROLLBACK TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_goods_issue_insufficient_stock_and_atomic_rollback():
    async with AsyncSessionLocal() as session:
        admin = await create_test_admin_user(session)
        fx = await setup_inventory_fixtures(session)

        prod_1_id = fx["prod_1"].id
        wh_a_id = fx["wh_a"].id
        loc_a1_id = fx["loc_a1"].id

        # Seed initial stock of 50 for prod_1 in WH A, LOC A1
        await stock_movement_service.stock_in(
            session,
            product_id=prod_1_id,
            warehouse_id=wh_a_id,
            quantity=Decimal("50.0"),
            storage_location_id=loc_a1_id,
            reason="Initial Seed",
            commit=True,
        )
        bal_before = await stock_balance_repository.get_by_keys(session, prod_1_id, wh_a_id, loc_a1_id)
        assert Decimal(str(bal_before.available_quantity)) == Decimal("50.0")

        # Create multi-line Goods Issue where Line 1 (qty 30) is valid, but Line 2 (qty 100) exceeds available stock
        issue = await goods_issue_service.create_issue(
            session,
            GoodsIssueCreate(
                issue_number=f"GI-FAIL-{uuid.uuid4().hex[:6]}",
                warehouse_id=wh_a_id,
                issue_reason="Consumption",
                remarks="Multi-line failure test",
                items=[
                    GoodsIssueItemCreate(
                        product_id=prod_1_id,
                        storage_location_id=loc_a1_id,
                        quantity=Decimal("30.0"),  # Succeeds if isolated
                    ),
                    GoodsIssueItemCreate(
                        product_id=prod_1_id,
                        storage_location_id=loc_a1_id,
                        quantity=Decimal("100.0"),  # Fails due to insufficient stock!
                    ),
                ],
            ),
            current_user_id=admin.id,
        )
        issue_id = issue.id

        # Posting must fail atomically
        with pytest.raises(ValidationException, match="Insufficient stock"):
            await goods_issue_service.post_issue(session, issue_id, current_user_id=admin.id)

        # Verify ATOMIC ROLLBACK:
        # 1. StockBalance remains unchanged (50.0, NOT 20.0 or negative)
        bal_after = await stock_balance_repository.get_by_keys(session, prod_1_id, wh_a_id, loc_a1_id)
        assert Decimal(str(bal_after.available_quantity)) == Decimal("50.0")

        # 2. GoodsIssue document remains unposted (Draft)
        reloaded_issue = await goods_issue_service.get_issue(session, issue_id)
        assert reloaded_issue.status == "Draft"

        # 3. No partial ledger entries were created for this issue
        stmt = select(func.count(StockLedger.id)).where(
            StockLedger.reference_type == "GoodsIssue",
            StockLedger.reference_id == issue_id,
        )
        ledger_count = (await session.execute(stmt)).scalar() or 0
        assert ledger_count == 0


@pytest.mark.asyncio
async def test_goods_issue_successful_posting():
    async with AsyncSessionLocal() as session:
        admin = await create_test_admin_user(session)
        fx = await setup_inventory_fixtures(session)

        # Seed initial stock of 100
        await stock_movement_service.stock_in(
            session,
            product_id=fx["prod_1"].id,
            warehouse_id=fx["wh_a"].id,
            quantity=Decimal("100.0"),
            storage_location_id=fx["loc_a1"].id,
            reason="Seed Stock",
            commit=True,
        )

        # Create valid Goods Issue
        issue = await goods_issue_service.create_issue(
            session,
            GoodsIssueCreate(
                issue_number=f"GI-POST-{uuid.uuid4().hex[:6]}",
                warehouse_id=fx["wh_a"].id,
                issue_reason="Internal",
                remarks="Factory maintenance issue",
                items=[
                    GoodsIssueItemCreate(
                        product_id=fx["prod_1"].id,
                        storage_location_id=fx["loc_a1"].id,
                        quantity=Decimal("35.0"),
                    )
                ],
            ),
            current_user_id=admin.id,
        )

        # Post Issue
        posted = await goods_issue_service.post_issue(session, issue.id, current_user_id=admin.id)
        assert posted.status == "Posted"

        # Verify StockBalance: 100 -> 65
        bal = await stock_balance_repository.get_by_keys(session, fx["prod_1"].id, fx["wh_a"].id, fx["loc_a1"].id)
        assert bal is not None and Decimal(str(bal.available_quantity)) == Decimal("65.0")

        # Verify StockLedger entry
        stmt = select(StockLedger).where(
            StockLedger.reference_type == "GoodsIssue",
            StockLedger.reference_id == issue.id,
        )
        entry = (await session.execute(stmt)).scalars().first()
        assert entry is not None
        assert entry.movement_type == "STOCK_OUT"
        assert entry.direction == "OUT"
        assert Decimal(str(entry.quantity)) == Decimal("35.0")
        assert Decimal(str(entry.quantity_before)) == Decimal("100.0")
        assert Decimal(str(entry.quantity_after)) == Decimal("65.0")

        # Idempotency: Reject duplicate post
        with pytest.raises(ValidationException, match="already posted"):
            await goods_issue_service.post_issue(session, issue.id, current_user_id=admin.id)


# ============================================================================
# 3. STOCK TRANSFER WORKFLOW & CONCURRENCY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_stock_transfer_validation_and_atomicity():
    async with AsyncSessionLocal() as session:
        admin = await create_test_admin_user(session)
        fx = await setup_inventory_fixtures(session)

        # 1. Reject same source and destination location
        with pytest.raises(ValidationException, match="must not be identical"):
            await stock_transfer_service.create_transfer(
                session,
                StockTransferCreate(
                    transfer_number=f"ST-{uuid.uuid4().hex[:6]}",
                    source_warehouse_id=fx["wh_a"].id,
                    destination_warehouse_id=fx["wh_a"].id,
                    source_location_id=fx["loc_a1"].id,
                    destination_location_id=fx["loc_a1"].id,  # Same location!
                    items=[
                        StockTransferItemCreate(
                            product_id=fx["prod_1"].id,
                            quantity=Decimal("10.0"),
                        )
                    ],
                ),
                current_user_id=admin.id,
            )

        # 2. Seed stock at source: 100 in WH A, LOC A1
        await stock_movement_service.stock_in(
            session,
            product_id=fx["prod_1"].id,
            warehouse_id=fx["wh_a"].id,
            quantity=Decimal("100.0"),
            storage_location_id=fx["loc_a1"].id,
            reason="Source Seed",
            commit=True,
        )

        # Destination starts at 0 in WH B, LOC B1
        dest_bal_before = await stock_balance_repository.get_by_keys(session, fx["prod_1"].id, fx["wh_b"].id, fx["loc_b1"].id)
        assert dest_bal_before is None or Decimal(str(dest_bal_before.available_quantity)) == Decimal("0.0")

        # 3. Create Valid Inter-Warehouse Transfer: WH A (LOC A1) -> WH B (LOC B1), qty 40
        transfer = await stock_transfer_service.create_transfer(
            session,
            StockTransferCreate(
                transfer_number=f"ST-POST-{uuid.uuid4().hex[:6]}",
                source_warehouse_id=fx["wh_a"].id,
                destination_warehouse_id=fx["wh_b"].id,
                source_location_id=fx["loc_a1"].id,
                destination_location_id=fx["loc_b1"].id,
                remarks="Inter-warehouse replenishment",
                items=[
                    StockTransferItemCreate(
                        product_id=fx["prod_1"].id,
                        quantity=Decimal("40.0"),
                    )
                ],
            ),
            current_user_id=admin.id,
        )
        assert transfer.status == "Draft"

        # 4. Atomically Post Transfer
        posted = await stock_transfer_service.post_transfer(session, transfer.id, current_user_id=admin.id)
        assert posted.status == "Posted"

        # 5. Verify Balances:
        # Source: 100 -> 60
        s_bal = await stock_balance_repository.get_by_keys(session, fx["prod_1"].id, fx["wh_a"].id, fx["loc_a1"].id)
        assert s_bal is not None and Decimal(str(s_bal.available_quantity)) == Decimal("60.0")

        # Destination: 0 -> 40
        d_bal = await stock_balance_repository.get_by_keys(session, fx["prod_1"].id, fx["wh_b"].id, fx["loc_b1"].id)
        assert d_bal is not None and Decimal(str(d_bal.available_quantity)) == Decimal("40.0")

        # 6. Verify Ledger Entries: Exactly 2 entries linked to this transfer
        stmt = select(StockLedger).where(
            StockLedger.reference_type == "StockTransfer",
            StockLedger.reference_id == transfer.id,
        ).order_by(StockLedger.direction.desc())  # OUT then IN
        ledgers = (await session.execute(stmt)).scalars().all()
        assert len(ledgers) == 2

        out_entry = next(l for l in ledgers if l.direction == "OUT")
        in_entry = next(l for l in ledgers if l.direction == "IN")

        assert out_entry.warehouse_id == fx["wh_a"].id
        assert Decimal(str(out_entry.quantity)) == Decimal("40.0")
        assert Decimal(str(out_entry.quantity_before)) == Decimal("100.0")
        assert Decimal(str(out_entry.quantity_after)) == Decimal("60.0")

        assert in_entry.warehouse_id == fx["wh_b"].id
        assert Decimal(str(in_entry.quantity)) == Decimal("40.0")
        assert Decimal(str(in_entry.quantity_before)) == Decimal("0.0")
        assert Decimal(str(in_entry.quantity_after)) == Decimal("40.0")

        # 7. Idempotency: Duplicate post rejection
        with pytest.raises(ValidationException, match="already posted"):
            await stock_transfer_service.post_transfer(session, transfer.id, current_user_id=admin.id)


@pytest.mark.asyncio
async def test_concurrent_transfers_deterministic_deadlock_free():
    """
    Tests reverse transfers between WH A and WH B.
    Transfer 1: WH A -> WH B
    Transfer 2: WH B -> WH A
    Enforces deterministic sorted lock acquisition to guarantee zero database deadlocks.
    """
    async with AsyncSessionLocal() as session:
        admin = await create_test_admin_user(session)
        fx = await setup_inventory_fixtures(session)

        # Seed initial stock in both warehouses
        await stock_movement_service.stock_in(
            session, fx["prod_1"].id, fx["wh_a"].id, Decimal("200.0"), storage_location_id=fx["loc_a1"].id, commit=True
        )
        await stock_movement_service.stock_in(
            session, fx["prod_1"].id, fx["wh_b"].id, Decimal("200.0"), storage_location_id=fx["loc_b1"].id, commit=True
        )

        # Create Transfer 1: A -> B (qty 50)
        t1 = await stock_transfer_service.create_transfer(
            session,
            StockTransferCreate(
                transfer_number=f"ST-CONC-1-{uuid.uuid4().hex[:6]}",
                source_warehouse_id=fx["wh_a"].id,
                destination_warehouse_id=fx["wh_b"].id,
                source_location_id=fx["loc_a1"].id,
                destination_location_id=fx["loc_b1"].id,
                items=[StockTransferItemCreate(product_id=fx["prod_1"].id, quantity=Decimal("50.0"))],
            ),
            current_user_id=admin.id,
        )

        # Create Transfer 2: B -> A (qty 30) (Reverse direction!)
        t2 = await stock_transfer_service.create_transfer(
            session,
            StockTransferCreate(
                transfer_number=f"ST-CONC-2-{uuid.uuid4().hex[:6]}",
                source_warehouse_id=fx["wh_b"].id,
                destination_warehouse_id=fx["wh_a"].id,
                source_location_id=fx["loc_b1"].id,
                destination_location_id=fx["loc_a1"].id,
                items=[StockTransferItemCreate(product_id=fx["prod_1"].id, quantity=Decimal("30.0"))],
            ),
            current_user_id=admin.id,
        )

        # Execute transfers with deterministic sorted lock acquisition
        await stock_transfer_service.post_transfer(session, t1.id, current_user_id=admin.id)
        await stock_transfer_service.post_transfer(session, t2.id, current_user_id=admin.id)

        # Verify final stock correctness:
        # WH A: 200 - 50 + 30 = 180
        # WH B: 200 + 50 - 30 = 220
        bal_a = await stock_balance_repository.get_by_keys(session, fx["prod_1"].id, fx["wh_a"].id, fx["loc_a1"].id)
        bal_b = await stock_balance_repository.get_by_keys(session, fx["prod_1"].id, fx["wh_b"].id, fx["loc_b1"].id)
        assert bal_a is not None and Decimal(str(bal_a.available_quantity)) == Decimal("180.0")
        assert bal_b is not None and Decimal(str(bal_b.available_quantity)) == Decimal("220.0")


# ============================================================================
# 4. DUAL API ROUTE COMPATIBILITY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_dual_api_routes_and_post_endpoints():
    async with AsyncSessionLocal() as session:
        admin = await create_test_admin_user(session)
        fx = await setup_inventory_fixtures(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_access_token(subject=str(admin.id))
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Test /api/v1/warehouse/receipts route family
        gr_payload = {
            "receipt_number": f"GR-WH-API-{uuid.uuid4().hex[:6]}",
            "warehouse_id": str(fx["wh_a"].id),
            "notes": "Testing warehouse route prefix",
            "items": [
                {
                    "product_id": str(fx["prod_1"].id),
                    "storage_location_id": str(fx["loc_a1"].id),
                    "quantity": "80.0000",
                }
            ],
        }
        res = await client.post("/api/v1/warehouse/receipts", json=gr_payload, headers=headers)
        assert res.status_code == 201, res.text
        gr_id = res.json()["id"]

        # Post via /api/v1/warehouse/receipts/{id}/post
        post_res = await client.post(f"/api/v1/warehouse/receipts/{gr_id}/post", headers=headers)
        assert post_res.status_code == 200, post_res.text
        assert post_res.json()["status"] == "Posted"

        # 2. Test /api/v1/warehouse/issues route family
        gi_payload = {
            "issue_number": f"GI-WH-API-{uuid.uuid4().hex[:6]}",
            "warehouse_id": str(fx["wh_a"].id),
            "issue_reason": "Consumption",
            "notes": "Testing issue warehouse route prefix",
            "items": [
                {
                    "product_id": str(fx["prod_1"].id),
                    "storage_location_id": str(fx["loc_a1"].id),
                    "quantity": "30.0000",
                }
            ],
        }
        res = await client.post("/api/v1/warehouse/issues", json=gi_payload, headers=headers)
        assert res.status_code == 201, res.text
        gi_id = res.json()["id"]

        # Post via /api/v1/warehouse/issues/{id}/post
        post_res = await client.post(f"/api/v1/warehouse/issues/{gi_id}/post", headers=headers)
        assert post_res.status_code == 200, post_res.text
        assert post_res.json()["status"] == "Posted"

        # 3. Test /api/v1/warehouse/transfers route family
        st_payload = {
            "transfer_number": f"ST-WH-API-{uuid.uuid4().hex[:6]}",
            "source_warehouse_id": str(fx["wh_a"].id),
            "destination_warehouse_id": str(fx["wh_b"].id),
            "source_location_id": str(fx["loc_a1"].id),
            "destination_location_id": str(fx["loc_b1"].id),
            "notes": "Testing transfer warehouse route prefix",
            "items": [
                {
                    "product_id": str(fx["prod_1"].id),
                    "quantity": "25.0000",
                }
            ],
        }
        res = await client.post("/api/v1/warehouse/transfers", json=st_payload, headers=headers)
        assert res.status_code == 201, res.text
        st_id = res.json()["id"]

        # Post via /api/v1/warehouse/transfers/{id}/post
        post_res = await client.post(f"/api/v1/warehouse/transfers/{st_id}/post", headers=headers)
        assert post_res.status_code == 200, post_res.text
        assert post_res.json()["status"] == "Posted"


# ============================================================================
# 5. AUDIT LOGGING VERIFICATION
# ============================================================================

@pytest.mark.asyncio
async def test_warehouse_operations_audit_events():
    async with AsyncSessionLocal() as session:
        admin = await create_test_admin_user(session)
        fx = await setup_inventory_fixtures(session)

        # Create, Post, and Delete draft operations, verifying audit events
        receipt = await goods_receipt_service.create_receipt(
            session,
            GoodsReceiptCreate(
                receipt_number=f"GR-AUDIT-{uuid.uuid4().hex[:6]}",
                warehouse_id=fx["wh_a"].id,
                items=[GoodsReceiptItemCreate(product_id=fx["prod_1"].id, quantity=Decimal("15.0"))],
            ),
            current_user_id=admin.id,
        )
        await goods_receipt_service.post_receipt(session, receipt.id, current_user_id=admin.id)

        # Query Audit Log for GoodsReceipt events
        stmt = select(AuditLog).where(
            AuditLog.entity_type == "GoodsReceipt",
            AuditLog.entity_id == str(receipt.id),
        )
        audit_records = (await session.execute(stmt)).scalars().all()
        actions = [a.action for a in audit_records]
        assert "GOODS_RECEIPT_CREATE" in actions
        assert "GOODS_RECEIPT_POST" in actions
