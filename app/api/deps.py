from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

# Common FastAPI dependencies for injection
__all__ = ["get_db"]
