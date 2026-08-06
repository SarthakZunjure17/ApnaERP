from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest

from app.db.session import AsyncSessionLocal
from app.models.crm import LeadSource, LeadTag, OpportunityStage
from app.schemas.crm import (
    ActivityCreate,
    CampaignCreate,
    CampaignMemberCreate,
    LeadConversionRequest,
    LeadCreate,
    LeadMergeRequest,
    LeadNoteCreate,
    LeadUpdate,
    MeetingCreate,
    OpportunityCreate,
    OpportunityStageCreate,
    OpportunityUpdate,
    OpportunityWinLossRequest,
    TaskCreate,
)
from app.services.crm_services import (
    ActivityService,
    CampaignService,
    CRMAnalyticsService,
    CRMImportExportService,
    CRMSearchService,
    LeadConversionService,
    LeadService,
    MeetingService,
    OpportunityService,
    TaskService,
)
from app.services.customer_services import CustomerService


@pytest.mark.asyncio
async def test_lead_crud_scoring_and_assignment():
    async with AsyncSessionLocal() as db_session:
        lead_service = LeadService()

        # 1. Setup Source & Tag
        source = LeadSource(code=f"SRC_{uuid.uuid4().hex[:4]}", name="Website Contact Form")
        db_session.add(source)
        tag = LeadTag(name=f"Enterprise_{uuid.uuid4().hex[:4]}", color="#EF4444")
        db_session.add(tag)
        await db_session.commit()

        # 2. Create Lead
        lead_in = LeadCreate(
            first_name="Alice",
            last_name="Smith",
            company="Acme Corp",
            title="CTO",
            email=f"alice_{uuid.uuid4().hex[:4]}@acme.com",
            phone="+15550199",
            source_id=source.id,
            tag_ids=[tag.id],
            estimated_value=Decimal("75000.00"),
        )
        lead = await lead_service.create_lead(db_session, lead_in)

        assert lead.id is not None
        assert lead.lead_code.startswith("LEAD-")
        assert lead.score > 50
        assert len(lead.tags) == 1

        # 3. Add Note
        note_in = LeadNoteCreate(content="Initial discovery call completed.", is_pinned=True)
        note = await lead_service.add_note(db_session, lead.id, note_in)
        assert note.id is not None
        assert note.is_pinned is True

        # 4. Search & Update
        leads, count = await lead_service.lead_repo.search_leads(db_session, query="Acme")
        assert count >= 1
        assert leads[0].company == "Acme Corp"


@pytest.mark.asyncio
async def test_opportunity_pipeline_and_stages():
    async with AsyncSessionLocal() as db_session:
        opp_service = OpportunityService()

        # 1. Create Stage
        stage = OpportunityStage(code=f"QUAL_{uuid.uuid4().hex[:4]}", name="Qualification", probability_default=Decimal("25.00"))
        db_session.add(stage)
        await db_session.commit()

        # 2. Create Opportunity
        opp_in = OpportunityCreate(
            title="Enterprise License Deal",
            stage_id=stage.id,
            expected_revenue=Decimal("120000.00"),
        )
        opp = await opp_service.create_opportunity(db_session, opp_in)

        assert opp.id is not None
        assert opp.opportunity_code.startswith("OPP-")
        assert opp.status == "Open"
        assert opp.probability == Decimal("25.00")

        # 3. Record Win
        won_opp = await opp_service.record_win_loss(db_session, opp.id, status="Won", reason="Superior feature set")
        assert won_opp.status == "Won"
        assert won_opp.probability == Decimal("100.00")
        assert won_opp.won_reason == "Superior feature set"


@pytest.mark.asyncio
async def test_lead_conversion_engine_with_customer_reuse():
    async with AsyncSessionLocal() as db_session:
        lead_service = LeadService()
        conversion_service = LeadConversionService()

        # Setup Stage
        stage = OpportunityStage(code=f"PROP_{uuid.uuid4().hex[:4]}", name="Proposal", probability_default=Decimal("60.00"))
        db_session.add(stage)
        await db_session.commit()

        shared_email = f"bob_{uuid.uuid4().hex[:4]}@techcorp.com"

        # 1. Create Lead 1
        lead1_in = LeadCreate(
            first_name="Bob",
            last_name="Jones",
            company="TechCorp Inc",
            email=shared_email,
            estimated_value=Decimal("50000.00"),
        )
        lead1 = await lead_service.create_lead(db_session, lead1_in)

        # 2. Convert Lead 1 -> creates a NEW Sales Customer
        conv_req1 = LeadConversionRequest(
            lead_id=lead1.id,
            opportunity_title="TechCorp Deal",
            stage_id=stage.id,
        )
        res1 = await conversion_service.convert_lead(db_session, conv_req1)

        assert res1.is_existing_customer is False
        assert res1.customer_id is not None
        assert res1.opportunity_id is not None

        # Verify Lead 1 is converted
        lead1_db = await lead_service.lead_repo.get_by_id(db_session, lead1.id)
        assert lead1_db.is_converted is True
        assert lead1_db.status == "Converted"

        # 3. Create Lead 2 with SAME email
        lead2_in = LeadCreate(
            first_name="Robert",
            last_name="Jones",
            company="TechCorp Inc",
            email=shared_email,
            estimated_value=Decimal("80000.00"),
        )
        lead2 = await lead_service.create_lead(db_session, lead2_in)

        # 4. Convert Lead 2 -> must REUSE existing Sales Customer!
        conv_req2 = LeadConversionRequest(
            lead_id=lead2.id,
            opportunity_title="TechCorp Expansion",
            stage_id=stage.id,
        )
        res2 = await conversion_service.convert_lead(db_session, conv_req2)

        assert res2.is_existing_customer is True
        assert res2.customer_id == res1.customer_id  # Reused exact customer record!


@pytest.mark.asyncio
async def test_activities_meetings_and_tasks():
    async with AsyncSessionLocal() as db_session:
        act_service = ActivityService()
        meeting_service = MeetingService()
        task_service = TaskService()

        # 1. Activity
        act_in = ActivityCreate(
            activity_type="Call",
            subject="Introductory Sales Call",
            due_date=datetime.now(timezone.utc) + timedelta(days=1),
        )
        act = await act_service.create_activity(db_session, act_in)
        assert act.status == "Pending"

        completed_act = await act_service.complete_activity(db_session, act.id)
        assert completed_act.status == "Completed"

        # 2. Meeting
        now = datetime.now(timezone.utc)
        meeting_in = MeetingCreate(
            subject="Product Demo Meeting",
            meeting_type="Meeting",
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(hours=3),
            location="Zoom Video Call",
        )
        meeting = await meeting_service.schedule_meeting(db_session, meeting_in)
        assert meeting.id is not None
        assert meeting.status == "Scheduled"

        # 3. Task with dependency
        task1_in = TaskCreate(title="Prepare Presentation Deck", priority="High")
        t1 = await task_service.create_task(db_session, task1_in)

        task2_in = TaskCreate(title="Present to Executive Committee", parent_task_id=t1.id)
        t2 = await task_service.create_task(db_session, task2_in)

        assert t2.parent_task_id == t1.id


@pytest.mark.asyncio
async def test_campaign_management_and_roi():
    async with AsyncSessionLocal() as db_session:
        camp_service = CampaignService()
        lead_service = LeadService()

        # 1. Create Campaign
        camp_in = CampaignCreate(
            name="Q3 Email Marketing",
            type="Email",
            budget=Decimal("5000.00"),
            actual_cost=Decimal("4000.00"),
            actual_revenue=Decimal("16000.00"),
        )
        camp = await camp_service.create_campaign(db_session, camp_in)
        assert camp.campaign_code.startswith("CMP-")

        # 2. Add Member
        lead = await lead_service.create_lead(db_session, LeadCreate(first_name="Charlie", email=f"charlie_{uuid.uuid4().hex[:4]}@test.com"))
        member_in = CampaignMemberCreate(lead_id=lead.id, status="Responded")
        member = await camp_service.add_member(db_session, camp.id, member_in)
        assert member.id is not None

        # 3. ROI Calculation
        roi_report = await camp_service.calculate_roi(db_session, camp.id)
        assert roi_report.roi_percentage == 300.0  # (16000 - 4000) / 4000 * 100 = 300%


@pytest.mark.asyncio
async def test_crm_analytics_search_and_import_export():
    async with AsyncSessionLocal() as db_session:
        analytics_service = CRMAnalyticsService()
        search_service = CRMSearchService()
        import_export_service = CRMImportExportService()

        # 1. Analytics
        summary = await analytics_service.get_summary_analytics(db_session)
        assert summary.total_leads >= 0

        # 2. Global Search
        search_res = await search_service.search_crm(db_session, query="Alice")
        assert isinstance(search_res.leads, list)

        # 3. Import & Export CSV
        csv_data = await import_export_service.export_leads_csv(db_session)
        assert "Lead Code" in csv_data

        sample_csv = f"First Name,Last Name,Company,Email\nDavid,Miller,Miller Corp,david_{uuid.uuid4().hex[:4]}@miller.com\n"
        imported = await import_export_service.import_leads_csv(db_session, sample_csv)
        assert imported == 1
