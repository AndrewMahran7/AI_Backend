#!/usr/bin/env python
"""Dentrix ↔ Backend CLI sync tool.

Run this script on the **local Windows machine** that has ODBC access to
the Dentrix database.  It fetches records, normalises them, and POSTs
them in batches to the remote FastAPI backend.

Usage
-----
Test the ODBC + backend connections::

    python scripts/sync_dentrix.py --test-connection

Sync patients (default limit 100)::

    python scripts/sync_dentrix.py --object patients --limit 100

Sync appointments since a timestamp::

    python scripts/sync_dentrix.py --object appointments --limit 200 --since 2025-01-01T00:00:00

Sync all three object types::

    python scripts/sync_dentrix.py --object all --limit 50

Dry-run (fetch + normalize only, no POST)::

    python scripts/sync_dentrix.py --object patients --limit 10 --dry-run

Environment
-----------
All settings are pulled from environment variables or a ``.env`` file.
See ``.env.example`` for the full list.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path so relative imports work when
# running the script directly (e.g. ``python scripts/sync_dentrix.py``).
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_PROJECT_ROOT / ".env")

from app.providers.adapters.dentrix_adapter import DentrixAdapter  # noqa: E402
from app.providers.adapters.dentrix_connector import DentrixConnector  # noqa: E402
from app.services.dentrix_sync_service import DentrixSyncService  # noqa: E402

# ── Logging setup ─────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("sync_dentrix")


# ── CLI commands ──────────────────────────────────────────────────────────

async def cmd_test_connection() -> None:
    """Test the Dentrix ODBC and backend connections."""
    service = DentrixSyncService(enable_file_logging=False)
    result = await service.test_connection()

    print("\n══════════════════════════════════════")
    print("  Dentrix Connection Test")
    print("══════════════════════════════════════")
    print(f"  Dentrix ODBC : {'✓ PASS' if result['dentrix_ok'] else '✗ FAIL'}")
    print(f"  Backend HTTP : {'✓ PASS' if result['backend_ok'] else '✗ FAIL'}")
    print(f"  Backend URL  : {result['backend_url']}")
    print("══════════════════════════════════════\n")

    if not result["dentrix_ok"]:
        print("⚠  Dentrix ODBC connection failed.")
        print("   Check DENTRIX_ODBC_* environment variables and ODBC driver setup.\n")
    if not result["backend_ok"]:
        print("⚠  Backend health check failed.")
        print("   Check DENTRIX_BACKEND_URL and ensure the backend is running.\n")

    sys.exit(0 if result["dentrix_ok"] and result["backend_ok"] else 1)


async def cmd_sync(
    object_type: str,
    limit: int,
    since: str | None,
    dry_run: bool,
) -> None:
    """Run the sync pipeline for one or all object types."""
    service = DentrixSyncService()

    if dry_run:
        logger.info("DRY RUN — records will be fetched and normalized but NOT posted")
        adapter = DentrixAdapter()

        object_types = (
            ["patients", "appointments", "providers"]
            if object_type == "all"
            else [object_type]
        )

        for ot in object_types:
            raw = await adapter.fetch_records(object_type=ot, limit=limit, since=since)
            normalized = []
            for r in raw:
                try:
                    normalized.append(await adapter.normalize_record(r))
                except Exception:
                    logger.exception("Normalization failed for %s", r)

            print(f"\n── {ot} ({len(raw)} fetched → {len(normalized)} normalized) ──")
            for rec in normalized[:5]:
                print(json.dumps(rec, indent=2, default=str))
            if len(normalized) > 5:
                print(f"  ... and {len(normalized) - 5} more")
        return

    if object_type == "all":
        results = await service.sync_all(limit=limit, since=since)
    else:
        results = {object_type: await service.sync(object_type=object_type, limit=limit, since=since)}

    # Print report
    print("\n══════════════════════════════════════════════════════")
    print("  Dentrix Sync Report")
    print("══════════════════════════════════════════════════════")

    for ot, summary in results.items():
        print(f"\n  [{ot.upper()}]")
        print(f"    Fetched         : {summary['fetched']}")
        print(f"    Normalized      : {summary['normalized']}")
        print(f"    Sent            : {summary['sent']}")
        print(f"    Succeeded       : {summary['succeeded']}")
        print(f"    Failed          : {summary['failed']}")
        print(f"    Dup. Skipped    : {summary['skipped_duplicates']}")
        print(f"    Batches         : {summary['batches']}")
        print(f"    Elapsed         : {summary['elapsed_seconds']}s")

        if summary.get("errors"):
            print(f"    Errors ({len(summary['errors'])}):")
            for err in summary["errors"][:5]:
                print(f"      - {err}")

    print("\n══════════════════════════════════════════════════════\n")

    # Exit with error if any failures
    total_failed = sum(r.get("failed", 0) for r in results.values())
    sys.exit(1 if total_failed > 0 else 0)


# ── Argument parser ──────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sync_dentrix",
        description="Dentrix → AI Backend sync CLI",
    )
    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="Test the Dentrix ODBC and backend connections, then exit.",
    )
    parser.add_argument(
        "--object",
        dest="object_type",
        choices=["patients", "appointments", "providers", "all"],
        default="patients",
        help="Dentrix object type to sync (default: patients).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of records to fetch (default: 100).",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="ISO-8601 timestamp for incremental sync (e.g. 2025-01-01T00:00:00).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and normalize records but do NOT post to the backend.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.test_connection:
        asyncio.run(cmd_test_connection())
    else:
        asyncio.run(
            cmd_sync(
                object_type=args.object_type,
                limit=args.limit,
                since=args.since,
                dry_run=args.dry_run,
            )
        )


if __name__ == "__main__":
    main()
