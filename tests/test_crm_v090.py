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
from app.models.crm import Activity, Lead, LeadNote, Opportunity, OpportunityStage
from app.models.customer import Customer
from app.models.sales_order import SalesOrder
from app.models.sales_quotation import SalesQuotation
from app.models.stock_balance import StockBalance
from app.models.stock_ledger import StockLedger
from app.models.user import User
from app.models.user_role import UserRole
from app.repositories.rbac import role_repository
from app.schemas.crm import (
    ActivityCreate,
    ActivityUpdate,
    LeadConversionRequest,
    LeadCreate,
    LeadNoteCreate,
    LeadUpdate,
    OpportunityCreate,
    OpportunityStageChangeRequest,
    OpportunityUpdate,
    OpportunityWinLossRequest,
)
from app.schemas.sales import CustomerCreate
from app.repositories.sales_repos import customer_repository
from app.services.crm_services import (
    activity_service,
    lead_conversion_service,
    lead_service,
    opportunity_service,
)
from app.services.customer_services import customer_service


async def get_test_crm_users(session):
    unique = uuid.uuid4().hex[:6]
    mgr_user = User(
        full_name="CRM Manager User",
        email=f"crm_mgr_{unique}@example.com",
        username=f"crm_mgr_{unique}",
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
        full_name="CRM Viewer User",
        email=f"crm_view_{unique}@example.com",
        username=f"crm_view_{unique}",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    session.add_all([mgr_user, rep_user, viewer_user])
    await session.flush()

    mgr_role = await role_repository.get_by_name(session, "CRM Manager")
    rep_role = await role_repository.get_by_name(session, "Sales Representative")
    viewer_role = await role_repository.get_by_name(session, "CRM Viewer")
    if not viewer_role:
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


@pytest.mark.asyncio
async def test_lead_crud_and_sequential_numbering():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]
        lead_in = LeadCreate(
            first_name="Jane",
            last_name="Doe",
            company=f"Acme Corp {unique}",
            email=f"jane_{unique}@acme.com",
            phone=f"+1-555-{unique[:4]}",
            estimated_value=Decimal("25000.00"),
            notes="Initial interest in enterprise solution",
        )
        lead = await lead_service.create_lead(session, lead_in)
        assert lead.id is not None
        assert lead.lead_code.startswith("LEAD-")
        assert lead.status == "NEW"
        assert lead.score > 0
        initial_score = lead.score
        assert len(lead.notes) == 1
        assert lead.notes[0].content == "Initial interest in enterprise solution"

        # Read
        fetched = await lead_service.lead_repo.get_by_id(session, lead.id)
        assert fetched is not None
        assert fetched.company == f"Acme Corp {unique}"

        # Update
        update_in = LeadUpdate(
            title="VP of Technology",
            estimated_value=Decimal("60000.00"),
        )
        updated = await lead_service.update_lead(session, lead.id, update_in)
        assert updated.title == "VP of Technology"
        assert updated.estimated_value == Decimal("60000.00")
        assert updated.score > initial_score  # value bonus


@pytest.mark.asyncio
async def test_lead_lifecycle_valid_transitions():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]
        lead = await lead_service.create_lead(
            session,
            LeadCreate(
                first_name="Bob",
                last_name="Smith",
                company=f"Beta LLC {unique}",
                email=f"bob_{unique}@beta.com",
            ),
        )
        assert lead.status == "NEW"

        # NEW -> CONTACTED
        lead = await lead_service.update_lead(session, lead.id, LeadUpdate(status="CONTACTED"))
        assert lead.status == "CONTACTED"

        # CONTACTED -> QUALIFIED
        lead = await lead_service.update_lead(session, lead.id, LeadUpdate(status="QUALIFIED"))
        assert lead.status == "QUALIFIED"


@pytest.mark.asyncio
async def test_lead_lifecycle_invalid_transition_new_to_qualified():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]
        lead = await lead_service.create_lead(
            session,
            LeadCreate(
                first_name="Invalid",
                company=f"Jump Corp {unique}",
            ),
        )
        assert lead.status == "NEW"

        with pytest.raises(ValidationException) as exc_info:
            await lead_service.update_lead(session, lead.id, LeadUpdate(status="QUALIFIED"))
        assert "Invalid lead status transition" in str(exc_info.value)


@pytest.mark.asyncio
async def test_lead_lifecycle_invalid_transition_new_to_converted():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]
        lead = await lead_service.create_lead(
            session,
            LeadCreate(
                first_name="Direct",
                company=f"Direct Corp {unique}",
            ),
        )
        with pytest.raises(ValidationException) as exc_info:
            await lead_service.update_lead(session, lead.id, LeadUpdate(status="CONVERTED"))
        assert "Invalid lead status transition" in str(exc_info.value)


@pytest.mark.asyncio
async def test_lead_lifecycle_transition_to_lost():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]
        lead = await lead_service.create_lead(
            session,
            LeadCreate(first_name="LostLead", company=f"Lost Inc {unique}"),
        )
        # NEW -> LOST
        lead = await lead_service.update_lead(session, lead.id, LeadUpdate(status="LOST"))
        assert lead.status == "LOST"


@pytest.mark.asyncio
async def test_lead_terminal_state_rejection_converted():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]
        lead = await lead_service.create_lead(
            session,
            LeadCreate(first_name="ConvertMe", company=f"Conv Inc {unique}", email=f"conv_{unique}@test.com"),
        )
        # Advance to QUALIFIED
        lead = await lead_service.update_lead(session, lead.id, LeadUpdate(status="CONTACTED"))
        lead = await lead_service.update_lead(session, lead.id, LeadUpdate(status="QUALIFIED"))

        # Convert
        conv_resp = await lead_conversion_service.convert_lead(
            session, LeadConversionRequest(lead_id=lead.id)
        )
        assert conv_resp.lead_id == lead.id

        # Attempt to modify converted lead
        with pytest.raises(ValidationException) as exc_info:
            await lead_service.update_lead(session, lead.id, LeadUpdate(first_name="Modified"))
        assert "terminal" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_lead_terminal_state_rejection_lost():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]
        lead = await lead_service.create_lead(
            session,
            LeadCreate(first_name="LostLead", company=f"Lost Inc {unique}"),
        )
        lead = await lead_service.update_lead(session, lead.id, LeadUpdate(status="LOST"))

        # Attempt to modify or convert lost lead
        with pytest.raises(ValidationException):
            await lead_service.update_lead(session, lead.id, LeadUpdate(first_name="New Name"))

        with pytest.raises(ValidationException) as exc_conv:
            await lead_conversion_service.convert_lead(session, LeadConversionRequest(lead_id=lead.id))
        assert "QUALIFIED" in str(exc_conv.value)


@pytest.mark.asyncio
async def test_lead_duplicate_detection():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]
        email = f"dup_{unique}@example.com"
        phone = f"+91-98765{unique[:4]}"

        await lead_service.create_lead(
            session, LeadCreate(first_name="First", company="Corp 1", email=email, phone=phone)
        )

        dups = await lead_service.lead_repo.find_duplicates(session, email=email, phone=phone)
        assert len(dups) >= 1
        assert dups[0].email == email


@pytest.mark.asyncio
async def test_lead_assignment():
    async with AsyncSessionLocal() as session:
        mgr, rep, _ = await get_test_crm_users(session)
        lead = await lead_service.create_lead(
            session, LeadCreate(first_name="Assignee", company="Target Corp")
        )
        assigned = await lead_service.assign_lead(session, lead.id, assigned_to_id=rep.id, current_user_id=mgr.id)
        assert assigned.assigned_to_id == rep.id


@pytest.mark.asyncio
async def test_lead_notes_creation():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_crm_users(session)
        lead = await lead_service.create_lead(
            session, LeadCreate(first_name="NotesTarget", company="Notes Corp")
        )
        note = await lead_service.add_note(
            session,
            lead.id,
            LeadNoteCreate(content="Discussed pricing model during call", is_pinned=True),
            author_id=mgr.id,
        )
        assert note.id is not None
        assert note.content == "Discussed pricing model during call"
        assert note.is_pinned is True


@pytest.mark.asyncio
async def test_lead_soft_delete():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_crm_users(session)
        lead = await lead_service.create_lead(
            session, LeadCreate(first_name="DeleteMe", company="Delete Corp")
        )
        success = await lead_service.delete_lead(session, lead.id, current_user_id=mgr.id)
        assert success is True

        # Ensure deleted lead not returned in normal get
        fetched = await lead_service.lead_repo.get_by_id(session, lead.id)
        assert fetched is None


@pytest.mark.asyncio
async def test_lead_conversion_unqualified_rejected():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]
        lead = await lead_service.create_lead(
            session,
            LeadCreate(first_name="Unqualified", company=f"Unqual Corp {unique}"),
        )
        assert lead.status == "NEW"

        with pytest.raises(ValidationException) as exc_info:
            await lead_conversion_service.convert_lead(
                session, LeadConversionRequest(lead_id=lead.id)
            )
        assert "QUALIFIED" in str(exc_info.value)


@pytest.mark.asyncio
async def test_lead_conversion_atomic_new_customer_creation():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_crm_users(session)
        unique = uuid.uuid4().hex[:6]
        lead = await lead_service.create_lead(
            session,
            LeadCreate(
                first_name="Alice",
                last_name="Wonder",
                company=f"Wonderland Tech {unique}",
                email=f"alice_{unique}@wonderland.io",
                phone=f"+1-415-{unique[:4]}",
                estimated_value=Decimal("75000.00"),
            ),
        )
        # Advance to QUALIFIED
        await lead_service.update_lead(session, lead.id, LeadUpdate(status="CONTACTED"))
        await lead_service.update_lead(session, lead.id, LeadUpdate(status="QUALIFIED"))

        # Convert
        conv_resp = await lead_conversion_service.convert_lead(
            session,
            LeadConversionRequest(
                lead_id=lead.id,
                opportunity_title=f"Wonderland Cloud Migration {unique}",
                create_opportunity=True,
            ),
            current_user_id=mgr.id,
        )

        assert conv_resp.lead_id == lead.id
        assert conv_resp.is_existing_customer is False
        assert conv_resp.customer_id is not None
        assert conv_resp.opportunity_id is not None

        # Verify created customer
        cust = await customer_repository.get_by_id(session, conv_resp.customer_id)
        assert cust is not None
        assert cust.name == f"Wonderland Tech {unique}"
        assert cust.email == f"alice_{unique}@wonderland.io"
        assert cust.customer_code.startswith("CUST-")
        assert len(cust.contacts) >= 1

        # Verify created opportunity
        opp = await opportunity_service.opp_repo.get_by_id(session, conv_resp.opportunity_id)
        assert opp is not None
        assert opp.title == f"Wonderland Cloud Migration {unique}"
        assert opp.customer_id == cust.id
        assert opp.lead_id == lead.id
        assert opp.expected_revenue == Decimal("75000.00")

        # Verify lead state
        lead_refreshed = await lead_service.lead_repo.get_by_id(session, lead.id)
        assert lead_refreshed.is_converted is True
        assert lead_refreshed.status == "CONVERTED"
        assert lead_refreshed.converted_customer_id == cust.id
        assert lead_refreshed.converted_opportunity_id == opp.id


@pytest.mark.asyncio
async def test_lead_conversion_existing_customer_reuse_by_email():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_crm_users(session)
        unique = uuid.uuid4().hex[:6]
        shared_email = f"shared_{unique}@enterprise.com"

        # Pre-create customer
        existing_cust = await customer_service.create_customer(
            session,
            CustomerCreate(
                customer_code=f"CUST-TEST-{unique}",
                name=f"Existing Enterprise {unique}",
                email=shared_email,
            ),
            current_user_id=mgr.id,
        )

        # Create lead with same email
        lead = await lead_service.create_lead(
            session,
            LeadCreate(
                first_name="David",
                company=f"Enterprise Sub {unique}",
                email=shared_email,
            ),
        )
        await lead_service.update_lead(session, lead.id, LeadUpdate(status="CONTACTED"))
        await lead_service.update_lead(session, lead.id, LeadUpdate(status="QUALIFIED"))

        # Convert
        conv_resp = await lead_conversion_service.convert_lead(
            session,
            LeadConversionRequest(lead_id=lead.id, create_opportunity=False),
            current_user_id=mgr.id,
        )

        assert conv_resp.is_existing_customer is True
        assert conv_resp.customer_id == existing_cust.id
        assert conv_resp.opportunity_id is None


@pytest.mark.asyncio
async def test_lead_conversion_existing_customer_reuse_by_phone():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_crm_users(session)
        unique = uuid.uuid4().hex[:6]
        shared_phone = f"+91-99887{unique[:4]}"

        existing_cust = await customer_service.create_customer(
            session,
            CustomerCreate(
                customer_code=f"CUST-PH-{unique}",
                name=f"Phone Match Corp {unique}",
                phone=shared_phone,
            ),
            current_user_id=mgr.id,
        )

        lead = await lead_service.create_lead(
            session,
            LeadCreate(
                first_name="PhoneContact",
                company=f"Phone Match Corp {unique}",
                phone=shared_phone,
            ),
        )
        await lead_service.update_lead(session, lead.id, LeadUpdate(status="CONTACTED"))
        await lead_service.update_lead(session, lead.id, LeadUpdate(status="QUALIFIED"))

        conv_resp = await lead_conversion_service.convert_lead(
            session,
            LeadConversionRequest(lead_id=lead.id),
            current_user_id=mgr.id,
        )

        assert conv_resp.is_existing_customer is True
        assert conv_resp.customer_id == existing_cust.id


@pytest.mark.asyncio
async def test_lead_conversion_explicit_customer_id():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_crm_users(session)
        unique = uuid.uuid4().hex[:6]

        target_cust = await customer_service.create_customer(
            session,
            CustomerCreate(
                customer_code=f"CUST-EXP-{unique}",
                name=f"Explicit Target {unique}",
            ),
            current_user_id=mgr.id,
        )

        lead = await lead_service.create_lead(
            session,
            LeadCreate(first_name="Explicit", company="Unrelated Name"),
        )
        await lead_service.update_lead(session, lead.id, LeadUpdate(status="CONTACTED"))
        await lead_service.update_lead(session, lead.id, LeadUpdate(status="QUALIFIED"))

        conv_resp = await lead_conversion_service.convert_lead(
            session,
            LeadConversionRequest(
                lead_id=lead.id,
                existing_customer_id=target_cust.id,
            ),
            current_user_id=mgr.id,
        )

        assert conv_resp.is_existing_customer is True
        assert conv_resp.customer_id == target_cust.id


@pytest.mark.asyncio
async def test_lead_conversion_duplicate_attempt_rejected():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]
        lead = await lead_service.create_lead(
            session, LeadCreate(first_name="DoubleConv", company=f"Double {unique}")
        )
        await lead_service.update_lead(session, lead.id, LeadUpdate(status="CONTACTED"))
        await lead_service.update_lead(session, lead.id, LeadUpdate(status="QUALIFIED"))

        await lead_conversion_service.convert_lead(session, LeadConversionRequest(lead_id=lead.id))

        with pytest.raises(ValidationException) as exc_info:
            await lead_conversion_service.convert_lead(session, LeadConversionRequest(lead_id=lead.id))
        assert "already been converted" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_opportunity_crud_and_sequential_numbering():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]
        opp_in = OpportunityCreate(
            title=f"ERP Implementation Deal {unique}",
            expected_revenue=Decimal("120000.00"),
            expected_closing_date=datetime.now(timezone.utc) + timedelta(days=60),
            competitors="SAP, Oracle",
            products_of_interest="Full ApnaERP Suite",
        )
        opp = await opportunity_service.create_opportunity(session, opp_in)
        assert opp.id is not None
        assert opp.opportunity_code.startswith("OPP-")
        assert opp.status == "Open"
        assert opp.expected_revenue == Decimal("120000.00")
        assert opp.probability == Decimal("10.00")  # Prospecting default

        # Update
        updated = await opportunity_service.update_opportunity(
            session,
            opp.id,
            OpportunityUpdate(expected_revenue=Decimal("150000.00")),
        )
        assert updated.expected_revenue == Decimal("150000.00")


@pytest.mark.asyncio
async def test_opportunity_pipeline_progression():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]
        opp = await opportunity_service.create_opportunity(
            session,
            OpportunityCreate(
                title=f"Pipeline Test Deal {unique}",
                expected_revenue=Decimal("50000.00"),
            ),
        )
        assert opp.probability == Decimal("10.00")

        # Stage 1 -> Qualification
        opp = await opportunity_service.change_stage(
            session, opp.id, OpportunityStageChangeRequest(stage_code="QUALIFICATION")
        )
        assert opp.probability == Decimal("30.00")

        # Stage 2 -> Proposal
        opp = await opportunity_service.change_stage(
            session, opp.id, OpportunityStageChangeRequest(stage_code="PROPOSAL")
        )
        assert opp.probability == Decimal("60.00")

        # Stage 3 -> Negotiation
        opp = await opportunity_service.change_stage(
            session, opp.id, OpportunityStageChangeRequest(stage_code="NEGOTIATION")
        )
        assert opp.probability == Decimal("80.00")

        # Stage 4 -> Won
        opp = await opportunity_service.change_stage(
            session, opp.id, OpportunityStageChangeRequest(stage_code="WON")
        )
        assert opp.probability == Decimal("100.00")
        assert opp.status == "Won"


@pytest.mark.asyncio
async def test_opportunity_win_loss_recording():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]
        # Win deal
        opp_win = await opportunity_service.create_opportunity(
            session, OpportunityCreate(title=f"Win Deal {unique}")
        )
        won = await opportunity_service.record_win_loss(
            session, opp_win.id, status="Won", reason="Superior features and responsive support"
        )
        assert won.status == "Won"
        assert won.probability == Decimal("100.00")
        assert won.won_reason == "Superior features and responsive support"

        # Lost deal
        opp_lost = await opportunity_service.create_opportunity(
            session, OpportunityCreate(title=f"Lost Deal {unique}")
        )
        lost = await opportunity_service.record_win_loss(
            session, opp_lost.id, status="Lost", reason="Budget freeze"
        )
        assert lost.status == "Lost"
        assert lost.probability == Decimal("0.00")
        assert lost.lost_reason == "Budget freeze"


@pytest.mark.asyncio
async def test_opportunity_terminal_state_modification_rejected():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]
        opp = await opportunity_service.create_opportunity(
            session, OpportunityCreate(title=f"Closed Deal {unique}")
        )
        await opportunity_service.record_win_loss(session, opp.id, status="Won", reason="Closed")

        with pytest.raises(ValidationException) as exc_info:
            await opportunity_service.change_stage(
                session, opp.id, OpportunityStageChangeRequest(stage_code="PROPOSAL")
            )
        assert "terminal" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_opportunity_soft_delete():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_crm_users(session)
        opp = await opportunity_service.create_opportunity(
            session, OpportunityCreate(title="Delete Opp")
        )
        success = await opportunity_service.delete_opportunity(session, opp.id, current_user_id=mgr.id)
        assert success is True

        fetched = await opportunity_service.opp_repo.get_by_id(session, opp.id)
        assert fetched is None


@pytest.mark.asyncio
async def test_activity_create_and_entity_linking():
    async with AsyncSessionLocal() as session:
        mgr, rep, _ = await get_test_crm_users(session)
        unique = uuid.uuid4().hex[:6]

        lead = await lead_service.create_lead(session, LeadCreate(first_name="ActLead", company="Act Corp"))
        opp = await opportunity_service.create_opportunity(session, OpportunityCreate(title="Act Opp"))

        act_in = ActivityCreate(
            activity_type="Call",
            subject=f"Follow-up discovery call {unique}",
            description="Discussed infrastructure specifications",
            status="Pending",
            due_date=datetime.now(timezone.utc) + timedelta(days=2),
            lead_id=lead.id,
            opportunity_id=opp.id,
            owner_id=rep.id,
        )
        act = await activity_service.create_activity(session, act_in, current_user_id=mgr.id)
        assert act.id is not None
        assert act.activity_type == "Call"
        assert act.status == "Pending"
        assert act.lead_id == lead.id
        assert act.opportunity_id == opp.id


@pytest.mark.asyncio
async def test_activity_search_and_filter():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]
        act = await activity_service.create_activity(
            session,
            ActivityCreate(
                activity_type="Meeting",
                subject=f"Executive Briefing {unique}",
                status="Pending",
            ),
        )
        acts, total = await activity_service.act_repo.search_activities(
            session, query=unique, activity_type="Meeting"
        )
        assert total >= 1
        assert acts[0].id == act.id


@pytest.mark.asyncio
async def test_activity_update_and_complete():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_crm_users(session)
        act = await activity_service.create_activity(
            session,
            ActivityCreate(
                activity_type="Email",
                subject="Send product brochure",
                status="Pending",
            ),
        )

        # Update
        updated = await activity_service.update_activity(
            session, act.id, ActivityUpdate(description="Brochure v2.1 sent via secure email")
        )
        assert updated.description == "Brochure v2.1 sent via secure email"

        # Complete
        completed = await activity_service.complete_activity(session, act.id, current_user_id=mgr.id)
        assert completed.status == "Completed"
        assert completed.completed_at is not None


@pytest.mark.asyncio
async def test_activity_delete():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_crm_users(session)
        act = await activity_service.create_activity(
            session, ActivityCreate(activity_type="Note", subject="Temporary note")
        )
        success = await activity_service.delete_activity(session, act.id, current_user_id=mgr.id)
        assert success is True

        fetched = await activity_service.act_repo.get_by_id(session, act.id)
        assert fetched is None


@pytest.mark.asyncio
async def test_rbac_crm_manager_access():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_crm_users(session)
        token = create_access_token(str(mgr.id))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {token}"}
        unique = uuid.uuid4().hex[:6]

        # Create Lead
        resp = await ac.post(
            "/api/v1/crm/leads",
            json={
                "first_name": "ManagerLead",
                "company": f"Manager Corp {unique}",
                "email": f"mgr_{unique}@test.com",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        lead_id = resp.json()["id"]

        # Advance to QUALIFIED
        await ac.put(f"/api/v1/crm/leads/{lead_id}", json={"status": "CONTACTED"}, headers=headers)
        await ac.put(f"/api/v1/crm/leads/{lead_id}", json={"status": "QUALIFIED"}, headers=headers)

        # Convert
        conv_resp = await ac.post(
            f"/api/v1/crm/leads/{lead_id}/convert",
            json={"create_opportunity": True},
            headers=headers,
        )
        assert conv_resp.status_code == 200
        assert conv_resp.json()["is_existing_customer"] is False


@pytest.mark.asyncio
async def test_rbac_sales_rep_access():
    async with AsyncSessionLocal() as session:
        _, rep, _ = await get_test_crm_users(session)
        token = create_access_token(str(rep.id))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {token}"}
        unique = uuid.uuid4().hex[:6]

        # Create Opportunity
        resp = await ac.post(
            "/api/v1/crm/opportunities",
            json={
                "title": f"Rep Opportunity {unique}",
                "expected_revenue": 45000,
            },
            headers=headers,
        )
        assert resp.status_code == 201

        # Create Activity
        act_resp = await ac.post(
            "/api/v1/crm/activities",
            json={
                "activity_type": "Call",
                "subject": f"Rep Call {unique}",
            },
            headers=headers,
        )
        assert act_resp.status_code == 201


@pytest.mark.asyncio
async def test_rbac_viewer_read_only():
    async with AsyncSessionLocal() as session:
        _, _, viewer = await get_test_crm_users(session)
        token = create_access_token(str(viewer.id))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {token}"}

        # List Leads -> OK 200
        list_resp = await ac.get("/api/v1/crm/leads", headers=headers)
        assert list_resp.status_code == 200

        # Create Lead -> Forbidden 403
        create_resp = await ac.post(
            "/api/v1/crm/leads",
            json={"first_name": "Illegal", "company": "NoAccess"},
            headers=headers,
        )
        assert create_resp.status_code == 403

        # Create Opportunity -> Forbidden 403
        opp_resp = await ac.post(
            "/api/v1/crm/opportunities",
            json={"title": "Illegal Opp"},
            headers=headers,
        )
        assert opp_resp.status_code == 403


@pytest.mark.asyncio
async def test_rbac_unauthenticated_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/crm/leads")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_audit_log_crm_operations():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_crm_users(session)
        unique = uuid.uuid4().hex[:6]

        lead = await lead_service.create_lead(
            session,
            LeadCreate(first_name="AuditLead", company=f"Audit Corp {unique}"),
            current_user_id=mgr.id,
        )
        await lead_service.update_lead(session, lead.id, LeadUpdate(status="CONTACTED"), current_user_id=mgr.id)
        await lead_service.update_lead(session, lead.id, LeadUpdate(status="QUALIFIED"), current_user_id=mgr.id)
        await lead_conversion_service.convert_lead(
            session, LeadConversionRequest(lead_id=lead.id), current_user_id=mgr.id
        )

        # Query audit logs for entity_id
        stmt = select(AuditLog).where(AuditLog.entity_id == str(lead.id))
        logs = (await session.execute(stmt)).scalars().all()
        actions = [l.action for l in logs]
        assert "CREATE_LEAD" in actions
        assert "UPDATE_LEAD" in actions
        assert "CONVERT_LEAD" in actions


@pytest.mark.asyncio
async def test_search_crm_global():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_crm_users(session)
        token = create_access_token(str(mgr.id))
        unique = uuid.uuid4().hex[:6]

        await lead_service.create_lead(
            session, LeadCreate(first_name=f"SearchLead_{unique}", company=f"SearchCo_{unique}")
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {token}"}
        resp = await ac.get(f"/api/v1/crm/search?q={unique}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["leads"]) >= 1


@pytest.mark.asyncio
async def test_pagination_leads_and_opportunities():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_crm_users(session)
        token = create_access_token(str(mgr.id))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {token}"}
        resp = await ac.get("/api/v1/crm/leads?skip=0&limit=5", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) <= 5

        opp_resp = await ac.get("/api/v1/crm/opportunities?skip=0&limit=5", headers=headers)
        assert opp_resp.status_code == 200
        assert isinstance(opp_resp.json(), list)
        assert len(opp_resp.json()) <= 5


@pytest.mark.asyncio
async def test_domain_isolation_no_stock_or_finance_mutation():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_crm_users(session)

        # Record initial counts
        init_stock_ledger = (await session.execute(select(func.count(StockLedger.id)))).scalar() or 0
        init_stock_balance = (await session.execute(select(func.count(StockBalance.id)))).scalar() or 0

        # Execute full CRM lifecycle
        unique = uuid.uuid4().hex[:6]
        lead = await lead_service.create_lead(
            session,
            LeadCreate(
                first_name="Isolated",
                company=f"Isolated Corp {unique}",
                estimated_value=Decimal("50000.00"),
            ),
            current_user_id=mgr.id,
        )
        await lead_service.update_lead(session, lead.id, LeadUpdate(status="CONTACTED"), current_user_id=mgr.id)
        await lead_service.update_lead(session, lead.id, LeadUpdate(status="QUALIFIED"), current_user_id=mgr.id)
        await lead_conversion_service.convert_lead(
            session, LeadConversionRequest(lead_id=lead.id, create_opportunity=True), current_user_id=mgr.id
        )

        # Check stock counts remained completely unchanged
        post_stock_ledger = (await session.execute(select(func.count(StockLedger.id)))).scalar() or 0
        post_stock_balance = (await session.execute(select(func.count(StockBalance.id)))).scalar() or 0

        assert post_stock_ledger == init_stock_ledger
        assert post_stock_balance == init_stock_balance


@pytest.mark.asyncio
async def test_domain_isolation_no_sales_order_mutation():
    async with AsyncSessionLocal() as session:
        mgr, _, _ = await get_test_crm_users(session)

        init_so = (await session.execute(select(func.count(SalesOrder.id)))).scalar() or 0
        init_sq = (await session.execute(select(func.count(SalesQuotation.id)))).scalar() or 0

        unique = uuid.uuid4().hex[:6]
        lead = await lead_service.create_lead(
            session,
            LeadCreate(first_name="NoSO", company=f"NoSO Corp {unique}"),
            current_user_id=mgr.id,
        )
        await lead_service.update_lead(session, lead.id, LeadUpdate(status="CONTACTED"), current_user_id=mgr.id)
        await lead_service.update_lead(session, lead.id, LeadUpdate(status="QUALIFIED"), current_user_id=mgr.id)
        await lead_conversion_service.convert_lead(
            session, LeadConversionRequest(lead_id=lead.id, create_opportunity=True), current_user_id=mgr.id
        )

        post_so = (await session.execute(select(func.count(SalesOrder.id)))).scalar() or 0
        post_sq = (await session.execute(select(func.count(SalesQuotation.id)))).scalar() or 0

        assert post_so == init_so
        assert post_sq == init_sq
