"""Retrieval service – hybrid search over the indexed knowledge base."""

import logging
import uuid
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chunk import RecordChunk
from app.db.models.record import Record
from app.db.models.summary import RecordSummary
from app.providers.embeddings.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)


class RetrievalService:
    """Performs hybrid (chunk + summary) semantic search and assembles enriched results."""

    def __init__(
        self,
        session: AsyncSession,
        embeddings: BaseEmbeddingProvider,
    ) -> None:
        self._session = session
        self._embeddings = embeddings

    # ── Public API ───────────────────────────────────────────────────────

    async def semantic_search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Embed *query*, find the closest chunks, and enrich with record metadata.

        Returns a list of dicts with keys:
        ``record_id``, ``title``, ``chunk_text``, ``chunk_summary``,
        ``score``, ``record_summary``.
        """
        query_embedding = await self._embeddings.embed_text(query)
        return await self._chunk_search(query_embedding, top_k)

    async def semantic_search_summaries(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Search *record summaries* by embedding the long_summary text.

        Embeds each summary's ``long_summary`` field at query-time using
        ``func.avg`` over the chunk embeddings that belong to each record.
        This avoids storing a separate summary embedding column.

        Returns a list of dicts with keys:
        ``record_id``, ``title``, ``score``, ``short_summary``,
        ``long_summary``, ``keywords``, ``category``.
        """
        query_embedding = await self._embeddings.embed_text(query)

        # Use the average embedding of all chunks in a record as the
        # "record-level" embedding and compute cosine distance.
        avg_emb = func.avg(RecordChunk.embedding).label("avg_emb")
        sub = (
            select(RecordChunk.record_id, avg_emb)
            .where(RecordChunk.embedding.is_not(None))
            .group_by(RecordChunk.record_id)
            .subquery()
        )

        # Cast the avg column back to Vector so the <=> operator is available.
        distance_expr = cast(sub.c.avg_emb, Vector(len(query_embedding))).cosine_distance(query_embedding)
        stmt = (
            select(RecordSummary, distance_expr.label("distance"))
            .join(sub, RecordSummary.record_id == sub.c.record_id)
            .order_by(distance_expr)
            .limit(top_k)
        )
        rows = (await self._session.execute(stmt)).all()

        if not rows:
            return []

        # Fetch matching records for titles
        record_ids = {row.RecordSummary.record_id for row in rows}
        records_map = await self._fetch_records(record_ids)

        results: list[dict[str, Any]] = []
        for row in rows:
            summary: RecordSummary = row.RecordSummary
            distance: float = row.distance
            record = records_map.get(summary.record_id)
            score = round(max(0.0, 1.0 - distance), 4)
            results.append(
                {
                    "record_id": str(summary.record_id),
                    "title": record.title if record else "Unknown",
                    "score": score,
                    "short_summary": summary.short_summary,
                    "long_summary": summary.long_summary,
                    "keywords": summary.keywords,
                    "category": summary.category,
                }
            )

        logger.info(
            "Summary search for %r returned %d results (top score=%.4f)",
            query[:80],
            len(results),
            results[0]["score"] if results else 0.0,
        )
        return results

    async def hybrid_search(
        self,
        query: str,
        chunk_top_k: int = 6,
        summary_top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Combine chunk-level and summary-level searches, de-duplicate by record_id.

        Merges results from :meth:`semantic_search` and
        :meth:`semantic_search_summaries`, keeping the *best* score for each
        record.  Final list is sorted descending by score.
        """
        query_embedding = await self._embeddings.embed_text(query)

        # Run both searches with the same embedding to avoid embedding twice
        chunk_results = await self._chunk_search(query_embedding, chunk_top_k)
        summary_results = await self._summary_search(query_embedding, summary_top_k)

        # Merge: best score per record
        merged: dict[str, dict[str, Any]] = {}
        for r in chunk_results:
            rid = r["record_id"]
            if rid not in merged or r["score"] > merged[rid]["score"]:
                merged[rid] = r

        for sr in summary_results:
            rid = sr["record_id"]
            if rid not in merged:
                # Promote summary-only hit to a chunk-like dict
                merged[rid] = {
                    "record_id": rid,
                    "title": sr["title"],
                    "chunk_text": sr["long_summary"],
                    "chunk_summary": sr["short_summary"],
                    "score": sr["score"],
                    "record_summary": sr["short_summary"],
                }
            elif sr["score"] > merged[rid]["score"]:
                merged[rid]["score"] = sr["score"]
                # Augment with summary data if missing
                if not merged[rid].get("record_summary"):
                    merged[rid]["record_summary"] = sr["short_summary"]

        results = sorted(merged.values(), key=lambda x: x["score"], reverse=True)

        logger.info(
            "Hybrid search for %r returned %d unique records (top score=%.4f)",
            query[:80],
            len(results),
            results[0]["score"] if results else 0.0,
        )
        return results

    @staticmethod
    def rerank_results(
        results: list[dict[str, Any]],
        query_type: str = "fact",
    ) -> list[dict[str, Any]]:
        """Re-rank results with heuristic boosts based on query classification.

        Applies lightweight score adjustments:
        - ``summary`` / ``compare`` types boost entries that have a record summary.
        - ``fact`` type boosts higher-granularity (chunk-level) high scores.
        - ``list`` type keeps ordering but favours breadth (unique records).
        """
        if not results:
            return results

        boosted: list[dict[str, Any]] = []
        for r in results:
            adjusted = r["score"]

            if query_type in ("summary", "compare"):
                # Favour items with a record-level summary available
                if r.get("record_summary"):
                    adjusted += 0.03
            elif query_type == "fact":
                # Favour high-confidence chunk hits
                if r["score"] > 0.8:
                    adjusted += 0.02
            # 'list' keeps natural ordering

            boosted.append({**r, "score": round(min(adjusted, 1.0), 4)})

        boosted.sort(key=lambda x: x["score"], reverse=True)
        return boosted

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _chunk_search(
        self,
        query_embedding: list[float],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Core chunk-level cosine-distance search."""
        distance_expr = RecordChunk.embedding.cosine_distance(query_embedding)
        stmt = (
            select(RecordChunk, distance_expr.label("distance"))
            .where(RecordChunk.embedding.is_not(None))
            .order_by(distance_expr)
            .limit(top_k)
        )
        rows = (await self._session.execute(stmt)).all()

        if not rows:
            return []

        record_ids: set[uuid.UUID] = {row.RecordChunk.record_id for row in rows}
        records_map = await self._fetch_records(record_ids)
        summaries_map = await self._fetch_summaries(record_ids)

        results: list[dict[str, Any]] = []
        for row in rows:
            chunk: RecordChunk = row.RecordChunk
            distance: float = row.distance
            record = records_map.get(chunk.record_id)
            summary = summaries_map.get(chunk.record_id)
            score = round(max(0.0, 1.0 - distance), 4)

            results.append(
                {
                    "record_id": str(chunk.record_id),
                    "title": record.title if record else "Unknown",
                    "chunk_text": chunk.text,
                    "chunk_summary": chunk.summary,
                    "score": score,
                    "record_summary": summary.short_summary if summary else None,
                }
            )

        logger.info(
            "Chunk search returned %d results (top score=%.4f)",
            len(results),
            results[0]["score"] if results else 0.0,
        )
        return results

    async def _summary_search(
        self,
        query_embedding: list[float],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Core summary-level search using avg chunk embeddings per record."""
        avg_emb = func.avg(RecordChunk.embedding).label("avg_emb")
        sub = (
            select(RecordChunk.record_id, avg_emb)
            .where(RecordChunk.embedding.is_not(None))
            .group_by(RecordChunk.record_id)
            .subquery()
        )

        # Cast the avg column back to Vector so the <=> operator is available.
        distance_expr = cast(sub.c.avg_emb, Vector(len(query_embedding))).cosine_distance(query_embedding)
        stmt = (
            select(RecordSummary, distance_expr.label("distance"))
            .join(sub, RecordSummary.record_id == sub.c.record_id)
            .order_by(distance_expr)
            .limit(top_k)
        )
        rows = (await self._session.execute(stmt)).all()

        if not rows:
            return []

        record_ids = {row.RecordSummary.record_id for row in rows}
        records_map = await self._fetch_records(record_ids)

        results: list[dict[str, Any]] = []
        for row in rows:
            summary: RecordSummary = row.RecordSummary
            distance: float = row.distance
            record = records_map.get(summary.record_id)
            score = round(max(0.0, 1.0 - distance), 4)
            results.append(
                {
                    "record_id": str(summary.record_id),
                    "title": record.title if record else "Unknown",
                    "score": score,
                    "short_summary": summary.short_summary,
                    "long_summary": summary.long_summary,
                    "keywords": summary.keywords,
                    "category": summary.category,
                }
            )

        logger.info(
            "Summary search returned %d results (top score=%.4f)",
            len(results),
            results[0]["score"] if results else 0.0,
        )
        return results

    async def _fetch_records(
        self,
        record_ids: set[uuid.UUID],
    ) -> dict[uuid.UUID, Record]:
        """Batch-fetch records by IDs."""
        stmt = select(Record).where(Record.id.in_(record_ids))
        return {
            r.id: r
            for r in (await self._session.execute(stmt)).scalars().all()
        }

    async def _fetch_summaries(
        self,
        record_ids: set[uuid.UUID],
    ) -> dict[uuid.UUID, RecordSummary]:
        """Batch-fetch summaries by record IDs."""
        stmt = select(RecordSummary).where(
            RecordSummary.record_id.in_(record_ids)
        )
        return {
            s.record_id: s
            for s in (await self._session.execute(stmt)).scalars().all()
        }
