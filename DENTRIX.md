# Dentrix Integration — Setup & Usage Guide

## Architecture

```
Dentrix Database (ODBC)
         │
         ▼
┌─────────────────────────┐
│  Local Python Agent     │   ← Runs on dental-office Windows PC
│  ├─ DentrixConnector    │      ODBC → raw rows
│  ├─ DentrixAdapter      │      raw rows → normalized records
│  └─ DentrixSyncService  │      batch POST → backend
└─────────┬───────────────┘
          │  HTTPS
          ▼
┌─────────────────────────┐
│  FastAPI Backend         │   ← Cloud / central server
│  POST /api/v1/ingest    │
│  POST /api/v1/dentrix/* │
└─────────────────────────┘
```

The Dentrix database runs on a **local Windows machine** inside the dental
office and is accessed via ODBC.  A local Python agent pulls data, normalizes
it, and POSTs batches to the remote backend.

---

## Prerequisites

| Requirement                | Notes                                                       |
|---------------------------|-------------------------------------------------------------|
| Python 3.11+              | On the local Windows machine                                |
| ODBC Driver               | `SQL Server` or `ODBC Driver 17 for SQL Server`             |
| Dentrix ODBC DSN          | Configured via Windows ODBC Data Source Administrator       |
| Network access             | The agent must be able to reach the backend URL over HTTPS  |
| pyodbc                    | `pip install pyodbc`                                        |

---

## 1. Install Dependencies

```powershell
cd ai_backend
pip install -r requirements.txt
```

This adds `pyodbc` and `httpx` (already in requirements).

---

## 2. Configure Environment

```powershell
copy .env.dentrix.example .env
```

Edit `.env` and fill in:

```ini
# Option A — DSN-based (recommended)
DENTRIX_ODBC_DSN=DentrixDB

# Option B — Driver-based (no DSN needed)
DENTRIX_ODBC_DRIVER={SQL Server}
DENTRIX_ODBC_SERVER=localhost\DENTRIX
DENTRIX_ODBC_DATABASE=DENTRIX
DENTRIX_ODBC_USERNAME=sa
DENTRIX_ODBC_PASSWORD=your_password

# Backend URL
DENTRIX_BACKEND_URL=https://your-backend.example.com
DENTRIX_API_KEY=your_api_key_if_needed
```

---

## 3. Set Up Windows ODBC DSN (if using DSN mode)

1. Open **ODBC Data Sources (64-bit)** from the Start menu
2. Go to **System DSN** tab → **Add**
3. Choose **SQL Server** driver
4. Name: `DentrixDB`
5. Server: `localhost\DENTRIX` (or whatever the Dentrix SQL instance is)
6. Authentication: Windows or SQL Server auth
7. Default database: `DENTRIX`
8. Test & finish

---

## 4. Test Connection

```powershell
python scripts/sync_dentrix.py --test-connection
```

Expected output:

```
══════════════════════════════════════
  Dentrix Connection Test
══════════════════════════════════════
  Dentrix ODBC : ✓ PASS
  Backend HTTP : ✓ PASS
  Backend URL  : https://your-backend.example.com
══════════════════════════════════════
```

---

## 5. Run a Sync

### Sync patients (first 100 rows)

```powershell
python scripts/sync_dentrix.py --object patients --limit 100
```

### Sync appointments

```powershell
python scripts/sync_dentrix.py --object appointments --limit 200
```

### Sync all object types

```powershell
python scripts/sync_dentrix.py --object all --limit 50
```

### Incremental sync (only records modified after a timestamp)

```powershell
python scripts/sync_dentrix.py --object patients --limit 100 --since 2025-06-01T00:00:00
```

### Dry-run (fetch + normalize, no POST)

```powershell
python scripts/sync_dentrix.py --object patients --limit 10 --dry-run
```

---

## 6. Backend API Endpoints

The backend exposes Dentrix-specific routes:

| Method | Path                           | Description                |
|--------|--------------------------------|----------------------------|
| GET    | `/api/v1/dentrix/status`       | Test Dentrix connectivity  |
| POST   | `/api/v1/dentrix/sync/{type}`  | Trigger server-side sync   |

These are useful if the backend can reach Dentrix directly (e.g.
self-hosted backend on the same LAN).  For remote backends, use the
CLI agent (`sync_dentrix.py`).

---

## 7. Adapting to Real Dentrix Schema

The SQL queries use **placeholder** view names:

```sql
SELECT TOP {limit} * FROM v_patient
SELECT TOP {limit} * FROM v_appointment
SELECT TOP {limit} * FROM v_provider
```

Once you have access to the real Dentrix database:

1. Open `app/providers/adapters/dentrix_connector.py`
2. Update the `DENTRIX_QUERIES` dict with real table/view names
3. Open `app/providers/adapters/dentrix_adapter.py`
4. Update `_FIELD_MAP` with real column names

**No other files need to change.**

---

## 8. Logging

All sync activity is logged to:
- **Console** (stdout)
- **File**: `dentrix_sync.log` (rotating, 5 MB × 3 backups)

Set `DENTRIX_LOG_FILE=` (empty) in `.env` to disable file logging.

---

## 9. Security Notes

- Credentials are **never hard-coded** — always in environment variables
- ODBC connection uses `autocommit=True` (read-only, no writes)
- The agent runs locally inside the office firewall
- HTTPS is recommended for the backend connection
- For HIPAA compliance, add encryption at rest and audit logging as needed

---

## Troubleshooting

| Problem                     | Fix                                                        |
|----------------------------|------------------------------------------------------------|
| `pyodbc not installed`     | `pip install pyodbc`                                       |
| ODBC connection timeout    | Check DENTRIX_ODBC_SERVER, firewall, SQL Server running    |
| `[IM002] Data source not found` | Check DSN name in ODBC administrator               |
| Backend POST 422           | Schema mismatch — check record format matches IngestRequest|
| Backend POST 401/403       | Set DENTRIX_API_KEY                                        |
