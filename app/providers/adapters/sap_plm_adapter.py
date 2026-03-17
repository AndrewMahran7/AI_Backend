"""SAP PLM read-only adapter.

This adapter normalises data from SAP Product Lifecycle Management (PLM) into
the backend's internal record schema.  It is intentionally generic — no
company-specific field mappings or business rules are baked in.

All SAP endpoint paths are centralised in ``_SAP_ENDPOINTS`` at the top of
this module.  Swap the values there when real service paths are confirmed;
the rest of the adapter requires no changes.

Authentication
--------------
SAP_AUTH_TYPE controls which scheme is used:

  basic       HTTP Basic (username + password)
  oauth2      Bearer token sourced from ``SAP_OAUTH_TOKEN``

The adapter never stores credentials beyond the request lifecycle.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.providers.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

settings = get_settings()

# ── Endpoint catalogue ────────────────────────────────────────────────────
# All SAP OData / REST paths live here.  Until confirmed,
# placeholder paths follow the common SAP S/4HANA OData v4 convention.

_SAP_ENDPOINTS: dict[str, str] = {
    "health":          "/sap/opu/odata4/sap/api_healthcheck/srvd_a2x/sap/healthcheck/0001/HealthCheck",
    "materials":       "/sap/opu/odata/sap/API_MATERIAL_STOCK_SRV/A_MaterialStock",
    "documents":       "/sap/opu/odata/sap/API_CV_ATTACHMENT_SRV/AttachmentContentSet",
    "boms":            "/sap/opu/odata/sap/API_BILL_OF_MATERIAL_SRV/MaterialBOMItem",
    "change_records":  "/sap/opu/odata/sap/API_CHANGERECORD_SRV/A_ChangeRecord",
}

# Fields that every SAP object family might contain.  Used during
# normalisation to extract content text and metadata keys without
# hard-coding any company schema.

_OBJECT_CONTENT_FIELDS: dict[str, list[str]] = {
    "material":       ["MaterialDescription", "BaseUnit", "MaterialGroup", "GrossWeight"],
    "document":       ["DocumentDescription", "DocumentPart", "DocumentVersion"],
    "bom":            ["BOMDescription", "BOMCategory", "BOMType", "ComponentQuantity"],
    "change_record":  ["ChangeRecordDescription", "ChangeRecordType", "ValidityStartDate"],
}

_OBJECT_TITLE_FIELD: dict[str, str] = {
    "material":      "Material",
    "document":      "DocumentNumber",
    "bom":           "BillOfMaterial",
    "change_record": "ChangeRecord",
}


class SAPPLMAdapter(BaseAdapter):
    """Generic, read-only adapter for SAP PLM object families.

    Parameters
    ----------
    base_url:
        Root URL of the SAP system, e.g. ``https://my-sap.example.com``.
        Defaults to ``settings.SAP_BASE_URL``.
    username:
        SAP dialog or service user.  Defaults to ``settings.SAP_USERNAME``.
    password:
        Corresponding password.  Defaults to ``settings.SAP_PASSWORD``.
    client:
        SAP client / Mandant number, e.g. ``"100"``.  Defaults to
        ``settings.SAP_CLIENT``.
    auth_type:
        ``"basic"`` or ``"oauth2"``.  Defaults to ``settings.SAP_AUTH_TYPE``.
    timeout:
        Per-request timeout in seconds.  Defaults to
        ``settings.SAP_TIMEOUT_SECONDS``.
    """

    def __init__(
        self,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        client: str | None = None,
        auth_type: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self._base_url = (base_url or settings.SAP_BASE_URL).rstrip("/")
        self._username = username or settings.SAP_USERNAME
        self._password = password or settings.SAP_PASSWORD
        self._client = client or settings.SAP_CLIENT
        self._auth_type = (auth_type or settings.SAP_AUTH_TYPE).lower()
        self._timeout = timeout or settings.SAP_TIMEOUT_SECONDS

    # ── Internal helpers ──────────────────────────────────────────────────

    def _build_client(self) -> httpx.AsyncClient:
        """Return a configured httpx.AsyncClient for this connection."""
        headers: dict[str, str] = {
            "Accept": "application/json",
            "sap-client": self._client,
        }
        auth: tuple[str, str] | None = None

        if self._auth_type == "basic":
            auth = (self._username, self._password)
        elif self._auth_type == "oauth2":
            token = settings.SAP_OAUTH_TOKEN
            if token:
                headers["Authorization"] = f"Bearer {token}"
            else:
                logger.warning(
                    "SAP_AUTH_TYPE=oauth2 but SAP_OAUTH_TOKEN is not set; "
                    "requests will be unauthenticated."
                )

        return httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            auth=auth,
            timeout=float(self._timeout),
        )

    async def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform a GET request and return parsed JSON.

        Returns an empty ``{"value": []}`` envelope on any error so
        callers can always iterate ``.get("value", [])`` safely.
        """
        async with self._build_client() as client:
            try:
                resp = await client.get(path, params=params or {})
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "SAP HTTP %s for %s: %s",
                    exc.response.status_code,
                    path,
                    exc.response.text[:200],
                )
            except httpx.RequestError as exc:
                logger.error("SAP request error for %s: %s", path, exc)
        return {"value": []}

    # ── BaseAdapter contract ──────────────────────────────────────────────

    async def test_connection(self) -> bool:
        """Ping the SAP health-check endpoint.

        Returns ``True`` only when the system responds with HTTP 2xx.
        """
        async with self._build_client() as client:
            try:
                resp = await client.get(_SAP_ENDPOINTS["health"])
                ok = resp.is_success
                logger.info("SAP connection test: %s (%s)", "OK" if ok else "FAIL", resp.status_code)
                return ok
            except httpx.RequestError as exc:
                logger.error("SAP connection test failed: %s", exc)
                return False

    async def fetch_records(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Generic fetch delegating to the appropriate typed method.

        Pass ``object_type`` in ``kwargs`` to select the object family.
        Supported values: ``"materials"``, ``"documents"``,
        ``"boms"``, ``"change_records"``.
        """
        object_type: str = kwargs.get("object_type", "materials")
        limit: int = int(kwargs.get("limit", 100))

        dispatch = {
            "materials":       self.fetch_materials,
            "documents":       self.fetch_documents,
            "boms":            self.fetch_boms,
            "change_records":  self.fetch_change_records,
        }
        handler = dispatch.get(object_type)
        if handler is None:
            raise ValueError(
                f"Unknown SAP object type '{object_type}'. "
                f"Supported: {list(dispatch)}"
            )
        return await handler(limit=limit)

    # ── Object-family fetch methods ───────────────────────────────────────

    async def fetch_materials(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch material master records from SAP PLM."""
        data = await self._get(
            _SAP_ENDPOINTS["materials"],
            params={"$top": limit, "$format": "json"},
        )
        records = data.get("value", data.get("d", {}).get("results", []))
        logger.info("SAP: fetched %d material records", len(records))
        return [{"_sap_object_type": "material", **r} for r in records]

    async def fetch_documents(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch document info records (DIR) from SAP PLM."""
        data = await self._get(
            _SAP_ENDPOINTS["documents"],
            params={"$top": limit, "$format": "json"},
        )
        records = data.get("value", data.get("d", {}).get("results", []))
        logger.info("SAP: fetched %d document records", len(records))
        return [{"_sap_object_type": "document", **r} for r in records]

    async def fetch_boms(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch bill-of-materials items from SAP PLM."""
        data = await self._get(
            _SAP_ENDPOINTS["boms"],
            params={"$top": limit, "$format": "json"},
        )
        records = data.get("value", data.get("d", {}).get("results", []))
        logger.info("SAP: fetched %d BOM records", len(records))
        return [{"_sap_object_type": "bom", **r} for r in records]

    async def fetch_change_records(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch engineering change records from SAP PLM."""
        data = await self._get(
            _SAP_ENDPOINTS["change_records"],
            params={"$top": limit, "$format": "json"},
        )
        records = data.get("value", data.get("d", {}).get("results", []))
        logger.info("SAP: fetched %d change records", len(records))
        return [{"_sap_object_type": "change_record", **r} for r in records]

    # ── Normalisation ─────────────────────────────────────────────────────

    async def normalize_record(self, raw_record: dict[str, Any]) -> dict[str, Any]:
        """Map a raw SAP object into the internal ingestion schema.

        The mapping is intentionally generic — it extracts whatever
        text fields are present and surfaces everything else as
        structured metadata.

        Internal schema (matches ``IngestRequest``):

        .. code-block:: python

            {
                "title":       str,   # mandatory
                "content":     str,   # mandatory – full-text for chunking
                "type":        str,   # record type tag
                "source":      str,   # always "sap_plm"
                "external_id": str,   # SAP primary key if present
                "metadata":    dict,  # structured fields for filtering
            }
        """
        obj_type: str = raw_record.get("_sap_object_type", "unknown")
        content_fields = _OBJECT_CONTENT_FIELDS.get(obj_type, [])
        title_field = _OBJECT_TITLE_FIELD.get(obj_type, "")

        # Build title — fall back to first available string key if missing
        title = str(raw_record.get(title_field, "")).strip()
        if not title:
            for key, val in raw_record.items():
                if not key.startswith("_") and isinstance(val, str) and val.strip():
                    title = val.strip()
                    break
        title = title or f"SAP {obj_type} record"

        # Build content from relevant text fields
        parts: list[str] = []
        for field in content_fields:
            val = raw_record.get(field)
            if val and str(val).strip():
                parts.append(f"{field}: {val}")

        # Append any remaining string fields not already included
        covered = set(content_fields) | {title_field, "_sap_object_type"}
        for key, val in raw_record.items():
            if key not in covered and isinstance(val, str) and val.strip():
                parts.append(f"{key}: {val}")

        content = "\n".join(parts) if parts else title

        # External ID — prefer dedicated key patterns common in SAP OData
        external_id: str | None = None
        for candidate in (title_field, "ObjectKey", "Guid", "ExternalDocumentKey"):
            v = raw_record.get(candidate)
            if v and str(v).strip():
                external_id = str(v)
                break

        # Metadata — everything except private keys
        metadata: dict[str, Any] = {
            k: v
            for k, v in raw_record.items()
            if not k.startswith("_")
        }

        return {
            "title":       title,
            "content":     content,
            "type":        f"sap_{obj_type}",
            "source":      "sap_plm",
            "external_id": external_id,
            "metadata":    metadata,
        }
