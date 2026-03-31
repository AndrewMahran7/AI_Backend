"""Query logging service – records every chat interaction for auditing."""

import logging
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.query_log import QueryLogRepository

logger = logging.getLogger(__name__)


class QueryLoggingService:
    """Thin wrapper around :class:`QueryLogRepository` with timing helpers."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = QueryLogRepository(session)

    async def log_query(
        self,
        *,
        query: str,
        classification: dict[str, Any],
        retrieved_record_ids: list[str],
        answer_result: dict[str, Any],
        start_time: float,
        iterations: int = 1,
        used_agentic_search: bool = False,
        agentic_search_queries: list[str] | None = None,
    ) -> None:
        """Persist an audit entry for a single query cycle.

        Parameters
        ----------
        query:
            The raw user query.
        classification:
            Output of :class:`QueryClassifier.classify`.
        retrieved_record_ids:
            List of record IDs surfaced by retrieval.
        answer_result:
            The full response dict from :class:`QueryService`.
        start_time:
            ``time.perf_counter()`` taken at the start of the request.
        iterations:
            Number of retrieval iterations used (1 = no agentic search).
        used_agentic_search:
            Whether the model triggered additional retrieval rounds.
        agentic_search_queries:
            The search queries the model generated for agentic retrieval.
        """
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        try:
            await self._repo.create(
                query=query,
                query_type=classification.get("type", "unknown"),
                classification_confidence=classification.get("confidence", 0.0),
                retrieved_record_ids=retrieved_record_ids,
                answer=answer_result.get("answer", ""),
                answer_confidence=answer_result.get("confidence", 0.0),
                sources=answer_result.get("sources", []),
                duration_ms=duration_ms,
                iterations=iterations,
                used_agentic_search=used_agentic_search,
                agentic_search_queries=agentic_search_queries or [],
            )
            logger.info(
                "Logged query (type=%s, confidence=%.2f, duration=%.0fms, iterations=%d, agentic=%s)",
                classification.get("type"),
                answer_result.get("confidence", 0.0),
                duration_ms,
                iterations,
                used_agentic_search,
            )
        except Exception:
            # Logging failures should never break the user response.
            logger.exception("Failed to persist query log entry")
