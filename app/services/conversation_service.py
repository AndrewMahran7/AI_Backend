"""Conversation service – orchestrates conversation and message logic."""

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.embeddings.gemini_embeddings import GeminiEmbeddingProvider
from app.providers.llm.gemini_provider import GeminiLLMProvider
from app.repositories.conversation import ConversationRepository
from app.services.query_service import QueryService
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class ConversationService:
    """Manages conversations and delegates query answering to QueryService."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ConversationRepository(session)

    async def create_conversation(self, title: str = "New Chat"):
        return await self._repo.create_conversation(title=title)

    async def list_conversations(self, limit: int = 50, offset: int = 0):
        return await self._repo.list_conversations(limit=limit, offset=offset)

    async def get_conversation(self, conversation_id: uuid.UUID):
        return await self._repo.get_conversation(conversation_id)

    async def get_messages(
        self, conversation_id: uuid.UUID, limit: int = 100, offset: int = 0
    ):
        return await self._repo.get_messages(
            conversation_id, limit=limit, offset=offset
        )

    async def send_message(self, conversation_id: uuid.UUID, content: str):
        """Store user message, run RAG pipeline, store assistant response."""
        # 1. Verify conversation exists
        conv = await self._repo.get_conversation(conversation_id)
        if conv is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        # 2. Store user message
        user_msg = await self._repo.add_message(
            conversation_id=conversation_id,
            role="user",
            content=content,
        )

        # 3. Run the query pipeline
        try:
            llm = GeminiLLMProvider()
            embeddings = GeminiEmbeddingProvider()
            retrieval = RetrievalService(session=self._session, embeddings=embeddings)
            query_svc = QueryService(llm=llm, retrieval=retrieval, session=self._session)
            result: dict[str, Any] = await query_svc.answer_query(content)
        except Exception:
            logger.exception("Query pipeline failed for conversation %s", conversation_id)
            result = {
                "answer": "An error occurred while generating the answer. Please try again.",
                "sources": [],
                "confidence": 0.0,
                "notes": "The query pipeline encountered an error.",
                "query_type": "fact",
            }

        # 4. Store assistant message
        assistant_msg = await self._repo.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=result.get("answer", ""),
            sources=result.get("sources", []),
            confidence=result.get("confidence", 0.0),
            notes=result.get("notes", ""),
            query_type=result.get("query_type", ""),
        )

        # 5. Auto-title conversation if it's the first message
        if conv.title == "New Chat" and content:
            short_title = content[:80].strip()
            if len(content) > 80:
                short_title += "…"
            await self._repo.update_conversation_title(conversation_id, short_title)

        # 6. Touch conversation timestamp
        await self._repo.touch_conversation(conversation_id)

        return user_msg, assistant_msg
