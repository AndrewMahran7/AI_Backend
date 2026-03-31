"""Query service – RAG pipeline that grounds LLM answers on retrieved context."""

import json
import logging
import re
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.llm.base import BaseLLMProvider
from app.services.query_classifier import QueryClassifier
from app.services.query_logging_service import QueryLoggingService
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

# ── Style instructions per query type ────────────────────────────────────

_STYLE_INSTRUCTIONS: dict[str, str] = {
    "fact": (
        "Respond concisely and directly. Provide the specific fact or definition "
        "the user is asking for. Use short paragraphs."
    ),
    "summary": (
        "Provide a structured, comprehensive overview. Use headings or bullet "
        "points where appropriate to organise information logically."
    ),
    "compare": (
        "Present a clear comparison. Use bullet points or a side-by-side format "
        "highlighting similarities and differences."
    ),
    "list": (
        "Respond with a well-organised numbered or bulleted list. Be thorough "
        "but concise for each item."
    ),
}

_QUERY_PROMPT = """\
You are an AI knowledge assistant. Answer the user's question using ONLY the \
context provided below. Do NOT use prior knowledge.

IMPORTANT – AGENTIC RETRIEVAL:
If the provided context does NOT contain enough information to fully answer the \
question, you MUST NOT say "I don't have enough information". Instead, request \
additional data by returning intent="search" with specific search queries.

Only return intent="search" when you are missing critical data needed to answer \
(e.g., comparison data for a product not in context, missing specifications). \
If you can provide a reasonable answer from the context, return intent="answer".

QUERY TYPE: {query_type}
STYLE: {style}
{history_section}
CONTEXT:
{context}

USER QUESTION:
{question}

Return your response as a JSON object with EXACTLY these keys – no extra keys, \
no markdown fences, no explanation outside the JSON:

{{
  "intent": "<answer OR search>",
  "search_queries": ["<specific search query 1>", "<specific search query 2>"],
  "answer": "<your detailed answer or empty string if intent is search>",
  "sources": [
    {{"record_id": "<id>", "title": "<title>"}}
  ],
  "confidence": <float between 0.0 and 1.0>,
  "notes": "<any caveats or additional observations>"
}}

Rules:
- "intent": MUST be either "answer" or "search".
- "search_queries": 1–3 specific search queries when intent="search"; empty list when intent="answer".
  Be specific in your search queries (e.g., "N-channel MOSFET comparison 30V low RDS(on)" NOT "more information").
- "answer": comprehensive answer grounded in the provided context. Follow the STYLE instructions above.
  Empty string "" when intent="search".
- "sources": list every record you referenced (deduplicate by record_id). Empty list when intent="search".
- "confidence": your confidence that the answer is correct (0.0–1.0). 0.0 when intent="search".
- "notes": brief note about data quality or gaps; empty string if none.
- Return ONLY valid JSON.
"""

_MAX_CONFIDENCE = 0.85
_LOW_CONFIDENCE_THRESHOLD = 0.6
_MAX_SOURCES = 3
_MAX_RETRIEVAL_ITERATIONS = 2
_MAX_CONTEXT_CHUNKS = 15
_MAX_HISTORY_MESSAGES = 10
_MAX_HISTORY_CHAR_BUDGET = 2000

_HISTORY_HEADER = """\
CONVERSATION HISTORY (use this to understand follow-up questions and references \
to previous messages. Always ground your answers in the CONTEXT section below, \
not in conversation history):
{history}
"""

# Weak hedge phrases to strip from answers (deterministic, no LLM call)
_WEAK_PHRASES: list[re.Pattern[str]] = [
    re.compile(r"\b(it seems( that)?|it appears( that)?|apparently|arguably)\b", re.IGNORECASE),
    re.compile(r"\bbased on the (provided |available )?data,?\s*", re.IGNORECASE),
    re.compile(r"\baccording to the (provided |available )?context,?\s*", re.IGNORECASE),
    re.compile(r"\bfrom the (provided |available )?(information|context|data),?\s*", re.IGNORECASE),
    re.compile(r"\b(I think|I believe|I would say)( that)?\b", re.IGNORECASE),
]

# Markdown patterns to strip from LLM answers at the backend level
_MD_STRIP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^#{1,6}\s+", re.MULTILINE), ""),
    (re.compile(r"\*\*\*(.+?)\*\*\*"), r"\1"),
    (re.compile(r"\*\*(.+?)\*\*"), r"\1"),
    (re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)"), r"\1"),
    (re.compile(r"__(.+?)__"), r"\1"),
    (re.compile(r"`(.+?)`"), r"\1"),
    (re.compile(r"^[*+]\s+", re.MULTILINE), "- "),
    (re.compile(r"^-{3,}$", re.MULTILINE), ""),
    (re.compile(r"(?<=\s)\*(?=\s)"), ""),
]

_NO_RESULTS_RESPONSE: dict[str, Any] = {
    "answer": "No relevant data found in the current dataset.",
    "sources": [],
    "confidence": 0.0,
    "notes": "The knowledge base did not contain information related to this question.",
}

_LLM_ERROR_RESPONSE: dict[str, Any] = {
    "answer": "An error occurred while generating the answer. Please try again.",
    "sources": [],
    "confidence": 0.0,
    "notes": "The language model was unable to produce a valid response.",
}

_FAILSAFE_RESPONSE: dict[str, Any] = {
    "answer": "Limited data available. The comparison or answer is incomplete.",
    "sources": [],
    "confidence": 0.3,
    "notes": "System attempted additional retrieval but the dataset is limited.",
}


# ── Post-processing helpers (deterministic – NO extra LLM calls) ─────────


def _clamp_confidence(raw_confidence: float) -> float:
    """Scale raw confidence into [0.0, MAX_CONFIDENCE] and never exceed the cap."""
    clamped = min(max(raw_confidence, 0.0), 1.0)
    # Scale into [0.5, MAX_CONFIDENCE] for non-zero values
    if clamped > 0.0:
        clamped = 0.5 + (clamped * (_MAX_CONFIDENCE - 0.5))
    return round(min(clamped, _MAX_CONFIDENCE), 2)


def _filter_sources(
    sources: list[dict[str, str]],
    *,
    max_sources: int = _MAX_SOURCES,
) -> list[dict[str, str]]:
    """Deduplicate by record_id and keep only the top *max_sources*."""
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for src in sources:
        rid = src.get("record_id", "")
        if rid and rid not in seen:
            seen.add(rid)
            deduped.append(src)
    return deduped[:max_sources]


def _refine_answer(answer: str, query_type: str) -> str:
    """Apply deterministic text clean-up and formatting."""
    text = answer.strip()

    # Remove weak hedge phrases
    for pat in _WEAK_PHRASES:
        text = pat.sub("", text)

    # Strip markdown formatting so the API returns clean text
    for pat, repl in _MD_STRIP:
        text = pat.sub(repl, text)

    # Collapse multiple spaces / leading whitespace on lines
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Capitalise the first letter if it became lowercase after stripping
    if text and text[0].islower():
        text = text[0].upper() + text[1:]

    return text.strip()


class QueryService:
    """Orchestrates classification → hybrid retrieval → reranking → LLM answer."""

    def __init__(
        self,
        llm: BaseLLMProvider,
        retrieval: RetrievalService,
        session: AsyncSession,
    ) -> None:
        self._llm = llm
        self._retrieval = retrieval
        self._classifier = QueryClassifier(llm)
        self._logging = QueryLoggingService(session)

    async def answer_query(
        self,
        query: str,
        top_k: int = 6,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Classify → hybrid-search → rerank → LLM answer (with agentic retrieval loop) → log.

        The LLM may return ``intent="search"`` with additional search queries
        instead of an immediate answer.  This triggers up to
        ``_MAX_RETRIEVAL_ITERATIONS`` additional retrieval rounds before
        forcing a final answer.

        Parameters
        ----------
        query:
            The user's natural-language question.
        top_k:
            Number of chunks to retrieve per search path.
        conversation_history:
            Optional list of ``{"role": ..., "content": ...}`` dicts
            representing recent messages in the conversation for continuity.

        Returns
        -------
        dict
            ``{"answer", "sources", "confidence", "notes", "query_type",
              "iterations", "used_agentic_search"}``
        """
        start_time = time.perf_counter()

        # 1 – Classify the query
        classification = await self._classifier.classify(query)
        query_type: str = classification["type"]
        logger.info(
            "Query classified as %r (confidence=%.2f)",
            query_type,
            classification["confidence"],
        )

        # 2 – Initial hybrid retrieval
        results = await self._retrieval.hybrid_search(
            query, chunk_top_k=top_k, summary_top_k=max(3, top_k // 2)
        )

        if not results:
            logger.info("No retrieval results for query: %s", query[:120])
            await self._logging.log_query(
                query=query,
                classification=classification,
                retrieved_record_ids=[],
                answer_result=_NO_RESULTS_RESPONSE,
                start_time=start_time,
            )
            return {
                **_NO_RESULTS_RESPONSE,
                "query_type": query_type,
                "iterations": 1,
                "used_agentic_search": False,
            }

        # 3 – Rerank based on classification
        results = RetrievalService.rerank_results(results, query_type=query_type)

        # 3b – Build conversation history section (computed once)
        history_section = self._format_history(conversation_history or [])

        # ── Agentic retrieval loop ───────────────────────────────────────
        iteration = 0
        used_agentic_search = False
        all_search_queries: list[str] = []
        # Accumulate all results across iterations (keyed by record_id)
        accumulated: dict[str, dict[str, Any]] = {
            r["record_id"]: r for r in results
        }

        while iteration < _MAX_RETRIEVAL_ITERATIONS + 1:  # +1 includes initial
            iteration += 1

            # Build context from accumulated results (capped)
            current_results = sorted(
                accumulated.values(), key=lambda x: x["score"], reverse=True
            )[:_MAX_CONTEXT_CHUNKS]
            context = self._build_context(current_results)

            # Call LLM
            style = _STYLE_INSTRUCTIONS.get(query_type, _STYLE_INSTRUCTIONS["fact"])
            prompt = _QUERY_PROMPT.format(
                query_type=query_type,
                style=style,
                history_section=history_section,
                context=context,
                question=query,
            )

            try:
                raw = await self._llm.generate_text(prompt)
            except Exception:
                logger.exception("LLM call failed for query: %s", query[:120])
                await self._logging.log_query(
                    query=query,
                    classification=classification,
                    retrieved_record_ids=[r["record_id"] for r in current_results],
                    answer_result=_LLM_ERROR_RESPONSE,
                    start_time=start_time,
                    iterations=iteration,
                    used_agentic_search=used_agentic_search,
                    agentic_search_queries=all_search_queries,
                )
                return {
                    **_LLM_ERROR_RESPONSE,
                    "query_type": query_type,
                    "iterations": iteration,
                    "used_agentic_search": used_agentic_search,
                }

            # Parse response
            answer_result = self._parse_response(raw, current_results)
            intent = answer_result.pop("intent", "answer")
            search_queries = answer_result.pop("search_queries", [])

            # If model wants to answer, or we've exhausted iterations → break
            if intent == "answer" or iteration > _MAX_RETRIEVAL_ITERATIONS:
                if intent == "search" and iteration > _MAX_RETRIEVAL_ITERATIONS:
                    # Exhausted iterations – use failsafe
                    logger.warning(
                        "Agentic retrieval exhausted %d iterations; returning failsafe.",
                        _MAX_RETRIEVAL_ITERATIONS,
                    )
                    answer_result = {**_FAILSAFE_RESPONSE}
                break

            # intent == "search": perform additional retrieval
            used_agentic_search = True
            all_search_queries.extend(search_queries)
            logger.info(
                "Agentic retrieval iteration %d – model requested search: %s",
                iteration,
                search_queries,
            )

            # Retrieve for each search query and merge
            for sq in search_queries[:3]:  # cap at 3 queries
                new_results = await self._retrieval.hybrid_search(
                    sq,
                    chunk_top_k=top_k,
                    summary_top_k=max(3, top_k // 2),
                )
                new_results = RetrievalService.rerank_results(
                    new_results, query_type=query_type
                )
                for nr in new_results:
                    rid = nr["record_id"]
                    if rid not in accumulated or nr["score"] > accumulated[rid]["score"]:
                        accumulated[rid] = nr

        # ── End of retrieval loop ────────────────────────────────────────

        final_results = sorted(
            accumulated.values(), key=lambda x: x["score"], reverse=True
        )[:_MAX_CONTEXT_CHUNKS]

        answer_result["query_type"] = query_type
        answer_result["iterations"] = iteration
        answer_result["used_agentic_search"] = used_agentic_search

        # Post-process (deterministic – no LLM calls)
        answer_result["confidence"] = _clamp_confidence(answer_result["confidence"])
        answer_result["sources"] = _filter_sources(answer_result["sources"])
        answer_result["answer"] = _refine_answer(answer_result["answer"], query_type)

        # Safety fallback: if confidence is too low, return a safe response
        if answer_result["confidence"] <= _LOW_CONFIDENCE_THRESHOLD and not answer_result["sources"]:
            answer_result["answer"] = "No relevant data found in the current dataset."
            answer_result["notes"] = (
                answer_result.get("notes", "")
                + " Low confidence – the retrieved context may not be sufficient."
            ).strip()

        # Log the interaction
        await self._logging.log_query(
            query=query,
            classification=classification,
            retrieved_record_ids=[r["record_id"] for r in final_results],
            answer_result=answer_result,
            start_time=start_time,
            iterations=iteration,
            used_agentic_search=used_agentic_search,
            agentic_search_queries=all_search_queries,
        )

        return answer_result

    # ── Internal helpers ─────────────────────────────────────────────────

    @staticmethod
    def _format_history(history: list[dict[str, str]]) -> str:
        """Format conversation history into a prompt section.

        Returns an empty string when there is no history, so the prompt
        template collapses cleanly.
        """
        if not history:
            return ""

        lines: list[str] = []
        total_chars = 0
        for msg in history[-_MAX_HISTORY_MESSAGES:]:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            if len(content) > 300:
                content = content[:300] + "…"
            line = f"{role}: {content}"
            total_chars += len(line)
            if total_chars > _MAX_HISTORY_CHAR_BUDGET:
                break
            lines.append(line)

        if not lines:
            return ""
        return _HISTORY_HEADER.format(history="\n".join(lines))

    @staticmethod
    def _build_context(results: list[dict[str, Any]]) -> str:
        """Format retrieval results into a numbered context block."""
        sections: list[str] = []
        for idx, r in enumerate(results, 1):
            header = f"[{idx}] {r['title']} (record_id: {r['record_id']}, relevance: {r['score']})"
            body = r["chunk_text"]
            summary_line = (
                f"  Summary: {r['record_summary']}" if r.get("record_summary") else ""
            )
            sections.append(f"{header}\n{body}\n{summary_line}".strip())
        return "\n\n---\n\n".join(sections)

    @staticmethod
    def _parse_response(
        raw: str,
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Parse the LLM JSON output with safe fallback.

        Now supports ``intent`` and ``search_queries`` keys for agentic retrieval.
        """
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[: cleaned.rfind("```")]
        cleaned = cleaned.strip()

        try:
            parsed: dict = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("LLM returned non-JSON answer; using raw text as fallback.")
            seen: set[str] = set()
            sources: list[dict[str, str]] = []
            for r in results:
                if r["record_id"] not in seen:
                    seen.add(r["record_id"])
                    sources.append({"record_id": r["record_id"], "title": r["title"]})
            return {
                "intent": "answer",
                "search_queries": [],
                "answer": raw,
                "sources": sources,
                "confidence": 0.5,
                "notes": "The model response could not be parsed as structured JSON.",
            }

        # Extract agentic fields
        intent = parsed.get("intent", "answer")
        search_queries = parsed.get("search_queries", [])

        # Validate intent
        if intent not in ("answer", "search"):
            intent = "answer"
        # Validate search_queries
        if not isinstance(search_queries, list):
            search_queries = []
        search_queries = [q for q in search_queries if isinstance(q, str) and q.strip()][:3]

        # Ensure all required keys are present.
        seen_ids: set[str] = set()
        deduped_sources: list[dict[str, str]] = []
        for src in parsed.get("sources", []):
            rid = src.get("record_id", "")
            if rid and rid not in seen_ids:
                seen_ids.add(rid)
                deduped_sources.append(
                    {"record_id": rid, "title": src.get("title", "")}
                )

        return {
            "intent": intent,
            "search_queries": search_queries,
            "answer": parsed.get("answer", ""),
            "sources": deduped_sources,
            "confidence": float(parsed.get("confidence", 0.0)),
            "notes": parsed.get("notes", ""),
        }
