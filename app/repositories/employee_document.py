import datetime
from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee_document import EmployeeDocument
from app.repositories.base_repository import BaseRepository
from app.schemas.employee_document import EmployeeDocumentCreate, EmployeeDocumentUpdate


class EmployeeDocumentRepository(BaseRepository[EmployeeDocument, EmployeeDocumentCreate, EmployeeDocumentUpdate]):
    """
    Repository handling database queries for EmployeeDocument model.
    """
    def __init__(self):
        super().__init__(EmployeeDocument)

    async def get_by_employee(self, db: AsyncSession, employee_id: uuid.UUID) -> List[EmployeeDocument]:
        """Retrieves active non-deleted documents for a given employee."""
        stmt = (
            select(EmployeeDocument)
            .where(EmployeeDocument.employee_id == employee_id, EmployeeDocument.is_deleted == False)
            .order_by(EmployeeDocument.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_by_file(self, db: AsyncSession, file_id: uuid.UUID) -> Optional[EmployeeDocument]:
        """Retrieves document linked to a specific File ID."""
        stmt = select(EmployeeDocument).where(EmployeeDocument.file_id == file_id, EmployeeDocument.is_deleted == False)
        res = await db.execute(stmt)
        return res.scalars().first()

    async def exists_mandatory_document_type(
        self, db: AsyncSession, employee_id: uuid.UUID, document_type: str, exclude_id: Optional[uuid.UUID] = None
    ) -> bool:
        """Checks if active mandatory document of same type already exists for employee."""
        stmt = select(EmployeeDocument).where(
            EmployeeDocument.employee_id == employee_id,
            EmployeeDocument.document_type == document_type,
            EmployeeDocument.is_mandatory == True,  # noqa: E712
            EmployeeDocument.is_deleted == False,   # noqa: E712
        )
        if exclude_id:
            stmt = stmt.where(EmployeeDocument.id != exclude_id)
        res = await db.execute(stmt)
        return res.scalars().first() is not None

    async def get_expiring_documents(self, db: AsyncSession, within_days: int = 30) -> List[EmployeeDocument]:
        """Queries documents expiring within specified days framework."""
        today = datetime.date.today()
        target_date = today + datetime.timedelta(days=within_days)
        stmt = (
            select(EmployeeDocument)
            .where(
                EmployeeDocument.expiry_date != None,  # noqa: E711
                EmployeeDocument.expiry_date >= today,
                EmployeeDocument.expiry_date <= target_date,
                EmployeeDocument.is_deleted == False,  # noqa: E712
            )
            .order_by(EmployeeDocument.expiry_date.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


employee_document_repository = EmployeeDocumentRepository()
