from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.goods_receipt import GoodsReceipt
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.stock_balance import StockBalance
from app.models.stock_ledger import StockLedger
from app.models.supplier import Supplier
from app.models.supplier_quotation import SupplierQuotation, SupplierQuotationItem
from app.models.unit_of_measure import UnitOfMeasure
from app.models.user import User
from app.models.warehouse import Warehouse
from app.repositories.rbac import role_repository, user_role_repository
from app.schemas.inventory import (
    ProductCategoryCreate,
    ProductCreate,
    UnitOfMeasureCreate,
    WarehouseCreate,
)
from app.schemas.procurement import (
    PurchaseOrderAmend,
    PurchaseOrderCreate,
    PurchaseOrderFromQuotationCreate,
    PurchaseOrderItemCreate,
    PurchaseOrderUpdate,
    RFQCreate,
    SupplierCategoryCreate,
    SupplierCreate,
    SupplierQuotationCreate,
    SupplierQuotationItemCreate,
)
from app.services.inventory_services import (
    category_service,
    product_service,
    unit_of_measure_service,
    warehouse_service,
)
from app.services.purchase_order_services import purchase_order_service
from app.services.rfq_services import rfq_service
from app.services.supplier_quotation_services import supplier_quotation_service
from app.services.supplier_services import supplier_service


from app.core.security import hash_password
from app.models.user_role import UserRole

async def get_test_procurement_users(session):
    unique = uuid.uuid4().hex[:6]
    mgr_user = User(
        full_name="Procurement Manager User",
        email=f"proc_mgr_{unique}@example.com",
        username=f"proc_mgr_{unique}",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    viewer_user = User(
        full_name="Procurement Viewer User",
        email=f"proc_view_{unique}@example.com",
        username=f"proc_view_{unique}",
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

    return mgr_user, viewer_user


async def setup_procurement_test_data(session, current_user):
    suffix = uuid.uuid4().hex[:6]

    cat = await category_service.create_category(
        session, obj_in=ProductCategoryCreate(code=f"CAT-{suffix}", name=f"Raw Materials {suffix}")
    )

    uom = await unit_of_measure_service.create_unit(
        session, obj_in=UnitOfMeasureCreate(name=f"Piece_{suffix}", symbol=f"pc_{suffix}", category="Count")
    )

    prod_dict = await product_service.create_product(
        session,
        obj_in=ProductCreate(
            sku=f"SKU-PO-{suffix}",
            name=f"Industrial Valve {suffix}",
            category_id=cat.id,
            base_unit_id=uom.id,
        ),
    )
    product = await product_service.get_product(session, prod_dict["id"])

    wh = await warehouse_service.create_warehouse(
        session, obj_in=WarehouseCreate(code=f"WH-PO-{suffix}", name=f"Main PO Warehouse {suffix}")
    )

    sup_cat = await supplier_service.create_category(
        session, obj_in=SupplierCategoryCreate(code=f"SCAT-{suffix}", name="Industrial Hardware")
    )

    supplier = await supplier_service.create_supplier(
        session,
        obj_in=SupplierCreate(
            code=f"SUP-{suffix}",
            name=f"Standard Supplies {suffix}",
            category_id=sup_cat.id,
            payment_terms="Net 30",
            currency="USD",
        ),
        current_user_id=current_user.id,
    )

    return product, wh, uom, supplier

    return product, wh, uom, supplier


@pytest.mark.asyncio
async def test_01_05_purchase_order_creation_validation_totals_draft_update():
    async with AsyncSessionLocal() as session:
        manager, _ = await get_test_procurement_users(session)
        product, wh, uom, supplier = await setup_procurement_test_data(session, manager)

        # 1. PO Create with line calculations
        po_in = PurchaseOrderCreate(
            supplier_id=supplier.id,
            expected_delivery_date=datetime.now(timezone.utc) + timedelta(days=10),
            payment_terms="Net 30",
            currency="USD",
            notes="Standard replenishment purchase order",
            items=[
                PurchaseOrderItemCreate(
                    product_id=product.id,
                    warehouse_id=wh.id,
                    quantity=Decimal("10.0"),
                    unit_price=Decimal("100.0"),
                    discount_pct=Decimal("10.0"),  # 10% discount: 1000 - 100 = 900
                    tax_pct=Decimal("5.0"),       # 5% tax: 900 * 0.05 = 45 -> line total 945
                ),
                PurchaseOrderItemCreate(
                    product_id=product.id,
                    warehouse_id=wh.id,
                    quantity=Decimal("5.0"),
                    unit_price=Decimal("50.0"),
                    discount_pct=Decimal("0.0"),   # 250
                    tax_pct=Decimal("10.0"),       # 250 * 0.10 = 25 -> line total 275
                ),
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=manager.id)
        assert po.status == "Draft"
        assert po.revision_number == 1
        assert po.po_number.startswith("PO-")
        assert po.subtotal == Decimal("1250.0")
        assert po.discount_amount == Decimal("100.0")
        assert po.tax_amount == Decimal("70.0")
        assert po.total_amount == Decimal("1220.0")
        assert len(po.items) == 2

        # 2. Validation failures
        with pytest.raises(Exception):
            # Qty <= 0
            invalid_in = po_in.model_copy(
                update={"items": [po_in.items[0].model_copy(update={"quantity": Decimal("0.0")})]}
            )
            await purchase_order_service.create_order(session, invalid_in, current_user_id=manager.id)

        with pytest.raises(Exception):
            # Unit Price < 0
            invalid_in = po_in.model_copy(
                update={"items": [po_in.items[0].model_copy(update={"unit_price": Decimal("-10.0")})]}
            )
            await purchase_order_service.create_order(session, invalid_in, current_user_id=manager.id)

        with pytest.raises(Exception):
            # Empty items
            invalid_in = po_in.model_copy(update={"items": []})
            await purchase_order_service.create_order(session, invalid_in, current_user_id=manager.id)

        # 3. Retrieval
        fetched_po = await purchase_order_service.get_order(session, po.id)
        assert fetched_po.po_number == po.po_number
        assert len(fetched_po.items) == 2

        # 4. Update in Draft
        update_in = PurchaseOrderUpdate(
            notes="Updated PO Notes in Draft",
            items=[
                PurchaseOrderItemCreate(
                    product_id=product.id,
                    warehouse_id=wh.id,
                    quantity=Decimal("20.0"),
                    unit_price=Decimal("100.0"),
                    discount_pct=Decimal("0.0"),
                    tax_pct=Decimal("10.0"),  # 2000 + 200 = 2200
                )
            ],
        )
        updated_po = await purchase_order_service.update_order(
            session, po.id, update_in, current_user_id=manager.id
        )
        assert updated_po.notes == "Updated PO Notes in Draft"
        assert updated_po.subtotal == Decimal("2000.0")
        assert updated_po.tax_amount == Decimal("200.0")
        assert updated_po.total_amount == Decimal("2200.0")
        assert len(updated_po.items) == 1


@pytest.mark.asyncio
async def test_06_09_purchase_order_submission_approval_rejection_immutability():
    async with AsyncSessionLocal() as session:
        manager, _ = await get_test_procurement_users(session)
        product, wh, uom, supplier = await setup_procurement_test_data(session, manager)

        po_in = PurchaseOrderCreate(
            supplier_id=supplier.id,
            items=[
                PurchaseOrderItemCreate(
                    product_id=product.id,
                    warehouse_id=wh.id,
                    quantity=Decimal("5.0"),
                    unit_price=Decimal("100.0"),
                )
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=manager.id)

        # 6. Submit PO -> Submitted (ApprovalEngine integration)
        submitted_po = await purchase_order_service.submit_order(session, po.id, current_user_id=manager.id)
        assert submitted_po.status == "Submitted"

        # 7. Rejection
        rejected_po = await purchase_order_service.reject_order(
            session, po.id, rejecter_id=manager.id, reason="Budget exceeded for Q3"
        )
        assert rejected_po.status == "Rejected"
        assert "Budget exceeded for Q3" in (rejected_po.notes or "")

        # Re-submit from Rejected
        re_submitted = await purchase_order_service.submit_order(session, po.id, current_user_id=manager.id)
        assert re_submitted.status == "Submitted"

        # 8. Direct Approval
        approved_po = await purchase_order_service.approve_order(session, po.id, approver_id=manager.id)
        assert approved_po.status == "Approved"
        assert approved_po.approved_by == manager.id
        assert approved_po.approved_at is not None

        # 9. Immutability of Approved PO
        with pytest.raises(Exception):
            await purchase_order_service.update_order(
                session, po.id, PurchaseOrderUpdate(notes="Hacking approved PO"), current_user_id=manager.id
            )


@pytest.mark.asyncio
async def test_10_11_purchase_order_amendment_and_revision_increment():
    async with AsyncSessionLocal() as session:
        manager, _ = await get_test_procurement_users(session)
        product, wh, uom, supplier = await setup_procurement_test_data(session, manager)

        po_in = PurchaseOrderCreate(
            supplier_id=supplier.id,
            items=[
                PurchaseOrderItemCreate(
                    product_id=product.id,
                    warehouse_id=wh.id,
                    quantity=Decimal("10.0"),
                    unit_price=Decimal("50.0"),
                )
            ],
        )
        po = await purchase_order_service.create_order(session, po_in, current_user_id=manager.id)
        await purchase_order_service.submit_order(session, po.id, current_user_id=manager.id)
        approved = await purchase_order_service.approve_order(session, po.id, approver_id=manager.id)
        assert approved.status == "Approved"
        assert approved.revision_number == 1

        # 10. Amend Approved PO
        amend_in = PurchaseOrderAmend(
            amendment_reason="Supplier requested price adjustment",
            items=[
                PurchaseOrderItemCreate(
                    product_id=product.id,
                    warehouse_id=wh.id,
                    quantity=Decimal("15.0"),
                    unit_price=Decimal("60.0"),
                )
            ],
        )
        amended = await purchase_order_service.amend_order(session, po.id, amend_in, current_user_id=manager.id)
        assert amended.revision_number == 2
        assert amended.status == "Draft"
        assert amended.subtotal == Decimal("900.0")
        assert amended.total_amount == Decimal("900.0")
        assert "Supplier requested price adjustment" in (amended.notes or "")

        # Resubmit and reapprove amendment
        await purchase_order_service.submit_order(session, po.id, current_user_id=manager.id)
        reapproved = await purchase_order_service.approve_order(session, po.id, approver_id=manager.id)
        assert reapproved.status == "Approved"
        assert reapproved.revision_number == 2

        # 11. Second amendment
        amend_in_2 = PurchaseOrderAmend(amendment_reason="Quantity reduction")
        amended_2 = await purchase_order_service.amend_order(session, po.id, amend_in_2, current_user_id=manager.id)
        assert amended_2.revision_number == 3


@pytest.mark.asyncio
async def test_12_14_supplier_validation_active_inactive_blacklisted():
    async with AsyncSessionLocal() as session:
        manager, _ = await get_test_procurement_users(session)
        product, wh, uom, supplier = await setup_procurement_test_data(session, manager)

        # Blacklist supplier
        blacklisted = await supplier_service.blacklist_supplier(
            session, supplier.id, reason="Severe quality defects", current_user_id=manager.id
        )
        assert blacklisted.status == "Blacklisted"

        po_in = PurchaseOrderCreate(
            supplier_id=supplier.id,
            items=[
                PurchaseOrderItemCreate(
                    product_id=product.id,
                    warehouse_id=wh.id,
                    quantity=Decimal("10.0"),
                    unit_price=Decimal("50.0"),
                )
            ],
        )

        # 13. Blacklisted supplier rejection
        with pytest.raises(Exception):
            await purchase_order_service.create_order(session, po_in, current_user_id=manager.id)

        # Inactive supplier
        await supplier_service.deactivate_supplier(session, supplier.id, current_user_id=manager.id)
        # 14. Inactive supplier rejection
        with pytest.raises(Exception):
            await purchase_order_service.create_order(session, po_in, current_user_id=manager.id)


@pytest.mark.asyncio
async def test_15_purchase_order_cancellation_lifecycle():
    async with AsyncSessionLocal() as session:
        manager, _ = await get_test_procurement_users(session)
        product, wh, uom, supplier = await setup_procurement_test_data(session, manager)

        # Cancel Draft
        po1 = await purchase_order_service.create_order(
            session,
            PurchaseOrderCreate(
                supplier_id=supplier.id,
                items=[PurchaseOrderItemCreate(product_id=product.id, warehouse_id=wh.id, quantity=Decimal("5.0"), unit_price=Decimal("10.0"))],
            ),
            current_user_id=manager.id,
        )
        cancelled1 = await purchase_order_service.cancel_order(session, po1.id, current_user_id=manager.id)
        assert cancelled1.status == "Cancelled"

        # Cancel Approved
        po2 = await purchase_order_service.create_order(
            session,
            PurchaseOrderCreate(
                supplier_id=supplier.id,
                items=[PurchaseOrderItemCreate(product_id=product.id, warehouse_id=wh.id, quantity=Decimal("5.0"), unit_price=Decimal("10.0"))],
            ),
            current_user_id=manager.id,
        )
        await purchase_order_service.submit_order(session, po2.id, current_user_id=manager.id)
        await purchase_order_service.approve_order(session, po2.id, approver_id=manager.id)
        cancelled2 = await purchase_order_service.cancel_order(session, po2.id, current_user_id=manager.id)
        assert cancelled2.status == "Cancelled"

        # Cancelling already cancelled PO rejected
        with pytest.raises(Exception):
            await purchase_order_service.cancel_order(session, po2.id, current_user_id=manager.id)


@pytest.mark.asyncio
async def test_16_purchase_order_dispatch():
    async with AsyncSessionLocal() as session:
        manager, _ = await get_test_procurement_users(session)
        product, wh, uom, supplier = await setup_procurement_test_data(session, manager)

        po = await purchase_order_service.create_order(
            session,
            PurchaseOrderCreate(
                supplier_id=supplier.id,
                items=[PurchaseOrderItemCreate(product_id=product.id, warehouse_id=wh.id, quantity=Decimal("5.0"), unit_price=Decimal("10.0"))],
            ),
            current_user_id=manager.id,
        )

        # Dispatching non-approved rejected
        with pytest.raises(Exception):
            await purchase_order_service.dispatch_order(session, po.id, current_user_id=manager.id)

        await purchase_order_service.submit_order(session, po.id, current_user_id=manager.id)
        await purchase_order_service.approve_order(session, po.id, approver_id=manager.id)

        # Dispatch approved PO
        dispatched = await purchase_order_service.dispatch_order(session, po.id, current_user_id=manager.id)
        assert dispatched.status == "Dispatched"


@pytest.mark.asyncio
async def test_17_19_quotation_to_purchase_order_creation_and_duplicate_prevention():
    async with AsyncSessionLocal() as session:
        manager, _ = await get_test_procurement_users(session)
        product, wh, uom, supplier = await setup_procurement_test_data(session, manager)

        # Setup RFQ and Supplier Quotation
        rfq_in = RFQCreate(
            title="Q3 Heavy Machinery Sourcing",
            submission_deadline=datetime.now(timezone.utc) + timedelta(days=7),
            supplier_ids=[supplier.id],
        )
        rfq = await rfq_service.create_rfq(session, rfq_in, current_user_id=manager.id)
        await rfq_service.issue_rfq(session, rfq.id, current_user_id=manager.id)

        sq_in = SupplierQuotationCreate(
            rfq_id=rfq.id,
            supplier_id=supplier.id,
            validity_date=datetime.now(timezone.utc) + timedelta(days=14),
            lead_time_days=5,
            items=[
                SupplierQuotationItemCreate(
                    product_id=product.id,
                    quantity=Decimal("50.0"),
                    unit_price=Decimal("40.0"),
                    discount_pct=Decimal("5.0"),  # 2000 - 100 = 1900
                    tax_pct=Decimal("10.0"),       # 1900 + 190 = 2090
                )
            ],
        )
        sq = await supplier_quotation_service.create_quotation(session, sq_in, current_user_id=manager.id)
        await supplier_quotation_service.submit_quotation(session, sq.id, current_user_id=manager.id)

        # 18. Creating PO from unapproved quotation rejected
        with pytest.raises(Exception):
            await purchase_order_service.create_from_quotation(
                session,
                quotation_id=sq.id,
                obj_in=PurchaseOrderFromQuotationCreate(warehouse_id=wh.id),
                current_user_id=manager.id,
            )

        # Award quotation
        await rfq_service.award_quotation(session, rfq.id, sq.id, current_user_id=manager.id)
        reloaded_sq = await supplier_quotation_service.get_quotation(session, sq.id)
        assert reloaded_sq.status == "Approved"

        # 17. Create PO from awarded quotation
        po = await purchase_order_service.create_from_quotation(
            session,
            quotation_id=sq.id,
            obj_in=PurchaseOrderFromQuotationCreate(warehouse_id=wh.id, notes="PO generated from Awarded Sourcing Bid"),
            current_user_id=manager.id,
        )
        assert po.origin_type == "Quotation"
        assert po.origin_document_id == sq.id
        assert po.supplier_id == supplier.id
        assert po.status == "Draft"
        assert po.subtotal == Decimal("2000.0")
        assert po.discount_amount == Decimal("100.0")
        assert po.tax_amount == Decimal("190.0")
        assert po.total_amount == Decimal("2090.0")
        assert len(po.items) == 1
        assert po.items[0].warehouse_id == wh.id

        # 19. Duplicate PO prevention from same quotation
        with pytest.raises(Exception):
            await purchase_order_service.create_from_quotation(
                session,
                quotation_id=sq.id,
                obj_in=PurchaseOrderFromQuotationCreate(warehouse_id=wh.id),
                current_user_id=manager.id,
            )


@pytest.mark.asyncio
async def test_20_21_purchase_order_search_filter_and_pagination():
    async with AsyncSessionLocal() as session:
        manager, _ = await get_test_procurement_users(session)
        product, wh, uom, supplier = await setup_procurement_test_data(session, manager)

        po = await purchase_order_service.create_order(
            session,
            PurchaseOrderCreate(
                supplier_id=supplier.id,
                notes="SearchableUniqueStringX123",
                items=[PurchaseOrderItemCreate(product_id=product.id, warehouse_id=wh.id, quantity=Decimal("5.0"), unit_price=Decimal("10.0"))],
            ),
            current_user_id=manager.id,
        )

        # Filter by supplier
        items, total = await purchase_order_service.list_orders(session, supplier_id=supplier.id)
        assert total >= 1
        assert any(p.id == po.id for p in items)

        # Filter by status
        items, total = await purchase_order_service.list_orders(session, status="Draft")
        assert total >= 1

        # Search by notes
        items, total = await purchase_order_service.list_orders(session, search="SearchableUniqueStringX123")
        assert total == 1
        assert items[0].id == po.id

        # Search by PO number
        items, total = await purchase_order_service.list_orders(session, search=po.po_number)
        assert total == 1
        assert items[0].id == po.id


@pytest.mark.asyncio
async def test_22_25_safe_numbering_and_concurrency():
    async with AsyncSessionLocal() as session:
        manager, _ = await get_test_procurement_users(session)
        product, wh, uom, supplier = await setup_procurement_test_data(session, manager)

        po1 = await purchase_order_service.create_order(
            session,
            PurchaseOrderCreate(
                supplier_id=supplier.id,
                items=[PurchaseOrderItemCreate(product_id=product.id, warehouse_id=wh.id, quantity=Decimal("5.0"), unit_price=Decimal("10.0"))],
            ),
            current_user_id=manager.id,
        )
        po2 = await purchase_order_service.create_order(
            session,
            PurchaseOrderCreate(
                supplier_id=supplier.id,
                items=[PurchaseOrderItemCreate(product_id=product.id, warehouse_id=wh.id, quantity=Decimal("5.0"), unit_price=Decimal("10.0"))],
            ),
            current_user_id=manager.id,
        )

        assert po1.po_number != po2.po_number
        assert po1.po_number.startswith("PO-")
        assert po2.po_number.startswith("PO-")


@pytest.mark.asyncio
async def test_26_27_procurement_rbac_authorization():
    async with AsyncSessionLocal() as session:
        manager, viewer = await get_test_procurement_users(session)
        product, wh, uom, supplier = await setup_procurement_test_data(session, manager)

        mgr_token = create_access_token(subject=str(manager.id))
        viewer_token = create_access_token(subject=str(viewer.id))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Manager can create PO
        po_payload = {
            "supplier_id": str(supplier.id),
            "payment_terms": "Net 30",
            "items": [
                {
                    "product_id": str(product.id),
                    "warehouse_id": str(wh.id),
                    "quantity": 10.0,
                    "unit_price": 50.0,
                }
            ],
        }
        res = await client.post(
            "/api/v1/purchase-orders",
            json=po_payload,
            headers={"Authorization": f"Bearer {mgr_token}"},
        )
        assert res.status_code == 201, res.text
        po_data = res.json()
        po_id = po_data["id"]

        # 2. Viewer can read
        res = await client.get(
            f"/api/v1/purchase-orders/{po_id}",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res.status_code == 200

        # 3. Viewer cannot create / mutate
        res = await client.post(
            "/api/v1/purchase-orders",
            json=po_payload,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res.status_code == 403

        res = await client.post(
            f"/api/v1/purchase-orders/{po_id}/submit",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res.status_code == 403

        # 4. Manager can submit, approve, dispatch
        res = await client.post(
            f"/api/v1/purchase-orders/{po_id}/submit",
            headers={"Authorization": f"Bearer {mgr_token}"},
        )
        assert res.status_code == 200

        res = await client.post(
            f"/api/v1/purchase-orders/{po_id}/approve",
            headers={"Authorization": f"Bearer {mgr_token}"},
        )
        assert res.status_code == 200

        res = await client.post(
            f"/api/v1/purchase-orders/{po_id}/dispatch",
            headers={"Authorization": f"Bearer {mgr_token}"},
        )
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_28_purchase_order_audit_events():
    async with AsyncSessionLocal() as session:
        manager, _ = await get_test_procurement_users(session)
        product, wh, uom, supplier = await setup_procurement_test_data(session, manager)

        po = await purchase_order_service.create_order(
            session,
            PurchaseOrderCreate(
                supplier_id=supplier.id,
                items=[PurchaseOrderItemCreate(product_id=product.id, warehouse_id=wh.id, quantity=Decimal("5.0"), unit_price=Decimal("10.0"))],
            ),
            current_user_id=manager.id,
        )
        await purchase_order_service.update_order(
            session, po.id, PurchaseOrderUpdate(notes="Updated audit test note"), current_user_id=manager.id
        )
        await purchase_order_service.submit_order(session, po.id, current_user_id=manager.id)
        await purchase_order_service.approve_order(session, po.id, approver_id=manager.id)
        await purchase_order_service.amend_order(
            session, po.id, PurchaseOrderAmend(amendment_reason="Audit test amendment"), current_user_id=manager.id
        )
        await purchase_order_service.submit_order(session, po.id, current_user_id=manager.id)
        await purchase_order_service.approve_order(session, po.id, approver_id=manager.id)
        await purchase_order_service.dispatch_order(session, po.id, current_user_id=manager.id)
        await purchase_order_service.cancel_order(session, po.id, current_user_id=manager.id)

        stmt = select(AuditLog).where(AuditLog.entity_id == str(po.id))
        res = await session.execute(stmt)
        logs = res.scalars().all()
        actions = [log.action for log in logs]

        assert "PURCHASE_ORDER_CREATE" in actions
        assert "PURCHASE_ORDER_UPDATE" in actions
        assert "PURCHASE_ORDER_SUBMIT" in actions
        assert "PURCHASE_ORDER_APPROVE" in actions
        assert "PURCHASE_ORDER_AMEND" in actions
        assert "PURCHASE_ORDER_DISPATCH" in actions
        assert "PURCHASE_ORDER_CANCEL" in actions


@pytest.mark.asyncio
async def test_29_32_inventory_and_goods_receipt_boundary_invariants():
    async with AsyncSessionLocal() as session:
        manager, _ = await get_test_procurement_users(session)
        product, wh, uom, supplier = await setup_procurement_test_data(session, manager)

        # Baseline counts
        ledger_count_before = (await session.execute(select(func.count()).select_from(StockLedger))).scalar() or 0
        balance_count_before = (await session.execute(select(func.count()).select_from(StockBalance))).scalar() or 0
        gr_count_before = (await session.execute(select(func.count()).select_from(GoodsReceipt))).scalar() or 0

        # Create PO
        po = await purchase_order_service.create_order(
            session,
            PurchaseOrderCreate(
                supplier_id=supplier.id,
                items=[PurchaseOrderItemCreate(product_id=product.id, warehouse_id=wh.id, quantity=Decimal("100.0"), unit_price=Decimal("10.0"))],
            ),
            current_user_id=manager.id,
        )

        # Submit PO
        await purchase_order_service.submit_order(session, po.id, current_user_id=manager.id)

        # Approve PO
        await purchase_order_service.approve_order(session, po.id, approver_id=manager.id)

        # Amend PO
        await purchase_order_service.amend_order(
            session,
            po.id,
            PurchaseOrderAmend(
                amendment_reason="Testing inventory boundary",
                items=[PurchaseOrderItemCreate(product_id=product.id, warehouse_id=wh.id, quantity=Decimal("120.0"), unit_price=Decimal("10.0"))],
            ),
            current_user_id=manager.id,
        )
        await purchase_order_service.submit_order(session, po.id, current_user_id=manager.id)
        await purchase_order_service.approve_order(session, po.id, approver_id=manager.id)

        # Dispatch PO
        await purchase_order_service.dispatch_order(session, po.id, current_user_id=manager.id)

        # Cancel PO
        await purchase_order_service.cancel_order(session, po.id, current_user_id=manager.id)

        # Verify strict boundary invariance
        ledger_count_after = (await session.execute(select(func.count()).select_from(StockLedger))).scalar() or 0
        balance_count_after = (await session.execute(select(func.count()).select_from(StockBalance))).scalar() or 0
        gr_count_after = (await session.execute(select(func.count()).select_from(GoodsReceipt))).scalar() or 0

        assert ledger_count_after == ledger_count_before, "StockLedger was modified during PO lifecycle!"
        assert balance_count_after == balance_count_before, "StockBalance was modified during PO lifecycle!"
        assert gr_count_after == gr_count_before, "GoodsReceipt was created during PO lifecycle!"


@pytest.mark.asyncio
async def test_33_34_procurement_foundation_and_sourcing_compatibility():
    async with AsyncSessionLocal() as session:
        manager, _ = await get_test_procurement_users(session)
        product, wh, uom, supplier = await setup_procurement_test_data(session, manager)

        # End to End: Supplier -> RFQ -> Quotation -> Award -> PO -> Submit -> Approve -> Dispatch
        rfq = await rfq_service.create_rfq(
            session,
            RFQCreate(
                title="Full End-to-End Procurement Flow",
                submission_deadline=datetime.now(timezone.utc) + timedelta(days=7),
                supplier_ids=[supplier.id],
            ),
            current_user_id=manager.id,
        )
        await rfq_service.issue_rfq(session, rfq.id, current_user_id=manager.id)

        sq = await supplier_quotation_service.create_quotation(
            session,
            SupplierQuotationCreate(
                rfq_id=rfq.id,
                supplier_id=supplier.id,
                validity_date=datetime.now(timezone.utc) + timedelta(days=14),
                lead_time_days=3,
                items=[SupplierQuotationItemCreate(product_id=product.id, quantity=Decimal("25.0"), unit_price=Decimal("80.0"))],
            ),
            current_user_id=manager.id,
        )
        await supplier_quotation_service.submit_quotation(session, sq.id, current_user_id=manager.id)
        await rfq_service.award_quotation(session, rfq.id, sq.id, current_user_id=manager.id)

        po = await purchase_order_service.create_from_quotation(
            session,
            quotation_id=sq.id,
            obj_in=PurchaseOrderFromQuotationCreate(warehouse_id=wh.id),
            current_user_id=manager.id,
        )
        assert po.status == "Draft"

        submitted = await purchase_order_service.submit_order(session, po.id, current_user_id=manager.id)
        assert submitted.status == "Submitted"

        approved = await purchase_order_service.approve_order(session, po.id, approver_id=manager.id)
        assert approved.status == "Approved"

        dispatched = await purchase_order_service.dispatch_order(session, po.id, current_user_id=manager.id)
        assert dispatched.status == "Dispatched"
        assert dispatched.origin_type == "Quotation"
        assert dispatched.origin_document_id == sq.id
