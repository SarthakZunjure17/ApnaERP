from datetime import datetime, timedelta, timezone
from decimal import Decimal
import io
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.redis import redis_manager
from app.core.security import create_access_token, hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.goods_receipt import GoodsReceipt
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.purchase_requisition import PurchaseRequisition, PurchaseRequisitionItem
from app.models.purchase_return import PurchaseReturn, PurchaseReturnItem
from app.models.rfq import RFQ, RFQSupplier
from app.models.stock_balance import StockBalance
from app.models.stock_ledger import StockLedger
from app.models.supplier import Supplier, SupplierRating
from app.models.supplier_quotation import SupplierQuotation, SupplierQuotationItem
from app.models.unit_of_measure import UnitOfMeasure
from app.models.user import User
from app.models.user_role import UserRole
from app.models.warehouse import Warehouse
from app.repositories.rbac import role_repository
from app.schemas.inventory import ProductCategoryCreate, ProductCreate, UnitOfMeasureCreate, WarehouseCreate
from app.schemas.procurement import (
    PurchaseOrderCreate,
    PurchaseOrderItemCreate,
    PurchaseRequisitionCreate,
    PurchaseRequisitionItemCreate,
    PurchaseReturnCreate,
    PurchaseReturnItemCreate,
    RFQCreate,
    SupplierCreate,
    SupplierQuotationCreate,
    SupplierQuotationItemCreate,
)
from app.services.inventory_services import category_service, product_service, unit_of_measure_service, warehouse_service
from app.services.procurement_report_services import procurement_analytics_service, procurement_report_service
from app.services.purchase_order_services import purchase_order_service
from app.services.purchase_requisition_services import purchase_requisition_service
from app.services.purchase_return_services import purchase_return_service
from app.services.rfq_services import rfq_service
from app.services.supplier_quotation_services import supplier_quotation_service
from app.services.supplier_services import supplier_service


def get_id(obj) -> uuid.UUID:
    if isinstance(obj, dict):
        raw = obj["id"]
        return uuid.UUID(str(raw)) if not isinstance(raw, uuid.UUID) else raw
    return obj.id


async def setup_test_fixtures(session):
    try:
        await redis_manager.delete("procurement:dashboard:summary:None:None")
    except Exception:
        pass
    suffix = uuid.uuid4().hex[:6]

    # Users
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
    unauth_user = User(
        full_name=f"Unauthorized User {suffix}",
        email=f"unauth_{suffix}@apnaerp.test",
        username=f"unauth_{suffix}",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    session.add_all([mgr_user, viewer_user, unauth_user])
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
    await session.refresh(unauth_user)

    # Master inventory setup
    cat = await category_service.create_category(session, obj_in=ProductCategoryCreate(code=f"CAT-{suffix}", name=f"Category {suffix}"))
    cat_id = get_id(cat)

    uom = await unit_of_measure_service.create_unit(session, obj_in=UnitOfMeasureCreate(name=f"Pcs_{suffix}", symbol=f"pc_{suffix}", category="Count"))
    uom_id = get_id(uom)

    wh = await warehouse_service.create_warehouse(session, obj_in=WarehouseCreate(code=f"WH-{suffix}", name=f"Main WH {suffix}"))
    wh_id = get_id(wh)

    prod_a = await product_service.create_product(
        session,
        obj_in=ProductCreate(sku=f"SKU-A-{suffix}", name=f"Product Alpha {suffix}", category_id=cat_id, base_unit_id=uom_id),
    )
    prod_a_id = get_id(prod_a)

    prod_b = await product_service.create_product(
        session,
        obj_in=ProductCreate(sku=f"SKU-B-{suffix}", name=f"Product Beta {suffix}", category_id=cat_id, base_unit_id=uom_id),
    )
    prod_b_id = get_id(prod_b)

    # Suppliers
    sup1 = await supplier_service.create_supplier(
        session,
        obj_in=SupplierCreate(code=f"SUP1-{suffix}", name=f"Apex Logistics {suffix}", payment_terms="Net 30"),
        current_user_id=mgr_user.id,
    )
    sup2 = await supplier_service.create_supplier(
        session,
        obj_in=SupplierCreate(code=f"SUP2-{suffix}", name=f"Beta Industrial {suffix}", payment_terms="Net 60"),
        current_user_id=mgr_user.id,
    )

    return {
        "mgr_user": mgr_user,
        "viewer_user": viewer_user,
        "unauth_user": unauth_user,
        "warehouse_id": wh_id,
        "product_a_id": prod_a_id,
        "product_b_id": prod_b_id,
        "supplier_1": sup1,
        "supplier_2": sup2,
    }


@pytest.mark.asyncio
async def test_procurement_dashboard_analytics():
    async with AsyncSessionLocal() as session:
        f = await setup_test_fixtures(session)
        mgr_user = f["mgr_user"]
        wh_id = f["warehouse_id"]
        prod_a_id = f["product_a_id"]
        sup1 = f["supplier_1"]
        sup2 = f["supplier_2"]

        # 1. Create Requisition
        req_in = PurchaseRequisitionCreate(
            required_date=datetime.now(timezone.utc) + timedelta(days=5),
            priority="High",
            remarks="Dashboard Requisition Test",
            items=[
                PurchaseRequisitionItemCreate(
                    product_id=prod_a_id,
                    quantity=Decimal("100.0"),
                    estimated_unit_price=Decimal("10.0"),
                )
            ],
        )
        req = await purchase_requisition_service.create_requisition(session, req_in, requester_id=mgr_user.id)
        await purchase_requisition_service.submit_requisition(session, req.id, requester_id=mgr_user.id)

        # 2. Create RFQ
        rfq_in = RFQCreate(
            title="Dashboard RFQ Test",
            requisition_id=req.id,
            submission_deadline=datetime.now(timezone.utc) + timedelta(days=7),
            supplier_ids=[sup1.id, sup2.id],
        )
        rfq = await rfq_service.create_rfq(session, rfq_in, current_user_id=mgr_user.id)
        await rfq_service.issue_rfq(session, rfq.id, current_user_id=mgr_user.id)

        # 3. Create Quotation
        quot_in = SupplierQuotationCreate(
            rfq_id=rfq.id,
            supplier_id=sup1.id,
            validity_date=datetime.now(timezone.utc) + timedelta(days=15),
            lead_time_days=5,
            items=[
                SupplierQuotationItemCreate(
                    product_id=prod_a_id,
                    quantity=Decimal("100.0"),
                    unit_price=Decimal("9.5"),
                )
            ],
        )
        quot = await supplier_quotation_service.create_quotation(session, quot_in, current_user_id=mgr_user.id)
        await supplier_quotation_service.submit_quotation(session, quot.id, current_user_id=mgr_user.id)
        await supplier_quotation_service.approve_quotation(session, quot.id, current_user_id=mgr_user.id)

        # 4. Create Purchase Order
        po_in = PurchaseOrderCreate(
            supplier_id=sup1.id,
            order_date=datetime.now(timezone.utc),
            items=[
                PurchaseOrderItemCreate(
                    product_id=prod_a_id,
                    quantity=Decimal("100.0"),
                    unit_price=Decimal("9.5"),
                    warehouse_id=wh_id,
                )
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=mgr_user.id)
        await purchase_order_service.approve_order(session, po.id, approver_id=mgr_user.id)

        # Receive 70 units
        po_item = po.items[0]
        await purchase_order_service.receive_goods(
            session,
            po_id=po.id,
            receiving_items=[{"po_item_id": str(po_item.id), "quantity": 70.0}],
            supplier_ref="INV-REC-70",
            current_user_id=mgr_user.id,
        )

        # Fetch dashboard summary
        try:
            await redis_manager.delete("procurement:dashboard:summary:None:None")
        except Exception:
            pass
        summary = await procurement_analytics_service.get_dashboard_summary(session)
        assert summary.total_suppliers >= 2
        assert summary.active_suppliers >= 2
        assert summary.total_purchase_spend >= Decimal("950.0")
        assert summary.total_ordered_quantity >= Decimal("100.0")
        assert summary.total_received_quantity >= Decimal("70.0")
        assert summary.open_requisitions >= 1
        assert summary.open_rfqs >= 1
        assert summary.approved_quotations >= 1


@pytest.mark.asyncio
async def test_purchase_orders_report_and_filters():
    async with AsyncSessionLocal() as session:
        f = await setup_test_fixtures(session)
        mgr_user = f["mgr_user"]
        wh_id = f["warehouse_id"]
        prod_a_id = f["product_a_id"]
        prod_b_id = f["product_b_id"]
        sup1 = f["supplier_1"]

        po_in = PurchaseOrderCreate(
            supplier_id=sup1.id,
            items=[
                PurchaseOrderItemCreate(
                    product_id=prod_a_id,
                    quantity=Decimal("50.0"),
                    unit_price=Decimal("20.0"),
                    warehouse_id=wh_id,
                ),
                PurchaseOrderItemCreate(
                    product_id=prod_b_id,
                    quantity=Decimal("25.0"),
                    unit_price=Decimal("40.0"),
                    warehouse_id=wh_id,
                ),
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=mgr_user.id)
        await purchase_order_service.approve_order(session, po.id, approver_id=mgr_user.id)

        # Report without filter
        report = await procurement_report_service.get_purchase_orders_report(session, supplier_id=sup1.id)
        assert report.total >= 1
        found = next(p for p in report.items if p.id == po.id)
        assert found.po_number == po.po_number
        assert found.total_amount == Decimal("2000.0")
        assert found.ordered_quantity == Decimal("75.0")
        assert found.items_count == 2

        # Report with product filter
        prod_report = await procurement_report_service.get_purchase_orders_report(session, product_id=prod_a_id)
        assert any(p.id == po.id for p in prod_report.items)


@pytest.mark.asyncio
async def test_supplier_performance_report():
    async with AsyncSessionLocal() as session:
        f = await setup_test_fixtures(session)
        mgr_user = f["mgr_user"]
        wh_id = f["warehouse_id"]
        prod_a_id = f["product_a_id"]
        sup1 = f["supplier_1"]

        po_in = PurchaseOrderCreate(
            supplier_id=sup1.id,
            items=[
                PurchaseOrderItemCreate(
                    product_id=prod_a_id,
                    quantity=Decimal("40.0"),
                    unit_price=Decimal("15.0"),
                    warehouse_id=wh_id,
                )
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=mgr_user.id)
        await purchase_order_service.approve_order(session, po.id, approver_id=mgr_user.id)

        report = await procurement_report_service.get_supplier_performance_report(session, supplier_id=sup1.id)
        assert report.total == 1
        item = report.items[0]
        assert item.supplier_id == sup1.id
        assert item.supplier_code == sup1.code
        assert item.total_pos >= 1
        assert item.ordered_quantity >= Decimal("40.0")


@pytest.mark.asyncio
async def test_requisitions_and_rfq_reports():
    async with AsyncSessionLocal() as session:
        f = await setup_test_fixtures(session)
        mgr_user = f["mgr_user"]
        prod_a_id = f["product_a_id"]
        sup1 = f["supplier_1"]

        # PR Report
        req_in = PurchaseRequisitionCreate(
            required_date=datetime.now(timezone.utc) + timedelta(days=3),
            priority="Urgent",
            remarks="PR Report Test",
            items=[
                PurchaseRequisitionItemCreate(
                    product_id=prod_a_id,
                    quantity=Decimal("15.0"),
                    estimated_unit_price=Decimal("10.0"),
                )
            ],
        )
        req = await purchase_requisition_service.create_requisition(session, req_in, requester_id=mgr_user.id)

        pr_report = await procurement_report_service.get_requisitions_report(session, priority="Urgent")
        assert any(r.id == req.id for r in pr_report.items)

        # RFQ Report
        rfq_in = RFQCreate(
            title="RFQ Report Test",
            requisition_id=req.id,
            submission_deadline=datetime.now(timezone.utc) + timedelta(days=5),
            supplier_ids=[sup1.id],
        )
        rfq = await rfq_service.create_rfq(session, rfq_in, current_user_id=mgr_user.id)
        rfq_report = await procurement_report_service.get_rfqs_report(session)
        assert any(r.id == rfq.id for r in rfq_report.items)


@pytest.mark.asyncio
async def test_quotation_and_receiving_and_returns_reports():
    async with AsyncSessionLocal() as session:
        f = await setup_test_fixtures(session)
        mgr_user = f["mgr_user"]
        wh_id = f["warehouse_id"]
        prod_a_id = f["product_a_id"]
        sup1 = f["supplier_1"]

        # 1. Quotation Report
        quot_in = SupplierQuotationCreate(
            supplier_id=sup1.id,
            validity_date=datetime.now(timezone.utc) + timedelta(days=20),
            items=[
                SupplierQuotationItemCreate(
                    product_id=prod_a_id,
                    quantity=Decimal("30.0"),
                    unit_price=Decimal("12.0"),
                )
            ],
        )
        quot = await supplier_quotation_service.create_quotation(session, quot_in, current_user_id=mgr_user.id)
        quot_report = await procurement_report_service.get_quotations_report(session, supplier_id=sup1.id)
        assert any(q.id == quot.id for q in quot_report.items)

        # 2. PO & Receiving Report
        po_in = PurchaseOrderCreate(
            supplier_id=sup1.id,
            items=[
                PurchaseOrderItemCreate(
                    product_id=prod_a_id,
                    quantity=Decimal("30.0"),
                    unit_price=Decimal("12.0"),
                    warehouse_id=wh_id,
                )
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=mgr_user.id)
        await purchase_order_service.approve_order(session, po.id, approver_id=mgr_user.id)
        po_item = po.items[0]

        receipt = await purchase_order_service.receive_goods(
            session,
            po_id=po.id,
            receiving_items=[{"po_item_id": str(po_item.id), "quantity": 30.0}],
            supplier_ref="GRN-REPORT-TEST",
            current_user_id=mgr_user.id,
        )
        rec_report = await procurement_report_service.get_receiving_report(session, warehouse_id=wh_id)
        assert any(r.id == receipt.id for r in rec_report.items)

        # 3. Returns Report
        ret_in = PurchaseReturnCreate(
            purchase_order_id=po.id,
            supplier_id=sup1.id,
            warehouse_id=wh_id,
            reason_code="Defective",
            remarks="Defective lot returned",
            items=[
                PurchaseReturnItemCreate(
                    po_item_id=po_item.id,
                    product_id=prod_a_id,
                    return_quantity=Decimal("5.0"),
                    unit_price=Decimal("12.0"),
                )
            ],
        )
        ret = await purchase_return_service.create_return(session, ret_in, current_user_id=mgr_user.id)
        await purchase_return_service.process_return(session, ret.id, current_user_id=mgr_user.id)

        ret_report = await procurement_report_service.get_returns_report(session, supplier_id=sup1.id)
        assert any(r.id == ret.id for r in ret_report.items)


@pytest.mark.asyncio
async def test_procurement_spend_and_efficiency_analytics():
    async with AsyncSessionLocal() as session:
        f = await setup_test_fixtures(session)
        mgr_user = f["mgr_user"]
        wh_id = f["warehouse_id"]
        prod_a_id = f["product_a_id"]
        sup1 = f["supplier_1"]

        po_in = PurchaseOrderCreate(
            supplier_id=sup1.id,
            items=[
                PurchaseOrderItemCreate(
                    product_id=prod_a_id,
                    quantity=Decimal("10.0"),
                    unit_price=Decimal("100.0"),
                    warehouse_id=wh_id,
                )
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=mgr_user.id)
        await purchase_order_service.approve_order(session, po.id, approver_id=mgr_user.id)

        # Spend Analytics
        spend = await procurement_report_service.get_spend_analytics(session, supplier_id=sup1.id)
        assert spend.total_spend >= Decimal("1000.0")
        assert len(spend.spend_by_supplier) >= 1
        assert len(spend.spend_by_warehouse) >= 1

        # Efficiency Metrics
        eff = await procurement_report_service.get_efficiency_metrics(session)
        assert eff.total_pos >= 1
        assert eff.total_ordered_quantity >= Decimal("10.0")


@pytest.mark.asyncio
async def test_read_only_guarantee():
    """
    Guarantees reports are 100% read-only and never mutate database state or counters.
    """
    async with AsyncSessionLocal() as session:
        # Pre-report snapshot of counts
        sup_cnt_before = (await session.execute(select(func.count(Supplier.id)))).scalar()
        po_cnt_before = (await session.execute(select(func.count(PurchaseOrder.id)))).scalar()
        gr_cnt_before = (await session.execute(select(func.count(GoodsReceipt.id)))).scalar()
        ret_cnt_before = (await session.execute(select(func.count(PurchaseReturn.id)))).scalar()
        stk_ledger_cnt_before = (await session.execute(select(func.count(StockLedger.id)))).scalar()
        stk_bal_cnt_before = (await session.execute(select(func.count(StockBalance.id)))).scalar()

        # Run all reports
        await procurement_analytics_service.get_dashboard_summary(session)
        await procurement_report_service.get_purchase_orders_report(session)
        await procurement_report_service.get_supplier_performance_report(session)
        await procurement_report_service.get_requisitions_report(session)
        await procurement_report_service.get_rfqs_report(session)
        await procurement_report_service.get_quotations_report(session)
        await procurement_report_service.get_receiving_report(session)
        await procurement_report_service.get_returns_report(session)
        await procurement_report_service.get_spend_analytics(session)
        await procurement_report_service.get_efficiency_metrics(session)

        # Post-report snapshot of counts
        sup_cnt_after = (await session.execute(select(func.count(Supplier.id)))).scalar()
        po_cnt_after = (await session.execute(select(func.count(PurchaseOrder.id)))).scalar()
        gr_cnt_after = (await session.execute(select(func.count(GoodsReceipt.id)))).scalar()
        ret_cnt_after = (await session.execute(select(func.count(PurchaseReturn.id)))).scalar()
        stk_ledger_cnt_after = (await session.execute(select(func.count(StockLedger.id)))).scalar()
        stk_bal_cnt_after = (await session.execute(select(func.count(StockBalance.id)))).scalar()

        assert sup_cnt_before == sup_cnt_after
        assert po_cnt_before == po_cnt_after
        assert gr_cnt_before == gr_cnt_after
        assert ret_cnt_before == ret_cnt_after
        assert stk_ledger_cnt_before == stk_ledger_cnt_after
        assert stk_bal_cnt_before == stk_bal_cnt_after


@pytest.mark.asyncio
async def test_procurement_reports_and_analytics_api_endpoints():
    async with AsyncSessionLocal() as session:
        f = await setup_test_fixtures(session)
        mgr_user = f["mgr_user"]
        viewer_user = f["viewer_user"]
        unauth_user = f["unauth_user"]

        mgr_token = create_access_token(subject=str(mgr_user.id))
        viewer_token = create_access_token(subject=str(viewer_user.id))
        unauth_token = create_access_token(subject=str(unauth_user.id))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Procurement Manager Access
        headers_mgr = {"Authorization": f"Bearer {mgr_token}"}
        res = await client.get("/api/v1/procurement/reports/dashboard", headers=headers_mgr)
        assert res.status_code == 200
        assert "total_suppliers" in res.json()

        res = await client.get("/api/v1/procurement/reports/purchase-orders", headers=headers_mgr)
        assert res.status_code == 200
        assert "items" in res.json()

        res = await client.get("/api/v1/procurement/reports/suppliers", headers=headers_mgr)
        assert res.status_code == 200

        res = await client.get("/api/v1/procurement/reports/requisitions", headers=headers_mgr)
        assert res.status_code == 200

        res = await client.get("/api/v1/procurement/reports/rfqs", headers=headers_mgr)
        assert res.status_code == 200

        res = await client.get("/api/v1/procurement/reports/quotations", headers=headers_mgr)
        assert res.status_code == 200

        res = await client.get("/api/v1/procurement/reports/receiving", headers=headers_mgr)
        assert res.status_code == 200

        res = await client.get("/api/v1/procurement/reports/returns", headers=headers_mgr)
        assert res.status_code == 200

        res = await client.get("/api/v1/procurement/reports/spend", headers=headers_mgr)
        assert res.status_code == 200

        res = await client.get("/api/v1/procurement/reports/efficiency", headers=headers_mgr)
        assert res.status_code == 200

        # Analytics router
        res = await client.get("/api/v1/procurement/analytics/dashboard-summary", headers=headers_mgr)
        assert res.status_code == 200

        res = await client.get("/api/v1/procurement/analytics/spend", headers=headers_mgr)
        assert res.status_code == 200

        res = await client.get("/api/v1/procurement/analytics/efficiency", headers=headers_mgr)
        assert res.status_code == 200

        # CSV Exports
        res = await client.get("/api/v1/procurement/import-export/export?entity_type=suppliers", headers=headers_mgr)
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]

        res = await client.get("/api/v1/procurement/import-export/export?entity_type=purchase_orders", headers=headers_mgr)
        assert res.status_code == 200

        res = await client.get("/api/v1/procurement/import-export/export?entity_type=receiving", headers=headers_mgr)
        assert res.status_code == 200

        res = await client.get("/api/v1/procurement/import-export/export?entity_type=returns", headers=headers_mgr)
        assert res.status_code == 200

        # 2. Procurement Viewer Access (Read-Only)
        headers_viewer = {"Authorization": f"Bearer {viewer_token}"}
        res_view = await client.get("/api/v1/procurement/reports/dashboard", headers=headers_viewer)
        assert res_view.status_code == 200

        res_view = await client.get("/api/v1/procurement/reports/purchase-orders", headers=headers_viewer)
        assert res_view.status_code == 200

        # 3. Unauthorized User Access (Must be rejected 403)
        headers_unauth = {"Authorization": f"Bearer {unauth_token}"}
        res_unauth = await client.get("/api/v1/procurement/reports/dashboard", headers=headers_unauth)
        assert res_unauth.status_code == 403
