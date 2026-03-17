"""Shared FastAPI dependencies used across route modules."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for request-scoped usage."""
    async for session in get_db_session():
        yield session
