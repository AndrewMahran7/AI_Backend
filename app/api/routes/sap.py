"""SAP PLM sync routes.

Endpoints
---------
POST /sap/sync/{object_type}
    Trigger a read-only sync from SAP PLM into the knowledge base.
    Supported object types: materials, documents, boms, change-records.

GET  /sap/status
    Test connectivity to the configured SAP system.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import get_settings
from app.providers.adapters.sap_plm_adapter import SAPPLMAdapter
from app.schemas.sap import SAPConnectionStatus, SAPSyncRequest, SAPSyncResponse
from app.services.sap_sync_service import SAPSyncService

router = APIRouter(prefix="/sap", tags=["sap"])

settings = get_settings()

# Maps URL-safe slug → service method name
_OBJECT_TYPE_MAP: dict[str, str] = {
    "materials":       "sync_materials",
    "documents":       "sync_documents",
    "boms":            "sync_boms",
    "change-records":  "sync_change_records",
}


@router.post(
    "/sync/{object_type}",
    response_model=SAPSyncResponse,
    status_code=202,
    summary="Sync SAP PLM object family",
    description=(
        "Fetch records from SAP PLM and queue them for AI processing "
        "(chunking, embedding, summarisation).  The sync is read-only — "
        "no data is written back to SAP."
    ),
)
async def sync_sap_object(
    object_type: str,
    body: SAPSyncRequest,
    session: AsyncSession = Depends(get_db),
) -> SAPSyncResponse:
    """Trigger a SAP → knowledge base sync for *object_type*."""
    method_name = _OBJECT_TYPE_MAP.get(object_type)
    if method_name is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported SAP object type '{object_type}'. "
                f"Supported values: {list(_OBJECT_TYPE_MAP)}"
            ),
        )

    service = SAPSyncService(session=session)
    method = getattr(service, method_name)
    result = await method(limit=body.limit)

    return SAPSyncResponse(
        object_type=result["object_type"],
        requested=body.limit,
        fetched=result["fetched"],
        queued=result["queued"],
        failed=result["failed"],
    )


@router.get(
    "/status",
    response_model=SAPConnectionStatus,
    summary="SAP connection status",
    description="Test whether the configured SAP system is reachable.",
)
async def sap_status() -> SAPConnectionStatus:
    """Return connectivity status for the SAP backend."""
    adapter = SAPPLMAdapter()
    reachable = await adapter.test_connection()
    return SAPConnectionStatus(
        reachable=reachable,
        base_url=settings.SAP_BASE_URL or "(not configured)",
        message="SAP system is reachable." if reachable else "SAP system is not reachable.",
    )
