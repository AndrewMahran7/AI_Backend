"""SAP PLM sync service.

Orchestrates the full pipeline from SAP object fetch through ingestion:

  SAPPLMAdapter.fetch_*()
    → normalize_record()
    → IngestionService.create_record_and_job()

Returns a summary dict so callers (e.g. API routes) can report progress.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.adapters.sap_plm_adapter import SAPPLMAdapter
from app.providers.embeddings.gemini_embeddings import GeminiEmbeddingProvider
from app.providers.llm.gemini_provider import GeminiLLMProvider
from app.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)


class SAPSyncService:
    """High-level sync coordinator for SAP PLM → internal knowledge base.

    Parameters
    ----------
    session:
        An active async SQLAlchemy session injected per request.
    adapter:
        Optional pre-configured adapter.  A default instance is created
        from application settings when not supplied.
    """

    def __init__(
        self,
        session: AsyncSession,
        adapter: SAPPLMAdapter | None = None,
    ) -> None:
        self._session = session
        self._adapter = adapter or SAPPLMAdapter()
        self._ingestion = IngestionService(
            session=session,
            llm=GeminiLLMProvider(),
            embeddings=GeminiEmbeddingProvider(),
        )

    # ── Internal ──────────────────────────────────────────────────────────

    async def _sync(
        self,
        object_type: str,
        raw_records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Normalise and queue *raw_records* for ingestion.

        Returns
        -------
        dict
            ``{"object_type", "fetched", "queued", "failed", "job_ids"}``
        """
        queued: list[str] = []
        failed: int = 0

        for raw in raw_records:
            try:
                normalised = await self._adapter.normalize_record(raw)
                _, job_id = await self._ingestion.create_record_and_job(
                    title=normalised["title"],
                    content=normalised["content"],
                    type=normalised["type"],
                    source=normalised["source"],
                    external_id=normalised.get("external_id"),
                    metadata=normalised.get("metadata"),
                )
                queued.append(str(job_id))
            except Exception:
                logger.exception(
                    "Failed to ingest SAP %s record: %s",
                    object_type,
                    raw,
                )
                failed += 1

        logger.info(
            "SAP sync %s: fetched=%d queued=%d failed=%d",
            object_type,
            len(raw_records),
            len(queued),
            failed,
        )

        return {
            "object_type": object_type,
            "fetched":     len(raw_records),
            "queued":      len(queued),
            "failed":      failed,
            "job_ids":     queued,
        }

    # ── Public methods ────────────────────────────────────────────────────

    async def sync_materials(self, limit: int = 100) -> dict[str, Any]:
        """Fetch and queue SAP material master records."""
        records = await self._adapter.fetch_materials(limit=limit)
        return await self._sync("materials", records)

    async def sync_documents(self, limit: int = 100) -> dict[str, Any]:
        """Fetch and queue SAP document info records."""
        records = await self._adapter.fetch_documents(limit=limit)
        return await self._sync("documents", records)

    async def sync_boms(self, limit: int = 100) -> dict[str, Any]:
        """Fetch and queue SAP bill-of-materials items."""
        records = await self._adapter.fetch_boms(limit=limit)
        return await self._sync("boms", records)

    async def sync_change_records(self, limit: int = 100) -> dict[str, Any]:
        """Fetch and queue SAP engineering change records."""
        records = await self._adapter.fetch_change_records(limit=limit)
        return await self._sync("change_records", records)
