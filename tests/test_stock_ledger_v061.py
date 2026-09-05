import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import AsyncGenerator
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.exceptions.base import NotFoundException, ValidationException
from app.main import app
from app.models.audit_log import AuditLog
from app.models.inventory_policy import InventoryPolicy
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.storage_location import StorageLocation
from app.models.stock_balance import StockBalance
from app.models.stock_ledger import StockLedger
from app.models.unit_of_measure import UnitOfMeasure
from app.models.warehouse import Warehouse
from app.repositories.user import user_repository
from app.schemas.stock_engine import StockMovementCreate
from app.services.stock_engine_services import (
    stock_balance_service,
    stock_ledger_service,
    stock_movement_service,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def auth_headers(async_client: AsyncClient):
    unique_id = uuid.uuid4().hex[:6]
    email = f"stockadmin_{unique_id}@example.com"
    username = f"stockadmin_{unique_id}"

    reg_payload = {
        "full_name": "Stock Admin User",
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


@pytest_asyncio.fixture(scope="function")
async def sample_setup(db_session: AsyncSession):
    uid = uuid.uuid4().hex[:6]
    cat = ProductCategory(code=f"CAT-{uid}", name=f"Category {uid}")
    unit = UnitOfMeasure(code=f"UOM-{uid}", name=f"Unit {uid}", symbol=f"u_{uid}", category="Count")
    wh = Warehouse(code=f"WH-{uid}", name=f"Warehouse {uid}", is_active=True)
    wh_other = Warehouse(code=f"WH-OTHER-{uid}", name=f"Other Warehouse {uid}", is_active=True)
    db_session.add_all([cat, unit, wh, wh_other])
    await db_session.flush()

    loc = StorageLocation(warehouse_id=wh.id, code=f"LOC-A1-{uid}", name="Rack A1", is_active=True)
    loc_other = StorageLocation(warehouse_id=wh_other.id, code=f"LOC-B1-{uid}", name="Rack B1", is_active=True)
    db_session.add_all([loc, loc_other])
    await db_session.flush()

    prod = Product(
        sku=f"SKU-STOCK-{uid}",
        name=f"Stockable Product {uid}",
        category_id=cat.id,
        base_unit_id=unit.id,
        is_active=True,
        is_stockable=True,
        track_inventory=True,
        allow_negative_stock=False,
    )
    non_stock_prod = Product(
        sku=f"SKU-NONSTOCK-{uid}",
        name=f"Service Product {uid}",
        category_id=cat.id,
        base_unit_id=unit.id,
        is_active=True,
        is_stockable=False,
        track_inventory=False,
    )
    db_session.add_all([prod, non_stock_prod])
    await db_session.commit()

    return {
        "category": cat,
        "unit": unit,
        "warehouse": wh,
        "warehouse_other": wh_other,
        "location": loc,
        "location_other": loc_other,
        "product": prod,
        "non_stock_product": non_stock_prod,
    }


# ============================================================
# SECTION A: STOCK IN OPERATIONS
# ============================================================

@pytest.mark.asyncio
async def test_initial_stock_in(db_session: AsyncSession, sample_setup: dict):
    """Verify initial stock IN creates balance and immutable ledger entry with before=0, after=qty."""
    wh = sample_setup["warehouse"]
    prod = sample_setup["product"]
    loc = sample_setup["location"]

    ledger = await stock_movement_service.stock_in(
        db_session,
        product_id=prod.id,
        warehouse_id=wh.id,
        storage_location_id=loc.id,
        quantity=Decimal("100.0000"),
        reason="Initial batch receipt",
        notes="First batch intake",
    )

    assert ledger.id is not None
    assert ledger.movement_type == "STOCK_IN"
    assert ledger.direction == "IN"
    assert Decimal(str(ledger.quantity)) == Decimal("100.0000")
    assert Decimal(str(ledger.quantity_before)) == Decimal("0.0000")
    assert Decimal(str(ledger.quantity_after)) == Decimal("100.0000")
    assert Decimal(str(ledger.running_balance)) == Decimal("100.0000")

    # Authoritative balance verification
    bal = await stock_balance_service.get_balances(
        db_session, product_id=prod.id, warehouse_id=wh.id, location_id=loc.id
    )
    assert len(bal) == 1
    assert Decimal(str(bal[0].quantity_on_hand)) == Decimal("100.0000")
    assert Decimal(str(bal[0].available_quantity)) == Decimal("100.0000")


@pytest.mark.asyncio
async def test_repeated_stock_in(db_session: AsyncSession, sample_setup: dict):
    """Verify repeated stock IN accumulates quantity and captures precise before/after locked states."""
    wh = sample_setup["warehouse"]
    prod = sample_setup["product"]
    loc = sample_setup["location"]

    l1 = await stock_movement_service.stock_in(
        db_session, product_id=prod.id, warehouse_id=wh.id, storage_location_id=loc.id, quantity=Decimal("50.0000")
    )
    assert Decimal(str(l1.quantity_before)) == Decimal("0.0000")
    assert Decimal(str(l1.quantity_after)) == Decimal("50.0000")

    l2 = await stock_movement_service.stock_in(
        db_session, product_id=prod.id, warehouse_id=wh.id, storage_location_id=loc.id, quantity=Decimal("75.5000")
    )
    assert Decimal(str(l2.quantity_before)) == Decimal("50.0000")
    assert Decimal(str(l2.quantity_after)) == Decimal("125.5000")

    bal = await stock_balance_service.get_balances(db_session, product_id=prod.id, warehouse_id=wh.id, location_id=loc.id)
    assert Decimal(str(bal[0].quantity_on_hand)) == Decimal("125.5000")


# ============================================================
# SECTION B: STOCK OUT OPERATIONS
# ============================================================

@pytest.mark.asyncio
async def test_valid_stock_out(db_session: AsyncSession, sample_setup: dict):
    """Verify valid stock OUT reduces balance and captures before/after quantities."""
    wh = sample_setup["warehouse"]
    prod = sample_setup["product"]
    loc = sample_setup["location"]

    await stock_movement_service.stock_in(
        db_session, product_id=prod.id, warehouse_id=wh.id, storage_location_id=loc.id, quantity=Decimal("100.0000")
    )

    out_ledger = await stock_movement_service.stock_out(
        db_session,
        product_id=prod.id,
        warehouse_id=wh.id,
        storage_location_id=loc.id,
        quantity=Decimal("35.0000"),
        reason="Manual material dispatch",
    )

    assert out_ledger.movement_type == "STOCK_OUT"
    assert out_ledger.direction == "OUT"
    assert Decimal(str(out_ledger.quantity)) == Decimal("35.0000")
    assert Decimal(str(out_ledger.quantity_before)) == Decimal("100.0000")
    assert Decimal(str(out_ledger.quantity_after)) == Decimal("65.0000")

    bal = await stock_balance_service.get_balances(db_session, product_id=prod.id, warehouse_id=wh.id, location_id=loc.id)
    assert Decimal(str(bal[0].quantity_on_hand)) == Decimal("65.0000")


@pytest.mark.asyncio
async def test_exact_depletion_stock_out(db_session: AsyncSession, sample_setup: dict):
    """Verify exact stock OUT depleting balance to precisely 0.0 is permitted."""
    wh = sample_setup["warehouse"]
    prod = sample_setup["product"]

    await stock_movement_service.stock_in(
        db_session, product_id=prod.id, warehouse_id=wh.id, quantity=Decimal("40.0000")
    )

    out_ledger = await stock_movement_service.stock_out(
        db_session, product_id=prod.id, warehouse_id=wh.id, quantity=Decimal("40.0000")
    )

    assert Decimal(str(out_ledger.quantity_after)) == Decimal("0.0000")
    bal = await stock_balance_service.get_balances(db_session, product_id=prod.id, warehouse_id=wh.id)
    assert Decimal(str(bal[0].quantity_on_hand)) == Decimal("0.0000")


@pytest.mark.asyncio
async def test_insufficient_stock_rejection(db_session: AsyncSession, sample_setup: dict):
    """Verify stock OUT exceeding available quantity is rejected when negative stock is disabled."""
    wh = sample_setup["warehouse"]
    prod = sample_setup["product"]

    await stock_movement_service.stock_in(
        db_session, product_id=prod.id, warehouse_id=wh.id, quantity=Decimal("20.0000")
    )

    with pytest.raises(ValidationException) as excinfo:
        await stock_movement_service.stock_out(
            db_session, product_id=prod.id, warehouse_id=wh.id, quantity=Decimal("25.0000")
        )
    assert "Insufficient stock" in str(excinfo.value)

    # Verify balance was unaffected
    bal = await stock_balance_service.get_balances(db_session, product_id=prod.id, warehouse_id=wh.id)
    assert Decimal(str(bal[0].quantity_on_hand)) == Decimal("20.0000")


# ============================================================
# SECTION C: ADJUSTMENT OPERATIONS
# ============================================================

@pytest.mark.asyncio
async def test_adjustment_in_and_out(db_session: AsyncSession, sample_setup: dict):
    """Verify generic ADJUSTMENT with explicit IN / OUT directions."""
    wh = sample_setup["warehouse"]
    prod = sample_setup["product"]

    # Initial IN = 50
    await stock_movement_service.stock_in(db_session, prod.id, wh.id, Decimal("50.0000"))

    # Adjustment IN = 10 -> 60
    adj_in = await stock_movement_service.adjustment(
        db_session, prod.id, wh.id, Decimal("10.0000"), direction="IN", reason="Found misplaced unit"
    )
    assert adj_in.movement_type == "ADJUSTMENT"
    assert adj_in.direction == "IN"
    assert Decimal(str(adj_in.quantity_after)) == Decimal("60.0000")

    # Adjustment OUT = 15 -> 45
    adj_out = await stock_movement_service.adjustment(
        db_session, prod.id, wh.id, Decimal("15.0000"), direction="OUT", reason="Damaged in shelf"
    )
    assert adj_out.movement_type == "ADJUSTMENT"
    assert adj_out.direction == "OUT"
    assert Decimal(str(adj_out.quantity_after)) == Decimal("45.0000")

    bal = await stock_balance_service.get_balances(db_session, prod.id, wh.id)
    assert Decimal(str(bal[0].quantity_on_hand)) == Decimal("45.0000")


# ============================================================
# SECTION D: IDEMPOTENCY
# ============================================================

@pytest.mark.asyncio
async def test_idempotent_stock_movement(db_session: AsyncSession, sample_setup: dict):
    """Verify submitting same idempotency_key returns identical movement without double-counting balance."""
    wh = sample_setup["warehouse"]
    prod = sample_setup["product"]
    loc = sample_setup["location"]
    idem_key = f"IDEM-KEY-{uuid.uuid4().hex}"

    mov = StockMovementCreate(
        product_id=prod.id,
        warehouse_id=wh.id,
        storage_location_id=loc.id,
        movement_type="STOCK_IN",
        quantity=Decimal("50.0000"),
        idempotency_key=idem_key,
    )

    m1 = await stock_movement_service.process_movement(db_session, mov)
    assert Decimal(str(m1.quantity_after)) == Decimal("50.0000")

    # Second submission with identical key
    m2 = await stock_movement_service.process_movement(db_session, mov)
    assert m1.id == m2.id

    # Check that balance remains exactly 50 (NOT 100!)
    bal = await stock_balance_service.get_balances(db_session, prod.id, wh.id, loc.id)
    assert Decimal(str(bal[0].quantity_on_hand)) == Decimal("50.0000")

    # Check that ledger contains only 1 entry
    entries, total = await stock_ledger_service.get_ledger_entries(db_session, product_id=prod.id, warehouse_id=wh.id)
    assert total == 1


# ============================================================
# SECTION E: NEGATIVE STOCK POLICY RESOLUTION
# ============================================================

@pytest.mark.asyncio
async def test_negative_stock_policy_warehouse_override(db_session: AsyncSession, sample_setup: dict):
    """Verify warehouse-specific policy allows negative stock even when global/product default is False."""
    wh = sample_setup["warehouse"]
    prod = sample_setup["product"]

    # Global policy: negative_stock_allowed = False
    global_policy = InventoryPolicy(
        warehouse_id=None,
        valuation_method="FIFO",
        negative_stock_allowed=False,
        is_active=True,
    )
    # Warehouse policy: negative_stock_allowed = True
    wh_policy = InventoryPolicy(
        warehouse_id=wh.id,
        valuation_method="FIFO",
        negative_stock_allowed=True,
        is_active=True,
    )
    db_session.add_all([global_policy, wh_policy])
    await db_session.commit()

    # OUT 20 from 0 initial stock -> should succeed and result in -20
    ledger = await stock_movement_service.stock_out(
        db_session, product_id=prod.id, warehouse_id=wh.id, quantity=Decimal("20.0000"), reason="Authorized negative dispatch"
    )
    assert Decimal(str(ledger.quantity_before)) == Decimal("0.0000")
    assert Decimal(str(ledger.quantity_after)) == Decimal("-20.0000")

    bal = await stock_balance_service.get_balances(db_session, prod.id, wh.id)
    assert Decimal(str(bal[0].quantity_on_hand)) == Decimal("-20.0000")


# ============================================================
# SECTION F: VALIDATION & ERROR HANDLING
# ============================================================

@pytest.mark.asyncio
async def test_cross_warehouse_location_rejection(db_session: AsyncSession, sample_setup: dict):
    """Verify assigning a storage location belonging to Warehouse B to Warehouse A is rejected."""
    wh_a = sample_setup["warehouse"]
    loc_b = sample_setup["location_other"]
    prod = sample_setup["product"]

    with pytest.raises(ValidationException) as excinfo:
        await stock_movement_service.stock_in(
            db_session,
            product_id=prod.id,
            warehouse_id=wh_a.id,
            storage_location_id=loc_b.id,
            quantity=Decimal("10.0000"),
        )
    assert "does not belong to the specified warehouse" in str(excinfo.value)


@pytest.mark.asyncio
async def test_non_stockable_product_rejection(db_session: AsyncSession, sample_setup: dict):
    """Verify non-stockable products cannot receive inventory movements."""
    wh = sample_setup["warehouse"]
    non_stock_prod = sample_setup["non_stock_product"]

    with pytest.raises(ValidationException) as excinfo:
        await stock_movement_service.stock_in(
            db_session,
            product_id=non_stock_prod.id,
            warehouse_id=wh.id,
            quantity=Decimal("10.0000"),
        )
    assert "not configured as stockable" in str(excinfo.value) or "does not track inventory" in str(excinfo.value)


@pytest.mark.asyncio
async def test_zero_and_negative_quantity_rejection(db_session: AsyncSession, sample_setup: dict):
    """Verify movement with quantity <= 0 is strictly rejected."""
    wh = sample_setup["warehouse"]
    prod = sample_setup["product"]

    with pytest.raises(ValidationException):
        await stock_movement_service.stock_in(db_session, prod.id, wh.id, Decimal("0.0000"))

    with pytest.raises(ValidationException):
        await stock_movement_service.stock_in(db_session, prod.id, wh.id, Decimal("-10.0000"))


# ============================================================
# SECTION G: CONCURRENCY PROTECTION
# ============================================================

@pytest.mark.asyncio
async def test_concurrent_stock_out_insufficient_protection(sample_setup: dict):
    """
    Verify concurrency safety:
    Initial stock = 100.
    Request A = OUT 70.
    Request B = OUT 50.
    With negative stock disabled:
    One MUST succeed (leaving 30 or 50) and the other MUST fail (insufficient stock).
    Final balance must be non-corrupted and non-negative.
    """
    wh = sample_setup["warehouse"]
    prod = sample_setup["product"]
    loc = sample_setup["location"]

    # Initial stock IN = 100
    async with AsyncSessionLocal() as session:
        await stock_movement_service.stock_in(
            session, product_id=prod.id, warehouse_id=wh.id, storage_location_id=loc.id, quantity=Decimal("100.0000")
        )

    # Simulate concurrent requests across two distinct DB sessions
    results = []
    errors = []

    async def execute_out(qty: Decimal):
        async with AsyncSessionLocal() as session:
            try:
                res = await stock_movement_service.stock_out(
                    session,
                    product_id=prod.id,
                    warehouse_id=wh.id,
                    storage_location_id=loc.id,
                    quantity=qty,
                )
                results.append(res)
            except Exception as e:
                errors.append(e)

    await asyncio.gather(
        execute_out(Decimal("70.0000")),
        execute_out(Decimal("50.0000")),
    )

    # Exactly one succeeded and one failed
    assert len(results) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], ValidationException)
    assert "Insufficient stock" in str(errors[0])

    # Final balance check
    async with AsyncSessionLocal() as session:
        bal = await stock_balance_service.get_balances(session, prod.id, wh.id, loc.id)
        assert len(bal) == 1
        # If 70 succeeded: 30 remaining; If 50 succeeded: 50 remaining
        assert Decimal(str(bal[0].quantity_on_hand)) in (Decimal("30.0000"), Decimal("50.0000"))


# ============================================================
# SECTION H: REST API ENDPOINTS & RBAC
# ============================================================

@pytest.mark.asyncio
async def test_rest_api_stock_movement_flow(async_client: AsyncClient, auth_headers: dict, sample_setup: dict):
    """Verify REST API POST /api/v1/stock/movements and query APIs."""
    wh = sample_setup["warehouse"]
    prod = sample_setup["product"]
    loc = sample_setup["location"]

    # 1. POST /api/v1/stock/movements (Stock IN)
    payload = {
        "product_id": str(prod.id),
        "warehouse_id": str(wh.id),
        "storage_location_id": str(loc.id),
        "movement_type": "STOCK_IN",
        "direction": "IN",
        "quantity": "80.0000",
        "reason": "REST API Intake",
    }
    resp = await async_client.post("/api/v1/stock/movements", json=payload, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["movement_type"] == "STOCK_IN"
    assert Decimal(str(data["quantity_after"])) == Decimal("80.0000")
    movement_id = data["id"]

    # 2. GET /api/v1/stock/ledger/{id}
    resp = await async_client.get(f"/api/v1/stock/ledger/{movement_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == movement_id

    # 3. GET /api/v1/products/{product_id}/stock
    resp = await async_client.get(f"/api/v1/products/{prod.id}/stock", headers=auth_headers)
    assert resp.status_code == 200
    prod_stock = resp.json()
    assert Decimal(str(prod_stock["total_available_stock"])) == Decimal("80.0000")

    # 4. GET /api/v1/warehouses/{warehouse_id}/stock
    resp = await async_client.get(f"/api/v1/warehouses/{wh.id}/stock", headers=auth_headers)
    assert resp.status_code == 200
    wh_stock = resp.json()
    assert Decimal(str(wh_stock["total_available_stock"])) == Decimal("80.0000")

    # 5. GET /api/v1/storage-locations/{location_id}/stock
    resp = await async_client.get(f"/api/v1/storage-locations/{loc.id}/stock", headers=auth_headers)
    assert resp.status_code == 200
    loc_stock = resp.json()
    assert Decimal(str(loc_stock["total_available_stock"])) == Decimal("80.0000")


@pytest.mark.asyncio
async def test_rest_api_immutability(async_client: AsyncClient, auth_headers: dict, sample_setup: dict):
    """Verify StockLedger is immutable: PUT and DELETE are 405 Method Not Allowed."""
    fake_id = uuid.uuid4()
    put_resp = await async_client.put(f"/api/v1/stock/ledger/{fake_id}", json={}, headers=auth_headers)
    assert put_resp.status_code in (404, 405)

    del_resp = await async_client.delete(f"/api/v1/stock/ledger/{fake_id}", headers=auth_headers)
    assert del_resp.status_code in (404, 405)


@pytest.mark.asyncio
async def test_rest_api_rbac_unauthenticated(async_client: AsyncClient):
    """Verify unauthenticated requests return 401 Unauthorized."""
    resp = await async_client.post("/api/v1/stock/movements", json={})
    assert resp.status_code == 401

    resp = await async_client.get("/api/v1/stock/ledger")
    assert resp.status_code == 401

    resp = await async_client.get("/api/v1/stock/balances")
    assert resp.status_code == 401


# ============================================================
# SECTION I: AUDIT LOGGING INTEGRATION
# ============================================================

@pytest.mark.asyncio
async def test_stock_movement_audit_logging(db_session: AsyncSession, sample_setup: dict):
    """Verify stock movements record an operational AuditLog record."""
    wh = sample_setup["warehouse"]
    prod = sample_setup["product"]

    ledger = await stock_movement_service.stock_in(
        db_session, product_id=prod.id, warehouse_id=wh.id, quantity=Decimal("45.0000"), reason="Audited delivery"
    )

    # Check AuditLog
    stmt = select(AuditLog).where(
        AuditLog.entity_type == "StockLedger",
        AuditLog.entity_id == str(ledger.id),
    )
    result = await db_session.execute(stmt)
    audit = result.scalars().first()
    assert audit is not None
    assert "STOCK_STOCK_IN_IN" in audit.action
