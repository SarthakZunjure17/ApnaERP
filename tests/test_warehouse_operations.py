from decimal import Decimal
from typing import AsyncGenerator
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.goods_issue import GoodsIssue
from app.models.goods_receipt import GoodsReceipt
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.stock_balance import StockBalance
from app.models.stock_ledger import StockLedger
from app.models.stock_transfer import StockTransfer
from app.models.storage_location import StorageLocation
from app.models.unit_of_measure import UnitOfMeasure
from app.models.warehouse import Warehouse
from app.repositories.user import user_repository
from app.services.stock_engine_services import stock_ledger_service
from app.services.warehouse_operations_services import (
    goods_issue_service,
    goods_receipt_service,
    stock_transfer_service,
)
from app.schemas.warehouse_operations import (
    GoodsIssueCreate,
    GoodsIssueItemCreate,
    GoodsReceiptCreate,
    GoodsReceiptItemCreate,
    StockTransferCreate,
    StockTransferItemCreate,
)
from app.exceptions.base import ValidationException


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def auth_headers(async_client: AsyncClient):
    unique_id = uuid.uuid4().hex[:6]
    email = f"whadmin_{unique_id}@example.com"
    username = f"whadmin_{unique_id}"

    reg_payload = {
        "full_name": "Warehouse Admin User",
        "email": email,
        "username": username,
        "password": "AdminPassword123!",
    }
    reg_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201, reg_resp.text
    user_id = uuid.UUID(reg_resp.json()["id"])

    async with AsyncSessionLocal() as session:
        from app.db.seed_rbac import seed_rbac_data
        from app.repositories.rbac import role_repository, user_role_repository
        user = await user_repository.get_by_id(session, user_id)
        role = await role_repository.get_by_name(session, "Super Admin")
        if not role:
            await seed_rbac_data(session)
            role = await role_repository.get_by_name(session, "Super Admin")
        if user and role:
            user.is_superuser = True
            await user_role_repository.assign_role_to_user(session, user_id=user.id, role_id=role.id)
            await session.commit()



    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={
            "username_or_email": email,
            "password": "AdminPassword123!",
        },
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_goods_receipt_lifecycle_and_ledger_integration():
    async with AsyncSessionLocal() as session:
        cat = ProductCategory(code=f"CAT-GR-{uuid.uuid4().hex[:6]}", name="Receipt Category")
        wh = Warehouse(code=f"WH-GR-{uuid.uuid4().hex[:6]}", name="Receipt WH", is_active=True)
        uom = UnitOfMeasure(name=f"Pieces {uuid.uuid4().hex[:4]}", symbol=f"pcs_{uuid.uuid4().hex[:4]}", category="Unit")
        session.add_all([cat, wh, uom])
        await session.commit()

        loc = StorageLocation(warehouse_id=wh.id, code=f"LOC-GR-{uuid.uuid4().hex[:6]}", name="Bin A")
        session.add(loc)
        await session.commit()

        prod = Product(
            sku=f"SKU-GR-{uuid.uuid4().hex[:6]}",
            name="Goods Receipt Test Item",
            category_id=cat.id,
            base_unit_id=uom.id,
            track_inventory=True,
            allow_negative_stock=False,
            status="Active",
        )
        session.add(prod)
        await session.commit()

        # Create GoodsReceipt
        receipt_in = GoodsReceiptCreate(
            receipt_number=f"GR-{uuid.uuid4().hex[:8]}",
            warehouse_id=wh.id,
            supplier_reference="SUPP-12345",
            remarks="Initial vendor receiving test",
            items=[
                GoodsReceiptItemCreate(
                    product_id=prod.id,
                    storage_location_id=loc.id,
                    quantity=Decimal("150.0000"),
                    unit_id=uom.id,
                    unit_cost=Decimal("25.5000"),
                )
            ],
        )

        receipt = await goods_receipt_service.create_receipt(session, receipt_in)
        assert receipt.status == "Draft"
        assert len(receipt.items) == 1

        # Approve GoodsReceipt
        approved = await goods_receipt_service.approve_receipt(session, receipt.id)
        assert approved.status == "Approved"

        # Receive GoodsReceipt (Execute)
        received = await goods_receipt_service.receive_receipt(session, receipt.id)
        assert received.status == "Received"

        # Verify StockLedger IN entry created
        ledger_entries = (
            await session.execute(
                select(StockLedger).where(
                    StockLedger.reference_type == "GoodsReceipt", StockLedger.reference_id == receipt.id
                )
            )
        ).scalars().all()

        assert len(ledger_entries) == 1
        entry = ledger_entries[0]
        assert entry.product_id == prod.id
        assert entry.warehouse_id == wh.id
        assert entry.quantity == Decimal("150.0000")
        assert entry.direction == "IN"
        assert entry.running_balance == Decimal("150.0000")

        # Verify StockBalance projection updated
        balance = (
            await session.execute(
                select(StockBalance).where(
                    StockBalance.product_id == prod.id,
                    StockBalance.warehouse_id == wh.id,
                    StockBalance.storage_location_id == loc.id,
                )
            )
        ).scalar_one_or_none()
        assert balance is not None
        assert balance.available_quantity == Decimal("150.0000")

        # Verify terminal status immutability guard
        with pytest.raises(ValidationException):
            await goods_receipt_service.cancel_receipt(session, receipt.id)


@pytest.mark.asyncio
async def test_goods_issue_lifecycle_and_negative_stock_validation():
    async with AsyncSessionLocal() as session:
        cat = ProductCategory(code=f"CAT-GI-{uuid.uuid4().hex[:6]}", name="Issue Category")
        wh = Warehouse(code=f"WH-GI-{uuid.uuid4().hex[:6]}", name="Issue WH", is_active=True)
        uom = UnitOfMeasure(name=f"Kilos {uuid.uuid4().hex[:4]}", symbol=f"kg_{uuid.uuid4().hex[:4]}", category="Weight")
        session.add_all([cat, wh, uom])
        await session.commit()

        prod = Product(
            sku=f"SKU-GI-{uuid.uuid4().hex[:6]}",
            name="Goods Issue Test Item",
            category_id=cat.id,
            base_unit_id=uom.id,
            track_inventory=True,
            allow_negative_stock=False,
            is_stockable=True,
            status="Active",
        )
        session.add(prod)
        await session.commit()
        await session.refresh(prod)

        wh_id = wh.id
        prod_id = prod.id
        uom_id = uom.id

        # Seed initial stock of 50.00
        await stock_ledger_service.create_ledger_entry(
            session,
            product_id=prod_id,
            warehouse_id=wh_id,
            storage_location_id=None,
            transaction_type_code="OPENING_STOCK",
            quantity=Decimal("50.0000"),
            direction="IN",
            unit_id=uom_id,
        )

        # Attempt to issue 100.00 (exceeds stock of 50.00)
        excess_issue_in = GoodsIssueCreate(
            issue_number=f"GI-ERR-{uuid.uuid4().hex[:6]}",
            warehouse_id=wh_id,
            issue_reason="Consumption",
            items=[
                GoodsIssueItemCreate(
                    product_id=prod_id,
                    quantity=Decimal("100.0000"),
                )
            ],
        )

        excess_issue = await goods_issue_service.create_issue(session, excess_issue_in)
        excess_issue_id = excess_issue.id
        with pytest.raises(ValidationException):
            await goods_issue_service.issue_issue(session, excess_issue_id)

        # Issue valid quantity of 30.00
        valid_issue_in = GoodsIssueCreate(
            issue_number=f"GI-OK-{uuid.uuid4().hex[:6]}",
            warehouse_id=wh_id,
            issue_reason="Internal",
            items=[
                GoodsIssueItemCreate(
                    product_id=prod_id,
                    quantity=Decimal("30.0000"),
                )
            ],
        )

        valid_issue = await goods_issue_service.create_issue(session, valid_issue_in)
        valid_issue_id = valid_issue.id
        issued = await goods_issue_service.issue_issue(session, valid_issue_id)
        assert issued.status == "Issued"

        # Verify StockLedger OUT entry and running balance (50 - 30 = 20)
        ledger_entries = (
            await session.execute(
                select(StockLedger).where(
                    StockLedger.reference_type == "GoodsIssue", StockLedger.reference_id == valid_issue_id
                )
            )
        ).scalars().all()

        assert len(ledger_entries) == 1
        assert ledger_entries[0].running_balance == Decimal("20.0000")


@pytest.mark.asyncio
async def test_stock_transfer_lifecycle():
    async with AsyncSessionLocal() as session:
        cat = ProductCategory(code=f"CAT-TR-{uuid.uuid4().hex[:6]}", name="Transfer Category")
        wh_src = Warehouse(code=f"WH-SRC-{uuid.uuid4().hex[:6]}", name="Source WH", is_active=True)
        wh_dest = Warehouse(code=f"WH-DST-{uuid.uuid4().hex[:6]}", name="Destination WH", is_active=True)
        uom = UnitOfMeasure(name=f"Boxes {uuid.uuid4().hex[:4]}", symbol=f"box_{uuid.uuid4().hex[:4]}", category="Unit")
        session.add_all([cat, wh_src, wh_dest, uom])
        await session.commit()

        prod = Product(
            sku=f"SKU-TR-{uuid.uuid4().hex[:6]}",
            name="Stock Transfer Item",
            category_id=cat.id,
            base_unit_id=uom.id,
            track_inventory=True,
            allow_negative_stock=False,
            status="Active",
        )
        session.add(prod)
        await session.commit()

        # Seed initial stock of 200.00 at Source WH
        await stock_ledger_service.create_ledger_entry(
            session,
            product_id=prod.id,
            warehouse_id=wh_src.id,
            storage_location_id=None,
            transaction_type_code="OPENING_STOCK",
            quantity=Decimal("200.0000"),
            direction="IN",
            unit_id=uom.id,
        )

        # Validate same source and destination warehouse failure
        with pytest.raises(ValidationException):
            await stock_transfer_service.create_transfer(
                session,
                StockTransferCreate(
                    transfer_number=f"TR-FAIL-{uuid.uuid4().hex[:6]}",
                    source_warehouse_id=wh_src.id,
                    destination_warehouse_id=wh_src.id,
                    items=[StockTransferItemCreate(product_id=prod.id, quantity=Decimal("50.0000"))],
                ),
            )

        # Create valid StockTransfer for 75.00
        transfer_in = StockTransferCreate(
            transfer_number=f"TR-{uuid.uuid4().hex[:8]}",
            source_warehouse_id=wh_src.id,
            destination_warehouse_id=wh_dest.id,
            remarks="Inter-branch warehouse transfer",
            items=[
                StockTransferItemCreate(
                    product_id=prod.id,
                    quantity=Decimal("75.0000"),
                )
            ],
        )

        transfer = await stock_transfer_service.create_transfer(session, transfer_in)
        assert transfer.status == "Draft"

        # Dispatch Transfer (In Transit)
        dispatched = await stock_transfer_service.dispatch_transfer(session, transfer.id)
        assert dispatched.status == "In Transit"

        # Verify OUT ledger at Source WH (200 - 75 = 125 balance at source)
        src_ledger = (
            await session.execute(
                select(StockLedger).where(
                    StockLedger.warehouse_id == wh_src.id,
                    StockLedger.reference_type == "StockTransfer",
                )
            )
        ).scalars().all()
        assert len(src_ledger) == 1
        assert src_ledger[0].direction == "OUT"
        assert src_ledger[0].running_balance == Decimal("125.0000")

        # Complete Transfer into Destination WH
        completed = await stock_transfer_service.complete_transfer(session, transfer.id)
        assert completed.status == "Completed"

        # Verify IN ledger at Destination WH (75 balance at dest)
        dest_ledger = (
            await session.execute(
                select(StockLedger).where(
                    StockLedger.warehouse_id == wh_dest.id,
                    StockLedger.reference_type == "StockTransfer",
                )
            )
        ).scalars().all()
        assert len(dest_ledger) == 1
        assert dest_ledger[0].direction == "IN"
        assert dest_ledger[0].running_balance == Decimal("75.0000")

        # Total quantity preserved across system: 125 + 75 = 200
        total_balance = (
            await session.execute(
                select(StockBalance.available_quantity).where(StockBalance.product_id == prod.id)
            )
        ).scalars().all()
        assert sum(total_balance) == Decimal("200.0000")


@pytest.mark.asyncio
async def test_cancelled_document_generates_zero_ledger_entries():
    async with AsyncSessionLocal() as session:
        cat = ProductCategory(code=f"CAT-CNC-{uuid.uuid4().hex[:6]}", name="Cancel Category")
        wh = Warehouse(code=f"WH-CNC-{uuid.uuid4().hex[:6]}", name="Cancel WH", is_active=True)
        uom = UnitOfMeasure(name=f"Units {uuid.uuid4().hex[:4]}", symbol=f"u_{uuid.uuid4().hex[:4]}", category="Unit")
        session.add_all([cat, wh, uom])
        await session.commit()

        prod = Product(
            sku=f"SKU-CNC-{uuid.uuid4().hex[:6]}",
            name="Cancel Test Item",
            category_id=cat.id,
            base_unit_id=uom.id,
            track_inventory=True,
            status="Active",
        )
        session.add(prod)
        await session.commit()

        receipt = await goods_receipt_service.create_receipt(
            session,
            GoodsReceiptCreate(
                receipt_number=f"GR-CNC-{uuid.uuid4().hex[:6]}",
                warehouse_id=wh.id,
                items=[GoodsReceiptItemCreate(product_id=prod.id, quantity=Decimal("10.0000"))],
            ),
        )

        cancelled = await goods_receipt_service.cancel_receipt(session, receipt.id)
        assert cancelled.status == "Cancelled"

        # Verify ZERO ledger entries
        entries = (
            await session.execute(
                select(StockLedger).where(
                    StockLedger.reference_type == "GoodsReceipt", StockLedger.reference_id == receipt.id
                )
            )
        ).scalars().all()
        assert len(entries) == 0


@pytest.mark.asyncio
async def test_warehouse_operations_api_endpoints(async_client: AsyncClient, auth_headers: dict):
    async with AsyncSessionLocal() as session:
        cat = ProductCategory(code=f"CAT-API-{uuid.uuid4().hex[:6]}", name="API Category")
        wh = Warehouse(code=f"WH-API-{uuid.uuid4().hex[:6]}", name="API WH", is_active=True)
        uom = UnitOfMeasure(name=f"Items {uuid.uuid4().hex[:4]}", symbol=f"itm_{uuid.uuid4().hex[:4]}", category="Unit")
        session.add_all([cat, wh, uom])
        await session.commit()

        prod = Product(
            sku=f"SKU-API-{uuid.uuid4().hex[:6]}",
            name="API Test Item",
            category_id=cat.id,
            base_unit_id=uom.id,
            track_inventory=True,
            status="Active",
        )
        session.add(prod)
        await session.commit()

    # 1. Goods Receipt API
    gr_payload = {
        "receipt_number": f"GR-API-{uuid.uuid4().hex[:6]}",
        "warehouse_id": str(wh.id),
        "remarks": "API Created Receipt",
        "items": [{"product_id": str(prod.id), "quantity": "50.0000", "unit_cost": "12.0000"}],
    }
    res = await async_client.post("/api/v1/inventory/goods-receipts", json=gr_payload, headers=auth_headers)
    assert res.status_code == 201, res.text
    gr_id = res.json()["id"]

    res = await async_client.get(f"/api/v1/inventory/goods-receipts/{gr_id}", headers=auth_headers)
    assert res.status_code == 200

    res = await async_client.post(f"/api/v1/inventory/goods-receipts/{gr_id}/receive", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "Received"

    # 2. Goods Issue API
    gi_payload = {
        "issue_number": f"GI-API-{uuid.uuid4().hex[:6]}",
        "warehouse_id": str(wh.id),
        "issue_reason": "Consumption",
        "remarks": "API Created Issue",
        "items": [{"product_id": str(prod.id), "quantity": "20.0000"}],
    }
    res = await async_client.post("/api/v1/inventory/goods-issues", json=gi_payload, headers=auth_headers)
    assert res.status_code == 201, res.text
    gi_id = res.json()["id"]

    res = await async_client.post(f"/api/v1/inventory/goods-issues/{gi_id}/issue", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "Issued"
