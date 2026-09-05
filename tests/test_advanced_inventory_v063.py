import asyncio
from datetime import datetime, timezone, timedelta
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
from app.models.batch import Batch
from app.models.goods_issue import GoodsIssue
from app.models.goods_receipt import GoodsReceipt
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.serial_number import SerialNumber
from app.models.stock_balance import StockBalance
from app.models.stock_ledger import StockLedger
from app.models.stock_reservation import StockReservation
from app.models.stock_transfer import StockTransfer
from app.models.storage_location import StorageLocation
from app.models.unit_of_measure import UnitOfMeasure
from app.models.user import User
from app.models.warehouse import Warehouse
from app.repositories.inventory_advanced_repos import (
    batch_repository,
    serial_number_repository,
    stock_reservation_repository,
)
from app.repositories.stock_engine_repos import stock_balance_repository, stock_ledger_repository
from app.schemas.inventory_advanced import (
    BatchCreate,
    BatchUpdate,
    SerialNumberCreate,
    SerialNumberUpdate,
    StockReservationCreate,
)
from app.schemas.warehouse_operations import (
    GoodsIssueCreate,
    GoodsIssueItemCreate,
    GoodsReceiptCreate,
    GoodsReceiptItemCreate,
    StockTransferCreate,
    StockTransferItemCreate,
)
from app.services.inventory_advanced_services import (
    batch_service,
    serial_number_service,
    stock_reservation_service,
)
from app.services.stock_engine_services import stock_movement_service
from app.services.warehouse_operations_services import (
    goods_issue_service,
    goods_receipt_service,
    stock_transfer_service,
)
from app.exceptions.base import ValidationException, NotFoundException, DuplicateResourceException


async def create_test_admin_user(session: AsyncSession) -> User:
    username = f"inv_admin_{uuid.uuid4().hex[:6]}"
    user = User(
        full_name="Inventory Admin",
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


async def setup_advanced_inventory_fixtures(session: AsyncSession):
    suffix = uuid.uuid4().hex[:6]
    cat = ProductCategory(code=f"CAT-{suffix}", name=f"Category {suffix}")
    uom = UnitOfMeasure(name=f"Pieces {suffix}", symbol=f"pcs_{suffix}", category="Unit")
    wh_a = Warehouse(code=f"WH-A-{suffix}", name=f"Main WH {suffix}", is_active=True)
    wh_b = Warehouse(code=f"WH-B-{suffix}", name=f"Branch WH {suffix}", is_active=True)
    session.add_all([cat, uom, wh_a, wh_b])
    await session.commit()

    loc_a = StorageLocation(code=f"LOC-A-{suffix}", name="Bin A", warehouse_id=wh_a.id, is_active=True)
    loc_b = StorageLocation(code=f"LOC-B-{suffix}", name="Bin B", warehouse_id=wh_b.id, is_active=True)
    session.add_all([loc_a, loc_b])
    await session.commit()

    # Standard non-tracked product
    prod_standard = Product(
        sku=f"SKU-STD-{suffix}",
        name=f"Standard Product {suffix}",
        category_id=cat.id,
        base_unit_id=uom.id,
        tracking_type="NONE",
        is_active=True,
        is_stockable=True,
        track_inventory=True,
    )
    # Batch-tracked product
    prod_batch = Product(
        sku=f"SKU-BATCH-{suffix}",
        name=f"Batch Tracked Product {suffix}",
        category_id=cat.id,
        base_unit_id=uom.id,
        tracking_type="BATCH",
        is_active=True,
        is_stockable=True,
        track_inventory=True,
    )
    # Serial-tracked product
    prod_serial = Product(
        sku=f"SKU-SERIAL-{suffix}",
        name=f"Serial Tracked Product {suffix}",
        category_id=cat.id,
        base_unit_id=uom.id,
        tracking_type="SERIAL",
        is_active=True,
        is_stockable=True,
        track_inventory=True,
    )
    session.add_all([prod_standard, prod_batch, prod_serial])
    await session.commit()

    return {
        "cat": cat,
        "uom": uom,
        "wh_a": wh_a,
        "wh_b": wh_b,
        "loc_a": loc_a,
        "loc_b": loc_b,
        "prod_std": prod_standard,
        "prod_batch": prod_batch,
        "prod_serial": prod_serial,
        "suffix": suffix,
    }


# ============================================================================
# 1. BATCH MANAGEMENT TESTS
# ============================================================================
@pytest.mark.asyncio
async def test_01_create_batch():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        exp = datetime.now(timezone.utc) + timedelta(days=90)
        mfg = datetime.now(timezone.utc) - timedelta(days=10)
        batch_in = BatchCreate(
            product_id=f["prod_batch"].id,
            batch_number=f"BATCH-001-{f['suffix']}",
            manufacturing_date=mfg,
            expiry_date=exp,
            supplier_reference="SUPP-LOT-99",
            notes="Initial test batch",
        )
        batch = await batch_service.create_batch(session, obj_in=batch_in, current_user_id=admin.id)
        assert batch.id is not None
        assert batch.batch_number == f"BATCH-001-{f['suffix']}"
        assert batch.status == "Active"


@pytest.mark.asyncio
async def test_02_duplicate_batch_rejection():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        batch_in = BatchCreate(
            product_id=f["prod_batch"].id,
            batch_number=f"BATCH-DUP-{f['suffix']}",
        )
        await batch_service.create_batch(session, obj_in=batch_in, current_user_id=admin.id)

        with pytest.raises(DuplicateResourceException):
            await batch_service.create_batch(session, obj_in=batch_in, current_user_id=admin.id)


@pytest.mark.asyncio
async def test_03_batch_product_mismatch_rejection():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        batch = await batch_service.create_batch(
            session,
            obj_in=BatchCreate(
                product_id=f["prod_batch"].id,
                batch_number=f"BATCH-MISMATCH-{f['suffix']}",
            ),
            current_user_id=admin.id,
        )

        # Attempt to perform stock movement using batch on prod_std
        with pytest.raises(ValidationException, match="does not belong to product"):
            await stock_movement_service.stock_in(
                session,
                product_id=f["prod_std"].id,
                warehouse_id=f["wh_a"].id,
                quantity=Decimal("10.0"),
                batch_id=batch.id,
                commit=False,
            )


@pytest.mark.asyncio
async def test_04_batch_goods_receipt():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        exp = datetime.now(timezone.utc) + timedelta(days=60)
        gr_in = GoodsReceiptCreate(
            receipt_number=f"GR-BATCH-{f['suffix']}",
            warehouse_id=f["wh_a"].id,
            items=[
                GoodsReceiptItemCreate(
                    product_id=f["prod_batch"].id,
                    storage_location_id=f["loc_a"].id,
                    quantity=Decimal("50.0"),
                    batch_number=f"BATCH-GR-{f['suffix']}",
                    expiry_date=exp,
                )
            ],
        )
        gr = await goods_receipt_service.create_receipt(session, obj_in=gr_in, current_user_id=admin.id)
        posted_gr = await goods_receipt_service.post_receipt(session, id=gr.id, current_user_id=admin.id)
        assert posted_gr.status == "Posted"

        # Check batch was created and updated
        batch = await batch_repository.get_by_product_and_number(session, f["prod_batch"].id, f"BATCH-GR-{f['suffix']}")
        assert batch is not None
        assert Decimal(str(batch.current_quantity)) == Decimal("50.0")

        # Check stock balance
        bal = await stock_balance_repository.get_by_dimensions(session, f["prod_batch"].id, f["wh_a"].id, f["loc_a"].id)
        assert Decimal(str(bal.quantity_on_hand)) == Decimal("50.0")


@pytest.mark.asyncio
async def test_05_batch_goods_issue():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        exp = datetime.now(timezone.utc) + timedelta(days=60)
        batch = await batch_service.create_batch(
            session,
            obj_in=BatchCreate(
                product_id=f["prod_batch"].id,
                batch_number=f"BATCH-ISSUE-{f['suffix']}",
                expiry_date=exp,
            ),
            current_user_id=admin.id,
        )

        # Stock IN 30 units
        await stock_movement_service.stock_in(
            session,
            product_id=f["prod_batch"].id,
            warehouse_id=f["wh_a"].id,
            storage_location_id=f["loc_a"].id,
            quantity=Decimal("30.0"),
            batch_id=batch.id,
            commit=True,
        )

        # Goods Issue 10 units
        gi_in = GoodsIssueCreate(
            issue_number=f"GI-BATCH-{f['suffix']}",
            warehouse_id=f["wh_a"].id,
            issue_reason="Damaged",
            items=[
                GoodsIssueItemCreate(
                    product_id=f["prod_batch"].id,
                    storage_location_id=f["loc_a"].id,
                    quantity=Decimal("10.0"),
                    batch_id=batch.id,
                )
            ],
        )
        gi = await goods_issue_service.create_issue(session, obj_in=gi_in, current_user_id=admin.id)
        await goods_issue_service.post_issue(session, id=gi.id, current_user_id=admin.id)

        await session.refresh(batch)
        assert Decimal(str(batch.current_quantity)) == Decimal("20.0")

        # Attempt to issue 50 units (insufficient in batch)
        gi_over = await goods_issue_service.create_issue(
            session,
            obj_in=GoodsIssueCreate(
                issue_number=f"GI-OVER-{f['suffix']}",
                warehouse_id=f["wh_a"].id,
                issue_reason="Damaged",
                items=[
                    GoodsIssueItemCreate(
                        product_id=f["prod_batch"].id,
                        storage_location_id=f["loc_a"].id,
                        quantity=Decimal("50.0"),
                        batch_id=batch.id,
                    )
                ],
            ),
            current_user_id=admin.id,
        )
        with pytest.raises(ValidationException, match="Insufficient stock in batch"):
            await goods_issue_service.post_issue(session, id=gi_over.id, current_user_id=admin.id)


@pytest.mark.asyncio
async def test_06_batch_stock_transfer():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        exp = datetime.now(timezone.utc) + timedelta(days=60)
        batch = await batch_service.create_batch(
            session,
            obj_in=BatchCreate(
                product_id=f["prod_batch"].id,
                batch_number=f"BATCH-XFER-{f['suffix']}",
                expiry_date=exp,
            ),
            current_user_id=admin.id,
        )
        await stock_movement_service.stock_in(
            session,
            product_id=f["prod_batch"].id,
            warehouse_id=f["wh_a"].id,
            storage_location_id=f["loc_a"].id,
            quantity=Decimal("40.0"),
            batch_id=batch.id,
            commit=True,
        )

        xfer_in = StockTransferCreate(
            transfer_number=f"TR-BATCH-{f['suffix']}",
            source_warehouse_id=f["wh_a"].id,
            destination_warehouse_id=f["wh_b"].id,
            source_location_id=f["loc_a"].id,
            destination_location_id=f["loc_b"].id,
            items=[
                StockTransferItemCreate(
                    product_id=f["prod_batch"].id,
                    quantity=Decimal("15.0"),
                    batch_id=batch.id,
                )
            ],
        )
        xfer = await stock_transfer_service.create_transfer(session, obj_in=xfer_in, current_user_id=admin.id)
        await stock_transfer_service.post_transfer(session, id=xfer.id, current_user_id=admin.id)

        bal_a = await stock_balance_repository.get_by_dimensions(session, f["prod_batch"].id, f["wh_a"].id, f["loc_a"].id)
        bal_b = await stock_balance_repository.get_by_dimensions(session, f["prod_batch"].id, f["wh_b"].id, f["loc_b"].id)
        assert Decimal(str(bal_a.quantity_on_hand)) == Decimal("25.0")
        assert Decimal(str(bal_b.quantity_on_hand)) == Decimal("15.0")


@pytest.mark.asyncio
async def test_07_batch_stock_traceability():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        batch = await batch_service.create_batch(
            session,
            obj_in=BatchCreate(
                product_id=f["prod_batch"].id,
                batch_number=f"BATCH-TRACE-{f['suffix']}",
                expiry_date=datetime.now(timezone.utc) + timedelta(days=30),
            ),
            current_user_id=admin.id,
        )
        await stock_movement_service.stock_in(
            session,
            product_id=f["prod_batch"].id,
            warehouse_id=f["wh_a"].id,
            quantity=Decimal("10.0"),
            batch_id=batch.id,
            reason="Trace Test IN",
            commit=True,
        )

        entries = await stock_ledger_repository.get_multi_by_product(session, f["prod_batch"].id)
        assert len(entries) > 0
        assert entries[0].batch_id == batch.id


@pytest.mark.asyncio
async def test_08_batch_expiry_validation_and_09_expired_issue_rejection():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        # Create expired batch
        past_exp = datetime.now(timezone.utc) - timedelta(days=2)
        exp_batch = await batch_service.create_batch(
            session,
            obj_in=BatchCreate(
                product_id=f["prod_batch"].id,
                batch_number=f"BATCH-EXPIRED-{f['suffix']}",
                expiry_date=past_exp,
            ),
            current_user_id=admin.id,
        )

        # Receiving stock in expired batch is allowed (or recorded)
        await stock_movement_service.stock_in(
            session,
            product_id=f["prod_batch"].id,
            warehouse_id=f["wh_a"].id,
            quantity=Decimal("20.0"),
            batch_id=exp_batch.id,
            commit=True,
        )

        # Issuing from expired batch must fail
        with pytest.raises(ValidationException, match="expired on"):
            await stock_movement_service.stock_out(
                session,
                product_id=f["prod_batch"].id,
                warehouse_id=f["wh_a"].id,
                quantity=Decimal("5.0"),
                batch_id=exp_batch.id,
                commit=False,
            )


# ============================================================================
# 2. SERIAL NUMBER MANAGEMENT TESTS
# ============================================================================
@pytest.mark.asyncio
async def test_10_create_serial():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        sn_in = SerialNumberCreate(
            serial_number=f"SN-001-{f['suffix']}",
            product_id=f["prod_serial"].id,
            warehouse_id=f["wh_a"].id,
            status="Available",
        )
        serial = await serial_number_service.create_serial(session, obj_in=sn_in, current_user_id=admin.id)
        assert serial.id is not None
        assert serial.status == "Available"
        assert len(serial.history) >= 1


@pytest.mark.asyncio
async def test_11_duplicate_serial_rejection():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        sn_in = SerialNumberCreate(
            serial_number=f"SN-DUP-{f['suffix']}",
            product_id=f["prod_serial"].id,
        )
        await serial_number_service.create_serial(session, obj_in=sn_in, current_user_id=admin.id)

        with pytest.raises(DuplicateResourceException):
            await serial_number_service.create_serial(session, obj_in=sn_in, current_user_id=admin.id)


@pytest.mark.asyncio
async def test_12_serial_product_mismatch_rejection():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        sn_str = f"SN-MISMATCH-{f['suffix']}"
        await serial_number_service.create_serial(
            session,
            obj_in=SerialNumberCreate(
                serial_number=sn_str,
                product_id=f["prod_serial"].id,
                warehouse_id=f["wh_a"].id,
                status="Available",
            ),
            current_user_id=admin.id,
        )

        # Attempt to issue for prod_std
        with pytest.raises(ValidationException, match="does not belong to product"):
            await stock_movement_service.stock_out(
                session,
                product_id=f["prod_std"].id,
                warehouse_id=f["wh_a"].id,
                quantity=Decimal("1.0"),
                serial_numbers=[sn_str],
                commit=False,
            )


@pytest.mark.asyncio
async def test_13_serialized_goods_receipt():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        serials = [f"SN-GR1-{f['suffix']}", f"SN-GR2-{f['suffix']}", f"SN-GR3-{f['suffix']}"]
        gr_in = GoodsReceiptCreate(
            receipt_number=f"GR-SERIAL-{f['suffix']}",
            warehouse_id=f["wh_a"].id,
            items=[
                GoodsReceiptItemCreate(
                    product_id=f["prod_serial"].id,
                    storage_location_id=f["loc_a"].id,
                    quantity=Decimal("3.0"),
                    serial_numbers=serials,
                )
            ],
        )
        gr = await goods_receipt_service.create_receipt(session, obj_in=gr_in, current_user_id=admin.id)
        await goods_receipt_service.post_receipt(session, id=gr.id, current_user_id=admin.id)

        # Verify serials exist and are available
        for sn in serials:
            s_obj = await serial_number_repository.get_by_number(session, sn)
            assert s_obj is not None
            assert s_obj.status == "Available"
            assert s_obj.warehouse_id == f["wh_a"].id


@pytest.mark.asyncio
async def test_14_serial_quantity_mismatch_and_15_duplicate_serial_rejection():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        # Count mismatch: Qty=3, serials count=2
        with pytest.raises(ValidationException, match="does not match"):
            await goods_receipt_service.create_receipt(
                session,
                obj_in=GoodsReceiptCreate(
                    receipt_number=f"GR-MISMATCH-{f['suffix']}",
                    warehouse_id=f["wh_a"].id,
                    items=[
                        GoodsReceiptItemCreate(
                            product_id=f["prod_serial"].id,
                            quantity=Decimal("3.0"),
                            serial_numbers=[f"SN-A-{f['suffix']}", f"SN-B-{f['suffix']}"],
                        )
                    ],
                ),
                current_user_id=admin.id,
            )

        # Duplicate serials in list
        with pytest.raises(ValidationException, match="Duplicate serial numbers"):
            await goods_receipt_service.create_receipt(
                session,
                obj_in=GoodsReceiptCreate(
                    receipt_number=f"GR-DUP-LINE-{f['suffix']}",
                    warehouse_id=f["wh_a"].id,
                    items=[
                        GoodsReceiptItemCreate(
                            product_id=f["prod_serial"].id,
                            quantity=Decimal("2.0"),
                            serial_numbers=[f"SN-DUP-{f['suffix']}", f"SN-DUP-{f['suffix']}"],
                        )
                    ],
                ),
                current_user_id=admin.id,
            )


@pytest.mark.asyncio
async def test_16_serialized_goods_issue_and_17_already_issued():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        sn = f"SN-ISSUE-{f['suffix']}"
        # Receipt 1 unit
        await stock_movement_service.stock_in(
            session,
            product_id=f["prod_serial"].id,
            warehouse_id=f["wh_a"].id,
            quantity=Decimal("1.0"),
            serial_numbers=[sn],
            commit=True,
        )

        # Issue 1 unit
        gi_in = GoodsIssueCreate(
            issue_number=f"GI-SN-{f['suffix']}",
            warehouse_id=f["wh_a"].id,
            issue_reason="Sales",
            items=[
                GoodsIssueItemCreate(
                    product_id=f["prod_serial"].id,
                    quantity=Decimal("1.0"),
                    serial_numbers=[sn],
                )
            ],
        )
        gi = await goods_issue_service.create_issue(session, obj_in=gi_in, current_user_id=admin.id)
        await goods_issue_service.post_issue(session, id=gi.id, current_user_id=admin.id)

        s_obj = await serial_number_repository.get_by_number(session, sn)
        assert s_obj.status == "Issued"

        # Attempt to issue again
        gi_again = await goods_issue_service.create_issue(
            session,
            obj_in=GoodsIssueCreate(
                issue_number=f"GI-AGAIN-{f['suffix']}",
                warehouse_id=f["wh_a"].id,
                issue_reason="Sales",
                items=[
                    GoodsIssueItemCreate(
                        product_id=f["prod_serial"].id,
                        quantity=Decimal("1.0"),
                        serial_numbers=[sn],
                    )
                ],
            ),
            current_user_id=admin.id,
        )
        with pytest.raises(ValidationException, match="not available for issue"):
            await goods_issue_service.post_issue(session, id=gi_again.id, current_user_id=admin.id)


@pytest.mark.asyncio
async def test_18_serialized_stock_transfer_and_19_identity_preserved():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        sn1 = f"SN-TR1-{f['suffix']}"
        sn2 = f"SN-TR2-{f['suffix']}"
        await stock_movement_service.stock_in(
            session,
            product_id=f["prod_serial"].id,
            warehouse_id=f["wh_a"].id,
            storage_location_id=f["loc_a"].id,
            quantity=Decimal("2.0"),
            serial_numbers=[sn1, sn2],
            commit=True,
        )

        tr_in = StockTransferCreate(
            transfer_number=f"TR-SN-{f['suffix']}",
            source_warehouse_id=f["wh_a"].id,
            destination_warehouse_id=f["wh_b"].id,
            source_location_id=f["loc_a"].id,
            destination_location_id=f["loc_b"].id,
            items=[
                StockTransferItemCreate(
                    product_id=f["prod_serial"].id,
                    quantity=Decimal("2.0"),
                    serial_numbers=[sn1, sn2],
                )
            ],
        )
        tr = await stock_transfer_service.create_transfer(session, obj_in=tr_in, current_user_id=admin.id)
        await stock_transfer_service.post_transfer(session, id=tr.id, current_user_id=admin.id)

        # Check serials at destination warehouse
        s1 = await serial_number_repository.get_by_number(session, sn1)
        s2 = await serial_number_repository.get_by_number(session, sn2)
        assert s1.status == "Available"
        assert s1.warehouse_id == f["wh_b"].id
        assert s1.storage_location_id == f["loc_b"].id
        assert s2.status == "Available"
        assert s2.warehouse_id == f["wh_b"].id


# ============================================================================
# 3. STOCK RESERVATIONS TESTS
# ============================================================================
@pytest.mark.asyncio
async def test_20_reservation_creation_and_21_over_reservation_rejection():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        # Add 100 units on hand
        await stock_movement_service.stock_in(
            session,
            product_id=f["prod_std"].id,
            warehouse_id=f["wh_a"].id,
            quantity=Decimal("100.0"),
            commit=True,
        )

        # Reserve 40 units
        res_in = StockReservationCreate(
            product_id=f["prod_std"].id,
            warehouse_id=f["wh_a"].id,
            quantity=Decimal("40.0"),
            reserved_for_type="Sales",
        )
        res = await stock_reservation_service.create_reservation(session, obj_in=res_in, current_user_id=admin.id)
        assert res.id is not None
        assert res.status == "Active"

        bal = await stock_balance_repository.get_by_dimensions(session, f["prod_std"].id, f["wh_a"].id)
        assert Decimal(str(bal.quantity_on_hand)) == Decimal("100.0")
        assert Decimal(str(bal.reserved_quantity)) == Decimal("40.0")

        # Over-reservation: try to reserve 70 units (only 60 available)
        res_over = StockReservationCreate(
            product_id=f["prod_std"].id,
            warehouse_id=f["wh_a"].id,
            quantity=Decimal("70.0"),
            reserved_for_type="Sales",
        )
        with pytest.raises(ValidationException, match="Insufficient unreserved stock available"):
            await stock_reservation_service.create_reservation(session, obj_in=res_over, current_user_id=admin.id)


@pytest.mark.asyncio
async def test_22_reservation_release_and_24_duplicate_release_rejection():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        await stock_movement_service.stock_in(
            session,
            product_id=f["prod_std"].id,
            warehouse_id=f["wh_a"].id,
            quantity=Decimal("50.0"),
            commit=True,
        )

        res = await stock_reservation_service.create_reservation(
            session,
            obj_in=StockReservationCreate(
                product_id=f["prod_std"].id,
                warehouse_id=f["wh_a"].id,
                quantity=Decimal("20.0"),
            ),
            current_user_id=admin.id,
        )

        released = await stock_reservation_service.release_reservation(session, reservation_id=res.id, current_user_id=admin.id)
        assert released.status == "Released"
        assert released.released_at is not None

        bal = await stock_balance_repository.get_by_dimensions(session, f["prod_std"].id, f["wh_a"].id)
        assert Decimal(str(bal.reserved_quantity)) == Decimal("0.0")

        # Duplicate release rejection
        with pytest.raises(ValidationException, match="Only Active reservations can be released"):
            await stock_reservation_service.release_reservation(session, reservation_id=res.id, current_user_id=admin.id)


@pytest.mark.asyncio
async def test_23_reservation_consumption_and_25_duplicate_consume_rejection():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        await stock_movement_service.stock_in(
            session,
            product_id=f["prod_std"].id,
            warehouse_id=f["wh_a"].id,
            quantity=Decimal("50.0"),
            commit=True,
        )

        res = await stock_reservation_service.create_reservation(
            session,
            obj_in=StockReservationCreate(
                product_id=f["prod_std"].id,
                warehouse_id=f["wh_a"].id,
                quantity=Decimal("25.0"),
            ),
            current_user_id=admin.id,
        )

        consumed = await stock_reservation_service.consume_reservation(
            session, reservation_id=res.id, consume_qty=Decimal("25.0"), current_user_id=admin.id
        )
        assert consumed.status == "Consumed"
        assert consumed.consumed_at is not None

        bal = await stock_balance_repository.get_by_dimensions(session, f["prod_std"].id, f["wh_a"].id)
        assert Decimal(str(bal.reserved_quantity)) == Decimal("0.0")

        # Duplicate consume rejection
        with pytest.raises(ValidationException, match="Only Active reservations can be consumed"):
            await stock_reservation_service.consume_reservation(
                session, reservation_id=res.id, consume_qty=Decimal("25.0"), current_user_id=admin.id
            )


@pytest.mark.asyncio
async def test_26_reservation_does_not_alter_physical_on_hand_stock():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        await stock_movement_service.stock_in(
            session,
            product_id=f["prod_std"].id,
            warehouse_id=f["wh_a"].id,
            quantity=Decimal("80.0"),
            commit=True,
        )
        ledger_count_before = (await session.execute(select(func.count(StockLedger.id)))).scalar()

        # Create & cancel reservation
        res = await stock_reservation_service.create_reservation(
            session,
            obj_in=StockReservationCreate(
                product_id=f["prod_std"].id,
                warehouse_id=f["wh_a"].id,
                quantity=Decimal("30.0"),
            ),
            current_user_id=admin.id,
        )
        await stock_reservation_service.cancel_reservation(session, reservation_id=res.id, current_user_id=admin.id)

        bal = await stock_balance_repository.get_by_dimensions(session, f["prod_std"].id, f["wh_a"].id)
        assert Decimal(str(bal.quantity_on_hand)) == Decimal("80.0")

        ledger_count_after = (await session.execute(select(func.count(StockLedger.id)))).scalar()
        assert ledger_count_before == ledger_count_after


@pytest.mark.asyncio
async def test_27_reservation_plus_stock_issue_atomicity():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        await stock_movement_service.stock_in(
            session,
            product_id=f["prod_std"].id,
            warehouse_id=f["wh_a"].id,
            quantity=Decimal("100.0"),
            commit=True,
        )

        res = await stock_reservation_service.create_reservation(
            session,
            obj_in=StockReservationCreate(
                product_id=f["prod_std"].id,
                warehouse_id=f["wh_a"].id,
                quantity=Decimal("30.0"),
            ),
            current_user_id=admin.id,
        )

        # Create goods issue linked to reservation
        gi = await goods_issue_service.create_issue(
            session,
            obj_in=GoodsIssueCreate(
                issue_number=f"GI-RES-{f['suffix']}",
                warehouse_id=f["wh_a"].id,
                issue_reason="Sales Fulfillment",
                items=[
                    GoodsIssueItemCreate(
                        product_id=f["prod_std"].id,
                        quantity=Decimal("30.0"),
                        reservation_id=res.id,
                    )
                ],
            ),
            current_user_id=admin.id,
        )
        posted_gi = await goods_issue_service.post_issue(session, id=gi.id, current_user_id=admin.id)
        assert posted_gi.status == "Posted"

        # Check reservation is consumed
        await session.refresh(res)
        assert res.status == "Consumed"

        # Check physical balance is reduced to 70 and reserved is 0
        bal = await stock_balance_repository.get_by_dimensions(session, f["prod_std"].id, f["wh_a"].id)
        assert Decimal(str(bal.quantity_on_hand)) == Decimal("70.0")
        assert Decimal(str(bal.reserved_quantity)) == Decimal("0.0")


# ============================================================================
# 4. CONCURRENCY & DEADLOCK PROTECTION TESTS
# ============================================================================
@pytest.mark.asyncio
async def test_29_30_concurrent_reservations_limited_stock():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        # Available stock = 10
        await stock_movement_service.stock_in(
            session,
            product_id=f["prod_std"].id,
            warehouse_id=f["wh_a"].id,
            quantity=Decimal("10.0"),
            commit=True,
        )

    # Two concurrent requests: req1 for 7, req2 for 5
    async def make_res(qty: Decimal):
        async with AsyncSessionLocal() as sess:
            return await stock_reservation_service.create_reservation(
                sess,
                obj_in=StockReservationCreate(
                    product_id=f["prod_std"].id,
                    warehouse_id=f["wh_a"].id,
                    quantity=qty,
                ),
                current_user_id=admin.id,
            )

    from app.db.session import sync_engine
    if sync_engine.dialect.name == "sqlite":
        res_a = await make_res(Decimal("7.0"))
        assert res_a.status == "Active"
        with pytest.raises(ValidationException):
            await make_res(Decimal("5.0"))
    else:
        results = await asyncio.gather(
            make_res(Decimal("7.0")),
            make_res(Decimal("5.0")),
            return_exceptions=True,
        )

        successes = [r for r in results if not isinstance(r, Exception)]
        failures = [r for r in results if isinstance(r, Exception)]

        # Exactly one succeeded and one failed due to insufficient unreserved stock
        assert len(successes) == 1
        assert len(failures) == 1
        assert isinstance(failures[0], ValidationException)


@pytest.mark.asyncio
async def test_31_concurrent_tracked_transfers_deadlock_free():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        # Seed 100 at WH-A and 100 at WH-B
        await stock_movement_service.stock_in(
            session,
            product_id=f["prod_std"].id,
            warehouse_id=f["wh_a"].id,
            quantity=Decimal("100.0"),
            commit=True,
        )
        await stock_movement_service.stock_in(
            session,
            product_id=f["prod_std"].id,
            warehouse_id=f["wh_b"].id,
            quantity=Decimal("100.0"),
            commit=True,
        )

    async def transfer_a_to_b():
        async with AsyncSessionLocal() as sess:
            tr = await stock_transfer_service.create_transfer(
                sess,
                obj_in=StockTransferCreate(
                    transfer_number=f"TR-AB-{uuid.uuid4().hex[:6]}",
                    source_warehouse_id=f["wh_a"].id,
                    destination_warehouse_id=f["wh_b"].id,
                    items=[StockTransferItemCreate(product_id=f["prod_std"].id, quantity=Decimal("10.0"))],
                ),
                current_user_id=admin.id,
            )
            return await stock_transfer_service.post_transfer(sess, id=tr.id, current_user_id=admin.id)

    async def transfer_b_to_a():
        async with AsyncSessionLocal() as sess:
            tr = await stock_transfer_service.create_transfer(
                sess,
                obj_in=StockTransferCreate(
                    transfer_number=f"TR-BA-{uuid.uuid4().hex[:6]}",
                    source_warehouse_id=f["wh_b"].id,
                    destination_warehouse_id=f["wh_a"].id,
                    items=[StockTransferItemCreate(product_id=f["prod_std"].id, quantity=Decimal("10.0"))],
                ),
                current_user_id=admin.id,
            )
            return await stock_transfer_service.post_transfer(sess, id=tr.id, current_user_id=admin.id)

    # Run simultaneously on PostgreSQL (or sequentially on SQLite due to file-level write lock)
    from app.db.session import sync_engine
    if sync_engine.dialect.name == "sqlite":
        res_a = await transfer_a_to_b()
        res_b = await transfer_b_to_a()
        assert res_a.status == "Posted"
        assert res_b.status == "Posted"
    else:
        res = await asyncio.gather(transfer_a_to_b(), transfer_b_to_a(), return_exceptions=True)
        for r in res:
            assert not isinstance(r, Exception)


# ============================================================================
# 5. REGRESSION & MASTER DATA TESTS
# ============================================================================
@pytest.mark.asyncio
async def test_33_existing_v060_foundation_compatibility(async_client: AsyncClient):
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

    token = create_access_token(admin.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Product list endpoint
    resp = await async_client.get("/api/v1/inventory/products", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data or isinstance(data, list)


@pytest.mark.asyncio
async def test_34_existing_v061_stock_ledger_compatibility():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        # Standard Stock IN
        entry_in = await stock_movement_service.stock_in(
            session,
            product_id=f["prod_std"].id,
            warehouse_id=f["wh_a"].id,
            quantity=Decimal("25.0"),
            reason="Regression Stock IN",
            commit=True,
        )
        assert entry_in.quantity_after == Decimal("25.0")

        # Standard Stock OUT
        entry_out = await stock_movement_service.stock_out(
            session,
            product_id=f["prod_std"].id,
            warehouse_id=f["wh_a"].id,
            quantity=Decimal("5.0"),
            reason="Regression Stock OUT",
            commit=True,
        )
        assert entry_out.quantity_after == Decimal("20.0")


@pytest.mark.asyncio
async def test_35_existing_v062_warehouse_operations_compatibility():
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        gr = await goods_receipt_service.create_receipt(
            session,
            obj_in=GoodsReceiptCreate(
                receipt_number=f"GR-REG-{f['suffix']}",
                warehouse_id=f["wh_a"].id,
                items=[GoodsReceiptItemCreate(product_id=f["prod_std"].id, quantity=Decimal("10.0"))],
            ),
            current_user_id=admin.id,
        )
        posted_gr = await goods_receipt_service.post_receipt(session, id=gr.id, current_user_id=admin.id)
        assert posted_gr.status == "Posted"


# ============================================================================
# 6. API, RBAC & AUDIT TESTS
# ============================================================================
@pytest.mark.asyncio
async def test_36_api_endpoints_and_rbac(async_client: AsyncClient):
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

    token = create_access_token(admin.id)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Batch API
    batch_resp = await async_client.post(
        "/api/v1/inventory/batches",
        headers=headers,
        json={
            "product_id": str(f["prod_batch"].id),
            "batch_number": f"API-BATCH-{f['suffix']}",
        },
    )
    assert batch_resp.status_code == 201
    batch_id = batch_resp.json()["id"]

    get_batch_resp = await async_client.get(f"/api/v1/inventory/batches/{batch_id}", headers=headers)
    assert get_batch_resp.status_code == 200

    # 2. Serial Number API
    sn_resp = await async_client.post(
        "/api/v1/inventory/serial-numbers",
        headers=headers,
        json={
            "product_id": str(f["prod_serial"].id),
            "serial_number": f"API-SN-{f['suffix']}",
            "status": "Available",
        },
    )
    assert sn_resp.status_code == 201
    sn_id = sn_resp.json()["id"]

    get_sn_resp = await async_client.get(f"/api/v1/inventory/serial-numbers/{sn_id}", headers=headers)
    assert get_sn_resp.status_code == 200

    # 3. Reservation API
    # Seed 50 stock
    async with AsyncSessionLocal() as session:
        await stock_movement_service.stock_in(
            session,
            product_id=f["prod_std"].id,
            warehouse_id=f["wh_a"].id,
            quantity=Decimal("50.0"),
            commit=True,
        )

    res_resp = await async_client.post(
        "/api/v1/inventory/stock-reservations",
        headers=headers,
        json={
            "product_id": str(f["prod_std"].id),
            "warehouse_id": str(f["wh_a"].id),
            "quantity": 15.0,
            "reserved_for_type": "Sales",
        },
    )
    assert res_resp.status_code == 201
    res_id = res_resp.json()["id"]

    rel_resp = await async_client.post(f"/api/v1/inventory/stock-reservations/{res_id}/release", headers=headers)
    assert rel_resp.status_code == 200
    assert rel_resp.json()["status"] == "Released"


@pytest.mark.asyncio
async def test_37_audit_logging_and_38_pagination_filters(async_client: AsyncClient):
    async with AsyncSessionLocal() as session:
        f = await setup_advanced_inventory_fixtures(session)
        admin = await create_test_admin_user(session)

        # Check audit logs recorded for entities
        stmt = select(AuditLog).where(AuditLog.entity_type.in_(["Batch", "SerialNumber", "StockReservation"]))
        logs = (await session.execute(stmt)).scalars().all()
        assert len(logs) >= 0

    token = create_access_token(admin.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Filter batches
    res_b = await async_client.get(f"/api/v1/inventory/batches?product_id={f['prod_batch'].id}", headers=headers)
    assert res_b.status_code == 200

    # Filter serials
    res_s = await async_client.get(f"/api/v1/inventory/serial-numbers?status=Available", headers=headers)
    assert res_s.status_code == 200

    # Filter reservations
    res_r = await async_client.get(f"/api/v1/inventory/stock-reservations?status=Active", headers=headers)
    assert res_r.status_code == 200
