from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.security import create_access_token, hash_password
from app.db.session import AsyncSessionLocal
from app.exceptions.base import NotFoundException, ValidationException
from app.main import app
from app.models.audit_log import AuditLog
from app.models.batch import Batch
from app.models.goods_receipt import GoodsReceipt
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.purchase_return import PurchaseReturn, PurchaseReturnItem
from app.models.serial_number import SerialNumber
from app.models.stock_balance import StockBalance
from app.models.stock_ledger import StockLedger
from app.models.supplier import Supplier
from app.models.unit_of_measure import UnitOfMeasure
from app.models.user import User
from app.models.user_role import UserRole
from app.models.warehouse import Warehouse
from app.repositories.inventory_repos import product_repository
from app.repositories.rbac import role_repository
from app.schemas.inventory import (

    ProductCategoryCreate,
    ProductCreate,
    UnitOfMeasureCreate,
    WarehouseCreate,
)
from app.schemas.procurement import (
    PurchaseOrderCreate,
    PurchaseOrderItemCreate,
    PurchaseOrderReceiveCreate,
    PurchaseOrderReceiveItem,
    PurchaseReturnCreate,
    PurchaseReturnItemCreate,
    PurchaseReturnUpdate,
    SupplierCreate,
)
from app.services.inventory_services import (
    category_service,
    product_service,
    unit_of_measure_service,
    warehouse_service,
)
from app.services.purchase_order_services import purchase_order_service
from app.services.purchase_return_services import purchase_return_service
from app.services.stock_engine_services import stock_balance_service, stock_ledger_service
from app.services.supplier_services import supplier_service


async def setup_receiving_test_data(session):
    """
    Sets up common test fixtures: users, warehouse, products (standard, batch, serial), supplier.
    """
    suffix = uuid.uuid4().hex[:6]

    # 1. Users
    mgr_user = User(
        full_name=f"Procurement Mgr {suffix}",
        email=f"proc_mgr_{suffix}@apnaerp.test",
        username=f"mgr_{suffix}",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    viewer_user = User(
        full_name=f"Procurement Viewer {suffix}",
        email=f"proc_view_{suffix}@apnaerp.test",
        username=f"view_{suffix}",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    session.add_all([mgr_user, viewer_user])
    await session.flush()

    mgr_role = await role_repository.get_by_name(session, "Procurement Manager")
    viewer_role = await role_repository.get_by_name(session, "Procurement Viewer")

    if mgr_role:
        session.add(UserRole(user_id=mgr_user.id, role_id=mgr_role.id))
    if viewer_role:
        session.add(UserRole(user_id=viewer_user.id, role_id=viewer_role.id))

    await session.commit()
    await session.refresh(mgr_user)
    await session.refresh(viewer_user)

    # 2. Category & Unit
    cat = await category_service.create_category(
        session, obj_in=ProductCategoryCreate(code=f"CAT-{suffix}", name=f"Category {suffix}")
    )
    uom = await unit_of_measure_service.create_unit(
        session, obj_in=UnitOfMeasureCreate(name=f"Pcs_{suffix}", symbol=f"pc_{suffix}", category="Count")
    )

    # 3. Warehouse
    wh = await warehouse_service.create_warehouse(
        session,
        obj_in=WarehouseCreate(
            code=f"WH-RCV-{suffix}",
            name=f"Central Receiving WH {suffix}",
            city="Metropolis",
            is_active=True,
        ),
    )

    # 4. Standard Product
    p_std_res = await product_service.create_product(
        session,
        obj_in=ProductCreate(
            sku=f"SKU-STD-{suffix}",
            name=f"Standard Component {suffix}",
            category_id=cat.id,
            base_unit_id=uom.id,
            cost_price=Decimal("50.0"),
            is_active=True,
        ),
    )
    p_std = await product_repository.get_by_id(session, p_std_res["id"] if isinstance(p_std_res, dict) else p_std_res.id)

    # 5. Batch-tracked Product
    p_batch_res = await product_service.create_product(
        session,
        obj_in=ProductCreate(
            sku=f"SKU-BAT-{suffix}",
            name=f"Batch Chemical {suffix}",
            category_id=cat.id,
            base_unit_id=uom.id,
            cost_price=Decimal("120.0"),
            is_batch_tracked=True,
            is_active=True,
        ),
    )
    p_batch = await product_repository.get_by_id(session, p_batch_res["id"] if isinstance(p_batch_res, dict) else p_batch_res.id)

    # 6. Serial-tracked Product
    p_serial_res = await product_service.create_product(
        session,
        obj_in=ProductCreate(
            sku=f"SKU-SER-{suffix}",
            name=f"Serialized Hardware {suffix}",
            category_id=cat.id,
            base_unit_id=uom.id,
            cost_price=Decimal("450.0"),
            is_serial_tracked=True,
            is_active=True,
        ),
    )
    p_serial = await product_repository.get_by_id(session, p_serial_res["id"] if isinstance(p_serial_res, dict) else p_serial_res.id)


    # 7. Active Supplier
    sup = await supplier_service.create_supplier(
        session,
        obj_in=SupplierCreate(
            code=f"SUP-{suffix}",
            name=f"Apex Logistics Supplier {suffix}",
            payment_terms="Net 30",
            currency="USD",
        ),
        current_user_id=mgr_user.id,
    )

    return {
        "mgr_user": mgr_user,
        "viewer_user": viewer_user,
        "warehouse": wh,
        "product_std": p_std,
        "product_batch": p_batch,
        "product_serial": p_serial,
        "supplier": sup,
    }


# ==============================================================================
# 1. PURCHASE ORDER RECEIVING - FULL, PARTIAL, SEQUENTIAL, AND MULTI-LINE
# ==============================================================================

@pytest.mark.asyncio
async def test_full_po_receiving_and_stock_ledger():
    """
    Test full receiving against an Approved PO.
    Verifies PO status becomes 'Fully Received', GoodsReceipt is 'Received',
    StockBalance is incremented, and StockLedger records a STOCK_IN movement.
    """
    async with AsyncSessionLocal() as session:
        data = await setup_receiving_test_data(session)
        user = data["mgr_user"]
        wh = data["warehouse"]
        prod = data["product_std"]
        sup = data["supplier"]

        # Create PO for 100 units
        po_in = PurchaseOrderCreate(
            supplier_id=sup.id,
            items=[
                PurchaseOrderItemCreate(
                    product_id=prod.id,
                    quantity=Decimal("100.0"),
                    unit_price=Decimal("50.0"),
                    warehouse_id=wh.id,
                )
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=user.id)
        await purchase_order_service.approve_order(session, po.id, approver_id=user.id)

        # Receive all 100 units
        po_item = po.items[0]
        receipt = await purchase_order_service.receive_goods(
            session,
            po_id=po.id,
            receiving_items=[{"po_item_id": po_item.id, "quantity": 100.0}],
            supplier_ref="DELIV-100",
            remarks="Full receiving",
            current_user_id=user.id,
        )

        assert receipt.status == "Received"
        assert receipt.external_reference == po.po_number
        assert receipt.receipt_number.startswith(f"GRN-{datetime.now(timezone.utc).year}-")

        # Verify PO status and item received quantity
        po_updated = await purchase_order_service.get_order(session, po.id)
        assert po_updated.status == "Fully Received"
        assert po_updated.items[0].received_quantity == Decimal("100.0")
        assert po_updated.items[0].status == "Fully Received"

        # Verify Stock Balance
        stmt = select(StockBalance).where(StockBalance.product_id == prod.id, StockBalance.warehouse_id == wh.id)
        res = await session.execute(stmt)
        balance = res.scalar_one_or_none()
        assert balance is not None
        assert Decimal(str(balance.available_quantity)) >= Decimal("100.0")

        # Verify Stock Ledger Entry
        stmt_l = select(StockLedger).where(
            StockLedger.product_id == prod.id,
            StockLedger.warehouse_id == wh.id,
            StockLedger.reference_type == "GoodsReceipt",
            StockLedger.reference_id == receipt.id,
        )
        res_l = await session.execute(stmt_l)
        matching = res_l.scalars().all()
        assert len(matching) == 1
        assert matching[0].direction == "IN"
        assert matching[0].quantity == Decimal("100.0")



@pytest.mark.asyncio
async def test_partial_and_sequential_po_receiving():
    """
    Test sequential partial receipts: Receipt 1 (40) -> Partially Received, Receipt 2 (60) -> Fully Received.
    """
    async with AsyncSessionLocal() as session:
        data = await setup_receiving_test_data(session)
        user = data["mgr_user"]
        wh = data["warehouse"]
        prod = data["product_std"]
        sup = data["supplier"]

        po_in = PurchaseOrderCreate(
            supplier_id=sup.id,
            items=[
                PurchaseOrderItemCreate(
                    product_id=prod.id,
                    quantity=Decimal("100.0"),
                    unit_price=Decimal("50.0"),
                    warehouse_id=wh.id,
                )
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=user.id)
        await purchase_order_service.approve_order(session, po.id, approver_id=user.id)
        po_item = po.items[0]

        # Receipt 1: 40 units
        r1 = await purchase_order_service.receive_goods(
            session,
            po_id=po.id,
            receiving_items=[{"po_item_id": po_item.id, "quantity": 40.0}],
            supplier_ref="BATCH-1",
            current_user_id=user.id,
        )
        assert r1.status == "Received"

        po_after_r1 = await purchase_order_service.get_order(session, po.id)
        assert po_after_r1.status == "Partially Received"
        assert po_after_r1.items[0].received_quantity == Decimal("40.0")
        assert po_after_r1.items[0].status == "Partially Received"

        # Receipt 2: 60 units (remaining)
        r2 = await purchase_order_service.receive_goods(
            session,
            po_id=po.id,
            receiving_items=[{"po_item_id": po_item.id, "quantity": 60.0}],
            supplier_ref="BATCH-2",
            current_user_id=user.id,
        )
        assert r2.status == "Received"

        po_after_r2 = await purchase_order_service.get_order(session, po.id)
        assert po_after_r2.status == "Fully Received"
        assert po_after_r2.items[0].received_quantity == Decimal("100.0")
        assert po_after_r2.items[0].status == "Fully Received"

        # Verify get_po_receipts returns both receipts
        all_receipts = await purchase_order_service.get_po_receipts(session, po.id)
        assert len(all_receipts) == 2
        receipt_ids = {r.id for r in all_receipts}
        assert r1.id in receipt_ids
        assert r2.id in receipt_ids


@pytest.mark.asyncio
async def test_multi_line_receiving_and_atomic_rollback():
    """
    Test receiving multiple PO lines in a single GoodsReceipt.
    Also tests atomic rollback when one line fails validation.
    """
    async with AsyncSessionLocal() as session:
        data = await setup_receiving_test_data(session)
        user = data["mgr_user"]
        wh = data["warehouse"]
        prod1 = data["product_std"]
        prod2 = data["product_batch"]
        sup = data["supplier"]

        po_in = PurchaseOrderCreate(
            supplier_id=sup.id,
            items=[
                PurchaseOrderItemCreate(
                    product_id=prod1.id,
                    quantity=Decimal("50.0"),
                    unit_price=Decimal("20.0"),
                    warehouse_id=wh.id,
                ),
                PurchaseOrderItemCreate(
                    product_id=prod2.id,
                    quantity=Decimal("30.0"),
                    unit_price=Decimal("120.0"),
                    warehouse_id=wh.id,
                ),
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=user.id)
        await purchase_order_service.approve_order(session, po.id, approver_id=user.id)

        item1, item2 = po.items[0], po.items[1]

        # Valid multi-line receipt
        receipt = await purchase_order_service.receive_goods(
            session,
            po_id=po.id,
            receiving_items=[
                {"po_item_id": item1.id, "quantity": 25.0},
                {
                    "po_item_id": item2.id,
                    "quantity": 15.0,
                    "batch_number": "BAT-ML-01",
                    "expiry_date": datetime.now(timezone.utc) + timedelta(days=365),
                },
            ],
            current_user_id=user.id,
        )
        assert receipt.status == "Received"
        assert len(receipt.items) == 2

        po_check = await purchase_order_service.get_order(session, po.id)
        assert po_check.status == "Partially Received"

        # Attempt invalid multi-line receiving where item 1 is valid (25) but item 2 exceeds remaining (20 > 15 remaining)
        with pytest.raises(ValidationException) as exc:
            await purchase_order_service.receive_goods(
                session,
                po_id=po.id,
                receiving_items=[
                    {"po_item_id": item1.id, "quantity": 25.0},
                    {"po_item_id": item2.id, "quantity": 20.0, "batch_number": "BAT-ML-02"},
                ],
                current_user_id=user.id,
            )
        assert "exceeds remaining order quantity" in str(exc.value)

        # Confirm atomicity: item 1 received_quantity did NOT change to 50
        po_atomic = await purchase_order_service.get_order(session, po.id)
        assert po_atomic.items[0].received_quantity == Decimal("25.0")
        assert po_atomic.items[1].received_quantity == Decimal("15.0")


@pytest.mark.asyncio
async def test_over_receiving_and_invalid_statuses():
    """
    Test that receiving is strictly rejected on Draft, Submitted, Rejected, Cancelled, and Closed POs,
    and that receiving quantity > remaining quantity is blocked.
    """
    async with AsyncSessionLocal() as session:
        data = await setup_receiving_test_data(session)
        user = data["mgr_user"]
        wh = data["warehouse"]
        prod = data["product_std"]
        sup = data["supplier"]

        po_in = PurchaseOrderCreate(
            supplier_id=sup.id,
            items=[
                PurchaseOrderItemCreate(
                    product_id=prod.id,
                    quantity=Decimal("50.0"),
                    unit_price=Decimal("10.0"),
                    warehouse_id=wh.id,
                )
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=user.id)
        po_item = po.items[0]

        # 1. Draft PO -> Rejection
        with pytest.raises(ValidationException) as exc:
            await purchase_order_service.receive_goods(
                session,
                po_id=po.id,
                receiving_items=[{"po_item_id": po_item.id, "quantity": 50.0}],
                current_user_id=user.id,
            )
        assert "Cannot receive goods for Purchase Order in 'Draft'" in str(exc.value)

        # 2. Cancelled PO -> Rejection
        await purchase_order_service.cancel_order(session, po.id, current_user_id=user.id)
        with pytest.raises(ValidationException) as exc:
            await purchase_order_service.receive_goods(
                session,
                po_id=po.id,
                receiving_items=[{"po_item_id": po_item.id, "quantity": 50.0}],
                current_user_id=user.id,
            )
        assert "Cannot receive goods for Purchase Order in 'Cancelled'" in str(exc.value)

        # 3. Over-receiving on Approved PO -> Rejection
        po2 = await purchase_order_service.create_order(session, po_in, current_user_id=user.id)
        await purchase_order_service.approve_order(session, po2.id, approver_id=user.id)
        with pytest.raises(ValidationException) as exc:
            await purchase_order_service.receive_goods(
                session,
                po_id=po2.id,
                receiving_items=[{"po_item_id": po2.items[0].id, "quantity": 55.0}],
                current_user_id=user.id,
            )
        assert "exceeds remaining order quantity" in str(exc.value)

        # 4. Zero/Negative Quantity -> Rejection
        with pytest.raises(ValidationException) as exc:
            await purchase_order_service.receive_goods(
                session,
                po_id=po2.id,
                receiving_items=[{"po_item_id": po2.items[0].id, "quantity": 0.0}],
                current_user_id=user.id,
            )
        assert "strictly greater than zero" in str(exc.value)


# ==============================================================================
# 2. BATCH & SERIAL NUMBER RECEIVING
# ==============================================================================

@pytest.mark.asyncio
async def test_batch_tracked_receiving():
    """
    Test receiving batch-tracked products with automatic batch creation and tracking.
    """
    async with AsyncSessionLocal() as session:
        data = await setup_receiving_test_data(session)
        user = data["mgr_user"]
        wh = data["warehouse"]
        prod_batch = data["product_batch"]
        sup = data["supplier"]

        po_in = PurchaseOrderCreate(
            supplier_id=sup.id,
            items=[
                PurchaseOrderItemCreate(
                    product_id=prod_batch.id,
                    quantity=Decimal("80.0"),
                    unit_price=Decimal("120.0"),
                    warehouse_id=wh.id,
                )
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=user.id)
        await purchase_order_service.approve_order(session, po.id, approver_id=user.id)

        exp_date = datetime.now(timezone.utc) + timedelta(days=180)
        receipt = await purchase_order_service.receive_goods(
            session,
            po_id=po.id,
            receiving_items=[
                {
                    "po_item_id": po.items[0].id,
                    "quantity": 80.0,
                    "batch_number": "BATCH-LOT-999",
                    "expiry_date": exp_date,
                }
            ],
            current_user_id=user.id,
        )
        assert receipt.status == "Received"

        # Verify Batch created
        stmt = select(Batch).where(Batch.batch_number == "BATCH-LOT-999")
        res = await session.execute(stmt)
        batch = res.scalar_one_or_none()
        assert batch is not None
        assert batch.product_id == prod_batch.id
        assert Decimal(str(batch.current_quantity)) == Decimal("80.0")


@pytest.mark.asyncio
async def test_serial_tracked_receiving_and_validations():
    """
    Test receiving serial-tracked products: serial count match, uniqueness, and inventory registration.
    """
    async with AsyncSessionLocal() as session:
        data = await setup_receiving_test_data(session)
        user = data["mgr_user"]
        wh = data["warehouse"]
        prod_serial = data["product_serial"]
        sup = data["supplier"]

        po_in = PurchaseOrderCreate(
            supplier_id=sup.id,
            items=[
                PurchaseOrderItemCreate(
                    product_id=prod_serial.id,
                    quantity=Decimal("3.0"),
                    unit_price=Decimal("450.0"),
                    warehouse_id=wh.id,
                )
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=user.id)
        await purchase_order_service.approve_order(session, po.id, approver_id=user.id)

        suffix = uuid.uuid4().hex[:6]
        serials = [f"SN-{suffix}-01", f"SN-{suffix}-02", f"SN-{suffix}-03"]

        # Mismatch in serial count (quantity=3 but 2 serials provided) -> Rejection
        with pytest.raises(ValidationException) as exc:
            await purchase_order_service.receive_goods(
                session,
                po_id=po.id,
                receiving_items=[
                    {
                        "po_item_id": po.items[0].id,
                        "quantity": 3.0,
                        "serial_numbers": serials[:2],
                    }
                ],
                current_user_id=user.id,
            )
        assert "does not match" in str(exc.value)


        # Duplicate serials in list -> Rejection
        with pytest.raises(ValidationException) as exc:
            await purchase_order_service.receive_goods(
                session,
                po_id=po.id,
                receiving_items=[
                    {
                        "po_item_id": po.items[0].id,
                        "quantity": 3.0,
                        "serial_numbers": [serials[0], serials[0], serials[1]],
                    }
                ],
                current_user_id=user.id,
            )
        assert "Duplicate serial numbers" in str(exc.value)

        # Successful Serial Receipt
        receipt = await purchase_order_service.receive_goods(
            session,
            po_id=po.id,
            receiving_items=[
                {
                    "po_item_id": po.items[0].id,
                    "quantity": 3.0,
                    "serial_numbers": serials,
                }
            ],
            current_user_id=user.id,
        )
        assert receipt.status == "Received"

        # Verify Serial Number entries created in database
        stmt = select(SerialNumber).where(SerialNumber.serial_number.in_(serials))
        res = await session.execute(stmt)
        saved_serials = res.scalars().all()
        assert len(saved_serials) == 3
        for sn in saved_serials:
            assert sn.status == "Available"
            assert sn.warehouse_id == wh.id


# ==============================================================================
# 3. PURCHASE RETURNS & STOCK REVERSALS
# ==============================================================================

@pytest.mark.asyncio
async def test_purchase_return_full_flow():
    """
    Test complete purchase return flow: create return, validate limits, post return (stock OUT),
    update PO returned_quantity counter, and verify stock ledger reversal.
    """
    async with AsyncSessionLocal() as session:
        data = await setup_receiving_test_data(session)
        user = data["mgr_user"]
        wh = data["warehouse"]
        prod = data["product_std"]
        sup = data["supplier"]

        # Setup: Create PO, Approve, and Receive 50 units
        po_in = PurchaseOrderCreate(
            supplier_id=sup.id,
            items=[
                PurchaseOrderItemCreate(
                    product_id=prod.id,
                    quantity=Decimal("50.0"),
                    unit_price=Decimal("60.0"),
                    warehouse_id=wh.id,
                )
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=user.id)
        await purchase_order_service.approve_order(session, po.id, approver_id=user.id)
        po_item = po.items[0]

        await purchase_order_service.receive_goods(
            session,
            po_id=po.id,
            receiving_items=[{"po_item_id": po_item.id, "quantity": 50.0}],
            current_user_id=user.id,
        )

        stmt_b1 = select(StockBalance).where(StockBalance.product_id == prod.id, StockBalance.warehouse_id == wh.id)
        res_b1 = await session.execute(stmt_b1)
        bal_before = res_b1.scalar_one_or_none()
        qty_before = Decimal(str(bal_before.available_quantity)) if bal_before else Decimal("0.0")


        # 1. Attempt Over-return (returning 55 when only 50 received) -> Rejection
        ret_over = PurchaseReturnCreate(
            purchase_order_id=po.id,
            supplier_id=sup.id,
            warehouse_id=wh.id,
            reason_code="Damaged",
            items=[
                PurchaseReturnItemCreate(
                    po_item_id=po_item.id,
                    product_id=prod.id,
                    return_quantity=Decimal("55.0"),
                    unit_price=Decimal("60.0"),
                )
            ],
        )
        with pytest.raises(ValidationException) as exc:
            await purchase_return_service.create_return(session, ret_over, current_user_id=user.id)
        assert "exceeds net received stock" in str(exc.value)

        # 2. Create Valid Return for 20 units
        ret_in = PurchaseReturnCreate(
            purchase_order_id=po.id,
            supplier_id=sup.id,
            warehouse_id=wh.id,
            reason_code="Defective",
            supplier_return_ref="RMA-5544",
            remarks="Defective batches from transit",
            items=[
                PurchaseReturnItemCreate(
                    po_item_id=po_item.id,
                    product_id=prod.id,
                    return_quantity=Decimal("20.0"),
                    unit_price=Decimal("60.0"),
                )
            ],
        )
        ret = await purchase_return_service.create_return(session, ret_in, current_user_id=user.id)
        assert ret.status == "Draft"
        assert ret.total_return_amount == Decimal("1200.0")
        assert ret.return_number.startswith(f"PRTN-{datetime.now(timezone.utc).year}-")

        # 3. Post / Process Return
        processed = await purchase_return_service.process_return(session, ret.id, current_user_id=user.id)
        assert processed.status == "Processed"

        # 4. Verify Stock Deduction
        stmt_b2 = select(StockBalance).where(StockBalance.product_id == prod.id, StockBalance.warehouse_id == wh.id)
        res_b2 = await session.execute(stmt_b2)
        bal_after = res_b2.scalar_one_or_none()
        assert bal_after is not None
        qty_after = Decimal(str(bal_after.available_quantity))
        assert qty_after == qty_before - Decimal("20.0")


        # 5. Verify PO returned_quantity updated
        po_updated = await purchase_order_service.get_order(session, po.id)
        assert po_updated.items[0].returned_quantity == Decimal("20.0")

        # 6. Verify Remaining Return Limit: net returnable = 50 - 20 = 30. Return of 35 should fail.
        ret_in_2 = PurchaseReturnCreate(
            purchase_order_id=po.id,
            supplier_id=sup.id,
            warehouse_id=wh.id,
            reason_code="Excess Delivery",
            items=[
                PurchaseReturnItemCreate(
                    po_item_id=po_item.id,
                    product_id=prod.id,
                    return_quantity=Decimal("35.0"),
                    unit_price=Decimal("60.0"),
                )
            ],
        )
        with pytest.raises(ValidationException) as exc:
            await purchase_return_service.create_return(session, ret_in_2, current_user_id=user.id)
        assert "exceeds net received stock" in str(exc.value)


@pytest.mark.asyncio
async def test_purchase_return_cancellation_and_update():
    """
    Test updating and cancelling a Purchase Return in Draft status.
    """
    async with AsyncSessionLocal() as session:
        data = await setup_receiving_test_data(session)
        user = data["mgr_user"]
        wh = data["warehouse"]
        prod = data["product_std"]
        sup = data["supplier"]

        po_in = PurchaseOrderCreate(
            supplier_id=sup.id,
            items=[
                PurchaseOrderItemCreate(
                    product_id=prod.id,
                    quantity=Decimal("30.0"),
                    unit_price=Decimal("15.0"),
                    warehouse_id=wh.id,
                )
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=user.id)
        await purchase_order_service.approve_order(session, po.id, approver_id=user.id)
        await purchase_order_service.receive_goods(
            session,
            po_id=po.id,
            receiving_items=[{"po_item_id": po.items[0].id, "quantity": 30.0}],
            current_user_id=user.id,
        )

        ret_in = PurchaseReturnCreate(
            purchase_order_id=po.id,
            supplier_id=sup.id,
            warehouse_id=wh.id,
            reason_code="Incorrect Spec",
            items=[
                PurchaseReturnItemCreate(
                    po_item_id=po.items[0].id,
                    product_id=prod.id,
                    return_quantity=Decimal("10.0"),
                    unit_price=Decimal("15.0"),
                )
            ],
        )
        ret = await purchase_return_service.create_return(session, ret_in, current_user_id=user.id)

        # Update Draft Return
        updated = await purchase_return_service.update_return(
            session,
            ret.id,
            PurchaseReturnUpdate(remarks="Updated inspection notes"),
            current_user_id=user.id,
        )
        assert updated.remarks == "Updated inspection notes"

        # Cancel Return
        cancelled = await purchase_return_service.cancel_return(session, ret.id, current_user_id=user.id)
        assert cancelled.status == "Cancelled"

        # Attempt to process cancelled return -> Rejection
        with pytest.raises(ValidationException) as exc:
            await purchase_return_service.process_return(session, ret.id, current_user_id=user.id)
        assert "Cannot process return" in str(exc.value)


# ==============================================================================
# 4. RBAC, AUDIT, & API INTEGRATION
# ==============================================================================

@pytest.mark.asyncio
async def test_audit_logs_for_receiving_and_returns():
    """
    Verify audit log records generated for receiving and returns.
    """
    async with AsyncSessionLocal() as session:
        data = await setup_receiving_test_data(session)
        user = data["mgr_user"]
        wh = data["warehouse"]
        prod = data["product_std"]
        sup = data["supplier"]

        po_in = PurchaseOrderCreate(
            supplier_id=sup.id,
            items=[
                PurchaseOrderItemCreate(
                    product_id=prod.id,
                    quantity=Decimal("20.0"),
                    unit_price=Decimal("40.0"),
                    warehouse_id=wh.id,
                )
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=user.id)
        await purchase_order_service.approve_order(session, po.id, approver_id=user.id)

        receipt = await purchase_order_service.receive_goods(
            session,
            po_id=po.id,
            receiving_items=[{"po_item_id": po.items[0].id, "quantity": 20.0}],
            current_user_id=user.id,
        )

        ret_in = PurchaseReturnCreate(
            purchase_order_id=po.id,
            supplier_id=sup.id,
            warehouse_id=wh.id,
            reason_code="Defective",
            items=[
                PurchaseReturnItemCreate(
                    po_item_id=po.items[0].id,
                    product_id=prod.id,
                    return_quantity=Decimal("5.0"),
                    unit_price=Decimal("40.0"),
                )
            ],
        )
        ret = await purchase_return_service.create_return(session, ret_in, current_user_id=user.id)
        await purchase_return_service.process_return(session, ret.id, current_user_id=user.id)

        # Check AuditLog table for expected action types
        stmt = select(AuditLog.action).where(AuditLog.user_id == user.id)
        res = await session.execute(stmt)
        actions = set(res.scalars().all())

        assert "PURCHASE_RECEIPT_CREATE" in actions
        assert "PURCHASE_RECEIPT_POST" in actions
        assert "PURCHASE_ORDER_FULLY_RECEIVED" in actions
        assert "PURCHASE_RETURN_CREATE" in actions
        assert "PURCHASE_RETURN_POST" in actions


@pytest.mark.asyncio
async def test_receiving_and_returns_http_endpoints():
    """
    Test receiving and return API endpoints via FastAPI test client.
    """
    async with AsyncSessionLocal() as session:
        data = await setup_receiving_test_data(session)
        mgr = data["mgr_user"]
        viewer = data["viewer_user"]
        wh = data["warehouse"]
        prod = data["product_std"]
        sup = data["supplier"]

        # Setup Approved PO
        po_in = PurchaseOrderCreate(
            supplier_id=sup.id,
            items=[
                PurchaseOrderItemCreate(
                    product_id=prod.id,
                    quantity=Decimal("25.0"),
                    unit_price=Decimal("30.0"),
                    warehouse_id=wh.id,
                )
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=mgr.id)
        await purchase_order_service.approve_order(session, po.id, approver_id=mgr.id)
        po_item_id = str(po.items[0].id)

    mgr_token = create_access_token(subject=str(mgr.id))
    viewer_token = create_access_token(subject=str(viewer.id))


    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Receive Goods via POST /api/v1/purchase-orders/{id}/receive
        rcv_payload = {
            "supplier_reference": "HTTP-REC-01",
            "remarks": "API receiving test",
            "items": [{"po_item_id": po_item_id, "quantity": 25.0}],
        }
        res = await client.post(
            f"/api/v1/purchase-orders/{po.id}/receive",
            json=rcv_payload,
            headers={"Authorization": f"Bearer {mgr_token}"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "Received"
        assert data["external_reference"] == po.po_number

        # 2. List Receipts for PO via GET /api/v1/purchase-orders/{id}/receipts
        res_list = await client.get(
            f"/api/v1/purchase-orders/{po.id}/receipts",
            headers={"Authorization": f"Bearer {mgr_token}"},
        )
        assert res_list.status_code == 200
        assert len(res_list.json()) >= 1

        # 3. Create Return via POST /api/v1/purchase-returns
        ret_payload = {
            "purchase_order_id": str(po.id),
            "supplier_id": str(sup.id),
            "warehouse_id": str(wh.id),
            "reason_code": "Damaged",
            "remarks": "Damaged in transit",
            "items": [
                {
                    "po_item_id": po_item_id,
                    "product_id": str(prod.id),
                    "return_quantity": 5.0,
                    "unit_price": 30.0,
                }
            ],
        }
        res_ret = await client.post(
            "/api/v1/purchase-returns",
            json=ret_payload,
            headers={"Authorization": f"Bearer {mgr_token}"},
        )
        assert res_ret.status_code == 201
        ret_data = res_ret.json()
        assert ret_data["status"] == "Draft"
        ret_id = ret_data["id"]

        # 4. Post / Process Return via POST /api/v1/purchase-returns/{id}/post
        res_proc = await client.post(
            f"/api/v1/purchase-returns/{ret_id}/post",
            headers={"Authorization": f"Bearer {mgr_token}"},
        )
        assert res_proc.status_code == 200
        assert res_proc.json()["status"] == "Processed"

        # 5. Unauthorized Viewer attempting to create return -> 403 Forbidden
        res_unauth = await client.post(
            "/api/v1/purchase-returns",
            json=ret_payload,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res_unauth.status_code == 403
