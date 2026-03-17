"""Ingestion service – orchestrates the full record processing pipeline."""

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.embeddings.base import BaseEmbeddingProvider
from app.providers.llm.base import BaseLLMProvider
from app.repositories.chunk import ChunkRepository
from app.repositories.job import JobRepository
from app.repositories.record import RecordRepository
from app.repositories.summary import SummaryRepository
from app.services.chunking import chunk_text

logger = logging.getLogger(__name__)


class IngestionService:
    """High-level orchestration for data ingestion and processing."""

    def __init__(
        self,
        session: AsyncSession,
        llm: BaseLLMProvider,
        embeddings: BaseEmbeddingProvider,
    ) -> None:
        self._session = session
        self._llm = llm
        self._embeddings = embeddings
        self._records = RecordRepository(session)
        self._chunks = ChunkRepository(session)
        self._summaries = SummaryRepository(session)
        self._jobs = JobRepository(session)

    # ── Public API ───────────────────────────────────────────────────────

    async def create_record_and_job(
        self,
        title: str,
        content: str,
        type: str,
        source: str,
        external_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[uuid.UUID, uuid.UUID]:
        """Create a record and queue a ``PROCESS_RECORD`` job.

        Returns
        -------
        tuple[uuid.UUID, uuid.UUID]
            ``(record_id, job_id)``
        """
        record = await self._records.create_record(
            title=title,
            content=content,
            type=type,
            source=source,
            external_id=external_id,
            metadata=metadata,
        )
        job = await self._jobs.create_job(
            job_type="PROCESS_RECORD",
            payload={"record_id": str(record.id)},
        )
        logger.info("Queued PROCESS_RECORD job %s for record %s", job.id, record.id)
        return record.id, job.id

    async def process_record_job(self, job_id: uuid.UUID) -> None:
        """Execute the full processing pipeline for a PROCESS_RECORD job.

        Steps
        -----
        1. Load job and mark as running.
        2. Load the associated record.
        3. Chunk the record text.
        4. Embed all chunks in batch.
        5. Store chunks with embeddings.
        6. Summarize the full document.
        7. Upsert the summary.
        8. Mark job completed.

        On failure the job is marked as ``failed`` with the error message.
        """
        try:
            # 1 – Load job, mark running
            job = await self._jobs.get_job_by_id(job_id)
            if job is None:
                logger.error("Job %s not found", job_id)
                return
            await self._jobs.update_job_status(job_id, "running")
            await self._session.commit()

            record_id = uuid.UUID(job.payload["record_id"])

            # 2 – Load record
            record = await self._records.get_record_by_id(record_id)
            if record is None:
                raise ValueError(f"Record {record_id} not found for job {job_id}")

            logger.info("Processing record %s (%s)", record.id, record.title)

            # 3 – Chunk text
            text_chunks = chunk_text(record.content)
            logger.info("Split into %d chunks", len(text_chunks))

            # 4 – Embed chunks
            embeddings = await self._embeddings.embed_batch(text_chunks)

            # 5 – Store chunks
            chunk_dicts = [
                {
                    "chunk_index": idx,
                    "text": text,
                    "embedding": emb,
                }
                for idx, (text, emb) in enumerate(zip(text_chunks, embeddings))
            ]
            await self._chunks.create_chunks_for_record(record_id, chunk_dicts)

            # 6 – Summarize document
            summary_data = await self._llm.summarize(record.content)

            # 7 – Upsert summary
            await self._summaries.upsert_summary(
                record_id=record_id,
                short_summary=summary_data["short_summary"],
                long_summary=summary_data["long_summary"],
                keywords=summary_data.get("keywords", []),
                entities=summary_data.get("entities", []),
            )

            # 8 – Mark completed
            await self._jobs.update_job_status(job_id, "completed")
            await self._session.commit()
            logger.info("Job %s completed successfully", job_id)

        except Exception as exc:
            await self._session.rollback()
            logger.exception("Job %s failed: %s", job_id, exc)
            try:
                await self._jobs.mark_failed(job_id, str(exc))
                await self._session.commit()
            except Exception:
                logger.exception("Failed to mark job %s as failed", job_id)
