"""Message model – individual messages within a conversation."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models.conversation import Conversation


class Message(Base):
    """A single message (user or assistant) within a conversation."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa_text("gen_random_uuid()"),
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(16), nullable=False, default="user"
    )  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=sa_text("'[]'::jsonb"),
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True, default="")
    query_type: Mapped[str] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=sa_text("now()"),
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )

    def __repr__(self) -> str:
        return f"<Message id={self.id} role={self.role!r}>"
