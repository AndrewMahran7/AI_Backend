"""Dentrix sync routes.

Endpoints
---------
POST /dentrix/sync/{object_type}
    Trigger a sync from the Dentrix database into the knowledge base.
    Supported object types: patients, appointments, providers.

GET  /dentrix/status
    Test connectivity to the configured Dentrix ODBC data source.

Note
----
These endpoints are useful when the backend runs on the **same LAN** as the
Dentrix machine (self-hosted).  For remote / cloud backends, use the
``sync_dentrix.py`` CLI agent running locally at the dental office.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.providers.adapters.dentrix_adapter import DentrixAdapter
from app.providers.embeddings.gemini_embeddings import GeminiEmbeddingProvider
from app.providers.llm.gemini_provider import GeminiLLMProvider
from app.schemas.dentrix import (
    DentrixConnectionStatus,
    DentrixSyncRequest,
    DentrixSyncResponse,
)
from app.services.ingestion_service import IngestionService

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dentrix", tags=["dentrix"])

# Maps URL slug → adapter method name
_OBJECT_TYPE_MAP: dict[str, str] = {
    "patients":     "fetch_patients",
    "appointments": "fetch_appointments",
    "providers":    "fetch_providers",
}


@router.post(
    "/sync/{object_type}",
    response_model=DentrixSyncResponse,
    status_code=202,
    summary="Sync Dentrix object family",
    description=(
        "Fetch records from the Dentrix ODBC database and queue them for "
        "AI processing (chunking, embedding, summarisation).  Read-only — "
        "nothing is written back to Dentrix."
    ),
)
async def sync_dentrix_object(
    object_type: str,
    body: DentrixSyncRequest,
    session: AsyncSession = Depends(get_db),
) -> DentrixSyncResponse:
    """Trigger a Dentrix → knowledge base sync for *object_type*."""
    fetch_method_name = _OBJECT_TYPE_MAP.get(object_type)
    if fetch_method_name is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported Dentrix object type '{object_type}'.  "
                f"Supported values: {list(_OBJECT_TYPE_MAP)}"
            ),
        )

    adapter = DentrixAdapter()
    fetch_method = getattr(adapter, fetch_method_name)
    raw_records = await fetch_method(limit=body.limit, since=body.since)

    # Normalise and queue via the ingestion service
    llm = GeminiLLMProvider()
    embeddings = GeminiEmbeddingProvider()
    ingestion = IngestionService(session=session, llm=llm, embeddings=embeddings)

    queued = 0
    failed = 0

    for raw in raw_records:
        try:
            normalised = await adapter.normalize_record(raw)
            await ingestion.create_record_and_job(
                title=normalised["title"],
                content=normalised["content"],
                type=normalised["type"],
                source=normalised["source"],
                external_id=normalised.get("external_id"),
                metadata=normalised.get("metadata"),
            )
            queued += 1
        except Exception:
            logger.exception(
                "Failed to ingest Dentrix %s record: %s", object_type, raw,
            )
            failed += 1

    logger.info(
        "Dentrix sync %s: fetched=%d queued=%d failed=%d",
        object_type, len(raw_records), queued, failed,
    )

    return DentrixSyncResponse(
        object_type=object_type,
        requested=body.limit,
        fetched=len(raw_records),
        queued=queued,
        failed=failed,
    )


@router.get(
    "/status",
    response_model=DentrixConnectionStatus,
    summary="Dentrix connection status",
    description="Test whether the configured Dentrix ODBC data source is reachable.",
)
async def dentrix_status() -> DentrixConnectionStatus:
    """Return connectivity status for the Dentrix ODBC connection."""
    adapter = DentrixAdapter()
    reachable = await adapter.test_connection()
    return DentrixConnectionStatus(
        reachable=reachable,
        message=(
            "Dentrix ODBC connection is reachable."
            if reachable
            else "Dentrix ODBC connection failed.  Check DENTRIX_ODBC_* env vars."
        ),
    )
