"""Query classifier – determines intent type so the RAG pipeline can adapt."""

import json
import logging
from typing import Any

from app.providers.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_CLASSIFY_PROMPT = """\
You are a query classification engine. Classify the user's question into \
exactly one type and return a JSON object with EXACTLY these keys – no extra \
keys, no markdown fences:

{{
  "type": "<one of: fact, summary, compare, list>",
  "confidence": <float between 0.0 and 1.0>
}}

Type definitions:
- "fact": the user asks for a specific piece of information, a definition, or a direct answer.
- "summary": the user asks for an overview, summary, or explanation of a topic.
- "compare": the user asks to compare, contrast, or evaluate two or more items.
- "list": the user asks for an enumeration, a set of items, steps, or recommendations.

If the question does not clearly match any type, default to "fact".

USER QUESTION:
{question}

Return ONLY valid JSON.
"""

# Lightweight keyword heuristics used as a fast-path before calling the LLM.
_KEYWORD_RULES: list[tuple[str, list[str]]] = [
    ("compare", ["compare", "contrast", "versus", " vs ", "differ", "better"]),
    ("list", ["list", "enumerate", "steps", "top ", "recommend", "what are the"]),
    ("summary", ["summarize", "summary", "overview", "explain", "describe"]),
]


class QueryClassifier:
    """Classifies a user query to drive retrieval and prompt strategy."""

    def __init__(self, llm: BaseLLMProvider) -> None:
        self._llm = llm

    async def classify(self, query: str) -> dict[str, Any]:
        """Return ``{"type": ..., "confidence": ...}`` for the given *query*.

        Uses a cheap keyword heuristic first; falls back to an LLM call when
        the heuristic is uncertain.
        """
        # Fast-path: keyword heuristic
        q_lower = query.lower()
        for qtype, keywords in _KEYWORD_RULES:
            if any(kw in q_lower for kw in keywords):
                logger.info("Query classified as %r via keyword heuristic", qtype)
                return {"type": qtype, "confidence": 0.85}

        # Slow-path: LLM classification
        prompt = _CLASSIFY_PROMPT.format(question=query)
        try:
            raw = await self._llm.generate_text(prompt)
            return self._parse(raw)
        except Exception:
            logger.exception("LLM classification failed; defaulting to 'fact'")
            return {"type": "fact", "confidence": 0.5}

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _parse(raw: str) -> dict[str, Any]:
        """Parse LLM JSON response with safe fallback."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[: cleaned.rfind("```")]
        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Classification response was not valid JSON; defaulting to 'fact'.")
            return {"type": "fact", "confidence": 0.5}

        qtype = parsed.get("type", "fact")
        if qtype not in ("fact", "summary", "compare", "list"):
            qtype = "fact"
        confidence = float(parsed.get("confidence", 0.5))

        return {"type": qtype, "confidence": round(confidence, 2)}
