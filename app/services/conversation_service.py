"""Conversation service – orchestrates conversation and message logic."""

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.embeddings.gemini_embeddings import GeminiEmbeddingProvider
from app.providers.llm.gemini_provider import GeminiLLMProvider
from app.repositories.conversation import ConversationRepository
from app.repositories.record import RecordRepository
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

    async def list_conversations(
        self, limit: int = 50, offset: int = 0, query: str | None = None
    ):
        if query and query.strip():
            return await self._repo.search_conversations(
                query=query.strip(), limit=limit, offset=offset
            )
        return await self._repo.list_conversations(limit=limit, offset=offset)

    async def get_conversation(self, conversation_id: uuid.UUID):
        return await self._repo.get_conversation(conversation_id)

    async def delete_conversation(self, conversation_id: uuid.UUID) -> bool:
        return await self._repo.delete_conversation(conversation_id)

    async def get_messages(
        self, conversation_id: uuid.UUID, limit: int = 100, offset: int = 0
    ):
        return await self._repo.get_messages(
            conversation_id, limit=limit, offset=offset
        )

    async def send_message(self, conversation_id: uuid.UUID, content: str):
        """Store user message, run RAG pipeline with conversation history, store assistant response."""
        # 1. Verify conversation exists
        conv = await self._repo.get_conversation(conversation_id)
        if conv is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        # 2. Fetch recent messages for conversation history (BEFORE storing new message)
        recent_messages = await self._repo.get_messages(
            conversation_id, limit=10
        )
        conversation_history = [
            {"role": m.role, "content": m.content}
            for m in recent_messages
        ]

        # 3. Store user message
        user_msg = await self._repo.add_message(
            conversation_id=conversation_id,
            role="user",
            content=content,
        )

        # 4. Run the query pipeline with conversation history
        try:
            llm = GeminiLLMProvider()
            embeddings = GeminiEmbeddingProvider()
            retrieval = RetrievalService(session=self._session, embeddings=embeddings)
            query_svc = QueryService(llm=llm, retrieval=retrieval, session=self._session)
            result: dict[str, Any] = await query_svc.answer_query(
                content, conversation_history=conversation_history
            )
        except Exception:
            logger.exception("Query pipeline failed for conversation %s", conversation_id)
            result = {
                "answer": "An error occurred while generating the answer. Please try again.",
                "sources": [],
                "confidence": 0.0,
                "notes": "The query pipeline encountered an error.",
                "query_type": "fact",
            }

        # 5. Enrich sources with record metadata (type, source, preview)
        enriched_sources = await self._enrich_sources(
            result.get("sources", [])
        )

        # 6. Store assistant message
        assistant_msg = await self._repo.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=result.get("answer", ""),
            sources=enriched_sources,
            confidence=result.get("confidence", 0.0),
            notes=result.get("notes", ""),
            query_type=result.get("query_type", ""),
        )

        # 7. Auto-title conversation if it's the first message
        if conv.title == "New Chat" and content:
            try:
                generated_title = await self._generate_title(llm, content)
                await self._repo.update_conversation_title(conversation_id, generated_title)
            except Exception:
                logger.warning("LLM title generation failed for %s, using fallback", conversation_id)
                fallback = self._fallback_title(content)
                await self._repo.update_conversation_title(conversation_id, fallback)

        # 8. Touch conversation timestamp
        await self._repo.touch_conversation(conversation_id)

        return user_msg, assistant_msg

    # ── Source enrichment ────────────────────────────────────────────────

    async def _enrich_sources(
        self, raw_sources: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        """Look up record metadata and return enriched source dicts."""
        if not raw_sources:
            return []

        repo = RecordRepository(self._session)
        enriched: list[dict[str, str]] = []

        for src in raw_sources:
            rid_str = src.get("record_id", "")
            if not rid_str:
                enriched.append(src)
                continue
            try:
                record = await repo.get_record_by_id(uuid.UUID(rid_str))
            except (ValueError, Exception):
                enriched.append(src)
                continue

            if record is None:
                enriched.append(src)
                continue

            summary = record.summary
            enriched.append({
                "record_id": rid_str,
                "title": src.get("title") or record.title,
                "source_type": record.type,
                "source": record.source,
                "preview_text": summary.short_summary if summary else "",
            })

        return enriched

    # ── Title helpers ─────────────────────────────────────────────────

    _TITLE_PROMPT = (
        "Generate a short conversation title (3-6 words) for this engineering query. "
        "Rules:\n"
        "- Exactly 3 to 6 words\n"
        "- No punctuation at the end\n"
        "- No filler words (the, a, an, is, what, how, can, etc.)\n"
        "- Descriptive of the technical intent\n"
        "- Title case\n"
        "- Return ONLY the title, nothing else\n\n"
        "Query: "
    )

    async def _generate_title(self, llm: GeminiLLMProvider, user_message: str) -> str:
        """Ask the LLM for a concise conversation title."""
        prompt = self._TITLE_PROMPT + user_message[:500]
        raw = await llm.generate_text(prompt)
        title = raw.strip().strip('"').strip("'").strip()
        # Remove trailing punctuation
        title = title.rstrip(".!?…")
        # Enforce max length
        if len(title) > 60:
            title = " ".join(title.split()[:6])
        if not title:
            title = self._fallback_title(user_message)
        return title

    @staticmethod
    def _fallback_title(content: str) -> str:
        """Create a short title from the first few meaningful words."""
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "what", "how",
                     "can", "do", "does", "i", "my", "me", "we", "our", "you",
                     "your", "it", "its", "this", "that", "of", "in", "to", "for",
                     "and", "or", "but", "with", "on", "at", "by", "be", "if"}
        words = content.split()
        meaningful = [w for w in words if w.lower().strip("?.,!") not in stopwords]
        selected = meaningful[:5] if meaningful else words[:5]
        return " ".join(selected)[:60].strip()
