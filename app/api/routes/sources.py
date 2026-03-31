"""Source detail endpoints – on-demand record viewer."""

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.repositories.record import RecordRepository
from app.schemas.source import SourceDetail

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/{record_id}", response_model=SourceDetail)
async def get_source_detail(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return enriched metadata and content for a single source record."""
    repo = RecordRepository(db)
    record = await repo.get_record_by_id(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Source record not found")

    # Record has eagerly-loaded summary + chunks via selectin
    summary = record.summary
    chunks = record.chunks or []

    return SourceDetail(
        record_id=str(record.id),
        title=record.title,
        source_type=record.type,
        source=record.source,
        external_id=record.external_id,
        preview_text=summary.short_summary if summary else "",
        long_summary=summary.long_summary if summary else "",
        keywords=summary.keywords if summary else [],
        entities=summary.entities if summary else [],
        category=summary.category if summary else None,
        content=record.content,
        chunk_count=len(chunks),
        metadata=record.metadata_,
        created_at=record.created_at,
        updated_at=record.updated_at,
        version=record.version,
    )
