"""Pydantic schemas for the ingestion endpoint."""

import uuid
from typing import Any

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """Request body for ``POST /ingest``."""

    title: str = Field(..., min_length=1, max_length=512, description="Record title")
    content: str = Field(..., min_length=1, description="Full text content to ingest")
    type: str = Field(..., min_length=1, max_length=128, description='Record type (e.g. "document", "ticket")')
    source: str = Field(..., min_length=1, max_length=256, description="Data source identifier")
    metadata: dict[str, Any] | None = Field(default=None, description="Optional JSONB metadata")


class IngestResponse(BaseModel):
    """Response returned by ``POST /ingest``."""

    record_id: uuid.UUID
    job_id: uuid.UUID
    status: str = "queued"
