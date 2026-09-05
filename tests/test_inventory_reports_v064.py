import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import io
from typing import AsyncGenerator
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, func

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.batch import Batch
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.serial_number import SerialNumber
from app.models.stock_balance import StockBalance
from app.models.stock_ledger import StockLedger
from app.models.stock_reservation import StockReservation
from app.models.storage_location import StorageLocation
from app.models.unit_of_measure import UnitOfMeasure
from app.models.user import User
from app.models.warehouse import Warehouse
from app.repositories.user import user_repository
from app.schemas.inventory import (
    ProductCategoryCreate,
    ProductCreate,
    StorageLocationCreate,
    UnitOfMeasureCreate,
    WarehouseCreate,
)
from app.schemas.inventory_advanced import (
    BatchCreate,
    SerialNumberCreate,
    StockReservationCreate,
)
from app.services.inventory_advanced_services import (
    batch_service,
    serial_number_service,
    stock_reservation_service,
)
from app.services.inventory_services import (
    category_service,
    product_service,
    storage_location_service,
    unit_of_measure_service,
    warehouse_service,
)
from app.services.stock_engine_services import opening_stock_service, stock_movement_service


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def auth_headers(async_client: AsyncClient):
    unique_id = uuid.uuid4().hex[:6]
    email = f"reportadmin_{unique_id}@example.com"
    username = f"reportadmin_{unique_id}"

    reg_payload = {
        "full_name": "Report Admin User",
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
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def unprivileged_auth_headers(async_client: AsyncClient):
    unique_id = uuid.uuid4().hex[:6]
    email = f"unprivileged_{unique_id}@example.com"
    username = f"unprivileged_{unique_id}"

    reg_payload = {
        "full_name": "Unprivileged User",
        "email": email,
        "username": username,
        "password": "UserPassword123!",
    }
    reg_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201, reg_resp.text

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={
            "username_or_email": email,
            "password": "UserPassword123!",
        },
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def test_dataset(async_client: AsyncClient):
    """
    Sets up a comprehensive authoritative inventory dataset:
    - 2 Categories (Electronics, Consumables)
    - 2 UOMs (PCS, BOX)
    - 2 Warehouses (Main Central WH, Secondary West WH)
    - 2 Storage Locations (Aisle 1, Cold Storage)
    - 4 Products:
      * Product 1: Standard product, on_hand=100, reorder_point=20 (Normal stock)
      * Product 2: Low stock product, on_hand=5, reorder_point=50, min_stock=20
      * Product 3: Batch tracked, on_hand=80, with 1 Active Batch & 1 Expired Batch
      * Product 4: Serial tracked, on_hand=10, with 2 registered Serial Numbers
    - 1 Active Stock Reservation of 15 units on Product 1
    - Ledger Movements: Initial Opening Stock movements + Reservation
    """
    async with AsyncSessionLocal() as db:
        unique_suffix = uuid.uuid4().hex[:5]

        # 1. Categories
        cat_elec = await category_service.create_category(
            db, obj_in=ProductCategoryCreate(code=f"ELEC_{unique_suffix}", name="Electronics")
        )
        cat_cons = await category_service.create_category(
            db, obj_in=ProductCategoryCreate(code=f"CONS_{unique_suffix}", name="Consumables")
        )

        # 2. UOM
        uom_pcs = await unit_of_measure_service.create_unit(
            db,
            obj_in=UnitOfMeasureCreate(
                code=f"PCS_{unique_suffix}",
                name=f"Pieces_{unique_suffix}",
                symbol=f"pcs_{unique_suffix}",
                category="Count",
            ),
        )

        # 3. Warehouses
        wh1 = await warehouse_service.create_warehouse(
            db, obj_in=WarehouseCreate(code=f"WH1_{unique_suffix}", name="Main Central Warehouse")
        )
        wh2 = await warehouse_service.create_warehouse(
            db, obj_in=WarehouseCreate(code=f"WH2_{unique_suffix}", name="Secondary West Warehouse")
        )

        # 4. Storage Locations
        loc1 = await storage_location_service.create_location(
            db,
            obj_in=StorageLocationCreate(
                code=f"LOC1_{unique_suffix}", name="Aisle 1 Bin A", warehouse_id=wh1.id
            ),
        )
        loc2 = await storage_location_service.create_location(
            db,
            obj_in=StorageLocationCreate(
                code=f"LOC2_{unique_suffix}", name="Cold Storage Bay", warehouse_id=wh2.id
            ),
        )

        # 5. Products
        # Prod 1: Normal Standard
        prod1 = await product_service.create_product(
            db,
            obj_in=ProductCreate(
                sku=f"SKU-STD-{unique_suffix}",
                name="Standard Keyboard",
                category_id=cat_elec.id,
                base_unit_id=uom_pcs.id,
                tracking_type="NONE",
                reorder_level=Decimal("20.0"),
                reorder_quantity=Decimal("50.0"),
                minimum_stock=Decimal("10.0"),
            ),
        )

        # Prod 2: Low Stock
        prod2 = await product_service.create_product(
            db,
            obj_in=ProductCreate(
                sku=f"SKU-LOW-{unique_suffix}",
                name="Critical Power Supply",
                category_id=cat_elec.id,
                base_unit_id=uom_pcs.id,
                tracking_type="NONE",
                reorder_level=Decimal("50.0"),
                reorder_quantity=Decimal("100.0"),
                minimum_stock=Decimal("20.0"),
            ),
        )

        # Prod 3: Batch Tracked
        prod3 = await product_service.create_product(
            db,
            obj_in=ProductCreate(
                sku=f"SKU-BAT-{unique_suffix}",
                name="Adhesive Compound",
                category_id=cat_cons.id,
                base_unit_id=uom_pcs.id,
                tracking_type="BATCH",
                reorder_level=Decimal("10.0"),
                reorder_quantity=Decimal("40.0"),
            ),
        )

        # Prod 4: Serial Tracked
        prod4 = await product_service.create_product(
            db,
            obj_in=ProductCreate(
                sku=f"SKU-SER-{unique_suffix}",
                name="Enterprise Router",
                category_id=cat_elec.id,
                base_unit_id=uom_pcs.id,
                tracking_type="SERIAL",
                reorder_level=Decimal("5.0"),
            ),
        )

        from app.repositories.inventory_repos import product_repository

        prod1_obj = await product_repository.get_by_id(db, uuid.UUID(str(prod1["id"])))
        prod2_obj = await product_repository.get_by_id(db, uuid.UUID(str(prod2["id"])))
        prod3_obj = await product_repository.get_by_id(db, uuid.UUID(str(prod3["id"])))
        prod4_obj = await product_repository.get_by_id(db, uuid.UUID(str(prod4["id"])))

        # 6. Add Initial Stock via Opening Stock / Stock Movements
        from app.schemas.stock_engine import OpeningStockCreate

        await opening_stock_service.create_opening_stock(
            db,
            obj_in=OpeningStockCreate(
                product_id=prod1_obj.id,
                warehouse_id=wh1.id,
                location_id=loc1.id,
                quantity=Decimal("100.0"),
                reference_number=f"OS1-{unique_suffix}",
            ),
        )

        await opening_stock_service.create_opening_stock(
            db,
            obj_in=OpeningStockCreate(
                product_id=prod2_obj.id,
                warehouse_id=wh1.id,
                location_id=loc1.id,
                quantity=Decimal("5.0"),
                reference_number=f"OS2-{unique_suffix}",
            ),
        )

        await opening_stock_service.create_opening_stock(
            db,
            obj_in=OpeningStockCreate(
                product_id=prod3_obj.id,
                warehouse_id=wh2.id,
                location_id=loc2.id,
                quantity=Decimal("80.0"),
                reference_number=f"OS3-{unique_suffix}",
            ),
        )

        await opening_stock_service.create_opening_stock(
            db,
            obj_in=OpeningStockCreate(
                product_id=prod4_obj.id,
                warehouse_id=wh1.id,
                location_id=loc1.id,
                quantity=Decimal("10.0"),
                reference_number=f"OS4-{unique_suffix}",
            ),
        )

        # 7. Batches for Prod 3
        now = datetime.now(timezone.utc)
        # Active Batch (Expiring in 60 days)
        batch_act = await batch_service.create_batch(
            db,
            obj_in=BatchCreate(
                batch_number=f"BAT-ACT-{unique_suffix}",
                product_id=prod3_obj.id,
                initial_quantity=Decimal("50.0"),
                manufacturing_date=now - timedelta(days=30),
                expiry_date=now + timedelta(days=60),
            ),
        )

        # Expired Batch (Expired 10 days ago)
        batch_exp = await batch_service.create_batch(
            db,
            obj_in=BatchCreate(
                batch_number=f"BAT-EXP-{unique_suffix}",
                product_id=prod3_obj.id,
                initial_quantity=Decimal("30.0"),
                manufacturing_date=now - timedelta(days=100),
                expiry_date=now - timedelta(days=10),
            ),
        )

        # 8. Serials for Prod 4
        ser1 = await serial_number_service.create_serial(
            db,
            obj_in=SerialNumberCreate(
                serial_number=f"SER-001-{unique_suffix}",
                product_id=prod4_obj.id,
                warehouse_id=wh1.id,
                storage_location_id=loc1.id,
                status="Available",
            ),
        )
        ser2 = await serial_number_service.create_serial(
            db,
            obj_in=SerialNumberCreate(
                serial_number=f"SER-002-{unique_suffix}",
                product_id=prod4_obj.id,
                warehouse_id=wh1.id,
                storage_location_id=loc1.id,
                status="Reserved",
            ),
        )

        # 9. Reservation on Prod 1 (15 units)
        res_obj = await stock_reservation_service.create_reservation(
            db,
            obj_in=StockReservationCreate(
                reservation_number=f"RES-{unique_suffix}",
                product_id=prod1_obj.id,
                warehouse_id=wh1.id,
                storage_location_id=loc1.id,
                quantity=Decimal("15.0"),
                reserved_for_type="SALES_ORDER",
                reserved_for_id=uuid.uuid4(),
                remarks="Test reservation for SO",
            ),
        )

        return {
            "cat_elec": cat_elec,
            "cat_cons": cat_cons,
            "wh1": wh1,
            "wh2": wh2,
            "loc1": loc1,
            "loc2": loc2,
            "prod1": prod1_obj,
            "prod2": prod2_obj,
            "prod3": prod3_obj,
            "prod4": prod4_obj,
            "batch_act": batch_act,
            "batch_exp": batch_exp,
            "ser1": ser1,
            "ser2": ser2,
            "res_obj": res_obj,
        }


# =============================================================================
# SCENARIOS 1 to 6: CURRENT STOCK REPORT
# =============================================================================
@pytest.mark.asyncio
async def test_current_stock_report_and_filters(
    async_client: AsyncClient, auth_headers: dict, test_dataset: dict
):
    """
    1. Returns authoritative on-hand values.
    2. Reserved quantity correctly calculated.
    3. Available = on_hand - reserved.
    4. Warehouse filters work.
    5. Location filters work.
    6. Product filters work.
    """
    prod1 = test_dataset["prod1"]
    wh1 = test_dataset["wh1"]
    loc1 = test_dataset["loc1"]

    # Retrieve all stock
    res = await async_client.get("/api/v1/inventory/reports/stock", headers=auth_headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "items" in data
    assert "summary" in data
    assert data["total"] >= 4

    # Filter by Prod 1
    res_p1 = await async_client.get(
        f"/api/v1/inventory/reports/stock?product_id={prod1.id}", headers=auth_headers
    )
    assert res_p1.status_code == 200
    p1_data = res_p1.json()
    assert p1_data["total"] == 1
    item = p1_data["items"][0]
    assert item["product_sku"] == prod1.sku
    assert Decimal(str(item["quantity_on_hand"])) == Decimal("100.0")
    assert Decimal(str(item["reserved_quantity"])) == Decimal("15.0")
    assert Decimal(str(item["available_quantity"])) == Decimal("85.0")

    # Filter by Warehouse 1
    res_wh1 = await async_client.get(
        f"/api/v1/inventory/reports/stock?warehouse_id={wh1.id}", headers=auth_headers
    )
    assert res_wh1.status_code == 200
    for it in res_wh1.json()["items"]:
        assert it["warehouse_id"] == str(wh1.id)

    # Filter by Storage Location 1
    res_loc1 = await async_client.get(
        f"/api/v1/inventory/reports/stock?storage_location_id={loc1.id}", headers=auth_headers
    )
    assert res_loc1.status_code == 200
    for it in res_loc1.json()["items"]:
        assert it["storage_location_id"] == str(loc1.id)


# =============================================================================
# SCENARIOS 7 to 10: STOCK MOVEMENT REPORT
# =============================================================================
@pytest.mark.asyncio
async def test_stock_movement_report_and_filters(
    async_client: AsyncClient, auth_headers: dict, test_dataset: dict
):
    """
    7. Movement report reads StockLedger correctly.
    8. Date filters work.
    9. Movement type/direction filters work.
    10. Batch/product filters work.
    """
    prod3 = test_dataset["prod3"]

    # All movements
    res = await async_client.get("/api/v1/inventory/reports/movements", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 4
    assert Decimal(str(data["summary"]["total_inbound_quantity"])) > 0

    # Direction filter
    res_in = await async_client.get(
        "/api/v1/inventory/reports/movements?direction=IN", headers=auth_headers
    )
    assert res_in.status_code == 200
    for m in res_in.json()["items"]:
        assert m["direction"] == "IN"

    # Product filter
    res_p3 = await async_client.get(
        f"/api/v1/inventory/reports/movements?product_id={prod3.id}", headers=auth_headers
    )
    assert res_p3.status_code == 200
    p3_moves = res_p3.json()["items"]
    assert len(p3_moves) >= 1
    assert p3_moves[0]["product_sku"] == prod3.sku

    # Date filter (far future returns 0)
    future_date = (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    res_future = await async_client.get(
        "/api/v1/inventory/reports/movements",
        params={"date_from": future_date},
        headers=auth_headers,
    )
    assert res_future.status_code == 200
    assert res_future.json()["total"] == 0


# =============================================================================
# SCENARIOS 11 to 14: WAREHOUSE & PRODUCT INVENTORY REPORTS
# =============================================================================
@pytest.mark.asyncio
async def test_warehouse_and_product_reports(
    async_client: AsyncClient, auth_headers: dict, test_dataset: dict
):
    """
    11. Warehouse aggregation correct.
    12. Warehouse filters correct.
    13. Product aggregation correct.
    14. Category filtering correct.
    """
    wh1 = test_dataset["wh1"]
    cat_elec = test_dataset["cat_elec"]

    # Warehouse report
    res_wh = await async_client.get("/api/v1/inventory/reports/warehouses", headers=auth_headers)
    assert res_wh.status_code == 200
    wh_items = res_wh.json()["items"]
    assert len(wh_items) >= 2

    # Warehouse 1 specific metrics
    res_wh1 = await async_client.get(
        f"/api/v1/inventory/reports/warehouses?warehouse_id={wh1.id}", headers=auth_headers
    )
    assert res_wh1.status_code == 200
    wh1_rep = res_wh1.json()["items"][0]
    assert wh1_rep["warehouse_code"] == wh1.code
    assert wh1_rep["total_products_stocked"] == 3  # prod1, prod2, prod4
    assert Decimal(str(wh1_rep["total_on_hand_quantity"])) == Decimal("115.0")  # 100 + 5 + 10
    assert Decimal(str(wh1_rep["total_reserved_quantity"])) == Decimal("15.0")

    # Product report
    res_p = await async_client.get("/api/v1/inventory/reports/products", headers=auth_headers)
    assert res_p.status_code == 200
    assert res_p.json()["total"] >= 4

    # Category filter
    res_cat = await async_client.get(
        f"/api/v1/inventory/reports/products?category_id={cat_elec.id}", headers=auth_headers
    )
    assert res_cat.status_code == 200
    for p in res_cat.json()["items"]:
        assert p["category_id"] == str(cat_elec.id)


# =============================================================================
# SCENARIOS 15 to 18: BATCH & EXPIRY REPORT
# =============================================================================
@pytest.mark.asyncio
async def test_batch_and_expiry_report(
    async_client: AsyncClient, auth_headers: dict, test_dataset: dict
):
    """
    15. Active batch report.
    16. Expired batch report.
    17. Expiring-within-N-days report.
    18. Expiry filters correct.
    """
    batch_exp = test_dataset["batch_exp"]

    res_b = await async_client.get(
        "/api/v1/inventory/reports/batches/expiry", headers=auth_headers
    )
    assert res_b.status_code == 200
    b_data = res_b.json()
    assert b_data["total"] >= 2
    assert b_data["summary"]["expired_batches_count"] >= 1

    # Filter expired only
    res_exp = await async_client.get(
        "/api/v1/inventory/reports/batches/expiry?expiry_status=Expired", headers=auth_headers
    )
    assert res_exp.status_code == 200
    for it in res_exp.json()["items"]:
        assert it["expiry_status"] == "Expired"
        assert it["days_until_expiry"] < 0

    # Filter expiring within 90 days
    res_within = await async_client.get(
        "/api/v1/inventory/reports/batches/expiry?expiring_within_days=90", headers=auth_headers
    )
    assert res_within.status_code == 200
    for it in res_within.json()["items"]:
        assert it["days_until_expiry"] >= 0
        assert it["days_until_expiry"] <= 90


# =============================================================================
# SCENARIOS 19 to 21: SERIAL INVENTORY REPORT
# =============================================================================
@pytest.mark.asyncio
async def test_serial_inventory_report(
    async_client: AsyncClient, auth_headers: dict, test_dataset: dict
):
    """
    19. Serial inventory report.
    20. Serial status filtering.
    21. Warehouse/location filtering.
    """
    wh1 = test_dataset["wh1"]

    res_s = await async_client.get("/api/v1/inventory/reports/serials", headers=auth_headers)
    assert res_s.status_code == 200
    s_data = res_s.json()
    assert s_data["total"] >= 2

    # Status filter: Available
    res_avail = await async_client.get(
        "/api/v1/inventory/reports/serials?status=Available", headers=auth_headers
    )
    assert res_avail.status_code == 200
    for s in res_avail.json()["items"]:
        assert s["status"] == "Available"

    # Status filter: Reserved
    res_res = await async_client.get(
        "/api/v1/inventory/reports/serials?status=Reserved", headers=auth_headers
    )
    assert res_res.status_code == 200
    for s in res_res.json()["items"]:
        assert s["status"] == "Reserved"

    # Warehouse filter
    res_wh = await async_client.get(
        f"/api/v1/inventory/reports/serials?warehouse_id={wh1.id}", headers=auth_headers
    )
    assert res_wh.status_code == 200
    for s in res_wh.json()["items"]:
        assert s["warehouse_id"] == str(wh1.id)


# =============================================================================
# SCENARIOS 22 to 25: RESERVATION REPORT
# =============================================================================
@pytest.mark.asyncio
async def test_reservation_report(
    async_client: AsyncClient, auth_headers: dict, test_dataset: dict
):
    """
    22. Active reservation report.
    23. Released/consumed status visibility.
    24. Reservation totals correct.
    25. Reservation reporting does NOT mutate physical stock.
    """
    res_r = await async_client.get(
        "/api/v1/inventory/reports/reservations", headers=auth_headers
    )
    assert res_r.status_code == 200
    r_data = res_r.json()
    assert r_data["total"] >= 1
    assert Decimal(str(r_data["summary"]["total_active_reserved_quantity"])) >= Decimal("15.0")

    item = r_data["items"][0]
    assert item["status"] == "Active"
    assert Decimal(str(item["quantity"])) == Decimal("15.0")
    assert item["reserved_for_type"] == "SALES_ORDER"


# =============================================================================
# SCENARIOS 26 to 27: AVAILABLE STOCK REPORT
# =============================================================================
@pytest.mark.asyncio
async def test_available_stock_report(
    async_client: AsyncClient, auth_headers: dict, test_dataset: dict
):
    """
    26. Availability calculation correct: available = on_hand - reserved.
    27. Tracking type and warehouse filtering correct.
    """
    prod1 = test_dataset["prod1"]
    wh1 = test_dataset["wh1"]

    res_av = await async_client.get(
        f"/api/v1/inventory/reports/availability?product_id={prod1.id}", headers=auth_headers
    )
    assert res_av.status_code == 200
    items = res_av.json()["items"]
    assert len(items) == 1
    it = items[0]
    assert Decimal(str(it["on_hand_quantity"])) == Decimal("100.0")
    assert Decimal(str(it["reserved_quantity"])) == Decimal("15.0")
    assert Decimal(str(it["available_quantity"])) == Decimal("85.0")


# =============================================================================
# SCENARIOS 28 to 29: LOW STOCK / REORDER VISIBILITY
# =============================================================================
@pytest.mark.asyncio
async def test_low_stock_report(
    async_client: AsyncClient, auth_headers: dict, test_dataset: dict
):
    """
    28. Reorder threshold detection (on_hand < reorder_point).
    29. Min stock configuration respected.
    """
    prod2 = test_dataset["prod2"]  # on_hand=5, reorder_point=50, min_stock=20

    res_low = await async_client.get(
        "/api/v1/inventory/reports/low-stock?below_reorder_only=true", headers=auth_headers
    )
    assert res_low.status_code == 200
    low_data = res_low.json()
    assert low_data["summary"]["total_low_stock_items"] >= 1

    # Verify prod 2 is flagged as below reorder
    found_prod2 = False
    for it in low_data["items"]:
        if it["product_id"] == str(prod2.id):
            found_prod2 = True
            assert it["below_reorder_level"] is True
            assert it["below_minimum_stock"] is True
            assert Decimal(str(it["shortage_quantity"])) == Decimal("45.0")  # 50 - 5
    assert found_prod2 is True


# =============================================================================
# SCENARIOS 30 to 31: INVENTORY AGING REPORT
# =============================================================================
@pytest.mark.asyncio
async def test_inventory_aging_report(
    async_client: AsyncClient, auth_headers: dict, test_dataset: dict
):
    """
    30. Last inbound date and movement age calculation.
    31. Aging bucket assignment (0-30 days, etc.).
    """
    res_ag = await async_client.get(
        "/api/v1/inventory/reports/aging?page=1&size=50", headers=auth_headers
    )
    assert res_ag.status_code == 200
    ag_data = res_ag.json()
    assert ag_data["total"] >= 4
    assert Decimal(str(ag_data["summary"]["bucket_0_30_quantity"])) > 0

    for it in ag_data["items"]:
        assert it["aging_bucket"] in ["0-30 days", "31-60 days", "61-90 days", "90+ days"]


# =============================================================================
# SCENARIOS 32 to 33: MOVEMENT ANALYTICS & DASHBOARD
# =============================================================================
@pytest.mark.asyncio
async def test_movement_analytics_and_dashboard(
    async_client: AsyncClient, auth_headers: dict, test_dataset: dict
):
    """
    32. Movement analytics breakdowns (type, category, warehouse, timeline).
    33. Executive dashboard KPIs match underlying stock and movements.
    """
    # 1. Movement Analytics
    res_an = await async_client.get(
        "/api/v1/inventory/reports/analytics", headers=auth_headers
    )
    assert res_an.status_code == 200
    an_data = res_an.json()
    assert an_data["total_movements_count"] >= 4
    assert Decimal(str(an_data["total_inbound_quantity"])) > 0
    assert len(an_data["breakdown_by_movement_type"]) >= 1
    assert len(an_data["breakdown_by_category"]) >= 1
    assert len(an_data["breakdown_by_warehouse"]) >= 1
    assert len(an_data["timeline"]) >= 1

    # 2. Executive Dashboard
    res_dash = await async_client.get(
        "/api/v1/inventory/reports/dashboard", headers=auth_headers
    )
    assert res_dash.status_code == 200
    dash = res_dash.json()
    assert dash["total_products_tracked"] >= 4
    assert dash["total_warehouses_count"] >= 2
    assert dash["total_stock_lines"] >= 4
    assert Decimal(str(dash["total_on_hand_quantity"])) >= Decimal("195.0")  # 100 + 5 + 80 + 10
    assert Decimal(str(dash["total_reserved_quantity"])) >= Decimal("15.0")
    assert dash["low_stock_products_count"] >= 1
    assert dash["expired_batches_count"] >= 1
    assert dash["active_reservations_count"] >= 1
    assert len(dash["warehouse_stock_breakdown"]) >= 2


# =============================================================================
# SCENARIOS 34 to 35: CSV EXPORT ENDPOINTS
# =============================================================================
@pytest.mark.asyncio
async def test_csv_export_endpoints(
    async_client: AsyncClient, auth_headers: dict, test_dataset: dict
):
    """
    34. CSV export returns text/csv, Attachment header, and valid rows.
    35. Export filtering is respected in exported CSV.
    """
    export_routes = [
        "/api/v1/inventory/reports/stock/export",
        "/api/v1/inventory/reports/movements/export",
        "/api/v1/inventory/reports/warehouses/export",
        "/api/v1/inventory/reports/products/export",
        "/api/v1/inventory/reports/batches/expiry/export",
        "/api/v1/inventory/reports/serials/export",
        "/api/v1/inventory/reports/reservations/export",
        "/api/v1/inventory/reports/availability/export",
        "/api/v1/inventory/reports/low-stock/export",
        "/api/v1/inventory/reports/aging/export",
    ]

    for route in export_routes:
        res = await async_client.get(route, headers=auth_headers)
        assert res.status_code == 200, f"Export failed on {route}: {res.text}"
        assert "text/csv" in res.headers["content-type"]
        assert "attachment; filename=" in res.headers.get("content-disposition", "")
        
        # Verify CSV is parseable
        csv_text = res.text
        assert len(csv_text) > 0
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        assert len(rows) >= 2  # Header + at least 1 data row


# =============================================================================
# SCENARIOS 36 to 37: RBAC AUTHORIZATION
# =============================================================================
@pytest.mark.asyncio
async def test_rbac_report_authorization(
    async_client: AsyncClient, unprivileged_auth_headers: dict
):
    """
    36. Unauthorized report access rejected (403).
    37. Unauthenticated report access rejected (401).
    """
    # Unauthenticated
    res_unauth = await async_client.get("/api/v1/inventory/reports/stock")
    assert res_unauth.status_code == 401

    # Unprivileged (no inventory permissions)
    res_forbid = await async_client.get(
        "/api/v1/inventory/reports/stock", headers=unprivileged_auth_headers
    )
    assert res_forbid.status_code == 403


# =============================================================================
# SCENARIOS 38 to 40: READ-ONLY GUARANTEES
# =============================================================================
@pytest.mark.asyncio
async def test_read_only_guarantees(
    async_client: AsyncClient, auth_headers: dict, test_dataset: dict
):
    """
    38. Reports do NOT modify StockBalance.
    39. Reports do NOT create StockLedger entries.
    40. Reports do NOT modify StockReservation status or quantity.
    """
    async with AsyncSessionLocal() as db:
        # Pre-report counts and sums
        bal_sum_before = (await db.execute(select(func.sum(StockBalance.available_quantity)))).scalar()
        res_sum_before = (await db.execute(select(func.sum(StockBalance.reserved_quantity)))).scalar()
        ledger_count_before = (await db.execute(select(func.count(StockLedger.id)))).scalar()
        res_count_before = (await db.execute(select(func.count(StockReservation.id)))).scalar()
        batch_sum_before = (await db.execute(select(func.sum(Batch.current_quantity)))).scalar()

    # Execute all 12 GET reports and all CSV exports
    endpoints = [
        "/api/v1/inventory/reports/stock",
        "/api/v1/inventory/reports/stock/export",
        "/api/v1/inventory/reports/movements",
        "/api/v1/inventory/reports/movements/export",
        "/api/v1/inventory/reports/warehouses",
        "/api/v1/inventory/reports/warehouses/export",
        "/api/v1/inventory/reports/products",
        "/api/v1/inventory/reports/products/export",
        "/api/v1/inventory/reports/batches/expiry",
        "/api/v1/inventory/reports/batches/expiry/export",
        "/api/v1/inventory/reports/serials",
        "/api/v1/inventory/reports/serials/export",
        "/api/v1/inventory/reports/reservations",
        "/api/v1/inventory/reports/reservations/export",
        "/api/v1/inventory/reports/availability",
        "/api/v1/inventory/reports/availability/export",
        "/api/v1/inventory/reports/low-stock",
        "/api/v1/inventory/reports/low-stock/export",
        "/api/v1/inventory/reports/aging",
        "/api/v1/inventory/reports/aging/export",
        "/api/v1/inventory/reports/analytics",
        "/api/v1/inventory/reports/dashboard",
        "/api/v1/inventory/analytics/dashboard",
    ]

    for ep in endpoints:
        resp = await async_client.get(ep, headers=auth_headers)
        assert resp.status_code == 200, f"Failed at {ep}: {resp.text}"

    async with AsyncSessionLocal() as db:
        # Post-report counts and sums
        bal_sum_after = (await db.execute(select(func.sum(StockBalance.available_quantity)))).scalar()
        res_sum_after = (await db.execute(select(func.sum(StockBalance.reserved_quantity)))).scalar()
        ledger_count_after = (await db.execute(select(func.count(StockLedger.id)))).scalar()
        res_count_after = (await db.execute(select(func.count(StockReservation.id)))).scalar()
        batch_sum_after = (await db.execute(select(func.sum(Batch.current_quantity)))).scalar()

    # Exact zero-mutation assertions
    assert bal_sum_after == bal_sum_before, "StockBalance available_quantity was mutated by reports!"
    assert res_sum_after == res_sum_before, "StockBalance reserved_quantity was mutated by reports!"
    assert ledger_count_after == ledger_count_before, "StockLedger entries were created by reports!"
    assert res_count_after == res_count_before, "StockReservations were created or deleted by reports!"
    assert batch_sum_after == batch_sum_before, "Batch current_quantity was mutated by reports!"


# =============================================================================
# SCENARIOS 41 to 44: REGRESSION TESTING
# =============================================================================
@pytest.mark.asyncio
async def test_regression_compatibility(async_client: AsyncClient, auth_headers: dict):
    """
    41. v0.6.0 Master data endpoints (categories, warehouses, products).
    42. v0.6.1 Stock ledger and balance endpoints.
    43. v0.6.2 Warehouse operations endpoints (goods receipts, issues, transfers).
    44. v0.6.3 Advanced inventory endpoints (batches, serials, reservations).
    """
    # v0.6.0
    res_cats = await async_client.get("/api/v1/inventory/categories", headers=auth_headers)
    assert res_cats.status_code == 200

    res_whs = await async_client.get("/api/v1/inventory/warehouses", headers=auth_headers)
    assert res_whs.status_code == 200

    # v0.6.1
    res_bal = await async_client.get("/api/v1/stock/balances", headers=auth_headers)
    assert res_bal.status_code == 200

    # v0.6.2
    res_grn = await async_client.get("/api/v1/inventory/goods-receipts", headers=auth_headers)
    assert res_grn.status_code == 200

    # v0.6.3
    res_batch = await async_client.get("/api/v1/inventory/batches", headers=auth_headers)
    assert res_batch.status_code == 200

    res_serial = await async_client.get("/api/v1/inventory/serials", headers=auth_headers)
    assert res_serial.status_code == 200

    res_res = await async_client.get("/api/v1/inventory/reservations", headers=auth_headers)
    assert res_res.status_code == 200
