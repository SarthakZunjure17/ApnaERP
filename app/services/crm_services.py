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
from app.exceptions.base import NotFoundException, ValidationException
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
from app.models.customer import Customer, CustomerContact
from app.repositories.crm_repos import (
    activity_repository,
    campaign_member_repository,
    campaign_repository,
    crm_report_snapshot_repository,
    lead_note_repository,
    lead_repository,
    lead_source_repository,
    lead_tag_repository,
    meeting_repository,
    opportunity_repository,
    opportunity_stage_repository,
    task_repository,
    timeline_event_repository,
)
from app.repositories.sales_repos import customer_repository
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
    OpportunityStageChangeRequest,
    OpportunityUpdate,
    TaskCreate,
    TaskUpdate,
)
from app.schemas.sales import CustomerContactCreate, CustomerCreate
from app.services.audit_log import audit_log_service
from app.services.customer_services import customer_service

logger = logging.getLogger("app.crm_services")

# Redis caching integration
try:
    from app.core.redis import redis_client
except Exception:
    redis_client = None


LEAD_LIFECYCLE_TRANSITIONS = {
    "NEW": ["CONTACTED", "LOST"],
    "CONTACTED": ["QUALIFIED", "LOST"],
    "QUALIFIED": ["CONVERTED", "LOST"],
    "CONVERTED": [],  # Terminal state
    "LOST": [],       # Terminal state
}

OPPORTUNITY_PIPELINE_ORDER = [
    "PROSPECTING",
    "QUALIFICATION",
    "PROPOSAL",
    "NEGOTIATION",
    "WON",
    "LOST",
]

STAGE_DEFAULT_PROBABILITIES = {
    "PROSPECTING": Decimal("10.00"),
    "QUALIFICATION": Decimal("30.00"),
    "PROPOSAL": Decimal("60.00"),
    "NEGOTIATION": Decimal("80.00"),
    "WON": Decimal("100.00"),
    "LOST": Decimal("0.00"),
}


class LeadService:
    def __init__(self):
        self.lead_repo = lead_repository
        self.source_repo = lead_source_repository
        self.tag_repo = lead_tag_repository
        self.note_repo = lead_note_repository
        self.timeline_repo = timeline_event_repository

    async def _generate_lead_code(self, db: AsyncSession) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"LEAD-{year}-"
        max_suffix = await self.lead_repo.get_max_number_suffix(db, prefix=prefix)
        new_num = max_suffix + 1
        return f"{prefix}{new_num:05d}"

    def _normalize_status(self, status_val: str) -> str:
        s = status_val.strip().upper()
        if s in LEAD_LIFECYCLE_TRANSITIONS:
            return s
        for key in LEAD_LIFECYCLE_TRANSITIONS:
            if key == s:
                return key
        return "NEW"

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
        if lead.estimated_value and lead.estimated_value > Decimal("50000"):
            score += 30
        elif lead.estimated_value and lead.estimated_value > Decimal("10000"):
            score += 15
        if lead.source_id:
            score += 10
        return score

    async def create_lead(self, db: AsyncSession, lead_in: LeadCreate, current_user_id: Optional[uuid.UUID] = None) -> Lead:
        # Check duplicate by email or phone
        duplicates = await self.lead_repo.find_duplicates(db, email=lead_in.email, phone=lead_in.phone)
        if duplicates:
            logger.info(f"Duplicate lead detected for email={lead_in.email}, phone={lead_in.phone}")

        lead_code = await self._generate_lead_code(db)
        norm_status = self._normalize_status(lead_in.status or "NEW")

        lead = Lead(
            lead_code=lead_code,
            first_name=lead_in.first_name,
            last_name=lead_in.last_name,
            company=lead_in.company,
            title=lead_in.title,
            email=lead_in.email,
            phone=lead_in.phone,
            status=norm_status,
            source_id=lead_in.source_id,
            assigned_to_id=lead_in.assigned_to_id,
            created_by=current_user_id,
            estimated_value=lead_in.estimated_value or Decimal("0.00"),
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
        await db.flush()

        # Initial note if provided
        if lead_in.notes:
            note = LeadNote(
                lead_id=lead.id,
                author_id=current_user_id,
                content=lead_in.notes,
                is_private=False,
                is_pinned=False,
            )
            db.add(note)

        # Log Timeline Event
        timeline_ev = TimelineEvent(
            entity_type="Lead",
            entity_id=lead.id,
            event_type="LeadCreated",
            title=f"Lead Created: {lead.first_name} {lead.last_name or ''}".strip(),
            description=f"Company: {lead.company or 'N/A'}, Status: {lead.status}",
            user_id=current_user_id,
        )
        db.add(timeline_ev)

        # AuditLog
        await audit_log_service.log_event(
            db,
            action="CREATE_LEAD",
            entity_type="Lead",
            entity_id=str(lead.id),
            user_id=current_user_id,
            new_data={
                "lead_code": lead.lead_code,
                "first_name": lead.first_name,
                "company": lead.company,
                "status": lead.status,
                "estimated_value": str(lead.estimated_value),
            },
        )

        await db.commit()
        lead = await self.lead_repo.get_by_id(db, lead.id)

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

    async def update_lead(self, db: AsyncSession, lead_id: uuid.UUID, lead_in: LeadUpdate, current_user_id: Optional[uuid.UUID] = None) -> Lead:
        lead = await self.lead_repo.get_by_id(db, lead_id)
        if not lead:
            raise NotFoundException(f"Lead ID '{lead_id}' not found.")

        current_status = lead.status.upper()
        if current_status in ["CONVERTED", "LOST"]:
            raise ValidationException(f"Cannot modify lead in terminal '{lead.status}' status.")

        prev_data = {
            "status": lead.status,
            "first_name": lead.first_name,
            "company": lead.company,
            "estimated_value": str(lead.estimated_value),
        }

        update_data = lead_in.model_dump(exclude_unset=True)
        tag_ids = update_data.pop("tag_ids", None)

        if "status" in update_data and update_data["status"]:
            target_status = self._normalize_status(update_data["status"])
            if target_status != current_status:
                allowed_transitions = LEAD_LIFECYCLE_TRANSITIONS.get(current_status, [])
                if target_status not in allowed_transitions:
                    raise ValidationException(
                        f"Invalid lead status transition from '{lead.status}' to '{target_status}'. "
                        f"Allowed transitions: {allowed_transitions}"
                    )
                update_data["status"] = target_status

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

        # AuditLog
        await audit_log_service.log_event(
            db,
            action="UPDATE_LEAD",
            entity_type="Lead",
            entity_id=str(lead.id),
            user_id=current_user_id,
            previous_data=prev_data,
            new_data={
                "status": lead.status,
                "first_name": lead.first_name,
                "company": lead.company,
                "estimated_value": str(lead.estimated_value),
            },
        )

        await db.commit()
        lead = await self.lead_repo.get_by_id(db, lead.id)
        return lead

    async def assign_lead(self, db: AsyncSession, lead_id: uuid.UUID, assigned_to_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None) -> Lead:
        lead = await self.lead_repo.get_by_id(db, lead_id)
        if not lead:
            raise NotFoundException(f"Lead ID '{lead_id}' not found.")

        if lead.status.upper() in ["CONVERTED", "LOST"]:
            raise ValidationException(f"Cannot assign lead in terminal '{lead.status}' status.")

        lead.assigned_to_id = assigned_to_id

        # AuditLog
        await audit_log_service.log_event(
            db,
            action="ASSIGN_LEAD",
            entity_type="Lead",
            entity_id=str(lead.id),
            user_id=current_user_id,
            new_data={"assigned_to_id": str(assigned_to_id)},
        )

        await db.commit()
        lead = await self.lead_repo.get_by_id(db, lead.id)

        domain_event_publisher.publish(
            CRM_LEAD_ASSIGNED,
            {"lead_id": str(lead.id), "assigned_to_id": str(assigned_to_id)},
        )
        return lead

    async def add_note(self, db: AsyncSession, lead_id: uuid.UUID, note_in: LeadNoteCreate, author_id: Optional[uuid.UUID] = None) -> LeadNote:
        lead = await self.lead_repo.get_by_id(db, lead_id)
        if not lead:
            raise NotFoundException(f"Lead ID '{lead_id}' not found.")

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

    async def delete_lead(self, db: AsyncSession, lead_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None) -> bool:
        lead = await self.lead_repo.get_by_id(db, lead_id)
        if not lead:
            raise NotFoundException(f"Lead ID '{lead_id}' not found.")

        await self.lead_repo.delete(db, lead_id)

        # AuditLog
        await audit_log_service.log_event(
            db,
            action="DELETE_LEAD",
            entity_type="Lead",
            entity_id=str(lead_id),
            user_id=current_user_id,
            previous_data={"lead_code": lead.lead_code, "company": lead.company},
        )
        return True

    async def merge_leads(self, db: AsyncSession, merge_in: LeadMergeRequest, current_user_id: Optional[uuid.UUID] = None) -> Lead:
        primary = await self.lead_repo.get_by_id(db, merge_in.primary_lead_id)
        if not primary:
            raise NotFoundException("Primary lead not found.")

        for sec_id in merge_in.secondary_lead_ids:
            sec = await self.lead_repo.get_by_id(db, sec_id)
            if sec and not sec.is_deleted:
                for note in sec.notes:
                    note.lead_id = primary.id
                sec.is_deleted = True
                sec.deleted_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(primary)
        return primary


class OpportunityService:
    def __init__(self):
        self.opp_repo = opportunity_repository
        self.stage_repo = opportunity_stage_repository
        self.timeline_repo = timeline_event_repository

    async def _generate_opportunity_code(self, db: AsyncSession) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"OPP-{year}-"
        max_suffix = await self.opp_repo.get_max_number_suffix(db, prefix=prefix)
        new_num = max_suffix + 1
        return f"{prefix}{new_num:05d}"

    async def _resolve_stage(self, db: AsyncSession, stage_id: Optional[uuid.UUID] = None, stage_code: Optional[str] = None) -> OpportunityStage:
        if stage_id:
            stage = await self.stage_repo.get_by_id(db, stage_id)
            if stage:
                return stage
        if stage_code:
            stage = await self.stage_repo.get_by_code(db, stage_code)
            if stage:
                return stage
        stages = await self.stage_repo.get_all_ordered(db)
        if stages:
            return stages[0]
        # Fallback create
        stage = OpportunityStage(code="PROSPECTING", name="Prospecting", probability_default=Decimal("10.00"), display_order=1)
        db.add(stage)
        await db.flush()
        return stage

    async def create_opportunity(self, db: AsyncSession, opp_in: OpportunityCreate, current_user_id: Optional[uuid.UUID] = None) -> Opportunity:
        stage = await self._resolve_stage(db, stage_id=opp_in.stage_id, stage_code=opp_in.stage_code)

        if opp_in.customer_id:
            cust = await customer_repository.get_by_id(db, opp_in.customer_id)
            if not cust:
                raise NotFoundException(f"Customer ID '{opp_in.customer_id}' not found.")

        opp_code = await self._generate_opportunity_code(db)
        prob = opp_in.probability if opp_in.probability is not None else stage.probability_default

        stage_code_upper = stage.code.upper()
        if stage_code_upper == "WON":
            status = "Won"
            prob = Decimal("100.00")
        elif stage_code_upper == "LOST":
            status = "Lost"
            prob = Decimal("0.00")
        else:
            status = "Open"

        opp = Opportunity(
            opportunity_code=opp_code,
            title=opp_in.title,
            customer_id=opp_in.customer_id,
            lead_id=opp_in.lead_id,
            stage_id=stage.id,
            expected_revenue=opp_in.expected_revenue or Decimal("0.00"),
            probability=prob,
            expected_closing_date=opp_in.expected_closing_date,
            owner_id=opp_in.owner_id or current_user_id,
            status=status,
            competitors=opp_in.competitors,
            products_of_interest=opp_in.products_of_interest,
            created_by=current_user_id,
        )

        db.add(opp)
        await db.flush()

        timeline_ev = TimelineEvent(
            entity_type="Opportunity",
            entity_id=opp.id,
            event_type="OpportunityCreated",
            title=f"Opportunity Created: {opp.title}",
            description=f"Value: {opp.expected_revenue}, Stage: {stage.name}",
            user_id=current_user_id,
        )
        db.add(timeline_ev)

        # AuditLog
        await audit_log_service.log_event(
            db,
            action="CREATE_OPPORTUNITY",
            entity_type="Opportunity",
            entity_id=str(opp.id),
            user_id=current_user_id,
            new_data={
                "opportunity_code": opp.opportunity_code,
                "title": opp.title,
                "expected_revenue": str(opp.expected_revenue),
                "stage": stage.name,
                "status": opp.status,
            },
        )

        await db.commit()
        await db.refresh(opp)

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
            raise NotFoundException(f"Opportunity ID '{opp_id}' not found.")

        if opp.status in ["Won", "Lost"] and (opp_in.status is None or opp_in.status == opp.status):
            # If changing stage or fields on a closed opportunity without reopening
            if opp_in.stage_id or opp_in.stage_code:
                raise ValidationException(f"Cannot change stage of opportunity in terminal '{opp.status}' status.")

        prev_data = {
            "title": opp.title,
            "expected_revenue": str(opp.expected_revenue),
            "status": opp.status,
            "stage_id": str(opp.stage_id),
        }

        update_data = opp_in.model_dump(exclude_unset=True)
        new_stage_id = update_data.pop("stage_id", None)
        new_stage_code = update_data.pop("stage_code", None)

        if new_stage_id or new_stage_code:
            stage = await self._resolve_stage(db, stage_id=new_stage_id, stage_code=new_stage_code)
            opp.stage_id = stage.id
            if opp_in.probability is None:
                opp.probability = stage.probability_default
            if stage.code.upper() == "WON":
                opp.status = "Won"
                opp.probability = Decimal("100.00")
            elif stage.code.upper() == "LOST":
                opp.status = "Lost"
                opp.probability = Decimal("0.00")
            else:
                opp.status = "Open"

        for field, val in update_data.items():
            setattr(opp, field, val)

        # AuditLog
        await audit_log_service.log_event(
            db,
            action="UPDATE_OPPORTUNITY",
            entity_type="Opportunity",
            entity_id=str(opp.id),
            user_id=current_user_id,
            previous_data=prev_data,
            new_data={
                "title": opp.title,
                "expected_revenue": str(opp.expected_revenue),
                "status": opp.status,
                "stage_id": str(opp.stage_id),
            },
        )

        await db.commit()
        await db.refresh(opp)
        return opp

    async def change_stage(self, db: AsyncSession, opp_id: uuid.UUID, req: OpportunityStageChangeRequest, current_user_id: Optional[uuid.UUID] = None) -> Opportunity:
        opp = await self.opp_repo.get_by_id(db, opp_id)
        if not opp:
            raise NotFoundException(f"Opportunity ID '{opp_id}' not found.")

        if opp.status in ["Won", "Lost"]:
            raise ValidationException(f"Cannot change stage of opportunity in terminal '{opp.status}' status.")

        stage = await self._resolve_stage(db, stage_id=req.stage_id, stage_code=req.stage_code)
        
        prev_stage_id = str(opp.stage_id)
        opp.stage_id = stage.id
        opp.probability = stage.probability_default

        stage_code_upper = stage.code.upper()
        if stage_code_upper == "WON":
            opp.status = "Won"
            opp.probability = Decimal("100.00")
            event_name = CRM_OPPORTUNITY_WON
        elif stage_code_upper == "LOST":
            opp.status = "Lost"
            opp.probability = Decimal("0.00")
            event_name = CRM_OPPORTUNITY_LOST
        else:
            opp.status = "Open"
            event_name = None

        # AuditLog
        await audit_log_service.log_event(
            db,
            action="CHANGE_OPPORTUNITY_STAGE",
            entity_type="Opportunity",
            entity_id=str(opp.id),
            user_id=current_user_id,
            previous_data={"stage_id": prev_stage_id},
            new_data={"stage_id": str(stage.id), "stage_name": stage.name, "status": opp.status},
        )

        await db.commit()
        await db.refresh(opp)

        if event_name:
            domain_event_publisher.publish(
                event_name,
                {"opportunity_id": str(opp.id), "status": opp.status},
            )

        return opp

    async def record_win_loss(self, db: AsyncSession, opp_id: uuid.UUID, status: str, reason: Optional[str] = None, current_user_id: Optional[uuid.UUID] = None) -> Opportunity:
        opp = await self.opp_repo.get_by_id(db, opp_id)
        if not opp:
            raise NotFoundException(f"Opportunity ID '{opp_id}' not found.")

        norm_status = status.strip().capitalize()
        if norm_status == "Won":
            opp.status = "Won"
            opp.won_reason = reason
            opp.probability = Decimal("100.00")
            won_stage = await self.stage_repo.get_by_code(db, "WON")
            if won_stage:
                opp.stage_id = won_stage.id
            event_name = CRM_OPPORTUNITY_WON
        elif norm_status == "Lost":
            opp.status = "Lost"
            opp.lost_reason = reason
            opp.probability = Decimal("0.00")
            lost_stage = await self.stage_repo.get_by_code(db, "LOST")
            if lost_stage:
                opp.stage_id = lost_stage.id
            event_name = CRM_OPPORTUNITY_LOST
        else:
            raise ValidationException("Status must be 'Won' or 'Lost'.")

        # AuditLog
        await audit_log_service.log_event(
            db,
            action="RECORD_OPPORTUNITY_WIN_LOSS",
            entity_type="Opportunity",
            entity_id=str(opp.id),
            user_id=current_user_id,
            new_data={"status": opp.status, "reason": reason, "probability": str(opp.probability)},
        )

        await db.commit()
        await db.refresh(opp)

        domain_event_publisher.publish(
            event_name,
            {"opportunity_id": str(opp.id), "status": opp.status, "reason": reason},
        )
        return opp

    async def delete_opportunity(self, db: AsyncSession, opp_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None) -> bool:
        opp = await self.opp_repo.get_by_id(db, opp_id)
        if not opp:
            raise NotFoundException(f"Opportunity ID '{opp_id}' not found.")

        await self.opp_repo.delete(db, opp_id)

        # AuditLog
        await audit_log_service.log_event(
            db,
            action="DELETE_OPPORTUNITY",
            entity_type="Opportunity",
            entity_id=str(opp_id),
            user_id=current_user_id,
            previous_data={"opportunity_code": opp.opportunity_code, "title": opp.title},
        )
        return True


class LeadConversionService:
    def __init__(self):
        self.lead_repo = lead_repository
        self.opp_service = OpportunityService()
        self.stage_repo = opportunity_stage_repository
        self.customer_repo = customer_repository
        self.customer_service = customer_service

    async def convert_lead(self, db: AsyncSession, req: LeadConversionRequest, current_user_id: Optional[uuid.UUID] = None) -> LeadConversionResponse:
        if not req.lead_id:
            raise ValidationException("Lead ID is required for conversion.")

        # Concurrency Lock
        lead = await self.lead_repo.get_for_update(db, req.lead_id)
        if not lead:
            raise NotFoundException(f"Lead ID '{req.lead_id}' not found.")

        # Check duplicate conversion rule
        if lead.is_converted or lead.status.upper() == "CONVERTED":
            raise ValidationException("Lead has already been converted.")

        # Check qualification rule
        if lead.status.upper() != "QUALIFIED":
            raise ValidationException(
                f"Only QUALIFIED leads can be converted. Current lead status is '{lead.status}'."
            )

        # 1. Canonical Customer Resolution (Prevent Duplicates)
        target_customer: Optional[Customer] = None
        is_existing_customer = False

        if req.existing_customer_id:
            target_customer = await self.customer_repo.get_by_id(db, req.existing_customer_id)
            if not target_customer:
                raise NotFoundException(f"Customer ID '{req.existing_customer_id}' not found.")
            is_existing_customer = True
        else:
            # Search existing customer by email
            if lead.email:
                existing_by_email, _ = await self.customer_repo.search_customers(db, query=lead.email, limit=1)
                if existing_by_email:
                    target_customer = existing_by_email[0]
                    is_existing_customer = True

            # Search existing customer by phone if not found by email
            if not target_customer and lead.phone:
                existing_by_phone, _ = await self.customer_repo.search_customers(db, query=lead.phone, limit=1)
                if existing_by_phone:
                    target_customer = existing_by_phone[0]
                    is_existing_customer = True

        # If still no customer, create a new canonical Customer master record
        if not target_customer:
            year = datetime.now(timezone.utc).year
            prefix = f"CUST-{year}-"
            max_suffix = await self.customer_repo.get_max_number_suffix(db, prefix=prefix)
            cust_code = f"{prefix}{max_suffix + 1:05d}"
            
            cust_name = (lead.company or f"{lead.first_name} {lead.last_name or ''}".strip())
            cust_in = CustomerCreate(
                customer_code=cust_code,
                name=cust_name,
                email=lead.email,
                phone=lead.phone,
                contacts=[
                    CustomerContactCreate(
                        contact_person=f"{lead.first_name} {lead.last_name or ''}".strip(),
                        email=lead.email,
                        phone=lead.phone,
                        designation=lead.title or "Primary Contact",
                        is_primary=True,
                    )
                ] if lead.first_name else [],
            )
            target_customer = await self.customer_service.create_customer(db, cust_in, current_user_id=current_user_id)
            is_existing_customer = False

        # 2. Opportunity Creation (when requested)
        opp: Optional[Opportunity] = None
        if req.create_opportunity:
            stage_id = req.stage_id
            if not stage_id:
                stage = await self.opp_service._resolve_stage(db, stage_code=req.stage_code or "QUALIFICATION")
                stage_id = stage.id

            opp_in = OpportunityCreate(
                title=req.opportunity_title or f"Opportunity for {lead.company or lead.first_name}",
                customer_id=target_customer.id,
                lead_id=lead.id,
                stage_id=stage_id,
                expected_revenue=req.expected_revenue if req.expected_revenue is not None else lead.estimated_value,
            )
            opp = await self.opp_service.create_opportunity(db, opp_in, current_user_id=current_user_id)

        # 3. Mark Lead as Converted
        now = datetime.now(timezone.utc)
        lead.is_converted = True
        lead.status = "CONVERTED"
        lead.converted_at = now
        lead.converted_customer_id = target_customer.id
        lead.converted_opportunity_id = opp.id if opp else None

        # AuditLog
        await audit_log_service.log_event(
            db,
            action="CONVERT_LEAD",
            entity_type="Lead",
            entity_id=str(lead.id),
            user_id=current_user_id,
            new_data={
                "customer_id": str(target_customer.id),
                "is_existing_customer": is_existing_customer,
                "opportunity_id": str(opp.id) if opp else None,
                "converted_at": now.isoformat(),
            },
        )

        await db.commit()
        await db.refresh(lead)

        # Publish Event
        domain_event_publisher.publish(
            CRM_LEAD_CONVERTED,
            {
                "lead_id": str(lead.id),
                "opportunity_id": str(opp.id) if opp else None,
                "customer_id": str(target_customer.id),
                "is_existing_customer": is_existing_customer,
            },
        )

        return LeadConversionResponse(
            lead_id=lead.id,
            opportunity_id=opp.id if opp else None,
            customer_id=target_customer.id,
            is_existing_customer=is_existing_customer,
            converted_at=now,
        )


class ActivityService:
    def __init__(self):
        self.act_repo = activity_repository

    async def create_activity(self, db: AsyncSession, act_in: ActivityCreate, current_user_id: Optional[uuid.UUID] = None) -> Activity:
        activity = Activity(
            activity_type=act_in.activity_type.capitalize() if act_in.activity_type else "Call",
            subject=act_in.subject,
            description=act_in.description,
            status=act_in.status or "Pending",
            priority=act_in.priority or "Medium",
            due_date=act_in.due_date or act_in.activity_date,
            owner_id=act_in.owner_id or current_user_id,
            lead_id=act_in.lead_id,
            opportunity_id=act_in.opportunity_id,
            customer_id=act_in.customer_id,
            campaign_id=act_in.campaign_id,
            is_recurring=act_in.is_recurring,
            recurrence_rule=act_in.recurrence_rule,
        )
        db.add(activity)
        await db.flush()

        # AuditLog
        await audit_log_service.log_event(
            db,
            action="CREATE_ACTIVITY",
            entity_type="Activity",
            entity_id=str(activity.id),
            user_id=current_user_id,
            new_data={
                "activity_type": activity.activity_type,
                "subject": activity.subject,
                "status": activity.status,
            },
        )

        await db.commit()
        await db.refresh(activity)
        return activity

    async def update_activity(self, db: AsyncSession, activity_id: uuid.UUID, act_in: ActivityUpdate, current_user_id: Optional[uuid.UUID] = None) -> Activity:
        activity = await self.act_repo.get_by_id(db, activity_id)
        if not activity:
            raise NotFoundException(f"Activity ID '{activity_id}' not found.")

        prev_data = {"subject": activity.subject, "status": activity.status}
        update_data = act_in.model_dump(exclude_unset=True)
        if "activity_type" in update_data and update_data["activity_type"]:
            update_data["activity_type"] = update_data["activity_type"].capitalize()

        for field, val in update_data.items():
            setattr(activity, field, val)

        # AuditLog
        await audit_log_service.log_event(
            db,
            action="UPDATE_ACTIVITY",
            entity_type="Activity",
            entity_id=str(activity.id),
            user_id=current_user_id,
            previous_data=prev_data,
            new_data={"subject": activity.subject, "status": activity.status},
        )

        await db.commit()
        await db.refresh(activity)
        return activity

    async def complete_activity(self, db: AsyncSession, activity_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None) -> Activity:
        activity = await self.act_repo.get_by_id(db, activity_id)
        if not activity:
            raise NotFoundException(f"Activity ID '{activity_id}' not found.")

        activity.status = "Completed"
        activity.completed_at = datetime.now(timezone.utc)

        # AuditLog
        await audit_log_service.log_event(
            db,
            action="COMPLETE_ACTIVITY",
            entity_type="Activity",
            entity_id=str(activity.id),
            user_id=current_user_id,
            new_data={"status": "Completed", "completed_at": activity.completed_at.isoformat()},
        )

        await db.commit()
        await db.refresh(activity)
        return activity

    async def delete_activity(self, db: AsyncSession, activity_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None) -> bool:
        activity = await self.act_repo.get_by_id(db, activity_id)
        if not activity:
            raise NotFoundException(f"Activity ID '{activity_id}' not found.")

        await self.act_repo.delete(db, activity_id)

        # AuditLog
        await audit_log_service.log_event(
            db,
            action="DELETE_ACTIVITY",
            entity_type="Activity",
            entity_id=str(activity_id),
            user_id=current_user_id,
            previous_data={"subject": activity.subject, "activity_type": activity.activity_type},
        )
        return True


class MeetingService:
    def __init__(self):
        self.meeting_repo = meeting_repository

    async def schedule_meeting(self, db: AsyncSession, meeting_in: MeetingCreate, organizer_id: Optional[uuid.UUID] = None) -> Meeting:
        meeting = Meeting(
            subject=meeting_in.subject,
            meeting_type=meeting_in.meeting_type,
            start_time=meeting_in.start_time,
            end_time=meeting_in.end_time,
            location=meeting_in.location,
            meeting_link=meeting_in.meeting_link,
            status=meeting_in.status,
            organizer_id=meeting_in.organizer_id or organizer_id,
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
            {"meeting_id": str(meeting.id), "start_time": meeting.start_time.isoformat()},
        )
        return meeting


class TaskService:
    def __init__(self):
        self.task_repo = task_repository

    async def create_task(self, db: AsyncSession, task_in: TaskCreate, created_by_id: Optional[uuid.UUID] = None) -> Task:
        task_code = f"TASK-{uuid.uuid4().hex[:8].upper()}"
        task = Task(
            task_code=task_code,
            title=task_in.title,
            description=task_in.description,
            status=task_in.status,
            priority=task_in.priority,
            due_date=task_in.due_date,
            assigned_to_id=task_in.assigned_to_id,
            created_by_id=created_by_id,
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


class CampaignService:
    def __init__(self):
        self.campaign_repo = campaign_repository
        self.member_repo = campaign_member_repository

    async def create_campaign(self, db: AsyncSession, camp_in: CampaignCreate, owner_id: Optional[uuid.UUID] = None) -> Campaign:
        camp_code = f"CAMP-{uuid.uuid4().hex[:8].upper()}"
        camp = Campaign(
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
            owner_id=camp_in.owner_id or owner_id,
        )
        db.add(camp)
        await db.commit()
        await db.refresh(camp)
        return camp


class CRMAnalyticsService:
    def __init__(self):
        self.lead_repo = lead_repository
        self.opp_repo = opportunity_repository
        self.campaign_repo = campaign_repository

    async def get_summary_analytics(self, db: AsyncSession) -> CRMAnalyticsSummary:
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
        self.lead_repo = lead_repository
        self.opp_repo = opportunity_repository
        self.task_repo = task_repository
        self.act_repo = activity_repository

    async def search_crm(self, db: AsyncSession, query: str) -> CRMSearchResult:
        leads, _ = await self.lead_repo.search_leads(db, query=query, limit=10)
        opps, _ = await self.opp_repo.search_opportunities(db, query=query, limit=10)
        tasks, _ = await self.task_repo.search_tasks(db, query=query, limit=10)
        acts, _ = await self.act_repo.search_activities(db, query=query, limit=10)

        return CRMSearchResult(
            leads=list(leads),
            opportunities=list(opps),
            tasks=list(tasks),
            activities=list(acts),
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


# Singleton service instances
lead_service = LeadService()
opportunity_service = OpportunityService()
lead_conversion_service = LeadConversionService()
activity_service = ActivityService()
meeting_service = MeetingService()
task_service = TaskService()
campaign_service = CampaignService()
crm_analytics_service = CRMAnalyticsService()
crm_search_service = CRMSearchService()
crm_import_export_service = CRMImportExportService()
