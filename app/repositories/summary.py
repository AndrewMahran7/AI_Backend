"""Repository for :class:`RecordSummary` upsert and retrieval."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.summary import RecordSummary


class SummaryRepository:
    """Data-access layer for the ``record_summaries`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_summary(
        self,
        record_id: uuid.UUID,
        short_summary: str,
        long_summary: str,
        keywords: list[str] | None = None,
        entities: list[dict] | None = None,
        category: str | None = None,
    ) -> RecordSummary:
        """Create or update the summary for a given record.

        If a summary already exists for *record_id* it is updated in place;
        otherwise a new row is inserted.
        """
        stmt = select(RecordSummary).where(RecordSummary.record_id == record_id)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if existing is not None:
            existing.short_summary = short_summary
            existing.long_summary = long_summary
            existing.keywords = keywords or []
            existing.entities = entities or []
            existing.category = category
            existing.last_generated_at = now
            await self._session.flush()
            return existing

        summary = RecordSummary(
            record_id=record_id,
            short_summary=short_summary,
            long_summary=long_summary,
            keywords=keywords or [],
            entities=entities or [],
            category=category,
            last_generated_at=now,
        )
        self._session.add(summary)
        await self._session.flush()
        return summary

    async def get_summary_by_record(self, record_id: uuid.UUID) -> RecordSummary | None:
        """Return the summary for a record, or ``None`` if none exists."""
        stmt = select(RecordSummary).where(RecordSummary.record_id == record_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
