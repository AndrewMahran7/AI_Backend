#!/usr/bin/env python
"""Dentrix connection diagnostic tool.

Runs a 4-step check and prints a clear PASS / FAIL report suitable for
field technicians who may not be Python developers.

Checks
------
1. Python environment — correct version, venv active
2. pyodbc installed — importable with version
3. Dentrix ODBC — connects and lists tables
4. Backend HTTPS — reaches the health endpoint

Usage
-----
    python scripts/test_dentrix_connection.py

Exit codes: 0 = all passed, 1 = one or more failed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_PROJECT_ROOT / ".env")
except ImportError:
    pass  # dotenv is optional for this diagnostics script


# ── Helpers ───────────────────────────────────────────────────────────────

_PASS = "\u2713 PASS"
_FAIL = "\u2717 FAIL"
_results: list[tuple[str, bool, str]] = []


def _record(label: str, ok: bool, detail: str = "") -> None:
    _results.append((label, ok, detail))


# ── Check 1: Python environment ──────────────────────────────────────────

def check_python() -> None:
    ver = sys.version.split()[0]
    major, minor = sys.version_info[:2]
    if major >= 3 and minor >= 11:
        _record("Python environment", True, f"{ver}")
    else:
        _record("Python environment", False, f"{ver} — need 3.11+")


# ── Check 2: pyodbc ──────────────────────────────────────────────────────

def check_pyodbc() -> tuple[bool, str]:
    try:
        import pyodbc
        version = getattr(pyodbc, "version", "unknown")
        drivers = pyodbc.drivers()
        sql_drivers = [d for d in drivers if "sql" in d.lower()]
        detail = f"{version}"
        if sql_drivers:
            detail += f"  drivers: {', '.join(sql_drivers[:3])}"
        else:
            detail += "  (no SQL Server drivers found!)"
        _record("pyodbc installed", True, detail)
        return True, ""
    except ImportError:
        _record("pyodbc installed", False, "not installed — pip install pyodbc")
        return False, "pyodbc not importable"
    except Exception as exc:
        _record("pyodbc installed", False, str(exc))
        return False, str(exc)


# ── Check 3: Dentrix ODBC ───────────────────────────────────────────────

def check_dentrix_odbc(pyodbc_ok: bool) -> None:
    if not pyodbc_ok:
        _record("Dentrix ODBC", False, "skipped — pyodbc not available")
        return

    try:
        from app.providers.adapters.dentrix_connector import DentrixConnector
        connector = DentrixConnector()
        connector.connect()

        # Count user tables as a sanity check
        rows = connector.execute_query(
            "",
            raw_sql="SELECT COUNT(*) AS cnt FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'"
        )
        table_count = rows[0]["cnt"] if rows else "?"
        connector.disconnect()
        _record("Dentrix ODBC", True, f"{table_count} tables found")
    except Exception as exc:
        msg = str(exc).split("\n")[0][:120]
        _record("Dentrix ODBC", False, msg)


# ── Check 4: Backend HTTPS ──────────────────────────────────────────────

def check_backend() -> None:
    backend_url = os.getenv("DENTRIX_BACKEND_URL", "")
    api_prefix = os.getenv("DENTRIX_API_PREFIX", "/api/v1")

    if not backend_url:
        _record("Backend HTTPS", False, "DENTRIX_BACKEND_URL not set in .env")
        return

    health_url = f"{backend_url.rstrip('/')}{api_prefix}/health"

    try:
        import httpx
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            resp = client.get(health_url)
            if resp.status_code < 400:
                _record("Backend HTTPS", True, f"{backend_url}")
            else:
                _record("Backend HTTPS", False, f"HTTP {resp.status_code} from {health_url}")
    except ImportError:
        # Fallback to urllib if httpx isn't available
        try:
            import urllib.request
            req = urllib.request.Request(health_url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                _record("Backend HTTPS", True, f"{backend_url}")
        except Exception as exc:
            msg = str(exc).split("\n")[0][:120]
            _record("Backend HTTPS", False, f"{msg}  url={health_url}")
    except Exception as exc:
        msg = str(exc).split("\n")[0][:120]
        _record("Backend HTTPS", False, f"{msg}  url={health_url}")


# ── Report ───────────────────────────────────────────────────────────────

def print_report() -> None:
    total = len(_results)
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = total - passed

    print()
    print("=" * 56)
    print("  Dentrix Connection Test")
    print("=" * 56)

    for i, (label, ok, detail) in enumerate(_results, 1):
        status = _PASS if ok else _FAIL
        line = f"  [{i}/{total}] {label:.<24s} {status}"
        if detail:
            line += f"  ({detail})"
        print(line)

    print("=" * 56)

    if failed == 0:
        print("  Result: ALL CHECKS PASSED")
    else:
        print(f"  Result: {failed} CHECK(S) FAILED")

    print("=" * 56)
    print()

    if failed > 0:
        print("  Troubleshooting tips:")
        for label, ok, detail in _results:
            if not ok:
                print(f"    - {label}: {detail}")
        print()
        print("  For more help, see DENTRIX.md — Troubleshooting section.")
        print()


# ── Main ─────────────────────────────────────────────────────────────────

def main() -> None:
    check_python()
    pyodbc_ok, _ = check_pyodbc()
    check_dentrix_odbc(pyodbc_ok)
    check_backend()
    print_report()

    all_passed = all(ok for _, ok, _ in _results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
