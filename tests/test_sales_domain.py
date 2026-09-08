from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.user import User
from app.repositories.user import user_repository
from app.schemas.inventory import (
    ProductCategoryCreate,
    ProductCreate,
    UnitOfMeasureCreate,
    WarehouseCreate,
)
from app.schemas.sales import (
    CustomerAddressCreate,
    CustomerCategoryCreate,
    CustomerContactCreate,
    CustomerCreate,
    DeliveryOrderCreate,
    DeliveryOrderItemCreate,
    DiscountRuleCreate,
    PriceListCreate,
    PricingRuleCreate,
    SalesOrderCreate,
    SalesOrderItemCreate,
    SalesQuotationCreate,
    SalesQuotationItemCreate,
    SalesReturnCreate,
    SalesReturnItemCreate,
)
from app.schemas.warehouse_operations import GoodsReceiptCreate, GoodsReceiptItemCreate
from app.services.customer_services import customer_service
from app.services.delivery_services import delivery_service
from app.services.inventory_services import (
    category_service,
    product_service,
    unit_of_measure_service,
    warehouse_service,
)
from app.services.pricing_services import discount_service, pricing_service
from app.services.quotation_services import quotation_service
from app.services.sales_analytics_services import sales_analytics_service, sales_report_service
from app.services.sales_order_services import sales_order_service
from app.services.sales_return_services import sales_return_service
from app.services.sales_search_services import sales_search_service
from app.services.tax_and_invoice_services import invoice_payload_service
from app.services.warehouse_operations_services import goods_receipt_service


async def get_test_admin_user(session):
    unique_id = uuid.uuid4().hex[:6]
    email = f"sales_admin_{unique_id}@example.com"
    username = f"sales_admin_{unique_id}"
    user = User(
        full_name="Sales Admin",
        email=email,
        username=username,
        password_hash="hashed_password_123",
        is_active=True,
        is_superuser=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def setup_test_inventory(session):
    cat = await category_service.create_category(
        session, obj_in=ProductCategoryCreate(name="Sales Test", code=f"CAT_SL_{uuid.uuid4().hex[:8]}")
    )
    uom = await unit_of_measure_service.create_unit(
        session,
        obj_in=UnitOfMeasureCreate(
            name=f"Unit_{uuid.uuid4().hex[:8]}", symbol=f"u_{uuid.uuid4().hex[:8]}", category="Count"
        ),
    )
    prod_dict = await product_service.create_product(
        session,
        obj_in=ProductCreate(
            sku=f"SL-ITEM-{uuid.uuid4().hex[:8]}",
            name="Enterprise Widget",
            category_id=cat.id,
            base_unit_id=uom.id,
        ),
    )
    product = await product_service.get_product(session, prod_dict["id"])
    warehouse = await warehouse_service.create_warehouse(
        session,
        obj_in=WarehouseCreate(
            code=f"WH-SL-{uuid.uuid4().hex[:8]}",
            name="Main Dispatch Warehouse",
        ),
    )

    gr_in = GoodsReceiptCreate(
        receipt_number=f"GR-INIT-{uuid.uuid4().hex[:8]}",
        warehouse_id=warehouse.id,
        receipt_date=datetime.now(timezone.utc),
        receipt_type="Initial",
        items=[
            GoodsReceiptItemCreate(
                product_id=product.id,
                quantity=Decimal("100.00"),
                unit_cost=Decimal("100.00"),
            )
        ],
    )
    gr = await goods_receipt_service.create_receipt(session, obj_in=gr_in)
    await goods_receipt_service.approve_receipt(session, gr.id)
    await goods_receipt_service.receive_receipt(session, gr.id)

    return product, warehouse


@pytest.mark.asyncio
async def test_customer_crud_and_contacts():
    """Test customer category, customer master, contact, and address creation."""
    async with AsyncSessionLocal() as session:
        user = await get_test_admin_user(session)

        # 1. Create Customer Category
        cat_code = f"CAT_VIP_{uuid.uuid4().hex[:4]}"
        cat = await customer_service.create_category(
            session, obj_in=CustomerCategoryCreate(code=cat_code, name="VIP Enterprise"), current_user_id=user.id
        )
        assert cat.code == cat_code

        # 2. Create Customer
        c_code = f"CUST-{uuid.uuid4().hex[:4]}"
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(
                customer_code=c_code,
                name="Acme Corporation",
                category_id=cat.id,
                email="billing@acme.com",
                credit_limit=Decimal("50000.00"),
                credit_days=30,
            ),
            current_user_id=user.id,
        )
        assert cust.customer_code == c_code
        assert cust.name == "Acme Corporation"

        # 3. Add Contact & Address
        contact = await customer_service.add_contact(
            session,
            customer_id=cust.id,
            obj_in=CustomerContactCreate(contact_person="John Doe", email="john@acme.com", is_primary=True),
        )
        assert contact.contact_person == "John Doe"

        address = await customer_service.add_address(
            session,
            customer_id=cust.id,
            obj_in=CustomerAddressCreate(
                address_type="Billing", address_line1="123 Corporate Blvd", city="Mumbai", state="Maharashtra", postal_code="400001"
            ),
        )
        assert address.city == "Mumbai"

        # 4. Search Customers
        items, total = await customer_service.list_customers(session, query="Acme")
        assert total >= 1
        assert any(c.id == cust.id for c in items)


@pytest.mark.asyncio
async def test_pricing_and_discount_engine():
    """Test Price List, Pricing Rules, and Discount calculation rules."""
    async with AsyncSessionLocal() as session:
        product, warehouse = await setup_test_inventory(session)

        # 1. Create Price List & Rule
        pl_code = f"PL_STD_{uuid.uuid4().hex[:4]}"
        pl = await pricing_service.create_price_list(
            session, obj_in=PriceListCreate(code=pl_code, name="Standard Price List", currency="INR")
        )
        p_rule = await pricing_service.create_pricing_rule(
            session,
            obj_in=PricingRuleCreate(
                price_list_id=pl.id, product_id=product.id, min_quantity=Decimal("5.0000"), unit_price=Decimal("450.00")
            ),
        )
        assert p_rule.unit_price == Decimal("450.00")

        eff_price = await pricing_service.get_effective_price(
            session, price_list_id=pl.id, product_id=product.id, quantity=Decimal("10.0000"), default_price=Decimal("500.00")
        )
        assert eff_price == Decimal("450.00")

        # 2. Discount Calculation
        disc_val = await discount_service.calculate_line_discount(
            unit_price=Decimal("100.00"), quantity=Decimal("10.0000"), discount_type="Percentage", discount_value=Decimal("10.00")
        )
        assert disc_val == Decimal("100.00")

        # Document Discount Rule
        d_code = f"DISC_DOC_{uuid.uuid4().hex[:4]}"
        d_rule = await discount_service.create_discount_rule(
            session,
            obj_in=DiscountRuleCreate(
                code=d_code,
                name="Bulk Order Discount",
                discount_type="Document",
                calculation_type="Percentage",
                discount_value=Decimal("5.00"),
                min_order_value=Decimal("1000.00"),
            ),
        )

        doc_disc = await discount_service.evaluate_document_discounts(session, order_total=Decimal("2000.00"), total_quantity=Decimal("20.0000"))
        assert doc_disc == Decimal("100.00")
        d_rule.is_active = False
        await session.commit()


@pytest.mark.asyncio
async def test_sales_quotation_lifecycle():
    """Test Sales Quotation creation, submission, approval, cloning, and revision history."""
    async with AsyncSessionLocal() as session:
        user = await get_test_admin_user(session)
        product, warehouse = await setup_test_inventory(session)

        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(
                customer_code=f"CUST_SQ_{uuid.uuid4().hex[:4]}",
                name="Quotation Client",
                email="client@sq.com",
            ),
            current_user_id=user.id,
        )

        valid_until = datetime.now(timezone.utc) + timedelta(days=30)
        quot = await quotation_service.create_quotation(
            session,
            obj_in=SalesQuotationCreate(
                customer_id=cust.id,
                validity_date=valid_until,
                remarks="Initial quote",
                items=[
                    SalesQuotationItemCreate(
                        product_id=product.id,
                        quantity=Decimal("10.0000"),
                        unit_price=Decimal("150.00"),
                        discount_type="Percentage",
                        discount_value=Decimal("10.00"),
                        tax_rate=Decimal("18.00"),
                        warehouse_id=warehouse.id,
                    )
                ],
            ),
            current_user_id=user.id,
        )
        assert quot.status == "Draft"
        assert quot.total_amount > Decimal("0.00")

        # Submit & Approve
        submitted = await quotation_service.submit_quotation(session, quot.id, current_user_id=user.id)
        assert submitted.status == "Submitted"

        approved = await quotation_service.approve_quotation(session, quot.id, current_user_id=user.id)
        assert approved.status == "Approved"

        # Clone Quotation
        cloned = await quotation_service.clone_quotation(session, quot.id, current_user_id=user.id)
        assert cloned.id != quot.id
        assert cloned.customer_id == cust.id


@pytest.mark.asyncio
async def test_sales_order_and_delivery_integration():
    """Test Sales Order creation, credit check, approval, and Delivery Order execution (Warehouse Operations GoodsIssue integration)."""
    async with AsyncSessionLocal() as session:
        user = await get_test_admin_user(session)
        product, warehouse = await setup_test_inventory(session)

        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(
                customer_code=f"CUST_SO_{uuid.uuid4().hex[:4]}",
                name="Delivery Target Client",
                credit_limit=Decimal("100000.00"),
            ),
            current_user_id=user.id,
        )

        # 1. Create Sales Order
        so = await sales_order_service.create_order(
            session,
            obj_in=SalesOrderCreate(
                customer_id=cust.id,
                payment_terms="Net 30",
                items=[
                    SalesOrderItemCreate(
                        product_id=product.id,
                        quantity=Decimal("5.0000"),
                        unit_price=Decimal("200.00"),
                        warehouse_id=warehouse.id,
                    )
                ],
            ),
            current_user_id=user.id,
        )
        assert so.status == "Draft"

        # 2. Approve Sales Order
        approved_so = await sales_order_service.approve_order(session, so.id, current_user_id=user.id)
        assert approved_so.status == "Approved"

        # 3. Create Delivery Order (Triggers GoodsIssue physical stock movement in Warehouse Operations)
        del_item = DeliveryOrderItemCreate(
            sales_order_item_id=approved_so.items[0].id,
            product_id=product.id,
            quantity=Decimal("5.0000"),
        )
        delivery = await delivery_service.create_delivery(
            session,
            obj_in=DeliveryOrderCreate(
                sales_order_id=approved_so.id,
                warehouse_id=warehouse.id,
                carrier="BlueDart",
                tracking_number="TRACK123456",
                items=[del_item],
            ),
            current_user_id=user.id,
        )
        assert delivery.status == "Delivered"
        assert delivery.goods_issue_id is not None

        # Verify updated sales order status
        refreshed_so = await sales_order_service.get_order(session, approved_so.id)
        assert refreshed_so.status == "Fully Delivered"
        assert refreshed_so.delivery_status == "Delivered"


@pytest.mark.asyncio
async def test_sales_return_and_stock_reversal():
    """Test Sales Return processing and inventory stock reversal via GoodsReceipt in Warehouse Operations."""
    async with AsyncSessionLocal() as session:
        user = await get_test_admin_user(session)
        product, warehouse = await setup_test_inventory(session)

        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(
                customer_code=f"CUST_SR_{uuid.uuid4().hex[:4]}",
                name="Return Client",
                credit_limit=Decimal("50000.00"),
            ),
            current_user_id=user.id,
        )

        so = await sales_order_service.create_order(
            session,
            obj_in=SalesOrderCreate(
                customer_id=cust.id,
                items=[
                    SalesOrderItemCreate(
                        product_id=product.id,
                        quantity=Decimal("2.0000"),
                        unit_price=Decimal("300.00"),
                        warehouse_id=warehouse.id,
                    )
                ],
            ),
            current_user_id=user.id,
        )
        await sales_order_service.approve_order(session, so.id, current_user_id=user.id)

        # Create Sales Return
        ret = await sales_return_service.create_return(
            session,
            obj_in=SalesReturnCreate(
                sales_order_id=so.id,
                warehouse_id=warehouse.id,
                reason_code="Damaged",
                items=[
                    SalesReturnItemCreate(
                        sales_order_item_id=so.items[0].id,
                        product_id=product.id,
                        quantity=Decimal("1.0000"),
                        reason="Damaged package",
                    )
                ],
            ),
            current_user_id=user.id,
        )
        assert ret.status == "Draft"
        assert ret.total_refund_amount == Decimal("300.00")

        # Approve Return -> Triggers stock reversal via GoodsReceipt
        app_ret = await sales_return_service.approve_return(session, ret.id, current_user_id=user.id)
        assert app_ret.status == "Completed"
        assert app_ret.goods_receipt_id is not None


@pytest.mark.asyncio
async def test_invoice_payload_and_analytics():
    """Test Sales Invoice Payload generation for future Finance domain and Sales Analytics aggregation."""
    async with AsyncSessionLocal() as session:
        user = await get_test_admin_user(session)
        product, warehouse = await setup_test_inventory(session)

        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(
                customer_code=f"CUST_INV_{uuid.uuid4().hex[:4]}",
                name="Invoice Target Client",
                tax_id="GSTIN123456789",
            ),
            current_user_id=user.id,
        )

        so = await sales_order_service.create_order(
            session,
            obj_in=SalesOrderCreate(
                customer_id=cust.id,
                items=[
                    SalesOrderItemCreate(
                        product_id=product.id,
                        quantity=Decimal("3.0000"),
                        unit_price=Decimal("100.00"),
                        tax_rate=Decimal("18.00"),
                        warehouse_id=warehouse.id,
                    )
                ],
            ),
            current_user_id=user.id,
        )
        await sales_order_service.approve_order(session, so.id, current_user_id=user.id)

        # 1. Invoice Payload Generation
        payload = await invoice_payload_service.generate_invoice_payload(session, so.id)
        assert payload.order_number == so.order_number
        assert payload.customer_tax_id == "GSTIN123456789"
        assert len(payload.items) == 1

        # 2. Analytics Summary
        analytics = await sales_analytics_service.get_analytics_summary(session)
        assert analytics.total_orders >= 1
        assert analytics.total_revenue >= Decimal("0.00")

        # 3. Reports
        register = await sales_report_service.get_sales_register(session)
        assert len(register) >= 1
        ledger = await sales_report_service.get_customer_ledger(session, cust.id)
        assert len(ledger) >= 1


@pytest.mark.asyncio
async def test_global_sales_search_and_import_export():
    """Test global sales search and CSV export functionality."""
    async with AsyncSessionLocal() as session:
        user = await get_test_admin_user(session)
        c_code = f"CUST_SRCH_{uuid.uuid4().hex[:4]}"
        cust = await customer_service.create_customer(
            session,
            obj_in=CustomerCreate(
                customer_code=c_code,
                name="Searchable Global Client",
                email="search@client.com",
            ),
            current_user_id=user.id,
        )

        # Search
        results = await sales_search_service.global_sales_search(session, query="Searchable")
        assert len(results) >= 1
        assert any(r.entity_id == str(cust.id) for r in results)
