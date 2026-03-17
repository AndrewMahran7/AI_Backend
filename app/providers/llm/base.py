"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """Contract that every LLM provider must fulfil."""

    @abstractmethod
    async def generate_text(self, prompt: str) -> str:
        """Generate text from a prompt.

        Parameters
        ----------
        prompt:
            The input prompt to send to the model.

        Returns
        -------
        str
            The generated text response.
        """
        ...

    @abstractmethod
    async def summarize(self, text: str) -> dict:
        """Produce a structured summary of the input text.

        Returns
        -------
        dict
            A dictionary with keys: ``short_summary``, ``long_summary``,
            ``keywords``, ``entities``.
        """
        ...
