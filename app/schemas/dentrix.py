"""Pydantic schemas for the Dentrix sync endpoints."""

from pydantic import BaseModel, Field


class DentrixSyncRequest(BaseModel):
    """Request body for ``POST /dentrix/sync/{object_type}``."""

    limit: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Maximum number of records to fetch from Dentrix per sync run.",
    )
    since: str | None = Field(
        default=None,
        description=(
            "Optional ISO-8601 timestamp for incremental sync.  "
            "Only records modified after this time are fetched."
        ),
    )


class DentrixSyncResponse(BaseModel):
    """Response returned by ``POST /dentrix/sync/{object_type}``."""

    object_type: str = Field(..., description="Dentrix object family that was synced.")
    requested: int = Field(..., description="Limit requested by the caller.")
    fetched: int = Field(..., description="Records returned by Dentrix.")
    queued: int = Field(..., description="Records successfully queued for ingestion.")
    failed: int = Field(default=0, description="Records that could not be ingested.")


class DentrixConnectionStatus(BaseModel):
    """Response returned by ``GET /dentrix/status``."""

    reachable: bool
    message: str
