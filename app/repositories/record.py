"""Repository for :class:`Record` CRUD operations."""

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.record import Record


class RecordRepository:
    """Data-access layer for the ``records`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_record(
        self,
        title: str,
        content: str,
        type: str,
        source: str,
        external_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Record:
        """Insert a new record and return the persisted instance."""
        record = Record(
            title=title,
            content=content,
            type=type,
            source=source,
            external_id=external_id,
            metadata_=metadata or {},
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_record_by_id(self, record_id: uuid.UUID) -> Record | None:
        """Return a record by primary key, or ``None`` if not found."""
        stmt = select(Record).where(Record.id == record_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_records(
        self,
        *,
        source: str | None = None,
        type: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Record]:
        """Return a paginated list of records with optional filters."""
        stmt = select(Record).order_by(Record.created_at.desc())
        if source is not None:
            stmt = stmt.where(Record.source == source)
        if type is not None:
            stmt = stmt.where(Record.type == type)
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_record(self, record_id: uuid.UUID) -> bool:
        """Delete a record by ID.  Returns ``True`` if a row was removed."""
        stmt = delete(Record).where(Record.id == record_id)
        result = await self._session.execute(stmt)
        return (result.rowcount or 0) > 0
