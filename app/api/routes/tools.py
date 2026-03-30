"""Tools route – lists available tools."""

from fastapi import APIRouter

from app.tools.registry import ToolRegistry

router = APIRouter(tags=["tools"])


@router.get(
    "/tools",
    summary="List available tools",
    description="Return all registered tools. Currently returns an empty list (future-ready).",
)
async def list_tools() -> dict:
    return {"tools": ToolRegistry.list_tools()}
