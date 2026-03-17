"""Gemini embedding provider using the Google GenAI SDK (google-genai)."""

import logging

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.providers.embeddings.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Embedding provider backed by Google Gemini (gemini-embedding-001).

    Supports two authentication modes controlled by ``GEMINI_TIER``:

    - ``dev``        – standard API key via ``GEMINI_API_KEY``
    - ``enterprise`` – Vertex AI using Application Default Credentials.
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
        self._model = settings.GEMINI_EMBEDDING_MODEL
        self._dimension = settings.EMBEDDING_DIMENSION

    async def embed_text(self, text: str) -> list[float]:
        """Generate an embedding for a single text string."""
        response = await self._client.aio.models.embed_content(
            model=self._model,
            contents=text,
            config=types.EmbedContentConfig(
                output_dimensionality=self._dimension,
            ),
        )
        return list(response.embeddings[0].values)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        The GenAI SDK accepts a list for the *contents* parameter,
        returning one embedding per item.
        """
        if not texts:
            return []

        response = await self._client.aio.models.embed_content(
            model=self._model,
            contents=texts,
            config=types.EmbedContentConfig(
                output_dimensionality=self._dimension,
            ),
        )
        return [list(e.values) for e in response.embeddings]
