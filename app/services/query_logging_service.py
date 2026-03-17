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
            )
            logger.info(
                "Logged query (type=%s, confidence=%.2f, duration=%.0fms)",
                classification.get("type"),
                answer_result.get("confidence", 0.0),
                duration_ms,
            )
        except Exception:
            # Logging failures should never break the user response.
            logger.exception("Failed to persist query log entry")
