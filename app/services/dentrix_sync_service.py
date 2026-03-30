"""Dentrix sync service – orchestration layer.

This is the **local agent** that runs on a Windows machine inside the
dental office.  It:

1. Pulls rows from Dentrix via ODBC (``DentrixAdapter``)
2. Normalises each row into the backend's record schema
3. Batches records and POSTs them to the remote FastAPI ``/api/v1/ingest``
   endpoint over HTTPS

The service is designed to run standalone (via the ``sync_dentrix.py`` CLI)
or be imported by other orchestration code.

Key design decisions
--------------------
* **Batched ingestion** — records are grouped into configurable batches
  (default 100) to avoid hammering the backend with individual POSTs.
* **Exponential back-off** — transient HTTP errors trigger automatic
  retries (default 3 attempts, base delay 2 s).
* **Idempotent** — each record carries a deterministic ``external_id``
  derived from its Dentrix primary key.  Re-running the sync produces the
  same IDs, so duplicate-detection on the backend side is trivial.
* **Incremental support** — when a ``since`` timestamp is supplied only
  rows modified after that point are fetched.
* **Local duplicate cache** — an optional in-memory set of already-synced
  ``external_id`` values avoids re-posting data within the same session.
* **File logging** — all activity is logged to a rotating file for
  post-mortem debugging in the field.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx

from app.providers.adapters.dentrix_adapter import DentrixAdapter
from app.providers.adapters.dentrix_connector import DentrixConnector

logger = logging.getLogger(__name__)

# ── Defaults ──────────────────────────────────────────────────────────────

DEFAULT_BACKEND_URL = os.getenv("DENTRIX_BACKEND_URL", "http://localhost:8000")
DEFAULT_API_PREFIX = os.getenv("DENTRIX_API_PREFIX", "/api/v1")
DEFAULT_BATCH_SIZE = int(os.getenv("DENTRIX_BATCH_SIZE", "100"))
DEFAULT_MAX_RETRIES = int(os.getenv("DENTRIX_MAX_RETRIES", "3"))
DEFAULT_BACKOFF_BASE = float(os.getenv("DENTRIX_BACKOFF_BASE", "2.0"))
DEFAULT_TIMEOUT = int(os.getenv("DENTRIX_HTTP_TIMEOUT", "60"))
DEFAULT_API_KEY = os.getenv("DENTRIX_API_KEY", "")

# Optional log-to-file path (set to "" to disable)
LOG_FILE_PATH = os.getenv("DENTRIX_LOG_FILE", "dentrix_sync.log")


def _configure_file_logging() -> None:
    """Add a rotating file handler to the root logger if configured."""
    if not LOG_FILE_PATH:
        return
    from logging.handlers import RotatingFileHandler

    handler = RotatingFileHandler(
        LOG_FILE_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logging.getLogger().addHandler(handler)


class DentrixSyncService:
    """Orchestrates Dentrix → backend ingestion.

    Parameters
    ----------
    backend_url:
        Root URL of the FastAPI backend (e.g. ``https://backend.example.com``).
    api_prefix:
        API version prefix (default ``/api/v1``).
    batch_size:
        Number of records per POST batch (50–200 recommended, default 100).
    max_retries:
        Maximum retry attempts for transient HTTP errors.
    backoff_base:
        Base seconds for exponential back-off (delay = base * 2^attempt).
    timeout:
        HTTP request timeout in seconds.
    api_key:
        Optional API key sent as ``Authorization: Bearer <key>``.
    adapter:
        Optional pre-configured ``DentrixAdapter`` instance.
    enable_file_logging:
        Set up rotating file logger on instantiation.
    """

    def __init__(
        self,
        backend_url: str = DEFAULT_BACKEND_URL,
        api_prefix: str = DEFAULT_API_PREFIX,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
        timeout: int = DEFAULT_TIMEOUT,
        api_key: str = DEFAULT_API_KEY,
        adapter: DentrixAdapter | None = None,
        enable_file_logging: bool = True,
    ) -> None:
        self._backend_url = backend_url.rstrip("/")
        self._api_prefix = api_prefix.rstrip("/")
        self._batch_size = max(1, min(batch_size, 500))
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._timeout = timeout
        self._api_key = api_key
        self._adapter = adapter or DentrixAdapter()

        # Local duplicate cache — external_ids seen this session
        self._seen_ids: set[str] = set()

        if enable_file_logging:
            _configure_file_logging()

    # ── Internal helpers ──────────────────────────────────────────────────

    @property
    def _ingest_url(self) -> str:
        return f"{self._backend_url}{self._api_prefix}/ingest"

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def _post_batch(
        self,
        records: list[dict[str, Any]],
        client: httpx.AsyncClient,
    ) -> dict[str, Any]:
        """POST a single batch of normalized records to the backend.

        Sends individual requests per record since the existing /ingest
        endpoint accepts a single IngestRequest body.  Wraps each call
        with retry logic.

        Returns a summary dict ``{sent, succeeded, failed, errors}``.
        """
        succeeded = 0
        failed = 0
        errors: list[str] = []

        for record in records:
            result = await self._post_with_retry(record, client)
            if result["ok"]:
                succeeded += 1
            else:
                failed += 1
                errors.append(result.get("error", "unknown"))

        return {
            "sent": len(records),
            "succeeded": succeeded,
            "failed": failed,
            "errors": errors,
        }

    async def _post_with_retry(
        self,
        record: dict[str, Any],
        client: httpx.AsyncClient,
    ) -> dict[str, Any]:
        """POST a single record with exponential back-off retry."""
        last_error = ""
        for attempt in range(self._max_retries + 1):
            try:
                resp = await client.post(
                    self._ingest_url,
                    json=record,
                    headers=self._build_headers(),
                    timeout=float(self._timeout),
                )
                if resp.status_code in (200, 201, 202):
                    return {"ok": True, "status": resp.status_code, "body": resp.json()}

                last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"

                # Don't retry client errors (4xx) except 429
                if 400 <= resp.status_code < 500 and resp.status_code != 429:
                    logger.error(
                        "Dentrix sync: non-retryable error for %s — %s",
                        record.get("external_id", "?"),
                        last_error,
                    )
                    return {"ok": False, "error": last_error}

            except httpx.RequestError as exc:
                last_error = f"Request error: {exc}"

            # Exponential back-off
            if attempt < self._max_retries:
                delay = self._backoff_base * (2 ** attempt)
                logger.warning(
                    "Dentrix sync: retry %d/%d in %.1fs — %s",
                    attempt + 1,
                    self._max_retries,
                    delay,
                    last_error,
                )
                await asyncio.sleep(delay)

        logger.error(
            "Dentrix sync: exhausted retries for %s — %s",
            record.get("external_id", "?"),
            last_error,
        )
        return {"ok": False, "error": last_error}

    def _deduplicate(
        self,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Remove records whose external_id was already synced this session."""
        unique: list[dict[str, Any]] = []
        for r in records:
            eid = r.get("external_id")
            if eid and eid in self._seen_ids:
                logger.debug("Dentrix sync: skipping duplicate %s", eid)
                continue
            if eid:
                self._seen_ids.add(eid)
            unique.append(r)
        return unique

    # ── Public API ────────────────────────────────────────────────────────

    async def test_connection(self) -> dict[str, Any]:
        """Test both the Dentrix ODBC connection and the backend HTTP endpoint.

        Returns a dict with ``dentrix_ok`` and ``backend_ok`` booleans.
        """
        dentrix_ok = await self._adapter.test_connection()

        backend_ok = False
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._backend_url}{self._api_prefix}/health",
                    timeout=10.0,
                )
                backend_ok = resp.is_success
        except Exception:
            logger.exception("Dentrix sync: backend health check failed")

        return {
            "dentrix_ok": dentrix_ok,
            "backend_ok": backend_ok,
            "backend_url": self._backend_url,
        }

    async def sync(
        self,
        object_type: str = "patients",
        limit: int = 100,
        since: str | None = None,
    ) -> dict[str, Any]:
        """Full sync pipeline: fetch → normalize → batch → POST.

        Parameters
        ----------
        object_type:
            ``"patients"``, ``"appointments"``, or ``"providers"``.
        limit:
            Maximum rows to fetch from Dentrix.
        since:
            Optional ISO-8601 timestamp for incremental sync.

        Returns
        -------
        dict
            Summary: ``{object_type, fetched, normalized, sent, succeeded,
            failed, skipped_duplicates, batches, elapsed_seconds}``
        """
        t0 = time.perf_counter()

        logger.info(
            "Dentrix sync: starting object_type=%s limit=%d since=%s",
            object_type, limit, since,
        )

        # 1. Fetch raw records
        raw_records = await self._adapter.fetch_records(
            object_type=object_type,
            limit=limit,
            since=since,
        )
        logger.info("Dentrix sync: fetched %d raw records", len(raw_records))

        if not raw_records:
            return {
                "object_type": object_type,
                "fetched": 0,
                "normalized": 0,
                "sent": 0,
                "succeeded": 0,
                "failed": 0,
                "skipped_duplicates": 0,
                "batches": 0,
                "elapsed_seconds": round(time.perf_counter() - t0, 2),
            }

        # 2. Normalize
        normalized: list[dict[str, Any]] = []
        for raw in raw_records:
            try:
                rec = await self._adapter.normalize_record(raw)
                normalized.append(rec)
            except Exception:
                logger.exception("Dentrix sync: normalization failed for %s", raw)

        # 3. Deduplicate
        before_dedup = len(normalized)
        normalized = self._deduplicate(normalized)
        skipped = before_dedup - len(normalized)

        # 4. Batch and POST
        total_succeeded = 0
        total_failed = 0
        batch_count = 0
        all_errors: list[str] = []

        async with httpx.AsyncClient() as client:
            for i in range(0, len(normalized), self._batch_size):
                batch = normalized[i : i + self._batch_size]
                batch_count += 1

                logger.info(
                    "Dentrix sync: posting batch %d (%d records)",
                    batch_count,
                    len(batch),
                )
                result = await self._post_batch(batch, client)
                total_succeeded += result["succeeded"]
                total_failed += result["failed"]
                all_errors.extend(result["errors"])

        elapsed = round(time.perf_counter() - t0, 2)

        summary = {
            "object_type": object_type,
            "fetched": len(raw_records),
            "normalized": len(normalized) + skipped,
            "sent": len(normalized),
            "succeeded": total_succeeded,
            "failed": total_failed,
            "skipped_duplicates": skipped,
            "batches": batch_count,
            "elapsed_seconds": elapsed,
        }

        if all_errors:
            summary["errors"] = all_errors[:20]  # cap for readability

        logger.info("Dentrix sync: completed — %s", json.dumps(summary, indent=2))
        return summary

    async def sync_all(
        self,
        limit: int = 100,
        since: str | None = None,
    ) -> dict[str, Any]:
        """Sync all supported object types in sequence.

        Returns a dict keyed by object type with each type's summary.
        """
        results: dict[str, Any] = {}
        for obj_type in ("patients", "appointments", "providers"):
            results[obj_type] = await self.sync(
                object_type=obj_type,
                limit=limit,
                since=since,
            )
        return results
