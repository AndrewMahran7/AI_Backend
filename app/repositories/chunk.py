"""Repository for :class:`RecordChunk` operations including similarity search."""

import uuid

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chunk import RecordChunk


class ChunkRepository:
    """Data-access layer for the ``record_chunks`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_chunks_for_record(
        self,
        record_id: uuid.UUID,
        chunks: list[dict],
    ) -> list[RecordChunk]:
        """Bulk-insert chunks for a given record.

        Parameters
        ----------
        record_id:
            The parent record's UUID.
        chunks:
            A list of dicts, each containing at minimum ``text`` and
            ``chunk_index``.  Optional keys: ``summary``, ``embedding``.

        Returns
        -------
        list[RecordChunk]
            The persisted chunk instances.
        """
        # Remove any pre-existing chunks for this record so re-processing
        # is idempotent.
        await self._session.execute(
            delete(RecordChunk).where(RecordChunk.record_id == record_id)
        )

        entities: list[RecordChunk] = []
        for chunk_data in chunks:
            entity = RecordChunk(
                record_id=record_id,
                chunk_index=chunk_data["chunk_index"],
                text=chunk_data["text"],
                summary=chunk_data.get("summary"),
                embedding=chunk_data.get("embedding"),
            )
            self._session.add(entity)
            entities.append(entity)

        await self._session.flush()
        return entities

    async def get_chunks_for_record(self, record_id: uuid.UUID) -> list[RecordChunk]:
        """Return all chunks for a record, ordered by index."""
        stmt = (
            select(RecordChunk)
            .where(RecordChunk.record_id == record_id)
            .order_by(RecordChunk.chunk_index)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def similarity_search(
        self,
        query_embedding: list[float],
        limit: int = 10,
    ) -> list[RecordChunk]:
        """Return the most similar chunks to *query_embedding*.

        Uses pgvector's cosine distance operator (``<=>``) for ranking.
        Only chunks that already have an embedding are considered.
        """
        stmt = (
            select(RecordChunk)
            .where(RecordChunk.embedding.is_not(None))
            .order_by(RecordChunk.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
