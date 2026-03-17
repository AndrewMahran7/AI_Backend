"""RecordSummary model – document-level summary and structured metadata."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RecordSummary(Base):
    """AI-generated summary and extracted metadata for a :class:`Record`."""

    __tablename__ = "record_summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("records.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    short_summary: Mapped[str] = mapped_column(Text, nullable=False)
    long_summary: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    entities: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    category: Mapped[str | None] = mapped_column(String(256), nullable=True)
    last_generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # ── Relationships ────────────────────────────────────────────────────
    record: Mapped["Record"] = relationship(
        "Record",
        back_populates="summary",
    )

    def __repr__(self) -> str:
        return f"<RecordSummary id={self.id} record_id={self.record_id}>"


from app.db.models.record import Record  # noqa: E402, F401
