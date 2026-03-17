"""Gemini LLM provider using the Google GenAI SDK (google-genai)."""

import json
import logging

from google import genai

from app.core.config import get_settings
from app.providers.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_SUMMARIZE_PROMPT = """\
You are a precise document analysis engine. Analyze the following text and return \
a JSON object with EXACTLY these keys – no extra keys, no markdown fences:

{
  "short_summary": "<1-2 sentence summary>",
  "long_summary": "<detailed 3-5 sentence summary>",
  "keywords": ["keyword1", "keyword2", ...],
  "entities": ["entity1", "entity2", ...]
}

Rules:
- keywords: 5-10 most relevant topic keywords.
- entities: named entities (people, organizations, products, places).
- Return ONLY valid JSON. No explanation, no markdown code block.

TEXT:
"""


class GeminiLLMProvider(BaseLLMProvider):
    """LLM provider backed by Google Gemini via the ``google-genai`` SDK.

    Supports two authentication modes controlled by ``GEMINI_TIER``:

    - ``dev``        – standard API key via ``GEMINI_API_KEY``
    - ``enterprise`` – Vertex AI using Application Default Credentials
                       (set by ``GOOGLE_APPLICATION_CREDENTIALS`` or
                       ``gcloud auth application-default login``).
    """

    def __init__(self) -> None:
        settings = get_settings()
        if settings.is_enterprise:
            self._client = genai.Client(
                vertexai=True,
                project=settings.GEMINI_VERTEX_PROJECT,
                location=settings.GEMINI_VERTEX_LOCATION,
            )
        else:
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model = settings.GEMINI_MODEL

    async def generate_text(self, prompt: str) -> str:
        """Send a prompt to Gemini and return the text response."""
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=prompt,
        )
        return response.text

    async def summarize(self, text: str) -> dict:
        """Generate a structured summary via Gemini.

        Returns
        -------
        dict
            ``{"short_summary", "long_summary", "keywords", "entities"}``
        """
        prompt = _SUMMARIZE_PROMPT + text
        raw = await self.generate_text(prompt)
        logger.debug("Raw summarize response: %s", raw[:500])

        # Strip markdown fences if the model wraps them anyway.
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[: cleaned.rfind("```")]
        cleaned = cleaned.strip()

        try:
            parsed: dict = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Gemini returned non-JSON summary; using fallback.")
            parsed = {
                "short_summary": raw[:200],
                "long_summary": raw,
                "keywords": [],
                "entities": [],
            }

        # Ensure all expected keys exist.
        return {
            "short_summary": parsed.get("short_summary", ""),
            "long_summary": parsed.get("long_summary", ""),
            "keywords": parsed.get("keywords", []),
            "entities": parsed.get("entities", []),
        }
