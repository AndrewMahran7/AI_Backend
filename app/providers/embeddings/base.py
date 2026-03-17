"""Abstract base class for embedding providers."""

from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    """Contract that every embedding provider must fulfil."""

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text.

        Parameters
        ----------
        text:
            The input string to embed.

        Returns
        -------
        list[float]
            A dense vector of floats.
        """
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a batch of texts.

        Parameters
        ----------
        texts:
            A list of input strings.

        Returns
        -------
        list[list[float]]
            One embedding vector per input string, in the same order.
        """
        ...
