"""Repository for :class:`QueryLog` persistence."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.query_log import QueryLog


class QueryLogRepository:
    """Data-access layer for the ``query_logs`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        query: str,
        query_type: str,
        classification_confidence: float,
        retrieved_record_ids: list[str],
        answer: str,
        answer_confidence: float,
        sources: list[dict],
        duration_ms: float,
        iterations: int = 1,
        used_agentic_search: bool = False,
        agentic_search_queries: list[str] | None = None,
    ) -> QueryLog:
        """Insert a new query log entry."""
        log = QueryLog(
            query=query,
            query_type=query_type,
            classification_confidence=classification_confidence,
            retrieved_record_ids=retrieved_record_ids,
            answer=answer,
            answer_confidence=answer_confidence,
            sources=sources,
            duration_ms=duration_ms,
            iterations=iterations,
            used_agentic_search=used_agentic_search,
            agentic_search_queries=agentic_search_queries or [],
        )
        self._session.add(log)
        await self._session.flush()
        return log
