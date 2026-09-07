from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.user import User
from app.repositories.rbac import role_repository, user_role_repository

from app.repositories.user import user_repository
from app.schemas.inventory import (
    ProductCategoryCreate,
    ProductCreate,
    UnitOfMeasureCreate,
    WarehouseCreate,
)
from app.schemas.procurement import (
    PurchaseOrderCreate,
    PurchaseOrderItemCreate,
    PurchaseRequisitionCreate,
    PurchaseRequisitionItemCreate,
    PurchaseReturnCreate,
    PurchaseReturnItemCreate,
    RFQCreate,
    SupplierCategoryCreate,
    SupplierContactCreate,
    SupplierCreate,
    SupplierQuotationCreate,
    SupplierQuotationItemCreate,
    SupplierRatingCreate,
)
from app.services.inventory_services import (
    category_service,
    product_service,
    unit_of_measure_service,
    warehouse_service,
)
from app.services.procurement_report_services import (
    procurement_analytics_service,
    procurement_report_service,
)
from app.services.procurement_search_services import procurement_search_service
from app.services.purchase_order_services import purchase_order_service
from app.services.purchase_requisition_services import purchase_requisition_service
from app.services.purchase_return_services import purchase_return_service
from app.services.supplier_quotation_services import supplier_quotation_service
from app.services.rfq_services import rfq_service
from app.services.supplier_services import supplier_service


async def get_test_admin_user(session):
    unique_id = uuid.uuid4().hex[:6]
    email = f"proc_admin_{unique_id}@example.com"
    username = f"proc_admin_{unique_id}"
    user = User(
        full_name="Procurement Admin",
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
        session, obj_in=ProductCategoryCreate(name="Procurement Test", code=f"CAT_PR_{uuid.uuid4().hex[:4]}")
    )
    uom = await unit_of_measure_service.create_unit(
        session,
        obj_in=UnitOfMeasureCreate(
            name=f"Unit_{uuid.uuid4().hex[:4]}", symbol=f"u_{uuid.uuid4().hex[:4]}", category="Count"
        ),
    )
    product = await product_service.create_product(
        session,
        obj_in=ProductCreate(
            sku=f"PR-ITEM-{uuid.uuid4().hex[:4]}",
            name="Industrial Valve",
            category_id=cat.id,
            base_unit_id=uom.id,
        ),
    )
    warehouse = await warehouse_service.create_warehouse(
        session,
        obj_in=WarehouseCreate(
            code=f"WH-PR-{uuid.uuid4().hex[:4]}",
            name="Central Receiving Warehouse",
        ),
    )
    return product, warehouse


@pytest.mark.asyncio
async def test_supplier_crud_and_blacklisting():
    async with AsyncSessionLocal() as session:
        admin_user = await get_test_admin_user(session)

        # 1. Create Category
        cat_in = SupplierCategoryCreate(
            code=f"CAT-RAW-{uuid.uuid4().hex[:4]}", name="Raw Materials", description="Metal and raw inputs"
        )
        cat = await supplier_service.create_category(session, cat_in)
        assert "CAT-RAW" in cat.code

        # 2. Create Supplier
        sup_in = SupplierCreate(
            code=f"SUP-{uuid.uuid4().hex[:6]}",
            name="Global Steel Works Ltd",
            category_id=cat.id,
            gst_vat_number="27AAACG1234F1Z5",
            payment_terms="Net 30",
            credit_limit=Decimal("50000.0"),
            currency="USD",
            contacts=[SupplierContactCreate(contact_name="John Doe", email="john@globalsteel.com", is_primary=True)],
        )
        supplier = await supplier_service.create_supplier(session, sup_in, current_user_id=admin_user.id)
        assert supplier.name == "Global Steel Works Ltd"
        assert supplier.status == "Active"
        assert len(supplier.contacts) == 1

        # 3. Add Rating
        rating_in = SupplierRatingCreate(score=Decimal("4.50"), comments="Excellent quality")
        await supplier_service.add_rating(session, supplier.id, rating_in, reviewer_id=admin_user.id)
        updated_sup = await supplier_service.get_supplier(session, supplier.id)
        assert updated_sup.rating == Decimal("4.50")

        # 4. Blacklist Supplier
        blacklisted = await supplier_service.blacklist_supplier(
            session, supplier.id, reason="Compliance audit failure", current_user_id=admin_user.id
        )
        assert blacklisted.status == "Blacklisted"


@pytest.mark.asyncio
async def test_purchase_requisition_lifecycle():
    async with AsyncSessionLocal() as session:
        admin_user = await get_test_admin_user(session)
        product, _ = await setup_test_inventory(session)
        product_id = product["id"] if isinstance(product, dict) else product.id

        pr_in = PurchaseRequisitionCreate(
            required_date=datetime.now(timezone.utc) + timedelta(days=7),
            priority="High",
            remarks="Urgent stock replenishment",
            items=[
                PurchaseRequisitionItemCreate(
                    product_id=product_id,
                    quantity=Decimal("100.0"),
                    estimated_unit_price=Decimal("25.0"),
                )
            ],
        )
        pr = await purchase_requisition_service.create_requisition(session, pr_in, requester_id=admin_user.id)
        assert pr.status == "Draft"
        assert pr.total_estimated_amount == Decimal("2500.0")

        # Submit PR
        submitted = await purchase_requisition_service.submit_requisition(session, pr.id, requester_id=admin_user.id)
        assert submitted.status in ("Submitted", "Approved")

        # Approve PR if not already auto-approved by approval engine
        if submitted.status != "Approved":
            approved = await purchase_requisition_service.approve_requisition(session, pr.id, approver_id=admin_user.id)
            assert approved.status == "Approved"
        else:
            assert submitted.status == "Approved"


@pytest.mark.asyncio
async def test_rfq_and_comparison_matrix():
    async with AsyncSessionLocal() as session:
        admin_user = await get_test_admin_user(session)
        product, _ = await setup_test_inventory(session)
        product_id = product["id"] if isinstance(product, dict) else product.id

        # Setup Active Supplier
        sup_in = SupplierCreate(
            code=f"SUP-{uuid.uuid4().hex[:6]}",
            name="Apex Industrial Supplies",
            payment_terms="Net 30",
            currency="USD",
        )
        supplier = await supplier_service.create_supplier(session, sup_in, current_user_id=admin_user.id)

        # Create RFQ
        rfq_in = RFQCreate(
            title="Procurement of Machined Valves",
            submission_deadline=datetime.now(timezone.utc) + timedelta(days=5),
            supplier_ids=[supplier.id],
        )
        rfq = await rfq_service.create_rfq(session, rfq_in, current_user_id=admin_user.id)
        assert rfq.status == "Draft"
        assert len(rfq.invited_suppliers) == 1

        # Issue RFQ
        issued = await rfq_service.issue_rfq(session, rfq.id, current_user_id=admin_user.id)
        assert issued.status == "Issued"

        # Submit Quotation for RFQ
        sq_in = SupplierQuotationCreate(
            rfq_id=rfq.id,
            supplier_id=supplier.id,
            validity_date=datetime.now(timezone.utc) + timedelta(days=14),
            lead_time_days=5,
            items=[
                SupplierQuotationItemCreate(
                    product_id=product_id,
                    quantity=Decimal("50.0"),
                    unit_price=Decimal("40.0"),
                    tax_pct=Decimal("10.0"),
                )
            ],
        )
        sq = await supplier_quotation_service.create_quotation(session, sq_in, current_user_id=admin_user.id)
        assert sq.status == "Draft"
        assert sq.total_amount == Decimal("2200.0")
        submitted = await supplier_quotation_service.submit_quotation(session, sq.id, current_user_id=admin_user.id)
        assert submitted.status == "Submitted"

        # Generate Comparison Matrix
        matrix = await rfq_service.get_comparison_matrix(session, rfq.id)
        assert matrix.quotations_count == 1
        assert len(matrix.comparison_items) == 1
        assert matrix.comparison_items[0]["total_amount"] == 2200.0


@pytest.mark.asyncio
async def test_purchase_order_goods_receipt_integration():
    async with AsyncSessionLocal() as session:
        admin_user = await get_test_admin_user(session)
        product, warehouse = await setup_test_inventory(session)
        product_id = product["id"] if isinstance(product, dict) else product.id

        # 1. Create Active Supplier
        sup_in = SupplierCreate(
            code=f"SUP-{uuid.uuid4().hex[:6]}",
            name="Precision Components Inc",
            payment_terms="Net 30",
            currency="USD",
        )
        supplier = await supplier_service.create_supplier(session, sup_in, current_user_id=admin_user.id)

        # 2. Create Purchase Order
        po_in = PurchaseOrderCreate(
            supplier_id=supplier.id,
            expected_delivery_date=datetime.now(timezone.utc) + timedelta(days=10),
            items=[
                PurchaseOrderItemCreate(
                    product_id=product_id,
                    quantity=Decimal("40.0"),
                    unit_price=Decimal("100.0"),
                    discount_pct=Decimal("5.0"),
                    tax_pct=Decimal("10.0"),
                    warehouse_id=warehouse.id,
                )
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=admin_user.id)
        assert po.status == "Draft"
        # Gross: 4000. Disc: 200. After Disc: 3800. Tax 10%: 380. Total: 4180.
        assert po.total_amount == Decimal("4180.0")

        # Approve PO
        approved_po = await purchase_order_service.approve_order(session, po.id, approver_id=admin_user.id)
        assert approved_po.status == "Approved"

        # 3. Receive Goods (GoodsReceipt Integration)
        po_item = approved_po.items[0]
        receipt = await purchase_order_service.receive_goods(
            session,
            po_id=approved_po.id,
            receiving_items=[{"po_item_id": str(po_item.id), "quantity": 40.0}],
            supplier_ref="INV-889900",
            remarks="Full delivery received clean",
            current_user_id=admin_user.id,
        )
        assert receipt.status == "Received"

        # Verify PO Receiving Counter and Status
        updated_po = await purchase_order_service.get_order(session, approved_po.id)
        assert updated_po.status == "Fully Received"
        assert updated_po.items[0].received_quantity == Decimal("40.0")
        assert updated_po.items[0].status == "Fully Received"


@pytest.mark.asyncio
async def test_purchase_return_stock_reversal():
    async with AsyncSessionLocal() as session:
        admin_user = await get_test_admin_user(session)
        product, warehouse = await setup_test_inventory(session)
        product_id = product["id"] if isinstance(product, dict) else product.id


        # Setup PO and receive stock first
        sup_in = SupplierCreate(code=f"SUP-{uuid.uuid4().hex[:6]}", name="Vortex Tech Supplies")
        supplier = await supplier_service.create_supplier(session, sup_in, current_user_id=admin_user.id)

        po_in = PurchaseOrderCreate(
            supplier_id=supplier.id,
            items=[
                PurchaseOrderItemCreate(
                    product_id=product_id,
                    quantity=Decimal("20.0"),
                    unit_price=Decimal("50.0"),
                    warehouse_id=warehouse.id,
                )
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=admin_user.id)
        await purchase_order_service.approve_order(session, po.id, approver_id=admin_user.id)
        po_item = po.items[0]
        await purchase_order_service.receive_goods(
            session,
            po_id=po.id,
            receiving_items=[{"po_item_id": str(po_item.id), "quantity": 20.0}],
            current_user_id=admin_user.id,
        )

        # Create Purchase Return
        ret_in = PurchaseReturnCreate(
            purchase_order_id=po.id,
            supplier_id=supplier.id,
            warehouse_id=warehouse.id,
            reason_code="Damaged",
            remarks="Damaged during shipping transit",
            items=[
                PurchaseReturnItemCreate(
                    po_item_id=po_item.id,
                    product_id=product_id,
                    return_quantity=Decimal("5.0"),
                    unit_price=Decimal("50.0"),
                )
            ],
        )
        ret = await purchase_return_service.create_return(session, ret_in, current_user_id=admin_user.id)
        assert ret.status == "Draft"
        assert ret.total_return_amount == Decimal("250.0")

        # Process Return (Triggers Stock Reversal OUT)
        processed = await purchase_return_service.process_return(session, ret.id, current_user_id=admin_user.id)
        assert processed.status == "Processed"

        # Verify PO Item Returned Counter updated
        updated_po = await purchase_order_service.get_order(session, po.id)
        assert updated_po.items[0].returned_quantity == Decimal("5.0")


@pytest.mark.asyncio
async def test_procurement_analytics_and_reports():
    async with AsyncSessionLocal() as session:
        register = await procurement_report_service.get_purchase_register(session)
        assert isinstance(register, list)

        ledger = await procurement_report_service.get_supplier_ledger(session)
        assert isinstance(ledger, list)

        summary = await procurement_analytics_service.get_dashboard_summary(session)
        assert summary.total_purchase_spend >= Decimal("0.0")
        assert summary.open_po_count >= 0


@pytest.mark.asyncio
async def test_global_procurement_search():
    async with AsyncSessionLocal() as session:
        res = await procurement_search_service.global_search(session, query="SUP")
        assert res.query == "SUP"
        assert isinstance(res.suppliers, list)
        assert isinstance(res.purchase_orders, list)
