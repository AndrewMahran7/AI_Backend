"""QueryLog model – stores audit records for every chat query processed."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QueryLog(Base):
    """Audit log row for a single chat query."""

    __tablename__ = "query_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa_text("gen_random_uuid()"),
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    query_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    classification_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    retrieved_record_ids: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=sa_text("'[]'::jsonb"),
    )
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    answer_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sources: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=sa_text("'[]'::jsonb"),
    )
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    iterations: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=sa_text("1")
    )
    used_agentic_search: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=sa_text("false")
    )
    agentic_search_queries: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=sa_text("'[]'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=sa_text("now()"),
    )

    def __repr__(self) -> str:
        return f"<QueryLog id={self.id} type={self.query_type!r}>"
