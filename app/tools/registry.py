"""Tool registry – central catalogue of available tools."""

from typing import Any

from app.tools.base import BaseTool


class ToolRegistry:
    """Singleton-style registry for all registered tools."""

    _tools: dict[str, BaseTool] = {}

    @classmethod
    def register(cls, tool: BaseTool) -> None:
        """Register a tool instance by its name."""
        cls._tools[tool.name] = tool

    @classmethod
    def get(cls, name: str) -> BaseTool | None:
        """Retrieve a registered tool by name."""
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> list[dict[str, str]]:
        """Return metadata for all registered tools."""
        return [t.to_dict() for t in cls._tools.values()]

    @classmethod
    def clear(cls) -> None:
        """Remove all registered tools (useful for testing)."""
        cls._tools.clear()
