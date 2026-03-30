"""Base class for pluggable tools."""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Abstract base for all tools that can be registered in the system."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""
        ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Run the tool with the given arguments and return a result."""
        ...

    def to_dict(self) -> dict[str, str]:
        """Serialise tool metadata for API responses."""
        return {
            "name": self.name,
            "description": self.description,
        }
