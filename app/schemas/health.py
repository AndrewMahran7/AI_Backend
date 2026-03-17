"""Pydantic response schemas for the health endpoint."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response returned by ``GET /health``."""

    status: str = "ok"
