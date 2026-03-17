"""Ingestion route – accepts data for processing."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.providers.embeddings.gemini_embeddings import GeminiEmbeddingProvider
from app.providers.llm.gemini_provider import GeminiLLMProvider
from app.schemas.ingest import IngestRequest, IngestResponse
from app.services.ingestion_service import IngestionService

router = APIRouter(tags=["ingest"])


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=201,
    summary="Ingest a record",
    description="Create a record and queue it for AI processing (chunking, embedding, summarisation).",
)
async def ingest_record(
    body: IngestRequest,
    session: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """Accept a record, persist it, and enqueue a processing job."""
    llm = GeminiLLMProvider()
    embeddings = GeminiEmbeddingProvider()
    service = IngestionService(session=session, llm=llm, embeddings=embeddings)

    record_id, job_id = await service.create_record_and_job(
        title=body.title,
        content=body.content,
        type=body.type,
        source=body.source,
        metadata=body.metadata,
    )

    return IngestResponse(record_id=record_id, job_id=job_id, status="queued")
