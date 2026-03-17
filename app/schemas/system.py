"""Pydantic response schemas for the system info endpoint."""

from pydantic import BaseModel


class SystemInfoResponse(BaseModel):
    """Non-secret runtime metadata returned by ``GET /system/info``."""

    app_name: str
    version: str
    environment: str
    debug: bool
    api_prefix: str
    database_configured: bool
    gemini_configured: bool
