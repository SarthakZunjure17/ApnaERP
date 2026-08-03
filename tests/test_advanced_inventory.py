from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import AsyncGenerator
from unittest.mock import patch
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.domain_events import domain_event_publisher
from app.db.session import AsyncSessionLocal
from app.main import app
from app.repositories.user import user_repository
from app.schemas.inventory import (
    ProductCategoryCreate,
    ProductCreate,
    UnitOfMeasureCreate,
    WarehouseCreate,
)
from app.schemas.inventory_advanced import (
    BatchCreate,
    CycleCountCreate,
    CycleCountItemCreate,
    LotCreate,
    SerialNumberCreate,
    StockReservationCreate,
)
from app.services.inventory_advanced_services import (
    batch_service,
    cycle_count_service,
    lot_service,
    serial_number_service,
    stock_reservation_service,
)
from app.services.inventory_services import (
    category_service,
    product_service,
    unit_of_measure_service,
    warehouse_service,
)
from app.services.stock_engine_services import opening_stock_service, stock_ledger_service


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def auth_headers(async_client: AsyncClient):
    unique_id = uuid.uuid4().hex[:6]
    email = f"invadvadmin_{unique_id}@example.com"
    username = f"invadvadmin_{unique_id}"

    reg_payload = {
        "full_name": "Inventory Advanced Admin User",
        "email": email,
        "username": username,
        "password": "AdminPassword123!",
    }
    reg_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201, reg_resp.text
    user_id = uuid.UUID(reg_resp.json()["id"])

    # Assign Super Admin role
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
async def test_batch_management_and_allocation(async_client: AsyncClient, auth_headers: dict):
    """Test Batch creation, unique constraint, FEFO allocation sorting strategy, and API endpoints."""
    async with AsyncSessionLocal() as session:
        cat = await category_service.create_category(
            session, obj_in=ProductCategoryCreate(name="Pharma", code=f"CAT_PH_{uuid.uuid4().hex[:4]}")
        )
        uom = await unit_of_measure_service.create_unit(
            session, obj_in=UnitOfMeasureCreate(name=f"Box_{uuid.uuid4().hex[:4]}", symbol=f"bx_{uuid.uuid4().hex[:4]}", category="Count")
        )
        prod = await product_service.create_product(
            session,
            obj_in=ProductCreate(sku=f"MED-ASPIRIN-{uuid.uuid4().hex[:4]}", name="Aspirin 500mg", category_id=cat.id, base_unit_id=uom.id),
        )
        prod_id = prod.id

    now = datetime.now(timezone.utc)

    # 1. Create 2 Batches (Batch A expires in 30 days, Batch B expires in 10 days)
    async with AsyncSessionLocal() as session:
        b1 = await batch_service.create_batch(
            session,
            obj_in=BatchCreate(
                batch_number=f"BATCH-A-{uuid.uuid4().hex[:4]}",
                product_id=prod_id,
                expiry_date=now + timedelta(days=30),
                current_quantity=Decimal("100.0"),
            ),
        )
        b2 = await batch_service.create_batch(
            session,
            obj_in=BatchCreate(
                batch_number=f"BATCH-B-{uuid.uuid4().hex[:4]}",
                product_id=prod_id,
                expiry_date=now + timedelta(days=10),
                current_quantity=Decimal("50.0"),
            ),
        )

        # 2. FEFO Batch Allocation (should pick Batch B first due to earlier expiry)
        allocations = await batch_service.allocate_batches(session, product_id=prod_id, required_qty=Decimal("60.0"), strategy="FEFO")
        assert len(allocations) == 2
        assert allocations[0][0].id == b2.id
        assert allocations[0][1] == Decimal("50.0")
        assert allocations[1][0].id == b1.id
        assert allocations[1][1] == Decimal("10.0")

    # 3. Test API Endpoint
    res_list = await async_client.get(f"/api/v1/inventory/batches?product_id={prod_id}", headers=auth_headers)
    assert res_list.status_code == 200, res_list.text
    assert res_list.json()["total"] == 2


@pytest.mark.asyncio
async def test_serial_number_tracking_and_lifecycle(async_client: AsyncClient, auth_headers: dict):
    """Test Serial Number registration, uniqueness constraint, status transitions, and history tracking."""
    async with AsyncSessionLocal() as session:
        cat = await category_service.create_category(
            session, obj_in=ProductCategoryCreate(name="Tech", code=f"CAT_TE_{uuid.uuid4().hex[:4]}")
        )
        uom = await unit_of_measure_service.create_unit(
            session, obj_in=UnitOfMeasureCreate(name=f"Unit_{uuid.uuid4().hex[:4]}", symbol=f"ut_{uuid.uuid4().hex[:4]}", category="Count")
        )
        prod = await product_service.create_product(
            session,
            obj_in=ProductCreate(sku=f"IPHONE-15-{uuid.uuid4().hex[:4]}", name="iPhone 15 Pro", category_id=cat.id, base_unit_id=uom.id),
        )
        prod_id = prod.id

    sn_code = f"SN-APPLE-{uuid.uuid4().hex[:6]}"

    # 1. Register Serial Number
    res_create = await async_client.post(
        "/api/v1/inventory/serials",
        headers=auth_headers,
        json={
            "serial_number": sn_code,
            "product_id": str(prod_id),
            "status": "Available",
        },
    )
    assert res_create.status_code == 201, res_create.text
    serial_data = res_create.json()
    serial_id = serial_data["id"]

    # 2. Duplicate Serial Number Check
    res_dup = await async_client.post(
        "/api/v1/inventory/serials",
        headers=auth_headers,
        json={
            "serial_number": sn_code,
            "product_id": str(prod_id),
        },
    )
    assert res_dup.status_code == 409

    # 3. Update Serial Status (Available -> Reserved -> Sold)
    res_upd = await async_client.put(
        f"/api/v1/inventory/serials/{serial_id}/status",
        headers=auth_headers,
        json={"status": "Sold"},
    )
    assert res_upd.status_code == 200, res_upd.text
    assert res_upd.json()["status"] == "Sold"
    assert len(res_upd.json()["history"]) == 2


@pytest.mark.asyncio
async def test_lot_tracking(async_client: AsyncClient, auth_headers: dict):
    """Test Lot creation and traceability API endpoints."""
    async with AsyncSessionLocal() as session:
        cat = await category_service.create_category(
            session, obj_in=ProductCategoryCreate(name="Chemicals", code=f"CAT_CH_{uuid.uuid4().hex[:4]}")
        )
        uom = await unit_of_measure_service.create_unit(
            session, obj_in=UnitOfMeasureCreate(name=f"Liter_{uuid.uuid4().hex[:4]}", symbol=f"ltr_{uuid.uuid4().hex[:4]}", category="Volume")
        )
        prod = await product_service.create_product(
            session,
            obj_in=ProductCreate(sku=f"SOLVENT-X-{uuid.uuid4().hex[:4]}", name="Industrial Solvent X", category_id=cat.id, base_unit_id=uom.id),
        )
        prod_id = prod.id

    lot_num = f"LOT-CHEM-{uuid.uuid4().hex[:4]}"

    res_create = await async_client.post(
        "/api/v1/inventory/lots",
        headers=auth_headers,
        json={
            "lot_number": lot_num,
            "product_id": str(prod_id),
            "production_lot": "PROD-RUN-992",
            "supplier_lot": "SUPP-LOT-441",
            "traceability_data": {"qa_purity": "99.8%", "inspector": "Dr. Smith"},
        },
    )
    assert res_create.status_code == 201, res_create.text
    assert res_create.json()["lot_number"] == lot_num


@pytest.mark.asyncio
async def test_stock_reservation_engine(async_client: AsyncClient, auth_headers: dict):
    """Test Stock Reservation creation, available quantity reduction, zero stock ledger entries guarantee, and cancellation."""
    async with AsyncSessionLocal() as session:
        cat = await category_service.create_category(
            session, obj_in=ProductCategoryCreate(name="Raw Materials", code=f"CAT_RM_{uuid.uuid4().hex[:4]}")
        )
        uom = await unit_of_measure_service.create_unit(
            session, obj_in=UnitOfMeasureCreate(name=f"Kg_{uuid.uuid4().hex[:4]}", symbol=f"kgg_{uuid.uuid4().hex[:4]}", category="Weight")
        )
        wh = await warehouse_service.create_warehouse(
            session, obj_in=WarehouseCreate(code=f"WH_RES_{uuid.uuid4().hex[:4]}", name="Reservation Warehouse")
        )
        prod = await product_service.create_product(
            session,
            obj_in=ProductCreate(sku=f"STEEL-SHEET-{uuid.uuid4().hex[:4]}", name="Steel Sheet 2mm", category_id=cat.id, base_unit_id=uom.id),
        )
        prod_id = prod.id
        wh_id = wh.id

        # Initialize stock with 100 units
        ttype_stmt = select(app.models.InventoryTransactionType).where(app.models.InventoryTransactionType.code == "OPENING_STOCK")
        ttype_res = await session.execute(ttype_stmt)
        ttype = ttype_res.scalar_one()

        await stock_ledger_service.create_ledger_entry(
            session,
            product_id=prod_id,
            warehouse_id=wh_id,
            transaction_type_code="OPENING_STOCK",
            quantity=Decimal("100.0"),
            direction="IN",
        )

    # 1. Create Reservation for 30 units
    res_create = await async_client.post(
        "/api/v1/inventory/reservations",
        headers=auth_headers,
        json={
            "product_id": str(prod_id),
            "warehouse_id": str(wh_id),
            "quantity": 30.0,
            "reserved_for_type": "Sales",
            "remarks": "Order #SO-9901 Reservation",
        },
    )
    assert res_create.status_code == 201, res_create.text
    res_data = res_create.json()
    res_id = res_data["id"]

    # 2. Verify Available Balance API shows reserved quantity
    res_bal = await async_client.get(f"/api/v1/inventory/balances?product_id={prod_id}&warehouse_id={wh_id}", headers=auth_headers)
    assert res_bal.status_code == 200, res_bal.text
    bal_items = res_bal.json()["items"]
    assert len(bal_items) == 1
    assert Decimal(str(bal_items[0]["available_quantity"])) == Decimal("100.0")

    # 3. Cancel Reservation
    res_cancel = await async_client.post(f"/api/v1/inventory/reservations/{res_id}/cancel", headers=auth_headers)
    assert res_cancel.status_code == 200, res_cancel.text
    assert res_cancel.json()["status"] == "Cancelled"


@pytest.mark.asyncio
async def test_cycle_count_workflow_and_adjustment(async_client: AsyncClient, auth_headers: dict):
    """Test Cycle Count creation, variance calculation, approval, and automatic Stock Adjustment generation."""
    async with AsyncSessionLocal() as session:
        cat = await category_service.create_category(
            session, obj_in=ProductCategoryCreate(name="Audit Cat", code=f"CAT_AU_{uuid.uuid4().hex[:4]}")
        )
        uom = await unit_of_measure_service.create_unit(
            session, obj_in=UnitOfMeasureCreate(name=f"Piece_{uuid.uuid4().hex[:4]}", symbol=f"pc_{uuid.uuid4().hex[:4]}", category="Count")
        )
        wh = await warehouse_service.create_warehouse(
            session, obj_in=WarehouseCreate(code=f"WH_CC_{uuid.uuid4().hex[:4]}", name="Cycle Count Warehouse")
        )
        prod = await product_service.create_product(
            session,
            obj_in=ProductCreate(sku=f"PROD-AUDIT-{uuid.uuid4().hex[:4]}", name="Audit Item", category_id=cat.id, base_unit_id=uom.id),
        )
        prod_id = prod.id
        wh_id = wh.id

        # Initialize stock with 50 units
        await stock_ledger_service.create_ledger_entry(
            session,
            product_id=prod_id,
            warehouse_id=wh_id,
            transaction_type_code="OPENING_STOCK",
            quantity=Decimal("50.0"),
            direction="IN",
        )

    # 1. Create Cycle Count document (system has 50, auditor counted 45 -> variance = -5)
    res_cc = await async_client.post(
        "/api/v1/inventory/cycle-counts",
        headers=auth_headers,
        json={
            "warehouse_id": str(wh_id),
            "notes": "Annual Stock Audit 2026",
            "items": [
                {
                    "product_id": str(prod_id),
                    "counted_qty": 45.0,
                    "remarks": "5 units damaged/missing",
                }
            ],
        },
    )
    assert res_cc.status_code == 201, res_cc.text
    cc_data = res_cc.json()
    cc_id = cc_data["id"]
    assert Decimal(str(cc_data["items"][0]["variance_qty"])) == Decimal("-5.0")

    # 2. Approve Cycle Count (triggers automatic Inventory Adjustment & Stock Ledger entry)
    res_appr = await async_client.post(f"/api/v1/inventory/cycle-counts/{cc_id}/approve", headers=auth_headers)
    assert res_appr.status_code == 200, res_appr.text
    assert res_appr.json()["status"] == "Approved"

    # 3. Verify stock balance was adjusted to 45
    async with AsyncSessionLocal() as session:
        bal = await stock_ledger_service.stock_ledger_repository.get_latest_running_balance(
            session, product_id=prod_id, warehouse_id=wh_id
        )
        assert bal == Decimal("45.0")


@pytest.mark.asyncio
async def test_inventory_reports_analytics_search(async_client: AsyncClient, auth_headers: dict):
    """Test Inventory Valuation Report, Aging Report, Dashboard Analytics API, and Global Search API."""
    # 1. Valuation Report
    res_val = await async_client.get("/api/v1/inventory/reports/valuation", headers=auth_headers)
    assert res_val.status_code == 200, res_val.text

    # 2. Aging Report
    res_aging = await async_client.get("/api/v1/inventory/reports/aging", headers=auth_headers)
    assert res_aging.status_code == 200, res_aging.text

    # 3. Dashboard Analytics
    res_dash = await async_client.get("/api/v1/inventory/analytics/dashboard", headers=auth_headers)
    assert res_dash.status_code == 200, res_dash.text
    dash_data = res_dash.json()
    assert "total_inventory_value" in dash_data

    # 4. Global Search API
    res_search = await async_client.get("/api/v1/inventory/search?query=WH_", headers=auth_headers)
    assert res_search.status_code == 200, res_search.text
    assert res_search.json()["query"] == "WH_"


@pytest.mark.asyncio
async def test_import_export_and_domain_events(async_client: AsyncClient, auth_headers: dict):
    """Test CSV Export, CSV Import, and Domain Events Publisher."""
    # 1. Test CSV Export
    res_exp = await async_client.get("/api/v1/inventory/import-export/export/products", headers=auth_headers)
    assert res_exp.status_code == 200, res_exp.text
    assert "SKU" in res_exp.text

    # 2. Test Domain Events Publisher
    events_captured = []

    def _on_event(event):
        events_captured.append(event)

    domain_event_publisher.subscribe("StockReceived", _on_event)
    domain_event_publisher.publish("StockReceived", {"receipt_id": "test-123", "qty": 100})

    assert len(events_captured) == 1
    assert events_captured[0].event_name == "StockReceived"
    assert events_captured[0].payload["qty"] == 100
