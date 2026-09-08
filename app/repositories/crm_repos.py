from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import Any, List, Optional, Tuple
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.crm import (
    LeadSource,
    LeadTag,
    Lead,
    LeadNote,
    OpportunityStage,
    Opportunity,
    Activity,
    Meeting,
    Task,
    Campaign,
    CampaignMember,
    CRMReportSnapshot,
    TimelineEvent,
)
from app.repositories.base_repository import BaseRepository


class LeadSourceRepository(BaseRepository[LeadSource, Any, Any]):
    def __init__(self):
        super().__init__(LeadSource)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[LeadSource]:
        stmt = select(LeadSource).where(LeadSource.code == code)
        res = await db.execute(stmt)
        return res.scalars().first()


class LeadTagRepository(BaseRepository[LeadTag, Any, Any]):
    def __init__(self):
        super().__init__(LeadTag)

    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[LeadTag]:
        stmt = select(LeadTag).where(LeadTag.name == name)
        res = await db.execute(stmt)
        return res.scalars().first()


class LeadRepository(BaseRepository[Lead, Any, Any]):
    def __init__(self):
        super().__init__(Lead)

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[Lead]:
        stmt = select(Lead).where(Lead.id == id, Lead.is_deleted.is_(False)).options(
            selectinload(Lead.source),
            selectinload(Lead.tags),
            selectinload(Lead.notes),
            selectinload(Lead.assigned_to),
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_for_update(self, db: AsyncSession, id: uuid.UUID) -> Optional[Lead]:
        stmt = (
            select(Lead)
            .options(
                selectinload(Lead.source),
                selectinload(Lead.tags),
                selectinload(Lead.notes),
                selectinload(Lead.assigned_to),
            )
            .where(Lead.id == id, Lead.is_deleted.is_(False))
            .with_for_update()
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_code(self, db: AsyncSession, lead_code: str) -> Optional[Lead]:
        stmt = select(Lead).where(Lead.lead_code == lead_code, Lead.is_deleted.is_(False)).options(
            selectinload(Lead.source),
            selectinload(Lead.tags),
            selectinload(Lead.notes),
            selectinload(Lead.assigned_to),
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_max_number_suffix(self, db: AsyncSession, prefix: str = "LEAD-") -> int:
        stmt = select(Lead.lead_code).where(Lead.lead_code.like(f"{prefix}%"))
        res = await db.execute(stmt)
        codes = res.scalars().all()
        max_num = 0
        for code_str in codes:
            suffix = code_str[len(prefix):]
            if suffix.isdigit():
                val = int(suffix)
                if val > max_num:
                    max_num = val
        return max_num

    async def find_duplicates(
        self, db: AsyncSession, email: Optional[str] = None, phone: Optional[str] = None, exclude_id: Optional[uuid.UUID] = None
    ) -> List[Lead]:
        if not email and not phone:
            return []
        conds = []
        if email:
            conds.append(Lead.email.ilike(email))
        if phone:
            conds.append(Lead.phone == phone)
        stmt = select(Lead).where(and_(Lead.is_deleted.is_(False), or_(*conds)))
        if exclude_id:
            stmt = stmt.where(Lead.id != exclude_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def search_leads(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        status: Optional[str] = None,
        assigned_to_id: Optional[uuid.UUID] = None,
        is_converted: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Lead], int]:
        filters = [Lead.is_deleted.is_(False)]
        if status:
            filters.append(Lead.status.ilike(status))
        if assigned_to_id:
            filters.append(Lead.assigned_to_id == assigned_to_id)
        if is_converted is not None:
            filters.append(Lead.is_converted.is_(is_converted))
        if query:
            q = f"%{query}%"
            filters.append(
                or_(
                    Lead.first_name.ilike(q),
                    Lead.last_name.ilike(q),
                    Lead.company.ilike(q),
                    Lead.email.ilike(q),
                    Lead.phone.ilike(q),
                    Lead.lead_code.ilike(q),
                )
            )

        count_stmt = select(func.count(Lead.id)).where(and_(*filters))
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Lead)
            .options(
                selectinload(Lead.source),
                selectinload(Lead.tags),
                selectinload(Lead.notes),
                selectinload(Lead.assigned_to),
            )
            .where(and_(*filters))
            .order_by(Lead.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all()), total

    async def delete(self, db: AsyncSession, id: uuid.UUID) -> bool:
        lead = await self.get_by_id(db, id)
        if not lead:
            return False
        lead.is_deleted = True
        lead.deleted_at = datetime.now(timezone.utc)
        await db.commit()
        return True


class LeadNoteRepository(BaseRepository[LeadNote, Any, Any]):
    def __init__(self):
        super().__init__(LeadNote)

    async def get_by_lead_id(self, db: AsyncSession, lead_id: uuid.UUID) -> List[LeadNote]:
        stmt = (
            select(LeadNote)
            .where(LeadNote.lead_id == lead_id)
            .order_by(LeadNote.is_pinned.desc(), LeadNote.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


class OpportunityStageRepository(BaseRepository[OpportunityStage, Any, Any]):
    def __init__(self):
        super().__init__(OpportunityStage)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[OpportunityStage]:
        stmt = select(OpportunityStage).where(OpportunityStage.code.ilike(code))
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_all_ordered(self, db: AsyncSession) -> List[OpportunityStage]:
        prospecting = await self.get_by_code(db, "PROSPECTING")
        if not prospecting:
            # Seed standard pipeline stages
            default_stages = [
                OpportunityStage(code="PROSPECTING", name="Prospecting", probability_default=Decimal("10.00"), display_order=1),
                OpportunityStage(code="QUALIFICATION", name="Qualification", probability_default=Decimal("30.00"), display_order=2),
                OpportunityStage(code="PROPOSAL", name="Proposal", probability_default=Decimal("60.00"), display_order=3),
                OpportunityStage(code="NEGOTIATION", name="Negotiation", probability_default=Decimal("80.00"), display_order=4),
                OpportunityStage(code="WON", name="Won", probability_default=Decimal("100.00"), display_order=5),
                OpportunityStage(code="LOST", name="Lost", probability_default=Decimal("0.00"), display_order=6),
            ]
            db.add_all(default_stages)
            await db.commit()
            for s in default_stages:
                await db.refresh(s)
        stmt = (
            select(OpportunityStage)
            .where(OpportunityStage.is_active.is_(True))
            .order_by(OpportunityStage.display_order.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


class OpportunityRepository(BaseRepository[Opportunity, Any, Any]):
    def __init__(self):
        super().__init__(Opportunity)

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[Opportunity]:
        stmt = select(Opportunity).where(Opportunity.id == id, Opportunity.is_deleted.is_(False)).options(
            selectinload(Opportunity.stage),
            selectinload(Opportunity.customer),
            selectinload(Opportunity.lead),
            selectinload(Opportunity.owner),
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_for_update(self, db: AsyncSession, id: uuid.UUID) -> Optional[Opportunity]:
        stmt = (
            select(Opportunity)
            .options(
                selectinload(Opportunity.stage),
                selectinload(Opportunity.customer),
                selectinload(Opportunity.lead),
                selectinload(Opportunity.owner),
            )
            .where(Opportunity.id == id, Opportunity.is_deleted.is_(False))
            .with_for_update()
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[Opportunity]:
        stmt = select(Opportunity).where(Opportunity.opportunity_code == code, Opportunity.is_deleted.is_(False)).options(
            selectinload(Opportunity.stage),
            selectinload(Opportunity.customer),
            selectinload(Opportunity.lead),
            selectinload(Opportunity.owner),
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_max_number_suffix(self, db: AsyncSession, prefix: str = "OPP-") -> int:
        stmt = select(Opportunity.opportunity_code).where(Opportunity.opportunity_code.like(f"{prefix}%"))
        res = await db.execute(stmt)
        codes = res.scalars().all()
        max_num = 0
        for code_str in codes:
            suffix = code_str[len(prefix):]
            if suffix.isdigit():
                val = int(suffix)
                if val > max_num:
                    max_num = val
        return max_num

    async def search_opportunities(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        stage_id: Optional[uuid.UUID] = None,
        customer_id: Optional[uuid.UUID] = None,
        lead_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        owner_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Opportunity], int]:
        filters = [Opportunity.is_deleted.is_(False)]
        if stage_id:
            filters.append(Opportunity.stage_id == stage_id)
        if customer_id:
            filters.append(Opportunity.customer_id == customer_id)
        if lead_id:
            filters.append(Opportunity.lead_id == lead_id)
        if status:
            filters.append(Opportunity.status.ilike(status))
        if owner_id:
            filters.append(Opportunity.owner_id == owner_id)
        if query:
            q = f"%{query}%"
            filters.append(or_(Opportunity.title.ilike(q), Opportunity.opportunity_code.ilike(q)))

        count_stmt = select(func.count(Opportunity.id)).where(and_(*filters))
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Opportunity)
            .options(
                selectinload(Opportunity.stage),
                selectinload(Opportunity.customer),
                selectinload(Opportunity.lead),
                selectinload(Opportunity.owner),
            )
            .where(and_(*filters))
            .order_by(Opportunity.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all()), total

    async def delete(self, db: AsyncSession, id: uuid.UUID) -> bool:
        opp = await self.get_by_id(db, id)
        if not opp:
            return False
        opp.is_deleted = True
        opp.deleted_at = datetime.now(timezone.utc)
        await db.commit()
        return True


class ActivityRepository(BaseRepository[Activity, Any, Any]):
    def __init__(self):
        super().__init__(Activity)

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[Activity]:
        stmt = select(Activity).where(Activity.id == id).options(selectinload(Activity.owner))
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_by_entity(
        self,
        db: AsyncSession,
        lead_id: Optional[uuid.UUID] = None,
        opportunity_id: Optional[uuid.UUID] = None,
        customer_id: Optional[uuid.UUID] = None,
        campaign_id: Optional[uuid.UUID] = None,
    ) -> List[Activity]:
        filters = []
        if lead_id:
            filters.append(Activity.lead_id == lead_id)
        if opportunity_id:
            filters.append(Activity.opportunity_id == opportunity_id)
        if customer_id:
            filters.append(Activity.customer_id == customer_id)
        if campaign_id:
            filters.append(Activity.campaign_id == campaign_id)

        stmt = select(Activity).options(selectinload(Activity.owner)).order_by(Activity.due_date.desc().nulls_last(), Activity.created_at.desc())
        if filters:
            stmt = stmt.where(or_(*filters))
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def search_activities(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        activity_type: Optional[str] = None,
        status: Optional[str] = None,
        owner_id: Optional[uuid.UUID] = None,
        lead_id: Optional[uuid.UUID] = None,
        opportunity_id: Optional[uuid.UUID] = None,
        customer_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Activity], int]:
        filters = []
        if activity_type:
            filters.append(Activity.activity_type.ilike(activity_type))
        if status:
            filters.append(Activity.status.ilike(status))
        if owner_id:
            filters.append(Activity.owner_id == owner_id)
        if lead_id:
            filters.append(Activity.lead_id == lead_id)
        if opportunity_id:
            filters.append(Activity.opportunity_id == opportunity_id)
        if customer_id:
            filters.append(Activity.customer_id == customer_id)
        if query:
            q = f"%{query}%"
            filters.append(or_(Activity.subject.ilike(q), Activity.description.ilike(q)))

        count_stmt = select(func.count(Activity.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Activity)
            .options(selectinload(Activity.owner))
            .order_by(Activity.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if filters:
            stmt = stmt.where(and_(*filters))
        res = await db.execute(stmt)
        return list(res.scalars().all()), total

    async def delete(self, db: AsyncSession, id: uuid.UUID) -> bool:
        activity = await self.get_by_id(db, id)
        if not activity:
            return False
        await db.delete(activity)
        await db.commit()
        return True


class MeetingRepository(BaseRepository[Meeting, Any, Any]):
    def __init__(self):
        super().__init__(Meeting)

    async def get_by_entity_or_date(
        self,
        db: AsyncSession,
        lead_id: Optional[uuid.UUID] = None,
        opportunity_id: Optional[uuid.UUID] = None,
        customer_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Meeting]:
        filters = []
        if lead_id:
            filters.append(Meeting.lead_id == lead_id)
        if opportunity_id:
            filters.append(Meeting.opportunity_id == opportunity_id)
        if customer_id:
            filters.append(Meeting.customer_id == customer_id)
        if start_date:
            filters.append(Meeting.start_time >= start_date)
        if end_date:
            filters.append(Meeting.start_time <= end_date)

        stmt = select(Meeting).order_by(Meeting.start_time.asc())
        if filters:
            stmt = stmt.where(and_(*filters))
        res = await db.execute(stmt)
        return list(res.scalars().all())


class TaskRepository(BaseRepository[Task, Any, Any]):
    def __init__(self):
        super().__init__(Task)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[Task]:
        stmt = select(Task).where(Task.task_code == code)
        res = await db.execute(stmt)
        return res.scalars().first()

    async def search_tasks(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        assigned_to_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Task], int]:
        filters = []
        if assigned_to_id:
            filters.append(Task.assigned_to_id == assigned_to_id)
        if status:
            filters.append(Task.status == status)
        if priority:
            filters.append(Task.priority == priority)
        if query:
            q = f"%{query}%"
            filters.append(or_(Task.title.ilike(q), Task.task_code.ilike(q)))

        count_stmt = select(func.count(Task.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = select(Task).order_by(Task.due_date.asc().nulls_last()).offset(skip).limit(limit)
        if filters:
            stmt = stmt.where(and_(*filters))
        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class CampaignRepository(BaseRepository[Campaign, Any, Any]):
    def __init__(self):
        super().__init__(Campaign)

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[Campaign]:
        stmt = select(Campaign).where(Campaign.id == id).options(selectinload(Campaign.members))
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[Campaign]:
        stmt = select(Campaign).where(Campaign.campaign_code == code).options(selectinload(Campaign.members))
        res = await db.execute(stmt)
        return res.scalars().first()

    async def search_campaigns(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        status: Optional[str] = None,
        type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Campaign], int]:
        filters = []
        if status:
            filters.append(Campaign.status == status)
        if type:
            filters.append(Campaign.type == type)
        if query:
            q = f"%{query}%"
            filters.append(or_(Campaign.name.ilike(q), Campaign.campaign_code.ilike(q)))

        count_stmt = select(func.count(Campaign.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = select(Campaign).options(selectinload(Campaign.members)).order_by(Campaign.created_at.desc()).offset(skip).limit(limit)
        if filters:
            stmt = stmt.where(and_(*filters))
        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class CampaignMemberRepository(BaseRepository[CampaignMember, Any, Any]):
    def __init__(self):
        super().__init__(CampaignMember)

    async def get_by_campaign(self, db: AsyncSession, campaign_id: uuid.UUID) -> List[CampaignMember]:
        stmt = select(CampaignMember).where(CampaignMember.campaign_id == campaign_id).options(
            selectinload(CampaignMember.lead), selectinload(CampaignMember.customer)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


class CRMReportSnapshotRepository(BaseRepository[CRMReportSnapshot, Any, Any]):
    def __init__(self):
        super().__init__(CRMReportSnapshot)

    async def get_latest(self, db: AsyncSession) -> Optional[CRMReportSnapshot]:
        stmt = select(CRMReportSnapshot).order_by(CRMReportSnapshot.snapshot_date.desc())
        res = await db.execute(stmt)
        return res.scalars().first()


class TimelineEventRepository(BaseRepository[TimelineEvent, Any, Any]):
    def __init__(self):
        super().__init__(TimelineEvent)

    async def get_by_entity(self, db: AsyncSession, entity_type: str, entity_id: uuid.UUID) -> List[TimelineEvent]:
        stmt = select(TimelineEvent).where(
            and_(TimelineEvent.entity_type == entity_type, TimelineEvent.entity_id == entity_id)
        ).order_by(TimelineEvent.timestamp.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())


# Singleton instances
lead_source_repository = LeadSourceRepository()
lead_tag_repository = LeadTagRepository()
lead_repository = LeadRepository()
lead_note_repository = LeadNoteRepository()
opportunity_stage_repository = OpportunityStageRepository()
opportunity_repository = OpportunityRepository()
activity_repository = ActivityRepository()
meeting_repository = MeetingRepository()
task_repository = TaskRepository()
campaign_repository = CampaignRepository()
campaign_member_repository = CampaignMemberRepository()
crm_report_snapshot_repository = CRMReportSnapshotRepository()
timeline_event_repository = TimelineEventRepository()
