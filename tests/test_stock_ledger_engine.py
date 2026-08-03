from decimal import Decimal
from typing import AsyncGenerator
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.unit_of_measure import UnitOfMeasure
from app.models.product_category import ProductCategory
from app.repositories.user import user_repository
from app.services.stock_engine_services import (
    inventory_adjustment_service,
    inventory_transaction_type_service,
    opening_stock_service,
    stock_balance_service,
    stock_ledger_service,
)
from app.schemas.stock_engine import (
    InventoryAdjustmentCreate,
    OpeningStockCreate,
)
from app.exceptions.base import DuplicateResourceException, ValidationException


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


@pytest.mark.asyncio
async def test_seed_transaction_types(db_session: AsyncSession):
    """Verify that default inventory transaction types exist and are active."""
    types = await inventory_transaction_type_service.get_all_active_types(db_session)
    codes = [t.code for t in types]
    assert "OPENING_STOCK" in codes
    assert "PURCHASE_RECEIPT" in codes
    assert "SALES_ISSUE" in codes
    assert "STOCK_ADJUSTMENT" in codes
    assert "TRANSFER_IN" in codes
    assert "TRANSFER_OUT" in codes


@pytest.mark.asyncio
async def test_opening_stock_and_ledger_entry(db_session: AsyncSession):
    """Verify creating opening stock generates an immutable stock ledger entry and updates balance projection."""
    cat = ProductCategory(code=f"CAT-{uuid.uuid4().hex[:6]}", name="Engine Test Category")
    unit = UnitOfMeasure(name=f"Pieces {uuid.uuid4().hex[:4]}", symbol=f"pcs_{uuid.uuid4().hex[:4]}", category="Count")
    wh = Warehouse(code=f"WH-{uuid.uuid4().hex[:6]}", name="Test Warehouse")
    db_session.add_all([cat, unit, wh])
    await db_session.commit()

    prod = Product(
        sku=f"SKU-{uuid.uuid4().hex[:6]}",
        name="Test Engine Product",
        category_id=cat.id,
        base_unit_id=unit.id,
        track_inventory=True,
        allow_negative_stock=False,
    )
    db_session.add(prod)
    await db_session.commit()

    ref_num = f"OP-REF-{uuid.uuid4().hex[:6]}"
    opening_in = OpeningStockCreate(
        product_id=prod.id,
        warehouse_id=wh.id,
        quantity=Decimal("100.0000"),
        reference_number=ref_num,
    )
    op = await opening_stock_service.create_opening_stock(db_session, opening_in)
    assert op.id is not None
    assert op.reference_number == ref_num

    entries, total = await stock_ledger_service.get_ledger_entries(
        db_session, product_id=prod.id, warehouse_id=wh.id
    )
    assert total == 1
    ledger = entries[0]
    assert Decimal(str(ledger.quantity)) == Decimal("100.0000")
    assert Decimal(str(ledger.running_balance)) == Decimal("100.0000")
    assert ledger.direction == "IN"

    balances = await stock_balance_service.get_balances(db_session, product_id=prod.id, warehouse_id=wh.id)
    assert len(balances) == 1
    assert Decimal(str(balances[0].available_quantity)) == Decimal("100.0000")


@pytest.mark.asyncio
async def test_duplicate_opening_stock_prevention(db_session: AsyncSession):
    """Verify creating duplicate opening stock for same product/warehouse location is rejected."""
    cat = ProductCategory(code=f"CAT-{uuid.uuid4().hex[:6]}", name="Dup Test Category")
    unit = UnitOfMeasure(name=f"Boxes {uuid.uuid4().hex[:4]}", symbol=f"box_{uuid.uuid4().hex[:4]}", category="Count")
    wh = Warehouse(code=f"WH-{uuid.uuid4().hex[:6]}", name="Dup Warehouse")
    db_session.add_all([cat, unit, wh])
    await db_session.commit()

    prod = Product(
        sku=f"SKU-{uuid.uuid4().hex[:6]}",
        name="Dup Test Product",
        category_id=cat.id,
        base_unit_id=unit.id,
        track_inventory=True,
    )
    db_session.add(prod)
    await db_session.commit()

    opening_in1 = OpeningStockCreate(
        product_id=prod.id,
        warehouse_id=wh.id,
        quantity=Decimal("50.0000"),
        reference_number=f"OP-REF-1-{uuid.uuid4().hex[:4]}",
    )
    await opening_stock_service.create_opening_stock(db_session, opening_in1)

    opening_in2 = OpeningStockCreate(
        product_id=prod.id,
        warehouse_id=wh.id,
        quantity=Decimal("20.0000"),
        reference_number=f"OP-REF-2-{uuid.uuid4().hex[:4]}",
    )
    with pytest.raises(DuplicateResourceException):
        await opening_stock_service.create_opening_stock(db_session, opening_in2)


@pytest.mark.asyncio
async def test_inventory_adjustment_lifecycle(db_session: AsyncSession):
    """Verify Inventory Adjustment lifecycle: Draft -> Approved -> Applied -> Stock Ledger updated."""
    cat = ProductCategory(code=f"CAT-{uuid.uuid4().hex[:6]}", name="Adj Test Category")
    unit = UnitOfMeasure(name=f"Kgs {uuid.uuid4().hex[:4]}", symbol=f"kg_{uuid.uuid4().hex[:4]}", category="Weight")
    wh = Warehouse(code=f"WH-{uuid.uuid4().hex[:6]}", name="Adj Warehouse")
    db_session.add_all([cat, unit, wh])
    await db_session.commit()

    prod = Product(
        sku=f"SKU-{uuid.uuid4().hex[:6]}",
        name="Adj Test Product",
        category_id=cat.id,
        base_unit_id=unit.id,
        track_inventory=True,
    )
    db_session.add(prod)
    await db_session.commit()

    op_in = OpeningStockCreate(
        product_id=prod.id,
        warehouse_id=wh.id,
        quantity=Decimal("100.0000"),
        reference_number=f"OP-ADJ-{uuid.uuid4().hex[:4]}",
    )
    await opening_stock_service.create_opening_stock(db_session, op_in)

    adj_in = InventoryAdjustmentCreate(
        product_id=prod.id,
        warehouse_id=wh.id,
        adjustment_type="Increase",
        reason="Physical count audit found surplus",
        actual_quantity=Decimal("115.0000"),
    )
    adj = await inventory_adjustment_service.create_adjustment(db_session, adj_in)
    assert adj.status == "Draft"
    assert Decimal(str(adj.expected_quantity)) == Decimal("100.0000")
    assert Decimal(str(adj.difference)) == Decimal("15.0000")

    adj = await inventory_adjustment_service.approve_adjustment(db_session, adj.id)
    assert adj.status == "Approved"

    adj = await inventory_adjustment_service.apply_adjustment(db_session, adj.id)
    assert adj.status == "Applied"

    entries, total = await stock_ledger_service.get_ledger_entries(db_session, product_id=prod.id, warehouse_id=wh.id)
    assert total == 2
    latest = entries[0]
    assert Decimal(str(latest.running_balance)) == Decimal("115.0000")


@pytest.mark.asyncio
async def test_negative_stock_validation(db_session: AsyncSession):
    """Verify negative stock is prevented when allow_negative_stock is False."""
    cat = ProductCategory(code=f"CAT-{uuid.uuid4().hex[:6]}", name="Neg Test Category")
    unit = UnitOfMeasure(name=f"Liters {uuid.uuid4().hex[:4]}", symbol=f"L_{uuid.uuid4().hex[:4]}", category="Volume")
    wh = Warehouse(code=f"WH-{uuid.uuid4().hex[:6]}", name="Neg Warehouse")
    db_session.add_all([cat, unit, wh])
    await db_session.commit()

    prod = Product(
        sku=f"SKU-{uuid.uuid4().hex[:6]}",
        name="Neg Test Product",
        category_id=cat.id,
        base_unit_id=unit.id,
        track_inventory=True,
        allow_negative_stock=False,
    )
    db_session.add(prod)
    await db_session.commit()

    op_in = OpeningStockCreate(
        product_id=prod.id,
        warehouse_id=wh.id,
        quantity=Decimal("10.0000"),
        reference_number=f"OP-NEG-{uuid.uuid4().hex[:4]}",
    )
    await opening_stock_service.create_opening_stock(db_session, op_in)

    with pytest.raises(ValidationException):
        await stock_ledger_service.create_ledger_entry(
            db_session,
            product_id=prod.id,
            warehouse_id=wh.id,
            transaction_type_code="SALES_ISSUE",
            quantity=Decimal("15.0000"),
            direction="OUT",
        )


@pytest.mark.asyncio
async def test_stock_balance_recalculation(db_session: AsyncSession):
    """Verify recalculating balance projection matches ledger history."""
    cat = ProductCategory(code=f"CAT-{uuid.uuid4().hex[:6]}", name="Recalc Category")
    unit = UnitOfMeasure(name=f"Units {uuid.uuid4().hex[:4]}", symbol=f"u_{uuid.uuid4().hex[:4]}", category="Count")
    wh = Warehouse(code=f"WH-{uuid.uuid4().hex[:6]}", name="Recalc Warehouse")
    db_session.add_all([cat, unit, wh])
    await db_session.commit()

    prod = Product(
        sku=f"SKU-{uuid.uuid4().hex[:6]}",
        name="Recalc Product",
        category_id=cat.id,
        base_unit_id=unit.id,
        track_inventory=True,
    )
    db_session.add(prod)
    await db_session.commit()

    await opening_stock_service.create_opening_stock(
        db_session,
        OpeningStockCreate(
            product_id=prod.id,
            warehouse_id=wh.id,
            quantity=Decimal("50.0000"),
            reference_number=f"OP-RC-{uuid.uuid4().hex[:4]}",
        ),
    )

    await stock_ledger_service.create_ledger_entry(
        db_session,
        product_id=prod.id,
        warehouse_id=wh.id,
        transaction_type_code="PURCHASE_RECEIPT",
        quantity=Decimal("30.0000"),
        direction="IN",
    )

    bal = await stock_balance_service.recalculate_balance_projection(db_session, prod.id, wh.id)
    assert Decimal(str(bal.available_quantity)) == Decimal("80.0000")


@pytest.mark.asyncio
async def test_stock_engine_api_endpoints(async_client: AsyncClient, auth_headers: dict):
    """Verify REST API endpoints for transaction types, ledger, and balances."""
    resp = await async_client.get("/api/v1/inventory/transaction-types", headers=auth_headers)
    assert resp.status_code == 200
    types = resp.json()
    assert len(types) >= 12

    resp = await async_client.get("/api/v1/inventory/ledger", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data

    resp = await async_client.get("/api/v1/inventory/balances", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
