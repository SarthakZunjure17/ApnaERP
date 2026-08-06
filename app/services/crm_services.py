import csv
from datetime import datetime, timezone
from decimal import Decimal
import io
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_events import (
    CRM_CAMPAIGN_COMPLETED,
    CRM_LEAD_ASSIGNED,
    CRM_LEAD_CONVERTED,
    CRM_LEAD_CREATED,
    CRM_MEETING_SCHEDULED,
    CRM_OPPORTUNITY_CREATED,
    CRM_OPPORTUNITY_LOST,
    CRM_OPPORTUNITY_WON,
    CRM_TASK_COMPLETED,
    domain_event_publisher,
)
from app.models.crm import (
    Activity,
    Campaign,
    CampaignMember,
    CRMReportSnapshot,
    Lead,
    LeadNote,
    LeadSource,
    LeadTag,
    Meeting,
    Opportunity,
    OpportunityStage,
    Task,
    TimelineEvent,
)
from app.models.customer import Customer
from app.repositories.crm_repos import (
    ActivityRepository,
    CampaignMemberRepository,
    CampaignRepository,
    CRMReportSnapshotRepository,
    LeadNoteRepository,
    LeadRepository,
    LeadSourceRepository,
    LeadTagRepository,
    MeetingRepository,
    OpportunityRepository,
    OpportunityStageRepository,
    TaskRepository,
    TimelineEventRepository,
)
from app.repositories.sales_repos import CustomerRepository
from app.schemas.crm import (
    ActivityCreate,
    ActivityUpdate,
    CampaignCreate,
    CampaignMemberCreate,
    CampaignROIReport,
    CampaignUpdate,
    CRMAnalyticsSummary,
    CRMSearchResult,
    LeadConversionRequest,
    LeadConversionResponse,
    LeadCreate,
    LeadFunnelReport,
    LeadMergeRequest,
    LeadNoteCreate,
    LeadUpdate,
    MeetingCreate,
    MeetingUpdate,
    OpportunityCreate,
    OpportunityUpdate,
    TaskCreate,
    TaskUpdate,
)
from app.schemas.sales import CustomerCreate
from app.services.customer_services import CustomerService

logger = logging.getLogger("app.crm_services")

# Redis caching integration
try:
    from app.core.redis import redis_client
except Exception:
    redis_client = None


class LeadService:
    def __init__(self):
        self.lead_repo = LeadRepository()
        self.source_repo = LeadSourceRepository()
        self.tag_repo = LeadTagRepository()
        self.note_repo = LeadNoteRepository()
        self.timeline_repo = TimelineEventRepository()

    async def create_lead(self, db: AsyncSession, lead_in: LeadCreate, current_user_id: Optional[uuid.UUID] = None) -> Lead:
        # Check duplicate by email or phone
        duplicates = await self.lead_repo.find_duplicates(db, email=lead_in.email, phone=lead_in.phone)
        if duplicates:
            logger.info(f"Duplicate lead detected for email={lead_in.email}, phone={lead_in.phone}")

        lead_code = f"LEAD-{uuid.uuid4().hex[:8].upper()}"
        lead = Lead(
            lead_code=lead_code,
            first_name=lead_in.first_name,
            last_name=lead_in.last_name,
            company=lead_in.company,
            title=lead_in.title,
            email=lead_in.email,
            phone=lead_in.phone,
            status=lead_in.status,
            source_id=lead_in.source_id,
            assigned_to_id=lead_in.assigned_to_id,
            created_by=current_user_id,
            estimated_value=lead_in.estimated_value,
        )

        # Tags attachment
        if lead_in.tag_ids:
            tags = []
            for tag_id in lead_in.tag_ids:
                tag = await self.tag_repo.get_by_id(db, tag_id)
                if tag:
                    tags.append(tag)
            lead.tags = tags

        # Calculate initial score
        lead.score = self._calculate_lead_scoring(lead)

        db.add(lead)
        await db.commit()
        await db.refresh(lead)

        # Log Timeline Event
        timeline_ev = TimelineEvent(
            entity_type="Lead",
            entity_id=lead.id,
            event_type="LeadCreated",
            title=f"Lead Created: {lead.first_name} {lead.last_name or ''}",
            description=f"Company: {lead.company or 'N/A'}, Status: {lead.status}",
            user_id=current_user_id,
        )
        db.add(timeline_ev)
        await db.commit()

        # Publish Event
        domain_event_publisher.publish(
            CRM_LEAD_CREATED,
            {
                "lead_id": str(lead.id),
                "lead_code": lead.lead_code,
                "email": lead.email,
                "created_by": str(current_user_id) if current_user_id else None,
            },
        )

        return lead

    def _calculate_lead_scoring(self, lead: Lead) -> int:
        score = 0
        if lead.email:
            score += 15
        if lead.phone:
            score += 15
        if lead.company:
            score += 20
        if lead.title:
            score += 10
        if lead.estimated_value > Decimal("50000"):
            score += 30
        elif lead.estimated_value > Decimal("10000"):
            score += 15
        if lead.source_id:
            score += 10
        return score

    async def update_lead(self, db: AsyncSession, lead_id: uuid.UUID, lead_in: LeadUpdate, current_user_id: Optional[uuid.UUID] = None) -> Lead:
        lead = await self.lead_repo.get_by_id(db, lead_id)
        if not lead:
            raise ValueError("Lead not found")

        update_data = lead_in.model_dump(exclude_unset=True)
        tag_ids = update_data.pop("tag_ids", None)

        for field, value in update_data.items():
            setattr(lead, field, value)

        if tag_ids is not None:
            tags = []
            for tag_id in tag_ids:
                tag = await self.tag_repo.get_by_id(db, tag_id)
                if tag:
                    tags.append(tag)
            lead.tags = tags

        lead.score = self._calculate_lead_scoring(lead)
        await db.commit()
        await db.refresh(lead)
        return lead

    async def assign_lead(self, db: AsyncSession, lead_id: uuid.UUID, assigned_to_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None) -> Lead:
        lead = await self.lead_repo.get_by_id(db, lead_id)
        if not lead:
            raise ValueError("Lead not found")

        lead.assigned_to_id = assigned_to_id
        await db.commit()
        await db.refresh(lead)

        domain_event_publisher.publish(
            CRM_LEAD_ASSIGNED,
            {"lead_id": str(lead.id), "assigned_to_id": str(assigned_to_id)},
        )
        return lead

    async def add_note(self, db: AsyncSession, lead_id: uuid.UUID, note_in: LeadNoteCreate, author_id: Optional[uuid.UUID] = None) -> LeadNote:
        note = LeadNote(
            lead_id=lead_id,
            author_id=author_id,
            content=note_in.content,
            is_private=note_in.is_private,
            is_pinned=note_in.is_pinned,
        )
        db.add(note)
        await db.commit()
        await db.refresh(note)
        return note

    async def merge_leads(self, db: AsyncSession, merge_in: LeadMergeRequest, current_user_id: Optional[uuid.UUID] = None) -> Lead:
        primary = await self.lead_repo.get_by_id(db, merge_in.primary_lead_id)
        if not primary:
            raise ValueError("Primary lead not found")

        for sec_id in merge_in.secondary_lead_ids:
            sec = await self.lead_repo.get_by_id(db, sec_id)
            if sec and not sec.is_deleted:
                # Merge notes
                for note in sec.notes:
                    note.lead_id = primary.id
                sec.is_deleted = True
                sec.deleted_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(primary)
        return primary


class OpportunityService:
    def __init__(self):
        self.opp_repo = OpportunityRepository()
        self.stage_repo = OpportunityStageRepository()
        self.timeline_repo = TimelineEventRepository()

    async def create_opportunity(self, db: AsyncSession, opp_in: OpportunityCreate, current_user_id: Optional[uuid.UUID] = None) -> Opportunity:
        stage = await self.stage_repo.get_by_id(db, opp_in.stage_id)
        if not stage:
            raise ValueError("Opportunity stage not found")

        opp_code = f"OPP-{uuid.uuid4().hex[:8].upper()}"
        opp = Opportunity(
            opportunity_code=opp_code,
            title=opp_in.title,
            customer_id=opp_in.customer_id,
            lead_id=opp_in.lead_id,
            stage_id=opp_in.stage_id,
            expected_revenue=opp_in.expected_revenue,
            probability=opp_in.probability or stage.probability_default,
            expected_closing_date=opp_in.expected_closing_date,
            owner_id=opp_in.owner_id or current_user_id,
            status="Open",
            competitors=opp_in.competitors,
            products_of_interest=opp_in.products_of_interest,
            created_by=current_user_id,
        )

        db.add(opp)
        await db.commit()
        await db.refresh(opp)

        timeline_ev = TimelineEvent(
            entity_type="Opportunity",
            entity_id=opp.id,
            event_type="OpportunityCreated",
            title=f"Opportunity Created: {opp.title}",
            description=f"Value: {opp.expected_revenue}, Stage: {stage.name}",
            user_id=current_user_id,
        )
        db.add(timeline_ev)
        await db.commit()

        domain_event_publisher.publish(
            CRM_OPPORTUNITY_CREATED,
            {
                "opportunity_id": str(opp.id),
                "opportunity_code": opp.opportunity_code,
                "expected_revenue": float(opp.expected_revenue),
            },
        )
        return opp

    async def update_opportunity(self, db: AsyncSession, opp_id: uuid.UUID, opp_in: OpportunityUpdate, current_user_id: Optional[uuid.UUID] = None) -> Opportunity:
        opp = await self.opp_repo.get_by_id(db, opp_id)
        if not opp:
            raise ValueError("Opportunity not found")

        update_data = opp_in.model_dump(exclude_unset=True)
        for field, val in update_data.items():
            setattr(opp, field, val)

        await db.commit()
        await db.refresh(opp)
        return opp

    async def record_win_loss(self, db: AsyncSession, opp_id: uuid.UUID, status: str, reason: Optional[str] = None, current_user_id: Optional[uuid.UUID] = None) -> Opportunity:
        opp = await self.opp_repo.get_by_id(db, opp_id)
        if not opp:
            raise ValueError("Opportunity not found")

        if status == "Won":
            opp.status = "Won"
            opp.won_reason = reason
            opp.probability = Decimal("100.00")
            event_name = CRM_OPPORTUNITY_WON
        elif status == "Lost":
            opp.status = "Lost"
            opp.lost_reason = reason
            opp.probability = Decimal("0.00")
            event_name = CRM_OPPORTUNITY_LOST
        else:
            raise ValueError("Status must be 'Won' or 'Lost'")

        await db.commit()
        await db.refresh(opp)

        domain_event_publisher.publish(
            event_name,
            {"opportunity_id": str(opp.id), "status": status, "reason": reason},
        )
        return opp


class ActivityService:
    def __init__(self):
        self.act_repo = ActivityRepository()

    async def create_activity(self, db: AsyncSession, act_in: ActivityCreate, current_user_id: Optional[uuid.UUID] = None) -> Activity:
        activity = Activity(
            activity_type=act_in.activity_type,
            subject=act_in.subject,
            description=act_in.description,
            status=act_in.status,
            priority=act_in.priority,
            due_date=act_in.due_date,
            owner_id=act_in.owner_id or current_user_id,
            lead_id=act_in.lead_id,
            opportunity_id=act_in.opportunity_id,
            customer_id=act_in.customer_id,
            campaign_id=act_in.campaign_id,
            is_recurring=act_in.is_recurring,
            recurrence_rule=act_in.recurrence_rule,
        )
        db.add(activity)
        await db.commit()
        await db.refresh(activity)
        return activity

    async def complete_activity(self, db: AsyncSession, activity_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None) -> Activity:
        act = await self.act_repo.get_by_id(db, activity_id)
        if not act:
            raise ValueError("Activity not found")
        act.status = "Completed"
        act.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(act)
        return act


class MeetingService:
    def __init__(self):
        self.meeting_repo = MeetingRepository()

    async def schedule_meeting(self, db: AsyncSession, meeting_in: MeetingCreate, current_user_id: Optional[uuid.UUID] = None) -> Meeting:
        meeting = Meeting(
            subject=meeting_in.subject,
            meeting_type=meeting_in.meeting_type,
            start_time=meeting_in.start_time,
            end_time=meeting_in.end_time,
            location=meeting_in.location,
            meeting_link=meeting_in.meeting_link,
            status=meeting_in.status,
            organizer_id=meeting_in.organizer_id or current_user_id,
            lead_id=meeting_in.lead_id,
            opportunity_id=meeting_in.opportunity_id,
            customer_id=meeting_in.customer_id,
            notes=meeting_in.notes,
        )
        db.add(meeting)
        await db.commit()
        await db.refresh(meeting)

        domain_event_publisher.publish(
            CRM_MEETING_SCHEDULED,
            {
                "meeting_id": str(meeting.id),
                "subject": meeting.subject,
                "start_time": meeting.start_time.isoformat(),
            },
        )
        return meeting


class TaskService:
    def __init__(self):
        self.task_repo = TaskRepository()

    async def create_task(self, db: AsyncSession, task_in: TaskCreate, current_user_id: Optional[uuid.UUID] = None) -> Task:
        task_code = f"TSK-{uuid.uuid4().hex[:8].upper()}"
        task = Task(
            task_code=task_code,
            title=task_in.title,
            description=task_in.description,
            status=task_in.status,
            priority=task_in.priority,
            due_date=task_in.due_date,
            assigned_to_id=task_in.assigned_to_id or current_user_id,
            created_by_id=current_user_id,
            parent_task_id=task_in.parent_task_id,
            lead_id=task_in.lead_id,
            opportunity_id=task_in.opportunity_id,
            customer_id=task_in.customer_id,
            campaign_id=task_in.campaign_id,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task

    async def complete_task(self, db: AsyncSession, task_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None) -> Task:
        task = await self.task_repo.get_by_id(db, task_id)
        if not task:
            raise ValueError("Task not found")
        task.status = "Completed"
        await db.commit()
        await db.refresh(task)

        domain_event_publisher.publish(
            CRM_TASK_COMPLETED,
            {"task_id": str(task.id), "task_code": task.task_code},
        )
        return task


class CampaignService:
    def __init__(self):
        self.campaign_repo = CampaignRepository()
        self.member_repo = CampaignMemberRepository()

    async def create_campaign(self, db: AsyncSession, camp_in: CampaignCreate, current_user_id: Optional[uuid.UUID] = None) -> Campaign:
        camp_code = f"CMP-{uuid.uuid4().hex[:8].upper()}"
        campaign = Campaign(
            campaign_code=camp_code,
            name=camp_in.name,
            type=camp_in.type,
            status=camp_in.status,
            budget=camp_in.budget,
            actual_cost=camp_in.actual_cost,
            expected_revenue=camp_in.expected_revenue,
            actual_revenue=camp_in.actual_revenue,
            start_date=camp_in.start_date,
            end_date=camp_in.end_date,
            owner_id=camp_in.owner_id or current_user_id,
        )
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)
        return campaign

    async def add_member(self, db: AsyncSession, campaign_id: uuid.UUID, member_in: CampaignMemberCreate) -> CampaignMember:
        member = CampaignMember(
            campaign_id=campaign_id,
            lead_id=member_in.lead_id,
            customer_id=member_in.customer_id,
            status=member_in.status,
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
        return member

    async def calculate_roi(self, db: AsyncSession, campaign_id: uuid.UUID) -> CampaignROIReport:
        campaign = await self.campaign_repo.get_by_id(db, campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")

        roi = 0.0
        if campaign.actual_cost > Decimal("0.00"):
            roi = float(((campaign.actual_revenue - campaign.actual_cost) / campaign.actual_cost) * Decimal("100.00"))

        return CampaignROIReport(
            campaign_id=campaign.id,
            campaign_name=campaign.name,
            budget=campaign.budget,
            actual_cost=campaign.actual_cost,
            actual_revenue=campaign.actual_revenue,
            roi_percentage=round(roi, 2),
        )


class LeadConversionService:
    """
    LeadConversionEngine converts a Lead into an Opportunity.
    REUSES existing Sales Customer record when possible (by explicit ID or matching email/phone/company),
    or creates a NEW Customer using CustomerService without duplicating.
    """
    def __init__(self):
        self.lead_repo = LeadRepository()
        self.customer_repo = CustomerRepository()
        self.customer_service = CustomerService()
        self.opp_service = OpportunityService()
        self.stage_repo = OpportunityStageRepository()

    async def convert_lead(
        self, db: AsyncSession, req: LeadConversionRequest, current_user_id: Optional[uuid.UUID] = None
    ) -> LeadConversionResponse:
        lead = await self.lead_repo.get_by_id(db, req.lead_id)
        if not lead:
            raise ValueError("Lead not found")
        if lead.is_converted:
            raise ValueError("Lead has already been converted")

        # 1. Customer Reuse Logic
        is_existing_customer = False
        target_customer: Optional[Customer] = None

        if req.existing_customer_id:
            target_customer = await self.customer_repo.get_by_id(db, req.existing_customer_id)
            if target_customer:
                is_existing_customer = True

        if not target_customer and lead.email:
            # Search customer by email
            existing_by_email, _ = await self.customer_repo.search_customers(db, query=lead.email, limit=1)
            if existing_by_email:
                target_customer = existing_by_email[0]
                is_existing_customer = True

        if not target_customer and lead.phone:
            # Search customer by phone
            existing_by_phone, _ = await self.customer_repo.search_customers(db, query=lead.phone, limit=1)
            if existing_by_phone:
                target_customer = existing_by_phone[0]
                is_existing_customer = True

        if not target_customer:
            cust_code = f"CUST-{uuid.uuid4().hex[:8].upper()}"
            cust_in = CustomerCreate(
                customer_code=cust_code,
                name=lead.company or f"{lead.first_name} {lead.last_name or ''}".strip(),
                email=lead.email,
                phone=lead.phone,
            )
            target_customer = await self.customer_service.create_customer(db, cust_in, current_user_id=current_user_id)
            is_existing_customer = False

        # 2. Opportunity Stage Resolution
        stage_id = req.stage_id
        if not stage_id:
            stages = await self.stage_repo.get_all_ordered(db)
            if not stages:
                # Default fallback stage
                default_stage = OpportunityStage(code="PROSPECTING", name="Prospecting", display_order=1)
                db.add(default_stage)
                await db.commit()
                stage_id = default_stage.id
            else:
                stage_id = stages[0].id

        # 3. Create Opportunity
        opp_in = OpportunityCreate(
            title=req.opportunity_title or f"Opportunity for {lead.company or lead.first_name}",
            customer_id=target_customer.id,
            lead_id=lead.id,
            stage_id=stage_id,
            expected_revenue=req.expected_revenue or lead.estimated_value,
        )
        opp = await self.opp_service.create_opportunity(db, opp_in, current_user_id=current_user_id)

        # 4. Mark Lead as Converted
        now = datetime.now(timezone.utc)
        lead.is_converted = True
        lead.status = "Converted"
        lead.converted_at = now
        lead.converted_opportunity_id = opp.id
        lead.converted_customer_id = target_customer.id
        await db.commit()

        # Publish Event
        domain_event_publisher.publish(
            CRM_LEAD_CONVERTED,
            {
                "lead_id": str(lead.id),
                "opportunity_id": str(opp.id),
                "customer_id": str(target_customer.id),
                "is_existing_customer": is_existing_customer,
            },
        )

        return LeadConversionResponse(
            lead_id=lead.id,
            opportunity_id=opp.id,
            customer_id=target_customer.id,
            is_existing_customer=is_existing_customer,
            converted_at=now,
        )


class CRMAnalyticsService:
    def __init__(self):
        self.lead_repo = LeadRepository()
        self.opp_repo = OpportunityRepository()
        self.campaign_repo = CampaignRepository()

    async def get_summary_analytics(self, db: AsyncSession) -> CRMAnalyticsSummary:
        # Check Redis Cache
        cache_key = "crm:analytics:summary"
        if redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    return CRMAnalyticsSummary(**json.loads(cached))
            except Exception:
                pass

        leads, total_leads = await self.lead_repo.search_leads(db, limit=1000)
        converted_count = sum(1 for l in leads if l.is_converted)
        conv_rate = (converted_count / total_leads * 100) if total_leads > 0 else 0.0

        opps, total_opps = await self.opp_repo.search_opportunities(db, limit=1000)
        open_val = sum(o.expected_revenue for o in opps if o.status == "Open")
        forecast_val = sum(o.expected_revenue * (o.probability / Decimal("100.00")) for o in opps if o.status == "Open")

        camps, total_camps = await self.campaign_repo.search_campaigns(db, limit=100)

        summary = CRMAnalyticsSummary(
            total_leads=total_leads,
            converted_leads=converted_count,
            conversion_rate=round(conv_rate, 2),
            total_opportunities=total_opps,
            open_opportunities_value=open_val,
            forecast_revenue=forecast_val,
            total_campaigns=total_camps,
            average_campaign_roi=0.0,
        )

        if redis_client:
            try:
                redis_client.setex(cache_key, 300, summary.model_dump_json())
            except Exception:
                pass

        return summary


class CRMSearchService:
    def __init__(self):
        self.lead_repo = LeadRepository()
        self.opp_repo = OpportunityRepository()
        self.task_repo = TaskRepository()

    async def search_crm(self, db: AsyncSession, query: str) -> CRMSearchResult:
        leads, _ = await self.lead_repo.search_leads(db, query=query, limit=10)
        opps, _ = await self.opp_repo.search_opportunities(db, query=query, limit=10)
        tasks, _ = await self.task_repo.search_tasks(db, query=query, limit=10)

        return CRMSearchResult(
            leads=[l for l in leads],
            opportunities=[o for o in opps],
            tasks=[t for t in tasks],
        )


class CRMImportExportService:
    def __init__(self):
        self.lead_service = LeadService()

    async def export_leads_csv(self, db: AsyncSession) -> str:
        leads, _ = await self.lead_service.lead_repo.search_leads(db, limit=5000)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Lead Code", "First Name", "Last Name", "Company", "Email", "Phone", "Status", "Score", "Estimated Value"])

        for l in leads:
            writer.writerow([l.lead_code, l.first_name, l.last_name, l.company, l.email, l.phone, l.status, l.score, l.estimated_value])

        return output.getvalue()

    async def import_leads_csv(self, db: AsyncSession, csv_content: str, current_user_id: Optional[uuid.UUID] = None) -> int:
        reader = csv.DictReader(io.StringIO(csv_content))
        imported_count = 0
        for row in reader:
            lead_in = LeadCreate(
                first_name=row.get("First Name") or row.get("first_name", "Lead"),
                last_name=row.get("Last Name") or row.get("last_name"),
                company=row.get("Company") or row.get("company"),
                email=row.get("Email") or row.get("email"),
                phone=row.get("Phone") or row.get("phone"),
                estimated_value=Decimal(row.get("Estimated Value") or row.get("estimated_value", "0.00")),
            )
            await self.lead_service.create_lead(db, lead_in, current_user_id=current_user_id)
            imported_count += 1
        return imported_count
