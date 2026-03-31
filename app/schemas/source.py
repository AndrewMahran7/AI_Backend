"""Pydantic schemas for source detail / viewer endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class SourceDetail(BaseModel):
    """Enriched source metadata returned by GET /sources/{record_id}."""

    record_id: str
    title: str
    source_type: str = Field(description="Record type, e.g. datasheet, manual, article")
    source: str = Field(description="Origin system, e.g. upload, dentrix, sap")
    external_id: str | None = None

    # Summary-derived fields
    preview_text: str = Field(default="", description="Short summary / first paragraph")
    long_summary: str = Field(default="", description="Full AI-generated summary")
    keywords: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    category: str | None = None

    # Content
    content: str = Field(default="", description="Full record content text")
    chunk_count: int = 0

    # Metadata
    metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1
