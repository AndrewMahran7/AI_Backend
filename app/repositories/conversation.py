"""Repository for Conversation and Message persistence."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.conversation import Conversation
from app.db.models.message import Message


class ConversationRepository:
    """Data-access layer for conversations and messages."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Conversations ────────────────────────────────────────────────────

    async def create_conversation(self, title: str = "New Chat") -> Conversation:
        conv = Conversation(title=title)
        self._session.add(conv)
        await self._session.flush()
        return conv

    async def list_conversations(self, limit: int = 50, offset: int = 0) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_conversation(self, conversation_id: uuid.UUID) -> Conversation | None:
        stmt = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_conversation_title(
        self, conversation_id: uuid.UUID, title: str
    ) -> None:
        stmt = (
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(title=title, updated_at=datetime.now(timezone.utc))
        )
        await self._session.execute(stmt)

    async def touch_conversation(self, conversation_id: uuid.UUID) -> None:
        """Update the updated_at timestamp."""
        stmt = (
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=datetime.now(timezone.utc))
        )
        await self._session.execute(stmt)

    # ── Messages ─────────────────────────────────────────────────────────

    async def add_message(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        sources: list[dict[str, str]] | None = None,
        confidence: float | None = None,
        notes: str = "",
        query_type: str | None = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources=sources or [],
            confidence=confidence,
            notes=notes,
            query_type=query_type,
        )
        self._session.add(msg)
        await self._session.flush()
        return msg

    async def get_messages(
        self, conversation_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
