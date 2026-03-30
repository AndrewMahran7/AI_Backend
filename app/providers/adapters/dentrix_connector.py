"""Low-level Dentrix ODBC data-access layer.

This module owns the ODBC connection to the Dentrix database running on a
local Windows machine inside the dental office.  It provides:

* Connection lifecycle management (connect / disconnect / reconnect)
* Query execution with parameterised bindings
* Connection-health testing
* Structured logging of every query

All configuration is sourced from environment variables so no credentials
are ever hard-coded.

Environment variables
---------------------
DENTRIX_ODBC_DSN          ODBC Data Source Name  (e.g. ``DentrixDB``)
DENTRIX_ODBC_DRIVER       ODBC driver string     (e.g. ``{SQL Server}``)
DENTRIX_ODBC_SERVER       Host\\instance           (e.g. ``localhost\\DENTRIX``)
DENTRIX_ODBC_DATABASE     Database name           (e.g. ``DENTRIX``)
DENTRIX_ODBC_USERNAME     Database user
DENTRIX_ODBC_PASSWORD     Database password
DENTRIX_ODBC_EXTRA        Extra connection-string params (e.g. ``Encrypt=yes``)
DENTRIX_ODBC_TIMEOUT      Connection timeout in seconds (default 30)

When ``DENTRIX_ODBC_DSN`` is set, a DSN-based connection string is used.
Otherwise, the driver / server / database triplet is used to build a
driver-based connection string.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Generator

try:
    import pyodbc
except ImportError:  # allow import on machines without pyodbc for testing
    pyodbc = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ── SQL query catalogue ───────────────────────────────────────────────────
# All Dentrix SQL lives here.  Replace the view / table names once the real
# Dentrix schema is confirmed; the rest of the connector needs no changes.

DENTRIX_QUERIES: dict[str, str] = {
    "patients": (
        "SELECT TOP {limit} * FROM v_patient"
    ),
    "appointments": (
        "SELECT TOP {limit} * FROM v_appointment"
    ),
    "providers": (
        "SELECT TOP {limit} * FROM v_provider"
    ),
    # Incremental sync variants (filtered by last-modified timestamp)
    "patients_incremental": (
        "SELECT TOP {limit} * FROM v_patient WHERE modified_date > ?"
    ),
    "appointments_incremental": (
        "SELECT TOP {limit} * FROM v_appointment WHERE modified_date > ?"
    ),
    "providers_incremental": (
        "SELECT TOP {limit} * FROM v_provider WHERE modified_date > ?"
    ),
}


class DentrixConnector:
    """Manages the ODBC connection to a local Dentrix database.

    Usage::

        connector = DentrixConnector()
        connector.connect()
        rows = connector.execute_query("patients", limit=100)
        connector.disconnect()

    Or as a context manager::

        with DentrixConnector() as conn:
            rows = conn.execute_query("patients", limit=50)
    """

    def __init__(self) -> None:
        self._dsn = os.getenv("DENTRIX_ODBC_DSN", "")
        self._driver = os.getenv("DENTRIX_ODBC_DRIVER", "{SQL Server}")
        self._server = os.getenv("DENTRIX_ODBC_SERVER", r"localhost\DENTRIX")
        self._database = os.getenv("DENTRIX_ODBC_DATABASE", "DENTRIX")
        self._username = os.getenv("DENTRIX_ODBC_USERNAME", "")
        self._password = os.getenv("DENTRIX_ODBC_PASSWORD", "")
        self._extra = os.getenv("DENTRIX_ODBC_EXTRA", "")
        self._timeout = int(os.getenv("DENTRIX_ODBC_TIMEOUT", "30"))

        self._connection: Any = None

    # ── Connection string builder ─────────────────────────────────────────

    def _build_connection_string(self) -> str:
        """Build an ODBC connection string from environment config."""
        if self._dsn:
            parts = [f"DSN={self._dsn}"]
        else:
            parts = [
                f"DRIVER={self._driver}",
                f"SERVER={self._server}",
                f"DATABASE={self._database}",
            ]

        if self._username:
            parts.append(f"UID={self._username}")
        if self._password:
            parts.append(f"PWD={self._password}")
        if not self._username and not self._dsn:
            parts.append("Trusted_Connection=yes")
        if self._extra:
            parts.append(self._extra)

        return ";".join(parts)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def connect(self) -> None:
        """Open the ODBC connection (idempotent)."""
        if pyodbc is None:
            raise RuntimeError(
                "pyodbc is not installed.  Run: pip install pyodbc"
            )
        if self._connection is not None:
            return

        conn_str = self._build_connection_string()
        logger.info(
            "Dentrix: connecting (DSN=%s, server=%s, db=%s, timeout=%ds)",
            self._dsn or "(none)",
            self._server,
            self._database,
            self._timeout,
        )
        try:
            self._connection = pyodbc.connect(
                conn_str,
                timeout=self._timeout,
                autocommit=True,  # read-only; no transactions needed
            )
            logger.info("Dentrix: connected successfully")
        except Exception:
            logger.exception("Dentrix: connection failed")
            raise

    def disconnect(self) -> None:
        """Close the ODBC connection (safe to call multiple times)."""
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                logger.warning("Dentrix: error closing connection", exc_info=True)
            finally:
                self._connection = None
                logger.info("Dentrix: disconnected")

    def reconnect(self) -> None:
        """Drop and re-establish the connection."""
        self.disconnect()
        self.connect()

    @property
    def is_connected(self) -> bool:
        """Return ``True`` if the underlying ODBC connection is open."""
        return self._connection is not None

    # ── Context manager ───────────────────────────────────────────────────

    def __enter__(self) -> "DentrixConnector":
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.disconnect()

    # ── Query execution ──────────────────────────────────────────────────

    def execute_query(
        self,
        query_name: str,
        *,
        limit: int = 100,
        params: tuple[Any, ...] | None = None,
        raw_sql: str | None = None,
    ) -> list[dict[str, Any]]:
        """Run a named query from ``DENTRIX_QUERIES`` or raw SQL.

        Parameters
        ----------
        query_name:
            Key in ``DENTRIX_QUERIES``.  Ignored when *raw_sql* is given.
        limit:
            Row cap substituted into the ``{limit}`` placeholder.
        params:
            Positional bind parameters for parameterised queries.
        raw_sql:
            Optional raw SQL that overrides the catalogue lookup.

        Returns
        -------
        list[dict[str, Any]]
            Each row as an ordered dict (column_name → value).
        """
        if not self.is_connected:
            self.connect()

        sql = raw_sql or DENTRIX_QUERIES.get(query_name, "")
        if not sql:
            raise ValueError(
                f"Unknown query '{query_name}'.  "
                f"Available: {list(DENTRIX_QUERIES)}"
            )

        sql = sql.format(limit=limit)

        logger.info("Dentrix query [%s]: %s  params=%s", query_name, sql, params)
        t0 = time.perf_counter()

        try:
            cursor = self._connection.cursor()  # type: ignore[union-attr]
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)

            columns = [col[0] for col in cursor.description] if cursor.description else []
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            elapsed = time.perf_counter() - t0

            logger.info(
                "Dentrix query [%s]: %d rows in %.3fs",
                query_name,
                len(rows),
                elapsed,
            )
            return rows

        except Exception:
            logger.exception("Dentrix query [%s] failed", query_name)
            # Attempt reconnect for transient connection errors
            try:
                self.reconnect()
            except Exception:
                logger.warning("Dentrix: reconnect after query failure also failed")
            raise

    # ── Health check ──────────────────────────────────────────────────────

    def test_connection(self) -> bool:
        """Open a connection and execute a trivial query.

        Returns ``True`` on success, ``False`` on any error.
        """
        try:
            self.connect()
            cursor = self._connection.cursor()  # type: ignore[union-attr]
            cursor.execute("SELECT 1")
            cursor.fetchone()
            logger.info("Dentrix: connection test passed")
            return True
        except Exception:
            logger.exception("Dentrix: connection test failed")
            return False
