"""Record model – a normalized piece of data from any external source."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Record(Base):
    """A single indexed record ingested from an external data source.

    Each record may be split into :class:`RecordChunk` objects for
    embedding, and may have an associated :class:`RecordSummary`.
    """

    __tablename__ = "records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    # ── Relationships ────────────────────────────────────────────────────
    chunks: Mapped[list["RecordChunk"]] = relationship(
        "RecordChunk",
        back_populates="record",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    summary: Mapped["RecordSummary | None"] = relationship(
        "RecordSummary",
        back_populates="record",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Record id={self.id} type={self.type!r} source={self.source!r}>"


# Resolve forward references after the module is fully loaded.
from app.db.models.chunk import RecordChunk  # noqa: E402, F401
from app.db.models.summary import RecordSummary  # noqa: E402, F401
