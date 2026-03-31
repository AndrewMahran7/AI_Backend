"""Ingestion route – accepts data for processing."""

import logging
from pathlib import PurePath

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.providers.embeddings.gemini_embeddings import GeminiEmbeddingProvider
from app.providers.llm.gemini_provider import GeminiLLMProvider
from app.repositories.job import JobRepository
from app.schemas.ingest import IngestRequest, IngestResponse, JobStatusResponse
from app.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ingest"])

# Allowed file extensions and their MIME prefixes for basic validation
_ALLOWED_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".log", ".xml", ".html", ".pdf"}
_MAX_FILE_SIZE_MB = 10


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


@router.post(
    "/ingest/upload",
    response_model=IngestResponse,
    status_code=201,
    summary="Upload a file for ingestion",
    description="Upload a file (txt, md, json, csv, etc.) to be ingested into the knowledge base.",
)
async def upload_file(
    file: UploadFile = File(..., description="File to ingest"),
    title: str | None = Form(default=None, description="Optional title (defaults to filename)"),
    type: str = Form(default="document", description="Record type"),
    source: str = Form(default="upload", description="Data source identifier"),
    session: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """Upload a file, extract text content, and queue for processing."""

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    ext = PurePath(file.filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}",
        )

    # Read file bytes with size guard
    raw = await file.read()
    size_mb = len(raw) / (1024 * 1024)
    if size_mb > _MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({size_mb:.1f} MB). Maximum is {_MAX_FILE_SIZE_MB} MB.",
        )

    # Extract text content based on extension
    try:
        content = _extract_text(raw, ext, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="File appears to be empty or contains no readable text.")

    record_title = title or file.filename

    logger.info("Uploading file '%s' (%.1f KB, %s)", file.filename, len(raw) / 1024, ext)

    llm = GeminiLLMProvider()
    embeddings = GeminiEmbeddingProvider()
    service = IngestionService(session=session, llm=llm, embeddings=embeddings)

    record_id, job_id = await service.create_record_and_job(
        title=record_title,
        content=content,
        type=type,
        source=source,
        metadata={"original_filename": file.filename, "file_size_bytes": len(raw), "file_extension": ext},
    )

    return IngestResponse(record_id=record_id, job_id=job_id, status="queued")


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status",
    description="Poll the status of an ingestion job.",
)
async def get_job_status(
    job_id: str,
    session: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    """Return the current status of a job."""
    import uuid as _uuid

    try:
        parsed_id = _uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format.")

    repo = JobRepository(session)
    job = await repo.get_job_by_id(parsed_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        job_type=job.job_type,
        created_at=job.created_at,
        started_at=getattr(job, "started_at", None),
        completed_at=getattr(job, "completed_at", None),
        error=getattr(job, "error", None),
    )


# ── Helpers ──────────────────────────────────────────────────────────────


def _extract_text(raw: bytes, ext: str, filename: str) -> str:
    """Extract text content from raw file bytes based on extension."""
    if ext in {".txt", ".md", ".csv", ".log", ".xml", ".html"}:
        return raw.decode("utf-8", errors="replace")

    if ext == ".json":
        import json

        try:
            parsed = json.loads(raw.decode("utf-8"))
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in '{filename}': {exc}")

    if ext == ".pdf":
        # Attempt basic PDF text extraction
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(stream=raw, filetype="pdf")
            pages = [page.get_text() for page in doc]
            doc.close()
            return "\n\n".join(pages)
        except ImportError:
            raise ValueError(
                "PDF support requires PyMuPDF. Install it with: pip install pymupdf"
            )
        except Exception as exc:
            raise ValueError(f"Failed to extract text from PDF '{filename}': {exc}")

    raise ValueError(f"No text extractor for extension '{ext}'.")
