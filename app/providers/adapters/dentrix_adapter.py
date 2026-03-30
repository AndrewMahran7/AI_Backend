"""Dentrix adapter – transformation layer.

Bridges the low-level ``DentrixConnector`` (ODBC rows) and the backend's
internal record schema used by the ingestion pipeline.  Follows the same
``BaseAdapter`` contract as the SAP PLM adapter so the system can drive
multiple data sources through a single interface.

Architecture
------------
::

    Dentrix DB  ──ODBC──▶  DentrixConnector
                                 │
                                 ▼
                          DentrixAdapter
                           ├─ fetch_patients()
                           ├─ fetch_appointments()
                           ├─ fetch_providers()
                           └─ normalize_record()
                                 │
                                 ▼
                         Internal record schema
                            {title, content, type, source, external_id, metadata}

Design notes
~~~~~~~~~~~~
* **No schema assumptions** — the connector returns whatever columns
  Dentrix exposes.  This adapter uses *placeholder* column names that are
  easy to swap once the real Dentrix views are inspected.
* **All raw fields preserved** — ``normalize_record`` copies every column
  into ``metadata`` so nothing is lost during transformation.
* Field-mapping tables (``_FIELD_MAP``) are centralised at the top of the
  module for single-place editing.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from app.providers.adapters.base import BaseAdapter
from app.providers.adapters.dentrix_connector import DentrixConnector, DENTRIX_QUERIES

logger = logging.getLogger(__name__)

# ── Field mapping catalogue ──────────────────────────────────────────────
# Keys are the *expected* column names coming out of the Dentrix view.
# Replace the values here once real column names are confirmed — nothing
# else in the module needs to change.
#
# ``title_fields``   – columns used to build the record title
# ``content_fields`` – columns concatenated for full-text content
# ``id_fields``      – columns combined to derive ``external_id``

_FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "patient": {
        "title_fields":   ["last_name", "first_name"],
        "content_fields": [
            "last_name", "first_name", "middle_name",
            "date_of_birth", "gender", "ssn_last4",
            "address1", "address2", "city", "state", "zip_code",
            "phone_home", "phone_cell", "email",
            "insurance_carrier", "policy_number",
            "preferred_provider", "patient_status",
        ],
        "id_fields":      ["patient_id"],
    },
    "appointment": {
        "title_fields":   ["patient_name", "appt_date", "appt_time"],
        "content_fields": [
            "patient_name", "patient_id",
            "appt_date", "appt_time", "appt_length",
            "provider_name", "provider_id",
            "operatory", "appt_status",
            "procedure_codes", "description", "notes",
        ],
        "id_fields":      ["appointment_id"],
    },
    "provider": {
        "title_fields":   ["provider_name"],
        "content_fields": [
            "provider_name", "provider_id",
            "npi", "license_number",
            "specialty", "provider_type",
            "phone", "email",
            "active_status",
        ],
        "id_fields":      ["provider_id"],
    },
}

# Readable type labels used in normalized records
_TYPE_LABELS: dict[str, str] = {
    "patient":     "dentrix_patient",
    "appointment": "dentrix_appointment",
    "provider":    "dentrix_provider",
}


class DentrixAdapter(BaseAdapter):
    """Transform Dentrix ODBC rows into the internal ingestion schema.

    Parameters
    ----------
    connector:
        Optional pre-built ``DentrixConnector``.  A fresh instance is
        created from environment variables when not supplied.
    """

    def __init__(self, connector: DentrixConnector | None = None) -> None:
        self._connector = connector or DentrixConnector()

    # ── helpers ───────────────────────────────────────────────────────────

    def _run_sync(self, fn, *args, **kwargs):
        """Execute a synchronous connector call in a thread so the
        adapter remains async-compatible."""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    @staticmethod
    def _safe_str(value: Any) -> str:
        """Convert a value to string, handling None and datetime."""
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value).strip()

    # ── BaseAdapter contract ──────────────────────────────────────────────

    async def test_connection(self) -> bool:
        """Verify reachability of the Dentrix ODBC data source."""
        try:
            result = await self._run_sync(self._connector.test_connection)
            return bool(result)
        except Exception:
            logger.exception("Dentrix: adapter-level connection test failed")
            return False

    async def fetch_records(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Generic fetch delegating to the appropriate typed method.

        Parameters
        ----------
        object_type : str
            ``"patients"``, ``"appointments"``, or ``"providers"``.
        limit : int
            Maximum rows to retrieve (default 100).
        since : str | None
            ISO-8601 timestamp for incremental sync (optional).
        """
        object_type: str = kwargs.get("object_type", "patients")
        limit: int = int(kwargs.get("limit", 100))
        since: str | None = kwargs.get("since")

        dispatch = {
            "patients":     self.fetch_patients,
            "appointments": self.fetch_appointments,
            "providers":    self.fetch_providers,
        }
        handler = dispatch.get(object_type)
        if handler is None:
            raise ValueError(
                f"Unknown Dentrix object type '{object_type}'.  "
                f"Supported: {list(dispatch)}"
            )
        return await handler(limit=limit, since=since)

    async def fetch_patients(
        self,
        limit: int = 100,
        since: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch patient records from Dentrix."""
        query_name = "patients_incremental" if since else "patients"
        params = (since,) if since else None
        rows = await self._run_sync(
            self._connector.execute_query,
            query_name,
            limit=limit,
            params=params,
        )
        logger.info("Dentrix: fetched %d patient records", len(rows))
        return [{"_dentrix_object_type": "patient", **r} for r in rows]

    async def fetch_appointments(
        self,
        limit: int = 100,
        since: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch appointment records from Dentrix."""
        query_name = "appointments_incremental" if since else "appointments"
        params = (since,) if since else None
        rows = await self._run_sync(
            self._connector.execute_query,
            query_name,
            limit=limit,
            params=params,
        )
        logger.info("Dentrix: fetched %d appointment records", len(rows))
        return [{"_dentrix_object_type": "appointment", **r} for r in rows]

    async def fetch_providers(
        self,
        limit: int = 100,
        since: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch provider records from Dentrix."""
        query_name = "providers_incremental" if since else "providers"
        params = (since,) if since else None
        rows = await self._run_sync(
            self._connector.execute_query,
            query_name,
            limit=limit,
            params=params,
        )
        logger.info("Dentrix: fetched %d provider records", len(rows))
        return [{"_dentrix_object_type": "provider", **r} for r in rows]

    # ── Normalisation ─────────────────────────────────────────────────────

    async def normalize_record(self, raw_record: dict[str, Any]) -> dict[str, Any]:
        """Map a raw Dentrix row into the internal ingestion schema.

        Schema::

            {
                "title":       str,
                "content":     str,
                "type":        str,       # e.g. "dentrix_patient"
                "source":      str,       # always "dentrix"
                "external_id": str|None,
                "metadata":    dict,      # ALL raw fields preserved
            }
        """
        obj_type: str = raw_record.get("_dentrix_object_type", "unknown")
        field_map = _FIELD_MAP.get(obj_type, {})

        # ── Title ─────────────────────────────────────────────────────────
        title_fields = field_map.get("title_fields", [])
        title_parts = [
            self._safe_str(raw_record.get(f))
            for f in title_fields
            if raw_record.get(f) is not None
        ]
        title = " ".join(title_parts).strip()

        # Fallback: first non-empty string column
        if not title:
            for key, val in raw_record.items():
                if not key.startswith("_") and isinstance(val, str) and val.strip():
                    title = val.strip()
                    break
        title = title or f"Dentrix {obj_type} record"

        # ── Content ───────────────────────────────────────────────────────
        content_fields = field_map.get("content_fields", [])
        parts: list[str] = []
        for field in content_fields:
            val = raw_record.get(field)
            if val is not None:
                parts.append(f"{field}: {self._safe_str(val)}")

        # Include any remaining columns not yet covered
        covered = set(content_fields) | set(title_fields) | {"_dentrix_object_type"}
        for key, val in raw_record.items():
            if key not in covered and val is not None:
                parts.append(f"{key}: {self._safe_str(val)}")

        content = "\n".join(parts) if parts else title

        # ── External ID ──────────────────────────────────────────────────
        id_fields = field_map.get("id_fields", [])
        id_parts = [
            self._safe_str(raw_record.get(f))
            for f in id_fields
            if raw_record.get(f) is not None
        ]
        external_id = "-".join(id_parts) if id_parts else None

        # ── Metadata (ALL raw fields) ────────────────────────────────────
        metadata: dict[str, Any] = {
            k: v for k, v in raw_record.items() if not k.startswith("_")
        }
        metadata["_object_type"] = obj_type

        return {
            "title":       title,
            "content":     content,
            "type":        _TYPE_LABELS.get(obj_type, f"dentrix_{obj_type}"),
            "source":      "dentrix",
            "external_id": external_id,
            "metadata":    metadata,
        }
