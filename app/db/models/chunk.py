"""RecordChunk model – chunked pieces of a record for embedding & retrieval."""

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Default embedding dimension (matches text-embedding-004 output).
EMBEDDING_DIMENSION: int = 768


class RecordChunk(Base):
    """A single chunk of text derived from a :class:`Record`.

    Each chunk stores its own embedding vector for similarity search.
    """

    __tablename__ = "record_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa_text("gen_random_uuid()"),
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIMENSION),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=sa_text("now()"),
    )

    # ── Relationships ────────────────────────────────────────────────────
    record: Mapped["Record"] = relationship(
        "Record",
        back_populates="chunks",
    )

    def __repr__(self) -> str:
        return f"<RecordChunk id={self.id} record_id={self.record_id} idx={self.chunk_index}>"


from app.db.models.record import Record  # noqa: E402, F401
