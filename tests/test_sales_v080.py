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
from app.models.customer import Customer
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.purchase_order import PurchaseOrder
from app.models.sales_order import SalesOrder, SalesOrderItem
from app.models.sales_quotation import SalesQuotation, SalesQuotationItem
from app.models.stock_balance import StockBalance
from app.models.stock_ledger import StockLedger
from app.models.supplier import Supplier
from app.models.supplier_quotation import SupplierQuotation
from app.models.unit_of_measure import UnitOfMeasure
from app.models.user import User
from app.models.user_role import UserRole
from app.models.warehouse import Warehouse
from app.repositories.rbac import role_repository
from app.schemas.inventory import (
    ProductCategoryCreate,
    ProductCreate,
    UnitOfMeasureCreate,
    WarehouseCreate,
)
from app.schemas.procurement import SupplierCreate
from app.schemas.sales import (
    CustomerAddressCreate,
    CustomerCategoryCreate,
    CustomerContactCreate,
    CustomerCreate,
    CustomerUpdate,
    SalesOrderCreate,
    SalesOrderItemCreate,
    SalesOrderUpdate,
    SalesQuotationCreate,
    SalesQuotationItemCreate,
    SalesQuotationUpdate,
)
from app.services.customer_services import customer_service
from app.services.inventory_services import (
    category_service,
    product_service,
    unit_of_measure_service,
    warehouse_service,
)
from app.services.quotation_services import quotation_service
from app.services.sales_order_services import sales_order_service
from app.services.supplier_services import supplier_service


async def get_test_sales_users(session):
    unique = uuid.uuid4().hex[:6]
    mgr_user = User(
        full_name="Sales Manager User",
        email=f"sales_mgr_{unique}@example.com",
        username=f"sales_mgr_{unique}",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    rep_user = User(
        full_name="Sales Representative User",
        email=f"sales_rep_{unique}@example.com",
        username=f"sales_rep_{unique}",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    viewer_user = User(
        full_name="Sales Viewer User",
        email=f"sales_view_{unique}@example.com",
        username=f"sales_view_{unique}",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    session.add_all([mgr_user, rep_user, viewer_user])
    await session.flush()

    mgr_role = await role_repository.get_by_name(session, "Sales Manager")
    rep_role = await role_repository.get_by_name(session, "Sales Representative")
    viewer_role = await role_repository.get_by_name(session, "Sales Viewer")

    if mgr_role:
        session.add(UserRole(user_id=mgr_user.id, role_id=mgr_role.id))
    if rep_role:
        session.add(UserRole(user_id=rep_user.id, role_id=rep_role.id))
    if viewer_role:
        session.add(UserRole(user_id=viewer_user.id, role_id=viewer_role.id))

    await session.commit()
    await session.refresh(mgr_user)
    await session.refresh(rep_user)
    await session.refresh(viewer_user)

    return mgr_user, rep_user, viewer_user


async def setup_sales_test_inventory(session):
    suffix = uuid.uuid4().hex[:6]
    cat = await category_service.create_category(
        session, obj_in=ProductCategoryCreate(name=f"Sales Category {suffix}", code=f"CAT_SL_{suffix}")
    )
    uom = await unit_of_measure_service.create_unit(
        session,
        obj_in=UnitOfMeasureCreate(
            name=f"Piece_{suffix}", symbol=f"pc_{suffix}", category="Count"
        ),
    )
    prod_dict = await product_service.create_product(
        session,
        obj_in=ProductCreate(
            sku=f"SKU-SL-{suffix}",
            name=f"Enterprise Widget {suffix}",
            category_id=cat.id,
            base_unit_id=uom.id,
        ),
    )
    product = await product_service.get_product(session, prod_dict["id"])
    warehouse = await warehouse_service.create_warehouse(
        session,
        obj_in=WarehouseCreate(
            code=f"WH-SL-{suffix}",
            name=f"Sales Warehouse {suffix}",
        ),
    )
    return product, warehouse, uom


# =========================================================================
# 1-5: CUSTOMER TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_01_customer_create():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        code = f"CUST-01-{uuid.uuid4().hex[:6]}"
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(
                customer_code=code,
                name="Acme International",
                legal_name="Acme International Ltd",
                email="contact@acme.com",
                phone="+91-9876543210",
                tax_id="GSTIN_ACME_01",
                currency="INR",
                payment_terms="Net 30",
                credit_limit=Decimal("100000.00"),
                contacts=[CustomerContactCreate(contact_person="Alice Smith", email="alice@acme.com", is_primary=True)],
                addresses=[CustomerAddressCreate(address_type="Billing", address_line1="Bldg 4", city="Bengaluru", state="Karnataka", postal_code="560001")],
            ),
            current_user_id=mgr.id,
        )
        assert cust.customer_code == code
        assert cust.name == "Acme International"
        assert cust.status == "Active"
        assert len(cust.contacts) == 1
        assert len(cust.addresses) == 1


@pytest.mark.asyncio
async def test_02_customer_update():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(
                customer_code=f"CUST-02-{uuid.uuid4().hex[:6]}",
                name="Beta Corp",
                email="beta@corp.com",
                credit_limit=Decimal("50000.00"),
            ),
            current_user_id=mgr.id,
        )
        updated = await customer_service.update_customer(
            session,
            cust.id,
            obj_in=CustomerUpdate(name="Beta Corporation Global", credit_limit=Decimal("75000.00")),
            current_user_id=mgr.id,
        )
        assert updated.name == "Beta Corporation Global"
        assert updated.credit_limit == Decimal("75000.00")


@pytest.mark.asyncio
async def test_03_customer_search():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        unique = uuid.uuid4().hex[:6]
        c_code = f"CUST-SRCH-{unique}"
        await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(
                customer_code=c_code,
                name=f"Zenith Logistics {unique}",
                email=f"info@{unique}.com",
            ),
            current_user_id=mgr.id,
        )
        results, total = await customer_service.list_customers(session, query=unique)
        assert total >= 1
        assert any(c.customer_code == c_code for c in results)


@pytest.mark.asyncio
async def test_04_customer_pagination():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        for i in range(5):
            await customer_service.create_customer(
                session,
                obj_in=CustomerCreate(
                    customer_code=f"CUST-PG-{i}-{uuid.uuid4().hex[:6]}",
                    name=f"Paging Customer {i}",
                ),
                current_user_id=mgr.id,
            )
        page1, total1 = await customer_service.list_customers(session, skip=0, limit=2)
        assert len(page1) == 2
        assert total1 >= 5


@pytest.mark.asyncio
async def test_05_customer_activate_deactivate():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(
                customer_code=f"CUST-ACT-{uuid.uuid4().hex[:6]}",
                name="Toggle Status Corp",
            ),
            current_user_id=mgr.id,
        )
        assert cust.status == "Active"

        deactivated = await customer_service.deactivate_customer(session, cust.id, current_user_id=mgr.id)
        assert deactivated.status == "Inactive"

        # Inactive customer cannot create quotation
        with pytest.raises(ValidationException):
            await quotation_service.create_quotation(
                session,
                obj_in=SalesQuotationCreate(
                    customer_id=cust.id,
                    items=[SalesQuotationItemCreate(product_id=product.id, quantity=Decimal("1.0"), unit_price=Decimal("100.0"))],
                ),
                current_user_id=mgr.id,
            )

        # Inactive customer cannot create sales order
        with pytest.raises(ValidationException):
            await sales_order_service.create_order(
                session,
                obj_in=SalesOrderCreate(
                    customer_id=cust.id,
                    items=[SalesOrderItemCreate(product_id=product.id, quantity=Decimal("1.0"), unit_price=Decimal("100.0"))],
                ),
                current_user_id=mgr.id,
            )

        activated = await customer_service.activate_customer(session, cust.id, current_user_id=mgr.id)
        assert activated.status == "Active"


# =========================================================================
# 6-14: SALES QUOTATION TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_06_quotation_creation_and_numbering():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-Q6-{uuid.uuid4().hex[:6]}", name="Q6 Customer"),
            current_user_id=mgr.id,
        )
        year = datetime.now(timezone.utc).year
        quot = await quotation_service.create_quotation(
            session,
            obj_in=SalesQuotationCreate(
                customer_id=cust.id,
                currency="INR",
                items=[
                    SalesQuotationItemCreate(
                        product_id=product.id,
                        quantity=Decimal("10.0000"),
                        unit_price=Decimal("500.00"),
                        warehouse_id=warehouse.id,
                    )
                ],
            ),
            current_user_id=mgr.id,
        )
        assert quot.status == "Draft"
        assert quot.quotation_number.startswith(f"SQ-{year}-")
        assert len(quot.quotation_number.split("-")[-1]) == 5
        assert quot.revision_number == 1


@pytest.mark.asyncio
async def test_07_quotation_line_validation():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-Q7-{uuid.uuid4().hex[:6]}", name="Q7 Customer"),
            current_user_id=mgr.id,
        )

        # Empty items
        with pytest.raises((ValidationException, Exception)):
            await quotation_service.create_quotation(
                session, obj_in=SalesQuotationCreate(customer_id=cust.id, items=[]), current_user_id=mgr.id
            )

        # Quantity <= 0
        with pytest.raises((ValidationException, Exception)):
            await quotation_service.create_quotation(
                session,
                obj_in=SalesQuotationCreate(
                    customer_id=cust.id,
                    items=[SalesQuotationItemCreate(product_id=product.id, quantity=Decimal("0.00"), unit_price=Decimal("100.0"))],
                ),
                current_user_id=mgr.id,
            )

        # Unit price < 0
        with pytest.raises((ValidationException, Exception)):
            await quotation_service.create_quotation(
                session,
                obj_in=SalesQuotationCreate(
                    customer_id=cust.id,
                    items=[SalesQuotationItemCreate(product_id=product.id, quantity=Decimal("1.00"), unit_price=Decimal("-10.0"))],
                ),
                current_user_id=mgr.id,
            )

        # Non-existent product
        with pytest.raises(NotFoundException):
            await quotation_service.create_quotation(
                session,
                obj_in=SalesQuotationCreate(
                    customer_id=cust.id,
                    items=[SalesQuotationItemCreate(product_id=uuid.uuid4(), quantity=Decimal("1.00"), unit_price=Decimal("100.0"))],
                ),
                current_user_id=mgr.id,
            )


@pytest.mark.asyncio
async def test_08_quotation_totals():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-Q8-{uuid.uuid4().hex[:6]}", name="Q8 Customer"),
            current_user_id=mgr.id,
        )
        # gross = 10 * 200 = 2000
        # discount 10% = 200 -> taxable = 1800
        # tax 18% = 324 -> line_total = 2124
        quot = await quotation_service.create_quotation(
            session,
            obj_in=SalesQuotationCreate(
                customer_id=cust.id,
                items=[
                    SalesQuotationItemCreate(
                        product_id=product.id,
                        quantity=Decimal("10.0000"),
                        unit_price=Decimal("200.00"),
                        discount_type="Percentage",
                        discount_value=Decimal("10.00"),
                        tax_rate=Decimal("18.00"),
                        warehouse_id=warehouse.id,
                    )
                ],
            ),
            current_user_id=mgr.id,
        )
        assert quot.subtotal_amount == Decimal("2000.00")
        assert quot.discount_amount == Decimal("200.00")
        assert quot.tax_amount == Decimal("324.00")
        assert quot.total_amount == Decimal("2124.00")


@pytest.mark.asyncio
async def test_09_quotation_update_in_draft():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-Q9-{uuid.uuid4().hex[:6]}", name="Q9 Customer"),
            current_user_id=mgr.id,
        )
        quot = await quotation_service.create_quotation(
            session,
            obj_in=SalesQuotationCreate(
                customer_id=cust.id,
                items=[SalesQuotationItemCreate(product_id=product.id, quantity=Decimal("5.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )
        assert quot.total_amount == Decimal("500.00")

        updated = await quotation_service.update_quotation(
            session,
            quot.id,
            obj_in=SalesQuotationUpdate(
                remarks="Updated notes",
                items=[SalesQuotationItemCreate(product_id=product.id, quantity=Decimal("8.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )
        assert updated.remarks == "Updated notes"
        assert updated.total_amount == Decimal("800.00")
        assert updated.revision_number == 2


@pytest.mark.asyncio
async def test_10_quotation_submit():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-Q10-{uuid.uuid4().hex[:6]}", name="Q10 Customer"),
            current_user_id=mgr.id,
        )
        quot = await quotation_service.create_quotation(
            session,
            obj_in=SalesQuotationCreate(
                customer_id=cust.id,
                items=[SalesQuotationItemCreate(product_id=product.id, quantity=Decimal("2.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )
        sub = await quotation_service.submit_quotation(session, quot.id, current_user_id=mgr.id)
        assert sub.status == "Submitted"


@pytest.mark.asyncio
async def test_11_quotation_approval():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-Q11-{uuid.uuid4().hex[:6]}", name="Q11 Customer"),
            current_user_id=mgr.id,
        )
        quot = await quotation_service.create_quotation(
            session,
            obj_in=SalesQuotationCreate(
                customer_id=cust.id,
                items=[SalesQuotationItemCreate(product_id=product.id, quantity=Decimal("2.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )
        await quotation_service.submit_quotation(session, quot.id, current_user_id=mgr.id)
        app_q = await quotation_service.approve_quotation(session, quot.id, current_user_id=mgr.id)
        assert app_q.status == "Approved"
        assert app_q.approved_by == mgr.id
        assert app_q.approved_at is not None


@pytest.mark.asyncio
async def test_12_quotation_rejection():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-Q12-{uuid.uuid4().hex[:6]}", name="Q12 Customer"),
            current_user_id=mgr.id,
        )
        quot = await quotation_service.create_quotation(
            session,
            obj_in=SalesQuotationCreate(
                customer_id=cust.id,
                items=[SalesQuotationItemCreate(product_id=product.id, quantity=Decimal("2.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )
        rej = await quotation_service.reject_quotation(session, quot.id, reason="Price too low", current_user_id=mgr.id)
        assert rej.status == "Rejected"
        assert "Price too low" in rej.remarks


@pytest.mark.asyncio
async def test_13_quotation_cancellation():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-Q13-{uuid.uuid4().hex[:6]}", name="Q13 Customer"),
            current_user_id=mgr.id,
        )
        quot = await quotation_service.create_quotation(
            session,
            obj_in=SalesQuotationCreate(
                customer_id=cust.id,
                items=[SalesQuotationItemCreate(product_id=product.id, quantity=Decimal("2.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )
        canc = await quotation_service.cancel_quotation(session, quot.id, current_user_id=mgr.id)
        assert canc.status == "Cancelled"


@pytest.mark.asyncio
async def test_14_quotation_immutability():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-Q14-{uuid.uuid4().hex[:6]}", name="Q14 Customer"),
            current_user_id=mgr.id,
        )
        quot = await quotation_service.create_quotation(
            session,
            obj_in=SalesQuotationCreate(
                customer_id=cust.id,
                items=[SalesQuotationItemCreate(product_id=product.id, quantity=Decimal("2.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )
        await quotation_service.approve_quotation(session, quot.id, current_user_id=mgr.id)

        # Attempting to update approved quotation raises ValidationException
        with pytest.raises(ValidationException):
            await quotation_service.update_quotation(
                session,
                quot.id,
                obj_in=SalesQuotationUpdate(remarks="Attempt illegal edit"),
                current_user_id=mgr.id,
            )


# =========================================================================
# 15-22: SALES ORDER TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_15_order_creation_and_numbering():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-O15-{uuid.uuid4().hex[:6]}", name="O15 Customer"),
            current_user_id=mgr.id,
        )
        year = datetime.now(timezone.utc).year
        order = await sales_order_service.create_order(
            session,
            obj_in=SalesOrderCreate(
                customer_id=cust.id,
                currency="INR",
                items=[SalesOrderItemCreate(product_id=product.id, quantity=Decimal("4.0000"), unit_price=Decimal("250.00"), warehouse_id=warehouse.id)],
            ),
            current_user_id=mgr.id,
        )
        assert order.status == "Draft"
        assert order.order_number.startswith(f"SO-{year}-")
        assert len(order.order_number.split("-")[-1]) == 5
        assert order.revision_number == 1


@pytest.mark.asyncio
async def test_16_order_validation():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-O16-{uuid.uuid4().hex[:6]}", name="O16 Customer"),
            current_user_id=mgr.id,
        )

        # Empty items
        with pytest.raises((ValidationException, Exception)):
            await sales_order_service.create_order(
                session, obj_in=SalesOrderCreate(customer_id=cust.id, items=[]), current_user_id=mgr.id
            )

        # Quantity <= 0
        with pytest.raises((ValidationException, Exception)):
            await sales_order_service.create_order(
                session,
                obj_in=SalesOrderCreate(
                    customer_id=cust.id,
                    items=[SalesOrderItemCreate(product_id=product.id, quantity=Decimal("0.00"), unit_price=Decimal("100.0"))],
                ),
                current_user_id=mgr.id,
            )

        # Negative price
        with pytest.raises((ValidationException, Exception)):
            await sales_order_service.create_order(
                session,
                obj_in=SalesOrderCreate(
                    customer_id=cust.id,
                    items=[SalesOrderItemCreate(product_id=product.id, quantity=Decimal("1.00"), unit_price=Decimal("-50.0"))],
                ),
                current_user_id=mgr.id,
            )


@pytest.mark.asyncio
async def test_17_order_totals():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-O17-{uuid.uuid4().hex[:6]}", name="O17 Customer"),
            current_user_id=mgr.id,
        )
        # gross = 5 * 300 = 1500
        # discount 10% = 150 -> taxable = 1350
        # tax 18% = 243 -> line_total = 1593
        order = await sales_order_service.create_order(
            session,
            obj_in=SalesOrderCreate(
                customer_id=cust.id,
                items=[
                    SalesOrderItemCreate(
                        product_id=product.id,
                        quantity=Decimal("5.0000"),
                        unit_price=Decimal("300.00"),
                        discount_type="Percentage",
                        discount_value=Decimal("10.00"),
                        tax_rate=Decimal("18.00"),
                        warehouse_id=warehouse.id,
                    )
                ],
            ),
            current_user_id=mgr.id,
        )
        assert order.subtotal_amount == Decimal("1500.00")
        assert order.discount_amount == Decimal("150.00")
        assert order.tax_amount == Decimal("243.00")
        assert order.total_amount == Decimal("1593.00")


@pytest.mark.asyncio
async def test_18_order_update_in_draft():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-O18-{uuid.uuid4().hex[:6]}", name="O18 Customer"),
            current_user_id=mgr.id,
        )
        order = await sales_order_service.create_order(
            session,
            obj_in=SalesOrderCreate(
                customer_id=cust.id,
                items=[SalesOrderItemCreate(product_id=product.id, quantity=Decimal("2.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )
        assert order.total_amount == Decimal("200.00")

        updated = await sales_order_service.update_order(
            session,
            order.id,
            obj_in=SalesOrderUpdate(
                remarks="Updated SO remarks",
                items=[SalesOrderItemCreate(product_id=product.id, quantity=Decimal("6.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )
        assert updated.remarks == "Updated SO remarks"
        assert updated.total_amount == Decimal("600.00")
        assert updated.revision_number == 2


@pytest.mark.asyncio
async def test_19_order_submit():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-O19-{uuid.uuid4().hex[:6]}", name="O19 Customer"),
            current_user_id=mgr.id,
        )
        order = await sales_order_service.create_order(
            session,
            obj_in=SalesOrderCreate(
                customer_id=cust.id,
                items=[SalesOrderItemCreate(product_id=product.id, quantity=Decimal("2.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )
        sub = await sales_order_service.submit_order(session, order.id, current_user_id=mgr.id)
        assert sub.status == "Submitted"


@pytest.mark.asyncio
async def test_20_order_approval_and_credit_limit():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(
                customer_code=f"CUST-O20-{uuid.uuid4().hex[:6]}",
                name="O20 Customer",
                credit_limit=Decimal("500.00"),
            ),
            current_user_id=mgr.id,
        )
        # Order within limit (300 <= 500)
        valid_order = await sales_order_service.create_order(
            session,
            obj_in=SalesOrderCreate(
                customer_id=cust.id,
                items=[SalesOrderItemCreate(product_id=product.id, quantity=Decimal("3.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )
        app_order = await sales_order_service.approve_order(session, valid_order.id, current_user_id=mgr.id)
        assert app_order.status == "Approved"
        assert app_order.approved_by == mgr.id

        # Order exceeding limit (1000 > 500)
        exceed_order = await sales_order_service.create_order(
            session,
            obj_in=SalesOrderCreate(
                customer_id=cust.id,
                items=[SalesOrderItemCreate(product_id=product.id, quantity=Decimal("10.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )
        with pytest.raises(ValidationException):
            await sales_order_service.approve_order(session, exceed_order.id, current_user_id=mgr.id)


@pytest.mark.asyncio
async def test_21_order_cancellation():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-O21-{uuid.uuid4().hex[:6]}", name="O21 Customer"),
            current_user_id=mgr.id,
        )
        order = await sales_order_service.create_order(
            session,
            obj_in=SalesOrderCreate(
                customer_id=cust.id,
                items=[SalesOrderItemCreate(product_id=product.id, quantity=Decimal("2.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )
        canc = await sales_order_service.cancel_order(session, order.id, current_user_id=mgr.id)
        assert canc.status == "Cancelled"
        assert canc.delivery_status == "Cancelled"


@pytest.mark.asyncio
async def test_22_order_immutability():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-O22-{uuid.uuid4().hex[:6]}", name="O22 Customer"),
            current_user_id=mgr.id,
        )
        order = await sales_order_service.create_order(
            session,
            obj_in=SalesOrderCreate(
                customer_id=cust.id,
                items=[SalesOrderItemCreate(product_id=product.id, quantity=Decimal("2.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )
        await sales_order_service.approve_order(session, order.id, current_user_id=mgr.id)

        # Updating approved order raises ValidationException
        with pytest.raises(ValidationException):
            await sales_order_service.update_order(
                session,
                order.id,
                obj_in=SalesOrderUpdate(remarks="Attempt illegal edit on approved order"),
                current_user_id=mgr.id,
            )


# =========================================================================
# 23-24: QUOTATION -> ORDER CONVERSION TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_23_quotation_to_order_conversion():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-C23-{uuid.uuid4().hex[:6]}", name="C23 Customer"),
            current_user_id=mgr.id,
        )
        quot = await quotation_service.create_quotation(
            session,
            obj_in=SalesQuotationCreate(
                customer_id=cust.id,
                remarks="Special client deal",
                items=[
                    SalesQuotationItemCreate(
                        product_id=product.id,
                        quantity=Decimal("12.0000"),
                        unit_price=Decimal("150.00"),
                        discount_type="Percentage",
                        discount_value=Decimal("5.00"),
                        tax_rate=Decimal("18.00"),
                        warehouse_id=warehouse.id,
                    )
                ],
            ),
            current_user_id=mgr.id,
        )
        await quotation_service.approve_quotation(session, quot.id, current_user_id=mgr.id)

        # Convert to Sales Order
        order = await sales_order_service.create_from_quotation(session, quot.id, current_user_id=mgr.id)
        assert order.status == "Draft"
        assert order.quotation_id == quot.id
        assert order.customer_id == cust.id
        assert order.total_amount == quot.total_amount
        assert len(order.items) == 1
        assert order.items[0].product_id == product.id
        assert order.items[0].quantity == Decimal("12.0000")

        # Quotation is now Converted
        refreshed_q = await quotation_service.get_quotation(session, quot.id)
        assert refreshed_q.status == "Converted"


@pytest.mark.asyncio
async def test_24_duplicate_conversion_prevention():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-C24-{uuid.uuid4().hex[:6]}", name="C24 Customer"),
            current_user_id=mgr.id,
        )
        quot = await quotation_service.create_quotation(
            session,
            obj_in=SalesQuotationCreate(
                customer_id=cust.id,
                items=[SalesQuotationItemCreate(product_id=product.id, quantity=Decimal("5.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )
        await quotation_service.approve_quotation(session, quot.id, current_user_id=mgr.id)

        # First conversion succeeds
        await sales_order_service.create_from_quotation(session, quot.id, current_user_id=mgr.id)

        # Duplicate conversion fails
        with pytest.raises(ValidationException) as exc_info:
            await sales_order_service.create_from_quotation(session, quot.id, current_user_id=mgr.id)
        assert "already been converted" in str(exc_info.value)


# =========================================================================
# 25-26: SALES / PROCUREMENT ISOLATION TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_25_sales_quotation_separate_from_supplier_quotation():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-ISO-{uuid.uuid4().hex[:6]}", name="Isolation Customer"),
            current_user_id=mgr.id,
        )
        sales_q = await quotation_service.create_quotation(
            session,
            obj_in=SalesQuotationCreate(
                customer_id=cust.id,
                items=[SalesQuotationItemCreate(product_id=product.id, quantity=Decimal("5.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )

        # Verify sales quotation exists in SalesQuotation table and NOT SupplierQuotation table
        stmt_sq = select(SalesQuotation).where(SalesQuotation.id == sales_q.id)
        assert (await session.execute(stmt_sq)).scalars().first() is not None

        stmt_supp_q = select(SupplierQuotation).where(SupplierQuotation.id == sales_q.id)
        assert (await session.execute(stmt_supp_q)).scalars().first() is None


@pytest.mark.asyncio
async def test_26_sales_service_does_not_touch_procurement_data():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        # Create a Supplier
        supp = await supplier_service.create_supplier(
            session,
            obj_in=SupplierCreate(supplier_code=f"SUPP-ISO-{uuid.uuid4().hex[:6]}", name="Isolation Supplier"),
            current_user_id=mgr.id,
        )
        # Attempting to use supplier ID as customer ID in sales quotation must fail
        with pytest.raises(NotFoundException):
            await quotation_service.create_quotation(
                session,
                obj_in=SalesQuotationCreate(
                    customer_id=supp.id,
                    items=[SalesQuotationItemCreate(product_id=product.id, quantity=Decimal("1.0"), unit_price=Decimal("100.0"))],
                ),
                current_user_id=mgr.id,
            )


# =========================================================================
# 27-30: RBAC TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_27_unauthorized_customer_mutation_via_api():
    async with AsyncSessionLocal() as session:
        _, _, viewer = await get_test_sales_users(session)
        token = create_access_token(str(viewer.id))
        headers = {"Authorization": f"Bearer {token}"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/customers",
                json={"customer_code": f"CUST-UNAUTH-{uuid.uuid4().hex[:6]}", "name": "Illegal Cust"},
                headers=headers,
            )
            assert resp.status_code == 403


@pytest.mark.asyncio
async def test_28_unauthorized_quotation_mutation_via_api():
    async with AsyncSessionLocal() as session:
        _, _, viewer = await get_test_sales_users(session)
        token = create_access_token(str(viewer.id))
        headers = {"Authorization": f"Bearer {token}"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/sales-quotations",
                json={"customer_id": str(uuid.uuid4()), "items": []},
                headers=headers,
            )
            assert resp.status_code == 403


@pytest.mark.asyncio
async def test_29_unauthorized_order_approval_via_api():
    async with AsyncSessionLocal() as session:
        mgr, rep, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-REP-{uuid.uuid4().hex[:6]}", name="Rep Customer"),
            current_user_id=mgr.id,
        )
        order = await sales_order_service.create_order(
            session,
            obj_in=SalesOrderCreate(
                customer_id=cust.id,
                items=[SalesOrderItemCreate(product_id=product.id, quantity=Decimal("2.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=rep.id,
        )

        rep_token = create_access_token(str(rep.id))
        rep_headers = {"Authorization": f"Bearer {rep_token}"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/sales-orders/{order.id}/approve",
                headers=rep_headers,
            )
            # Sales Representative does not have sales.order.approve
            assert resp.status_code == 403


@pytest.mark.asyncio
async def test_30_viewer_read_only_via_api():
    async with AsyncSessionLocal() as session:
        mgr, _, viewer = await get_test_sales_users(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-VW-{uuid.uuid4().hex[:6]}", name="Viewer Customer"),
            current_user_id=mgr.id,
        )

        token = create_access_token(str(viewer.id))
        headers = {"Authorization": f"Bearer {token}"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Read allowed
            get_resp = await client.get("/api/v1/customers", headers=headers)
            assert get_resp.status_code == 200

            get_cust = await client.get(f"/api/v1/customers/{cust.id}", headers=headers)
            assert get_cust.status_code == 200

            # Mutation forbidden
            del_resp = await client.delete(f"/api/v1/customers/{cust.id}", headers=headers)
            assert del_resp.status_code == 403


# =========================================================================
# 31-32: APPROVAL ENGINE TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_31_approval_engine_start_workflow():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-WF-{uuid.uuid4().hex[:6]}", name="Workflow Customer"),
            current_user_id=mgr.id,
        )
        order = await sales_order_service.create_order(
            session,
            obj_in=SalesOrderCreate(
                customer_id=cust.id,
                items=[SalesOrderItemCreate(product_id=product.id, quantity=Decimal("5.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )
        # Submitting order triggers ApprovalEngineService
        submitted = await sales_order_service.submit_order(session, order.id, current_user_id=mgr.id)
        assert submitted.status == "Submitted"


@pytest.mark.asyncio
async def test_32_duplicate_submission_protection():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-DS-{uuid.uuid4().hex[:6]}", name="DS Customer"),
            current_user_id=mgr.id,
        )
        order = await sales_order_service.create_order(
            session,
            obj_in=SalesOrderCreate(
                customer_id=cust.id,
                items=[SalesOrderItemCreate(product_id=product.id, quantity=Decimal("1.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )
        await sales_order_service.submit_order(session, order.id, current_user_id=mgr.id)

        # Resubmitting submitted order fails
        with pytest.raises(ValidationException):
            await sales_order_service.submit_order(session, order.id, current_user_id=mgr.id)


# =========================================================================
# 33-35: AUDIT LOG TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_33_customer_audit():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-AUD-{uuid.uuid4().hex[:6]}", name="Audit Customer"),
            current_user_id=mgr.id,
        )
        await customer_service.deactivate_customer(session, cust.id, current_user_id=mgr.id)
        await customer_service.activate_customer(session, cust.id, current_user_id=mgr.id)

        stmt = select(AuditLog).where(AuditLog.entity_id == str(cust.id))
        logs = (await session.execute(stmt)).scalars().all()
        actions = [l.action for l in logs]
        assert "CUSTOMER_CREATE" in actions
        assert "CUSTOMER_DEACTIVATE" in actions
        assert "CUSTOMER_ACTIVATE" in actions


@pytest.mark.asyncio
async def test_34_quotation_audit():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-QAUD-{uuid.uuid4().hex[:6]}", name="QAUD Customer"),
            current_user_id=mgr.id,
        )
        quot = await quotation_service.create_quotation(
            session,
            obj_in=SalesQuotationCreate(
                customer_id=cust.id,
                items=[SalesQuotationItemCreate(product_id=product.id, quantity=Decimal("2.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )
        await quotation_service.submit_quotation(session, quot.id, current_user_id=mgr.id)
        await quotation_service.approve_quotation(session, quot.id, current_user_id=mgr.id)

        stmt = select(AuditLog).where(AuditLog.entity_id == str(quot.id))
        logs = (await session.execute(stmt)).scalars().all()
        actions = [l.action for l in logs]
        assert "SALES_QUOTATION_CREATE" in actions
        assert "SALES_QUOTATION_SUBMIT" in actions
        assert "SALES_QUOTATION_APPROVE" in actions


@pytest.mark.asyncio
async def test_35_order_audit():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-OAUD-{uuid.uuid4().hex[:6]}", name="OAUD Customer"),
            current_user_id=mgr.id,
        )
        order = await sales_order_service.create_order(
            session,
            obj_in=SalesOrderCreate(
                customer_id=cust.id,
                items=[SalesOrderItemCreate(product_id=product.id, quantity=Decimal("2.0000"), unit_price=Decimal("100.00"))],
            ),
            current_user_id=mgr.id,
        )
        await sales_order_service.submit_order(session, order.id, current_user_id=mgr.id)
        await sales_order_service.approve_order(session, order.id, current_user_id=mgr.id)

        stmt = select(AuditLog).where(AuditLog.entity_id == str(order.id))
        logs = (await session.execute(stmt)).scalars().all()
        actions = [l.action for l in logs]
        assert "SALES_ORDER_CREATE" in actions
        assert "SALES_ORDER_SUBMIT" in actions
        assert "SALES_ORDER_APPROVE" in actions


# =========================================================================
# 36-38: INVENTORY BOUNDARY TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_36_sales_operations_do_not_mutate_stock_balance():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-IB36-{uuid.uuid4().hex[:6]}", name="IB36 Customer"),
            current_user_id=mgr.id,
        )
        initial_balance_count = (await session.execute(select(func.count(StockBalance.id)))).scalar() or 0

        # Create & approve sales order
        order = await sales_order_service.create_order(
            session,
            obj_in=SalesOrderCreate(
                customer_id=cust.id,
                items=[SalesOrderItemCreate(product_id=product.id, quantity=Decimal("10.0000"), unit_price=Decimal("100.00"), warehouse_id=warehouse.id)],
            ),
            current_user_id=mgr.id,
        )
        await sales_order_service.approve_order(session, order.id, current_user_id=mgr.id)

        # Verify no direct changes to StockBalance
        post_balance_count = (await session.execute(select(func.count(StockBalance.id)))).scalar() or 0
        assert post_balance_count == initial_balance_count


@pytest.mark.asyncio
async def test_37_sales_operations_do_not_insert_stock_ledger():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-IB37-{uuid.uuid4().hex[:6]}", name="IB37 Customer"),
            current_user_id=mgr.id,
        )
        initial_ledger_count = (await session.execute(select(func.count(StockLedger.id)))).scalar() or 0

        # Create & approve sales quotation & order
        quot = await quotation_service.create_quotation(
            session,
            obj_in=SalesQuotationCreate(
                customer_id=cust.id,
                items=[SalesQuotationItemCreate(product_id=product.id, quantity=Decimal("5.0000"), unit_price=Decimal("100.00"), warehouse_id=warehouse.id)],
            ),
            current_user_id=mgr.id,
        )
        await quotation_service.approve_quotation(session, quot.id, current_user_id=mgr.id)
        order = await sales_order_service.create_from_quotation(session, quot.id, current_user_id=mgr.id)
        await sales_order_service.approve_order(session, order.id, current_user_id=mgr.id)

        # Verify no direct inserts into StockLedger
        post_ledger_count = (await session.execute(select(func.count(StockLedger.id)))).scalar() or 0
        assert post_ledger_count == initial_ledger_count


@pytest.mark.asyncio
async def test_38_no_duplicate_stock_engine():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, _ = await setup_sales_test_inventory(session)
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(customer_code=f"CUST-IB38-{uuid.uuid4().hex[:6]}", name="IB38 Customer"),
            current_user_id=mgr.id,
        )
        order = await sales_order_service.create_order(
            session,
            obj_in=SalesOrderCreate(
                customer_id=cust.id,
                items=[SalesOrderItemCreate(product_id=product.id, quantity=Decimal("2.0000"), unit_price=Decimal("100.00"), warehouse_id=warehouse.id)],
            ),
            current_user_id=mgr.id,
        )
        # Verify order items have fulfilled/delivered tracking fields initialized at 0 without executing stock deduction
        assert order.items[0].delivered_quantity == Decimal("0.0000")
        assert order.items[0].status == "Pending"
        assert order.delivery_status == "Pending"


# =========================================================================
# 39-40: REGRESSION COMPATIBILITY TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_39_procurement_compatibility():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_sales_users(session)
        product, warehouse, uom = await setup_sales_test_inventory(session)
        supp = await supplier_service.create_supplier(
            session,
            obj_in=SupplierCreate(supplier_code=f"SUPP-REG-{uuid.uuid4().hex[:6]}", name="Procurement Reg Supplier"),
            current_user_id=mgr.id,
        )
        assert supp.status == "Active"


@pytest.mark.asyncio
async def test_40_inventory_compatibility():
    async with AsyncSessionLocal() as session:
        product, warehouse, uom = await setup_sales_test_inventory(session)
        assert product.id is not None
        assert warehouse.id is not None
        assert uom.id is not None
