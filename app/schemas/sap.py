"""Pydantic schemas for the SAP PLM sync endpoint."""

from pydantic import BaseModel, Field


class SAPSyncRequest(BaseModel):
    """Request body for ``POST /sap/sync/{object_type}``."""

    limit: int = Field(
        default=25,
        ge=1,
        le=500,
        description="Maximum number of records to fetch from SAP per sync run.",
    )


class SAPSyncResponse(BaseModel):
    """Response returned by ``POST /sap/sync/{object_type}``."""

    object_type: str = Field(..., description="SAP object family that was synced.")
    requested:   int = Field(..., description="Limit requested by the caller.")
    fetched:     int = Field(..., description="Records returned by SAP.")
    queued:      int = Field(..., description="Records successfully queued for ingestion.")
    failed:      int = Field(default=0, description="Records that could not be ingested.")


class SAPConnectionStatus(BaseModel):
    """Response returned by ``GET /sap/status``."""

    reachable: bool
    base_url:  str
    message:   str
