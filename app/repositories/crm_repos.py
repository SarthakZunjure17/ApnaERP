from datetime import datetime
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
        stmt = select(Lead).where(Lead.id == id).options(
            selectinload(Lead.source),
            selectinload(Lead.tags),
            selectinload(Lead.notes),
            selectinload(Lead.assigned_to),
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_by_code(self, db: AsyncSession, lead_code: str) -> Optional[Lead]:
        stmt = select(Lead).where(Lead.lead_code == lead_code).options(
            selectinload(Lead.source),
            selectinload(Lead.tags),
            selectinload(Lead.notes),
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    async def find_duplicates(
        self, db: AsyncSession, email: Optional[str] = None, phone: Optional[str] = None
    ) -> List[Lead]:
        if not email and not phone:
            return []
        conds = []
        if email:
            conds.append(Lead.email.ilike(email))
        if phone:
            conds.append(Lead.phone == phone)
        stmt = select(Lead).where(or_(*conds))
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
        filters = []
        if status:
            filters.append(Lead.status == status)
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

        count_stmt = select(func.count(Lead.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = select(Lead).options(
            selectinload(Lead.source),
            selectinload(Lead.tags),
            selectinload(Lead.notes),
        ).order_by(Lead.created_at.desc()).offset(skip).limit(limit)
        if filters:
            stmt = stmt.where(and_(*filters))

        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class LeadNoteRepository(BaseRepository[LeadNote, Any, Any]):
    def __init__(self):
        super().__init__(LeadNote)

    async def get_by_lead_id(self, db: AsyncSession, lead_id: uuid.UUID) -> List[LeadNote]:
        stmt = select(LeadNote).where(LeadNote.lead_id == lead_id).order_by(LeadNote.is_pinned.desc(), LeadNote.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())


class OpportunityStageRepository(BaseRepository[OpportunityStage, Any, Any]):
    def __init__(self):
        super().__init__(OpportunityStage)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[OpportunityStage]:
        stmt = select(OpportunityStage).where(OpportunityStage.code == code)
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_all_ordered(self, db: AsyncSession) -> List[OpportunityStage]:
        stmt = select(OpportunityStage).where(OpportunityStage.is_active.is_(True)).order_by(OpportunityStage.display_order.asc())
        res = await db.execute(stmt)
        return list(res.scalars().all())


class OpportunityRepository(BaseRepository[Opportunity, Any, Any]):
    def __init__(self):
        super().__init__(Opportunity)

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[Opportunity]:
        stmt = select(Opportunity).where(Opportunity.id == id).options(
            selectinload(Opportunity.stage),
            selectinload(Opportunity.customer),
            selectinload(Opportunity.lead),
            selectinload(Opportunity.owner),
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[Opportunity]:
        stmt = select(Opportunity).where(Opportunity.opportunity_code == code).options(
            selectinload(Opportunity.stage),
            selectinload(Opportunity.customer),
            selectinload(Opportunity.lead),
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    async def search_opportunities(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        stage_id: Optional[uuid.UUID] = None,
        customer_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        owner_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Opportunity], int]:
        filters = []
        if stage_id:
            filters.append(Opportunity.stage_id == stage_id)
        if customer_id:
            filters.append(Opportunity.customer_id == customer_id)
        if status:
            filters.append(Opportunity.status == status)
        if owner_id:
            filters.append(Opportunity.owner_id == owner_id)
        if query:
            q = f"%{query}%"
            filters.append(or_(Opportunity.title.ilike(q), Opportunity.opportunity_code.ilike(q)))

        count_stmt = select(func.count(Opportunity.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = select(Opportunity).options(
            selectinload(Opportunity.stage),
            selectinload(Opportunity.customer),
            selectinload(Opportunity.lead),
        ).order_by(Opportunity.created_at.desc()).offset(skip).limit(limit)
        if filters:
            stmt = stmt.where(and_(*filters))

        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class ActivityRepository(BaseRepository[Activity, Any, Any]):
    def __init__(self):
        super().__init__(Activity)

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

        stmt = select(Activity).order_by(Activity.due_date.desc())
        if filters:
            stmt = stmt.where(or_(*filters))
        res = await db.execute(stmt)
        return list(res.scalars().all())


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
