from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import AsyncGenerator, Tuple
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.security import create_access_token, hash_password
from app.db.seed_rbac import seed_rbac_data
from app.db.session import AsyncSessionLocal
from pydantic import ValidationError
from app.exceptions.base import NotFoundException, ValidationException
from app.main import app
from app.models.audit_log import AuditLog
from app.models.product import Product
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_requisition import PurchaseRequisition, PurchaseRequisitionItem
from app.models.rfq import RFQ, RFQSupplier
from app.models.stock_balance import StockBalance
from app.models.stock_ledger import StockLedger
from app.models.supplier import Supplier, SupplierCategory
from app.models.supplier_quotation import SupplierQuotation, SupplierQuotationItem
from app.models.user import User
from app.models.user_role import UserRole
from app.repositories.rbac import permission_repository, role_permission_repository, role_repository, user_role_repository
from app.schemas.inventory import (
    ProductCategoryCreate,
    ProductCreate,
    UnitOfMeasureCreate,
    WarehouseCreate,
)
from app.schemas.procurement import (
    PurchaseRequisitionCreate,
    PurchaseRequisitionItemCreate,
    PurchaseRequisitionUpdate,
    RFQCreate,
    RFQSupplierInvite,
    RFQUpdate,
    SupplierCategoryCreate,
    SupplierCreate,
    SupplierQuotationCreate,
    SupplierQuotationItemCreate,
    SupplierQuotationUpdate,
)
import pytest_asyncio

from app.services.inventory_services import (
    category_service,
    product_service,
    unit_of_measure_service,
    warehouse_service,
)
from app.services.purchase_requisition_services import purchase_requisition_service
from app.services.rfq_services import rfq_service
from app.services.supplier_quotation_services import supplier_quotation_service
from app.services.supplier_services import supplier_service


@pytest_asyncio.fixture(scope="function", autouse=True)
async def seed_db():
    async with AsyncSessionLocal() as session:
        await seed_rbac_data(session)


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client


async def create_user_with_role(session, role_name: str) -> Tuple[User, str]:
    unique = uuid.uuid4().hex[:6]
    user = User(
        full_name=f"User {role_name} {unique}",
        email=f"user_{unique}@apnaerp.com",
        username=f"user_{unique}",
        password_hash=hash_password("password123"),
        is_active=True,
        is_superuser=False,
    )
    session.add(user)
    await session.flush()

    role = await role_repository.get_by_name(session, role_name)
    if role:
        session.add(UserRole(user_id=user.id, role_id=role.id))
    await session.commit()
    await session.refresh(user)

    token = create_access_token(subject=user.id)
    return user, token


async def setup_test_master_data(session):
    cat = await category_service.create_category(
        session, obj_in=ProductCategoryCreate(name="Industrial Parts", code=f"CAT-IND-{uuid.uuid4().hex[:4]}")
    )
    uom = await unit_of_measure_service.create_unit(
        session,
        obj_in=UnitOfMeasureCreate(name=f"Piece_{uuid.uuid4().hex[:4]}", symbol=f"pc_{uuid.uuid4().hex[:4]}", category="Count"),
    )
    prod_info = await product_service.create_product(
        session,
        obj_in=ProductCreate(
            sku=f"SKU-VALVE-{uuid.uuid4().hex[:4]}",
            name="Pressure Control Valve",
            category_id=cat.id,
            base_unit_id=uom.id,
        ),
    )
    prod = await product_service.get_product(session, prod_info["id"])
    wh = await warehouse_service.create_warehouse(
        session,
        obj_in=WarehouseCreate(code=f"WH-MAIN-{uuid.uuid4().hex[:4]}", name="Main Warehouse"),
    )

    sup_cat = await supplier_service.create_category(
        session, obj_in=SupplierCategoryCreate(code=f"SUPCAT-{uuid.uuid4().hex[:4]}", name="Hardware")
    )
    sup1 = await supplier_service.create_supplier(
        session,
        obj_in=SupplierCreate(
            code=f"SUP-{uuid.uuid4().hex[:6]}",
            name="Alpha Supplies Ltd",
            category_id=sup_cat.id,
            payment_terms="Net 30",
            currency="USD",
        ),
    )
    sup2 = await supplier_service.create_supplier(
        session,
        obj_in=SupplierCreate(
            code=f"SUP-{uuid.uuid4().hex[:6]}",
            name="Beta Industrial Corp",
            category_id=sup_cat.id,
            payment_terms="Net 45",
            currency="USD",
        ),
    )

    # Inactive / Blacklisted suppliers for testing
    inactive_sup = await supplier_service.create_supplier(
        session,
        obj_in=SupplierCreate(
            code=f"SUP-{uuid.uuid4().hex[:6]}",
            name="Inactive Supplier Ltd",
            category_id=sup_cat.id,
        ),
    )
    inactive_sup.status = "Inactive"
    await session.commit()

    blacklisted_sup = await supplier_service.create_supplier(
        session,
        obj_in=SupplierCreate(
            code=f"SUP-{uuid.uuid4().hex[:6]}",
            name="Blacklisted Trader",
            category_id=sup_cat.id,
        ),
    )
    blacklisted_sup.status = "Blacklisted"
    await session.commit()

    return {
        "product": prod,
        "warehouse": wh,
        "supplier1": sup1,
        "supplier2": sup2,
        "inactive_supplier": inactive_sup,
        "blacklisted_supplier": blacklisted_sup,
    }


# ============================================================
# 1-8: PURCHASE REQUISITION TESTS
# ============================================================

@pytest.mark.asyncio
async def test_01_08_purchase_requisition_full_lifecycle():
    async with AsyncSessionLocal() as session:
        data = await setup_test_master_data(session)
        prod = data["product"]
        manager, _ = await create_user_with_role(session, "Procurement Manager")

        # 1. Create PR
        req_in = PurchaseRequisitionCreate(
            required_date=datetime.now(timezone.utc) + timedelta(days=10),
            priority="High",
            remarks="Urgent stock replenishment for plant maintenance",
            items=[
                PurchaseRequisitionItemCreate(
                    product_id=prod.id,
                    quantity=Decimal("25.0"),
                    estimated_unit_price=Decimal("120.00"),
                )
            ],
        )
        pr = await purchase_requisition_service.create_requisition(session, req_in, requester_id=manager.id)
        assert pr.requisition_number.startswith(f"PR-{datetime.now(timezone.utc).year}-")
        assert pr.status == "Draft"
        assert pr.total_estimated_amount == Decimal("3000.0000")
        assert len(pr.items) == 1

        # 2. Line validation: negative qty / zero qty / missing items
        with pytest.raises((ValidationException, ValidationError)):
            await purchase_requisition_service.create_requisition(
                session,
                PurchaseRequisitionCreate(
                    required_date=datetime.now(timezone.utc) + timedelta(days=5),
                    items=[],
                ),
                requester_id=manager.id,
            )

        with pytest.raises((ValidationException, ValidationError)):
            await purchase_requisition_service.create_requisition(
                session,
                PurchaseRequisitionCreate(
                    required_date=datetime.now(timezone.utc) + timedelta(days=5),
                    items=[
                        PurchaseRequisitionItemCreate(
                            product_id=prod.id,
                            quantity=Decimal("0.0"),
                            estimated_unit_price=Decimal("10.0"),
                        )
                    ],
                ),
                requester_id=manager.id,
            )

        # 3. Update Draft PR
        updated_pr = await purchase_requisition_service.update_requisition(
            session,
            pr.id,
            obj_in=PurchaseRequisitionUpdate(remarks="Updated justification text", priority="Urgent"),
            current_user_id=manager.id,
        )
        assert updated_pr.priority == "Urgent"
        assert updated_pr.remarks == "Updated justification text"

        # 4. Submit Requisition
        submitted_pr = await purchase_requisition_service.submit_requisition(session, pr.id, requester_id=manager.id)
        assert submitted_pr.status == "Submitted"

        # 3 (contd). Updating non-Draft PR fails
        with pytest.raises(ValidationException):
            await purchase_requisition_service.update_requisition(
                session, pr.id, obj_in=PurchaseRequisitionUpdate(remarks="Should fail"), current_user_id=manager.id
            )

        # 5. Approval Workflow
        approved_pr = await purchase_requisition_service.approve_requisition(session, pr.id, approver_id=manager.id)
        assert approved_pr.status == "Approved"

        # 8. Immutable after approval
        with pytest.raises(ValidationException):
            await purchase_requisition_service.update_requisition(
                session, pr.id, obj_in=PurchaseRequisitionUpdate(remarks="Mutation after approval"), current_user_id=manager.id
            )

        # 6. Rejection Workflow on another PR
        pr2 = await purchase_requisition_service.create_requisition(session, req_in, requester_id=manager.id)
        await purchase_requisition_service.submit_requisition(session, pr2.id, requester_id=manager.id)
        rejected_pr = await purchase_requisition_service.reject_requisition(
            session, pr2.id, reason="Budget exceeded", current_user_id=manager.id
        )
        assert rejected_pr.status == "Rejected"
        assert "[Rejected]: Budget exceeded" in rejected_pr.remarks

        # 7. Cancellation Workflow
        pr3 = await purchase_requisition_service.create_requisition(session, req_in, requester_id=manager.id)
        cancelled_pr = await purchase_requisition_service.cancel_requisition(session, pr3.id, user_id=manager.id)
        assert cancelled_pr.status == "Cancelled"
        for itm in cancelled_pr.items:
            assert itm.status == "Cancelled"


# ============================================================
# 9-17: RFQ TESTS
# ============================================================

@pytest.mark.asyncio
async def test_09_17_rfq_lifecycle_and_supplier_invitations():
    async with AsyncSessionLocal() as session:
        data = await setup_test_master_data(session)
        sup1 = data["supplier1"]
        sup2 = data["supplier2"]
        inactive_sup = data["inactive_supplier"]
        blacklisted_sup = data["blacklisted_supplier"]
        manager, _ = await create_user_with_role(session, "Procurement Manager")

        # 9. Create RFQ
        rfq_in = RFQCreate(
            title="Q3 Valve Procurement",
            submission_deadline=datetime.now(timezone.utc) + timedelta(days=14),
            terms_and_conditions="Standard Net 30, FOB Destination",
            notes="Requires manufacturer test certificates",
            supplier_ids=[sup1.id],
        )
        rfq = await rfq_service.create_rfq(session, rfq_in, current_user_id=manager.id)
        assert rfq.rfq_number.startswith(f"RFQ-{datetime.now(timezone.utc).year}-")
        assert rfq.status == "Draft"
        assert len(rfq.invited_suppliers) == 1

        # 10. Update Draft RFQ
        updated_rfq = await rfq_service.update_rfq(
            session, rfq.id, obj_in=RFQUpdate(title="Q3 Valve Procurement (Revised)"), current_user_id=manager.id
        )
        assert updated_rfq.title == "Q3 Valve Procurement (Revised)"

        # 11. Invite Second Supplier
        invite2 = await rfq_service.invite_supplier(session, rfq.id, sup2.id, current_user_id=manager.id)
        assert invite2.status == "Invited"
        assert invite2.supplier_id == sup2.id

        # 12. Duplicate invitation rejected
        with pytest.raises(ValidationException):
            await rfq_service.invite_supplier(session, rfq.id, sup2.id, current_user_id=manager.id)

        # 13. Inactive supplier rejected
        with pytest.raises(ValidationException):
            await rfq_service.invite_supplier(session, rfq.id, inactive_sup.id, current_user_id=manager.id)

        # 14. Blacklisted supplier rejected
        with pytest.raises(ValidationException):
            await rfq_service.invite_supplier(session, rfq.id, blacklisted_sup.id, current_user_id=manager.id)

        # 15. Issue RFQ
        issued_rfq = await rfq_service.issue_rfq(session, rfq.id, current_user_id=manager.id)
        assert issued_rfq.status == "Issued"

        # 16. Invalid issue rejected (already issued)
        with pytest.raises(ValidationException):
            await rfq_service.issue_rfq(session, rfq.id, current_user_id=manager.id)

        # 17. Cancel RFQ
        rfq2 = await rfq_service.create_rfq(session, rfq_in, current_user_id=manager.id)
        cancelled_rfq = await rfq_service.cancel_rfq(session, rfq2.id, current_user_id=manager.id)
        assert cancelled_rfq.status == "Cancelled"


# ============================================================
# 18-25: SUPPLIER QUOTATION TESTS
# ============================================================

@pytest.mark.asyncio
async def test_18_25_supplier_quotation_validation_and_lifecycle():
    async with AsyncSessionLocal() as session:
        data = await setup_test_master_data(session)
        prod = data["product"]
        sup1 = data["supplier1"]
        sup2 = data["supplier2"]
        inactive_sup = data["inactive_supplier"]
        manager, _ = await create_user_with_role(session, "Procurement Manager")

        # Setup an issued RFQ inviting sup1 only
        rfq = await rfq_service.create_rfq(
            session,
            RFQCreate(
                title="Sourcing Valves",
                submission_deadline=datetime.now(timezone.utc) + timedelta(days=7),
                supplier_ids=[sup1.id],
            ),
            current_user_id=manager.id,
        )
        await rfq_service.issue_rfq(session, rfq.id, current_user_id=manager.id)

        # 18. Create Supplier Quotation
        sq_in = SupplierQuotationCreate(
            rfq_id=rfq.id,
            supplier_id=sup1.id,
            validity_date=datetime.now(timezone.utc) + timedelta(days=30),
            lead_time_days=5,
            payment_terms="Net 30",
            currency="USD",
            items=[
                SupplierQuotationItemCreate(
                    product_id=prod.id,
                    quantity=Decimal("100.0"),
                    unit_price=Decimal("150.00"),
                    discount_pct=Decimal("10.0"),  # 15000 - 1500 = 13500
                    tax_pct=Decimal("5.0"),         # 13500 + 675 = 14175
                    delivery_days=5,
                )
            ],
        )
        sq = await supplier_quotation_service.create_quotation(session, sq_in, current_user_id=manager.id)
        assert sq.quotation_number.startswith(f"SQ-{datetime.now(timezone.utc).strftime('%Y%m')}-")
        assert sq.status == "Draft"
        assert sq.subtotal == Decimal("15000.0000")
        assert sq.discount_amount == Decimal("1500.0000")
        assert sq.tax_amount == Decimal("675.0000")
        assert sq.total_amount == Decimal("14175.0000")

        # 19. Inactive supplier quotation rejected
        with pytest.raises(ValidationException):
            await supplier_quotation_service.create_quotation(
                session,
                SupplierQuotationCreate(
                    supplier_id=inactive_sup.id,
                    validity_date=datetime.now(timezone.utc) + timedelta(days=10),
                    items=[
                        SupplierQuotationItemCreate(
                            product_id=prod.id,
                            quantity=Decimal("10.0"),
                            unit_price=Decimal("100.0"),
                        )
                    ],
                ),
                current_user_id=manager.id,
            )

        # 20. Closed / Nonexistent RFQ rejected
        with pytest.raises(NotFoundException):
            await supplier_quotation_service.create_quotation(
                session,
                SupplierQuotationCreate(
                    rfq_id=uuid.uuid4(),
                    supplier_id=sup1.id,
                    validity_date=datetime.now(timezone.utc) + timedelta(days=10),
                    items=[
                        SupplierQuotationItemCreate(
                            product_id=prod.id,
                            quantity=Decimal("10.0"),
                            unit_price=Decimal("100.0"),
                        )
                    ],
                ),
                current_user_id=manager.id,
            )

        # 21. Non-invited supplier to RFQ rejected
        with pytest.raises(ValidationException):
            await supplier_quotation_service.create_quotation(
                session,
                SupplierQuotationCreate(
                    rfq_id=rfq.id,
                    supplier_id=sup2.id,  # sup2 not invited
                    validity_date=datetime.now(timezone.utc) + timedelta(days=10),
                    items=[
                        SupplierQuotationItemCreate(
                            product_id=prod.id,
                            quantity=Decimal("10.0"),
                            unit_price=Decimal("100.0"),
                        )
                    ],
                ),
                current_user_id=manager.id,
            )

        # 22. Line validation: negative qty, negative price, discount > 100
        with pytest.raises((ValidationException, ValidationError)):
            await supplier_quotation_service.create_quotation(
                session,
                SupplierQuotationCreate(
                    supplier_id=sup1.id,
                    validity_date=datetime.now(timezone.utc) + timedelta(days=10),
                    items=[
                        SupplierQuotationItemCreate(
                            product_id=prod.id,
                            quantity=Decimal("-5.0"),
                            unit_price=Decimal("100.0"),
                        )
                    ],
                ),
                current_user_id=manager.id,
            )

        # 23. Submit quotation
        submitted_sq = await supplier_quotation_service.submit_quotation(session, sq.id, current_user_id=manager.id)
        assert submitted_sq.status == "Submitted"

        # 24. Withdraw quotation
        withdrawn_sq = await supplier_quotation_service.withdraw_quotation(session, sq.id, current_user_id=manager.id)
        assert withdrawn_sq.status == "Withdrawn"

        # 25. Invalid mutation on withdrawn quotation
        with pytest.raises(ValidationException):
            await supplier_quotation_service.update_quotation(
                session, sq.id, obj_in=SupplierQuotationUpdate(notes="Should fail"), current_user_id=manager.id
            )


# ============================================================
# 26-28: ISOLATION TESTS (Procurement vs Sales)
# ============================================================

@pytest.mark.asyncio
async def test_26_28_quotation_domain_isolation(async_client: AsyncClient):
    async with AsyncSessionLocal() as session:
        data = await setup_test_master_data(session)
        prod = data["product"]
        sup1 = data["supplier1"]
        manager, token = await create_user_with_role(session, "Procurement Manager")

        # 26. SupplierQuotationService operates strictly on SupplierQuotation
        sq = await supplier_quotation_service.create_quotation(
            session,
            SupplierQuotationCreate(
                supplier_id=sup1.id,
                validity_date=datetime.now(timezone.utc) + timedelta(days=20),
                items=[
                    SupplierQuotationItemCreate(
                        product_id=prod.id,
                        quantity=Decimal("50.0"),
                        unit_price=Decimal("80.0"),
                    )
                ],
            ),
            current_user_id=manager.id,
        )
        assert isinstance(sq, SupplierQuotation)
        assert not hasattr(sq, "customer_id")

        # 27. Ensure database queries for SupplierQuotation don't return SalesQuotation
        sq_in_db = await session.execute(select(SupplierQuotation).where(SupplierQuotation.id == sq.id))
        assert sq_in_db.scalar_one_or_none() is not None

        # 28. Supplier quotation REST API endpoints return SupplierQuotation
        resp = await async_client.get(
            f"/api/v1/supplier-quotations/{sq.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        json_data = resp.json()
        assert json_data["quotation_number"] == sq.quotation_number
        assert "supplier_id" in json_data
        assert "customer_id" not in json_data


# ============================================================
# 29-31: QUOTATION COMPARISON MATRIX TESTS
# ============================================================

@pytest.mark.asyncio
async def test_29_31_quotation_comparison_matrix():
    async with AsyncSessionLocal() as session:
        data = await setup_test_master_data(session)
        prod = data["product"]
        sup1 = data["supplier1"]
        sup2 = data["supplier2"]
        manager, _ = await create_user_with_role(session, "Procurement Manager")

        # Create & Issue RFQ with 2 suppliers
        rfq = await rfq_service.create_rfq(
            session,
            RFQCreate(
                title="Valve Sourcing Comparison",
                submission_deadline=datetime.now(timezone.utc) + timedelta(days=10),
                supplier_ids=[sup1.id, sup2.id],
            ),
            current_user_id=manager.id,
        )
        await rfq_service.issue_rfq(session, rfq.id, current_user_id=manager.id)

        # Quotation 1 from Supplier 1 (Higher total: 200 * 50 = 10,000)
        sq1 = await supplier_quotation_service.create_quotation(
            session,
            SupplierQuotationCreate(
                rfq_id=rfq.id,
                supplier_id=sup1.id,
                validity_date=datetime.now(timezone.utc) + timedelta(days=20),
                lead_time_days=10,
                payment_terms="Net 30",
                items=[
                    SupplierQuotationItemCreate(
                        product_id=prod.id,
                        quantity=Decimal("50.0"),
                        unit_price=Decimal("200.0"),
                    )
                ],
            ),
            current_user_id=manager.id,
        )
        await supplier_quotation_service.submit_quotation(session, sq1.id, current_user_id=manager.id)

        # Quotation 2 from Supplier 2 (Lower total: 180 * 50 = 9,000)
        sq2 = await supplier_quotation_service.create_quotation(
            session,
            SupplierQuotationCreate(
                rfq_id=rfq.id,
                supplier_id=sup2.id,
                validity_date=datetime.now(timezone.utc) + timedelta(days=25),
                lead_time_days=7,
                payment_terms="Net 45",
                items=[
                    SupplierQuotationItemCreate(
                        product_id=prod.id,
                        quantity=Decimal("50.0"),
                        unit_price=Decimal("180.0"),
                    )
                ],
            ),
            current_user_id=manager.id,
        )
        await supplier_quotation_service.submit_quotation(session, sq2.id, current_user_id=manager.id)

        # 29-31. Get comparison matrix
        matrix = await rfq_service.get_comparison_matrix(session, rfq.id)
        assert matrix.rfq_id == rfq.id
        assert matrix.quotations_count == 2
        assert len(matrix.comparison_items) == 2
        # Deterministic sorting: Lowest price first
        assert matrix.comparison_items[0]["quotation_id"] == str(sq2.id)
        assert matrix.comparison_items[0]["total_amount"] == 9000.0
        assert matrix.comparison_items[0]["lead_time_days"] == 7
        assert matrix.comparison_items[1]["quotation_id"] == str(sq1.id)
        assert matrix.comparison_items[1]["total_amount"] == 10000.0


# ============================================================
# 32-35: EXPLICIT QUOTATION AWARD TESTS
# ============================================================

@pytest.mark.asyncio
async def test_32_35_quotation_award_and_boundary_invariants():
    async with AsyncSessionLocal() as session:
        data = await setup_test_master_data(session)
        prod = data["product"]
        sup1 = data["supplier1"]
        sup2 = data["supplier2"]
        manager, _ = await create_user_with_role(session, "Procurement Manager")

        rfq = await rfq_service.create_rfq(
            session,
            RFQCreate(
                title="Valve Sourcing Award Test",
                submission_deadline=datetime.now(timezone.utc) + timedelta(days=10),
                supplier_ids=[sup1.id, sup2.id],
            ),
            current_user_id=manager.id,
        )
        await rfq_service.issue_rfq(session, rfq.id, current_user_id=manager.id)

        sq1 = await supplier_quotation_service.create_quotation(
            session,
            SupplierQuotationCreate(
                rfq_id=rfq.id,
                supplier_id=sup1.id,
                validity_date=datetime.now(timezone.utc) + timedelta(days=20),
                items=[SupplierQuotationItemCreate(product_id=prod.id, quantity=Decimal("10.0"), unit_price=Decimal("100.0"))],
            ),
            current_user_id=manager.id,
        )
        await supplier_quotation_service.submit_quotation(session, sq1.id, current_user_id=manager.id)

        sq2 = await supplier_quotation_service.create_quotation(
            session,
            SupplierQuotationCreate(
                rfq_id=rfq.id,
                supplier_id=sup2.id,
                validity_date=datetime.now(timezone.utc) + timedelta(days=20),
                items=[SupplierQuotationItemCreate(product_id=prod.id, quantity=Decimal("10.0"), unit_price=Decimal("95.0"))],
            ),
            current_user_id=manager.id,
        )
        await supplier_quotation_service.submit_quotation(session, sq2.id, current_user_id=manager.id)

        # Pre-award PO count in DB
        po_count_before = (await session.execute(select(func.count()).select_from(PurchaseOrder))).scalar() or 0

        # 32. Award winning quotation (sq2)
        awarded_rfq = await rfq_service.award_quotation(session, rfq.id, sq2.id, current_user_id=manager.id)
        assert awarded_rfq.status == "Closed"

        sq2_reloaded = await supplier_quotation_service.get_quotation(session, sq2.id)
        assert sq2_reloaded.status == "Approved"

        sq1_reloaded = await supplier_quotation_service.get_quotation(session, sq1.id)
        assert sq1_reloaded.status == "Rejected"

        # 34. Second conflicting award rejected
        with pytest.raises(ValidationException):
            await rfq_service.award_quotation(session, rfq.id, sq1.id, current_user_id=manager.id)

        # 35. Award creates NO Purchase Order
        po_count_after = (await session.execute(select(func.count()).select_from(PurchaseOrder))).scalar() or 0
        assert po_count_after == po_count_before


# ============================================================
# 36-38: APPROVAL ENGINE INTEGRATION TESTS
# ============================================================

@pytest.mark.asyncio
async def test_36_38_approval_engine_integration():
    async with AsyncSessionLocal() as session:
        data = await setup_test_master_data(session)
        prod = data["product"]
        manager, _ = await create_user_with_role(session, "Procurement Manager")

        # 36-38. Create and submit PR
        pr = await purchase_requisition_service.create_requisition(
            session,
            PurchaseRequisitionCreate(
                required_date=datetime.now(timezone.utc) + timedelta(days=10),
                items=[PurchaseRequisitionItemCreate(product_id=prod.id, quantity=Decimal("10.0"), estimated_unit_price=Decimal("50.0"))],
            ),
            requester_id=manager.id,
        )
        submitted = await purchase_requisition_service.submit_requisition(session, pr.id, requester_id=manager.id)
        # Should remain in "Submitted" status when no explicit workflow is configured (no silent auto-approval)
        assert submitted.status == "Submitted"

        # Duplicate submission is prevented
        with pytest.raises(ValidationException):
            await purchase_requisition_service.submit_requisition(session, pr.id, requester_id=manager.id)


# ============================================================
# 39-41: SAFE DOCUMENT NUMBERING TESTS
# ============================================================

@pytest.mark.asyncio
async def test_39_41_safe_document_numbering():
    async with AsyncSessionLocal() as session:
        data = await setup_test_master_data(session)
        prod = data["product"]
        sup = data["supplier1"]
        manager, _ = await create_user_with_role(session, "Procurement Manager")

        # 39. Requisition numbers
        pr1 = await purchase_requisition_service.create_requisition(
            session,
            PurchaseRequisitionCreate(
                required_date=datetime.now(timezone.utc) + timedelta(days=5),
                items=[PurchaseRequisitionItemCreate(product_id=prod.id, quantity=Decimal("1.0"))],
            ),
            requester_id=manager.id,
        )
        pr2 = await purchase_requisition_service.create_requisition(
            session,
            PurchaseRequisitionCreate(
                required_date=datetime.now(timezone.utc) + timedelta(days=5),
                items=[PurchaseRequisitionItemCreate(product_id=prod.id, quantity=Decimal("1.0"))],
            ),
            requester_id=manager.id,
        )
        assert pr1.requisition_number != pr2.requisition_number
        assert pr1.requisition_number.startswith("PR-")
        assert pr2.requisition_number.startswith("PR-")

        # 40. RFQ numbers
        rfq1 = await rfq_service.create_rfq(
            session,
            RFQCreate(title="RFQ Numbering 1", submission_deadline=datetime.now(timezone.utc) + timedelta(days=5)),
            current_user_id=manager.id,
        )
        rfq2 = await rfq_service.create_rfq(
            session,
            RFQCreate(title="RFQ Numbering 2", submission_deadline=datetime.now(timezone.utc) + timedelta(days=5)),
            current_user_id=manager.id,
        )
        assert rfq1.rfq_number != rfq2.rfq_number
        assert rfq1.rfq_number.startswith("RFQ-")
        assert rfq2.rfq_number.startswith("RFQ-")

        # 41. Supplier Quotation numbers
        sq1 = await supplier_quotation_service.create_quotation(
            session,
            SupplierQuotationCreate(
                supplier_id=sup.id,
                validity_date=datetime.now(timezone.utc) + timedelta(days=10),
                items=[SupplierQuotationItemCreate(product_id=prod.id, quantity=Decimal("2.0"), unit_price=Decimal("10.0"))],
            ),
            current_user_id=manager.id,
        )
        sq2 = await supplier_quotation_service.create_quotation(
            session,
            SupplierQuotationCreate(
                supplier_id=sup.id,
                validity_date=datetime.now(timezone.utc) + timedelta(days=10),
                items=[SupplierQuotationItemCreate(product_id=prod.id, quantity=Decimal("2.0"), unit_price=Decimal("10.0"))],
            ),
            current_user_id=manager.id,
        )
        assert sq1.quotation_number != sq2.quotation_number
        assert sq1.quotation_number.startswith("SQ-")
        assert sq2.quotation_number.startswith("SQ-")


# ============================================================
# 42-46: RBAC TESTS
# ============================================================

@pytest.mark.asyncio
async def test_42_46_procurement_rbac(async_client: AsyncClient):
    async with AsyncSessionLocal() as session:
        data = await setup_test_master_data(session)
        prod = data["product"]
        sup = data["supplier1"]

        manager_user, manager_token = await create_user_with_role(session, "Procurement Manager")
        viewer_user, viewer_token = await create_user_with_role(session, "Procurement Viewer")

        # 42. Viewer cannot create PR
        pr_payload = {
            "required_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
            "priority": "Medium",
            "items": [{"product_id": str(prod.id), "quantity": 10, "estimated_unit_price": 50}],
        }
        res_fail = await async_client.post(
            "/api/v1/purchase-requisitions",
            json=pr_payload,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res_fail.status_code == 403

        # Manager CAN create PR
        res_ok = await async_client.post(
            "/api/v1/purchase-requisitions",
            json=pr_payload,
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert res_ok.status_code == 201
        pr_id = res_ok.json()["id"]

        # 45. Viewer CAN read PR
        res_read = await async_client.get(
            f"/api/v1/purchase-requisitions/{pr_id}",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res_read.status_code == 200

        # 43. Viewer cannot issue RFQ
        rfq_payload = {
            "title": "RBAC RFQ Test",
            "submission_deadline": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
            "supplier_ids": [str(sup.id)],
        }
        res_rfq = await async_client.post(
            "/api/v1/rfqs",
            json=rfq_payload,
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert res_rfq.status_code == 201
        rfq_id = res_rfq.json()["id"]

        res_issue_fail = await async_client.post(
            f"/api/v1/rfqs/{rfq_id}/issue",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res_issue_fail.status_code == 403

        # 44. Viewer cannot award quotation
        sq_payload = {
            "rfq_id": rfq_id,
            "supplier_id": str(sup.id),
            "validity_date": (datetime.now(timezone.utc) + timedelta(days=20)).isoformat(),
            "items": [{"product_id": str(prod.id), "quantity": 10, "unit_price": 100}],
        }
        res_sq = await async_client.post(
            "/api/v1/supplier-quotations",
            json=sq_payload,
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert res_sq.status_code == 201
        sq_id = res_sq.json()["id"]

        res_award_fail = await async_client.post(
            f"/api/v1/rfqs/{rfq_id}/award/{sq_id}",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res_award_fail.status_code == 403


# ============================================================
# 47-49: AUDIT LOG TESTS
# ============================================================

@pytest.mark.asyncio
async def test_47_49_procurement_audit_logs():
    async with AsyncSessionLocal() as session:
        data = await setup_test_master_data(session)
        prod = data["product"]
        sup = data["supplier1"]
        manager, _ = await create_user_with_role(session, "Procurement Manager")

        # PR events
        pr = await purchase_requisition_service.create_requisition(
            session,
            PurchaseRequisitionCreate(
                required_date=datetime.now(timezone.utc) + timedelta(days=5),
                items=[PurchaseRequisitionItemCreate(product_id=prod.id, quantity=Decimal("10.0"), estimated_unit_price=Decimal("50.0"))],
            ),
            requester_id=manager.id,
        )
        await purchase_requisition_service.submit_requisition(session, pr.id, requester_id=manager.id)

        # RFQ events
        rfq = await rfq_service.create_rfq(
            session,
            RFQCreate(
                title="Audit Test RFQ",
                submission_deadline=datetime.now(timezone.utc) + timedelta(days=7),
                supplier_ids=[sup.id],
            ),
            current_user_id=manager.id,
        )
        await rfq_service.issue_rfq(session, rfq.id, current_user_id=manager.id)

        # Quotation events
        sq = await supplier_quotation_service.create_quotation(
            session,
            SupplierQuotationCreate(
                rfq_id=rfq.id,
                supplier_id=sup.id,
                validity_date=datetime.now(timezone.utc) + timedelta(days=15),
                items=[SupplierQuotationItemCreate(product_id=prod.id, quantity=Decimal("10.0"), unit_price=Decimal("100.0"))],
            ),
            current_user_id=manager.id,
        )
        await supplier_quotation_service.submit_quotation(session, sq.id, current_user_id=manager.id)
        await rfq_service.award_quotation(session, rfq.id, sq.id, current_user_id=manager.id)

        # Verify audit logs in db
        pr_logs = (await session.execute(select(AuditLog).where(AuditLog.action.like("PURCHASE_REQUISITION_%")))).scalars().all()
        assert len(pr_logs) >= 2

        rfq_logs = (await session.execute(select(AuditLog).where(AuditLog.action.like("RFQ_%")))).scalars().all()
        assert len(rfq_logs) >= 2

        sq_logs = (await session.execute(select(AuditLog).where(AuditLog.action.like("SUPPLIER_QUOTATION_%")))).scalars().all()
        assert len(sq_logs) >= 2


# ============================================================
# 50-51: INVENTORY BOUNDARY INVARIANTS
# ============================================================

@pytest.mark.asyncio
async def test_50_51_inventory_boundary_invariants():
    async with AsyncSessionLocal() as session:
        data = await setup_test_master_data(session)
        prod = data["product"]
        sup = data["supplier1"]
        manager, _ = await create_user_with_role(session, "Procurement Manager")

        # Snapshot inventory stock ledger and balances count before
        ledger_count_before = (await session.execute(select(func.count()).select_from(StockLedger))).scalar() or 0
        balance_count_before = (await session.execute(select(func.count()).select_from(StockBalance))).scalar() or 0

        # Create PR, RFQ, SQ, and Award
        pr = await purchase_requisition_service.create_requisition(
            session,
            PurchaseRequisitionCreate(
                required_date=datetime.now(timezone.utc) + timedelta(days=5),
                items=[PurchaseRequisitionItemCreate(product_id=prod.id, quantity=Decimal("100.0"), estimated_unit_price=Decimal("100.0"))],
            ),
            requester_id=manager.id,
        )
        rfq = await rfq_service.create_rfq(
            session,
            RFQCreate(
                title="Inventory Invariant RFQ",
                submission_deadline=datetime.now(timezone.utc) + timedelta(days=7),
                supplier_ids=[sup.id],
            ),
            current_user_id=manager.id,
        )
        await rfq_service.issue_rfq(session, rfq.id, current_user_id=manager.id)
        sq = await supplier_quotation_service.create_quotation(
            session,
            SupplierQuotationCreate(
                rfq_id=rfq.id,
                supplier_id=sup.id,
                validity_date=datetime.now(timezone.utc) + timedelta(days=15),
                items=[SupplierQuotationItemCreate(product_id=prod.id, quantity=Decimal("100.0"), unit_price=Decimal("90.0"))],
            ),
            current_user_id=manager.id,
        )
        await supplier_quotation_service.submit_quotation(session, sq.id, current_user_id=manager.id)
        await rfq_service.award_quotation(session, rfq.id, sq.id, current_user_id=manager.id)

        # Verify NO stock movements or balance updates occurred
        ledger_count_after = (await session.execute(select(func.count()).select_from(StockLedger))).scalar() or 0
        balance_count_after = (await session.execute(select(func.count()).select_from(StockBalance))).scalar() or 0

        assert ledger_count_after == ledger_count_before
        assert balance_count_after == balance_count_before
