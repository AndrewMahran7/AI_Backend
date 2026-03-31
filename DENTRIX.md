# Dentrix Integration — Deployment Playbook

> **Audience**: Field technicians, IT admins, and developers deploying the
> Dentrix data-extraction agent at dental offices.
>
> **Time estimate**: 30–60 minutes for a typical install.

---

## Quick Reference

| Task                        | Command / Script                                          | Time  |
|-----------------------------|----------------------------------------------------------|-------|
| Full automated setup        | `.\scripts\setup_dentrix.ps1`                            | 15 min |
| Generate `.env` interactively | `.\scripts\setup_env.ps1`                              | 5 min  |
| Test ODBC + backend         | `python scripts\test_dentrix_connection.py`              | 1 min  |
| Run a sync                  | `.\scripts\run_dentrix_sync.ps1 patients 100`            | 2 min  |
| Manual sync (advanced)      | `python scripts\sync_dentrix.py --object patients`       | 2 min  |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  DENTAL OFFICE  (Windows PC)            NO local database    │
│                                                              │
│   Dentrix G (SQL Server)                                     │
│        │  ODBC                                               │
│        ▼                                                     │
│   ┌──────────────────────┐                                   │
│   │  Local Python Agent  │                                   │
│   │  ├─ DentrixConnector │  ODBC → raw SQL rows              │
│   │  ├─ DentrixAdapter   │  raw rows → normalized records    │
│   │  └─ DentrixSyncService│ batch POST → backend             │
│   └──────────┬───────────┘                                   │
│              │  HTTPS (outbound only)                        │
└──────────────┼───────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│  CLOUD / DATA CENTER                                         │
│                                                              │
│   ┌──────────────────────┐    ┌────────────────────────┐     │
│   │  FastAPI Backend     │───▶│  PostgreSQL + pgvector  │     │
│   │  POST /api/v1/ingest │    └────────────────────────┘     │
│   │  POST /api/v1/dentrix│                                   │
│   └──────────────────────┘                                   │
└──────────────────────────────────────────────────────────────┘
```

**Key principle**: The local machine is **only** a data-extraction agent.
There is **no** local PostgreSQL database.  All data flows outbound over
HTTPS to the cloud backend.

---

## Data Storage Model

| Layer          | Location             | What lives there                       |
|---------------|----------------------|----------------------------------------|
| Dentrix DB    | Local SQL Server     | Source of truth — patients, appts, etc. |
| Python Agent  | Local Windows PC     | Reads data via ODBC, normalizes, POSTs  |
| `.env` file   | Local `ai_backend/`  | ODBC credentials, backend URL           |
| Sync logs     | Local `dentrix_sync.log` | Rotating 5 MB × 3 backups          |
| Backend DB    | Cloud PostgreSQL     | Ingested records, embeddings, chunks    |

**Nothing is stored permanently on the local machine** except logs and the
`.env` config file.

---

## Pre-Deployment Checklist

Run through this **before arriving at the dental office** or starting setup:

- [ ] Confirm the office runs **Dentrix G** (G5, G6, or G7)
- [ ] Confirm the office PC has **Windows 10/11** (64-bit)
- [ ] Ask IT: What SQL Server instance does Dentrix use? (usually `localhost\INTUIT_DG`)
- [ ] Ask IT: Is SQL Server authentication enabled, or Windows auth only?
- [ ] Ask IT: What login credentials can we use? (ideally a read-only SQL login)
- [ ] Confirm the PC can reach the internet (for HTTPS POSTs to the backend)
- [ ] Get the **backend URL** and **API key** from the ops team
- [ ] Have a USB drive or download link for the Python installer + project files

---

## Identify the Correct Machine

Dentrix stores data in a **SQL Server** database.  In multi-workstation
offices, the database typically runs on one of these:

| Setup               | Where the DB lives                         | How to identify                        |
|--------------------|-------------------------------------------|----------------------------------------|
| **Single PC**      | The one Dentrix workstation               | Only one machine in the office          |
| **Peer-to-peer**   | The "main" workstation / file server      | Look for `INTUIT_DG` SQL instance       |
| **Dedicated server**| A server in the back closet              | Ask IT; check `services.msc` for SQL    |
| **Cloud (Dentrix Ascend)** | N/A — Ascend uses a web API, not ODBC | This playbook does NOT apply      |

### How to verify the machine has the Dentrix database

Open **PowerShell** on the candidate machine and run:

```powershell
Get-Service | Where-Object { $_.Name -like "*SQL*" -or $_.Name -like "*INTUIT*" }
```

If you see `MSSQL$INTUIT_DG` or a similar SQL Server service, you're on
the right machine.  You can also check:

```powershell
sqlcmd -L   # Lists local SQL Server instances
```

---

## Prerequisites

| Requirement          | Notes                                                          |
|---------------------|----------------------------------------------------------------|
| Python 3.11+        | On the local Windows machine — [python.org/downloads](https://www.python.org/downloads/) |
| ODBC Driver         | `SQL Server` or `ODBC Driver 17 for SQL Server`                |
| Dentrix ODBC DSN    | Configured via Windows ODBC Data Source Administrator (optional)|
| Network access      | Outbound HTTPS to the backend URL                               |
| pyodbc              | Installed automatically by `setup_dentrix.ps1`                  |

---

## Step-by-Step Setup

### Option A: Automated Setup (Recommended)

The setup script handles Python verification, dependencies, `.env` creation,
ODBC testing, and backend connectivity in one pass:

```powershell
cd ai_backend
.\scripts\setup_dentrix.ps1
```

The script will:
1. Verify Python 3.11+ is installed
2. Create a virtual environment (if missing)
3. Install pip dependencies (`pyodbc`, `httpx`, etc.)
4. Launch the interactive `.env` generator
5. Test the ODBC connection to Dentrix
6. Test HTTPS connectivity to the backend
7. Print a PASS / FAIL summary

**If everything passes, you're done.  Skip to [Run a Sync](#run-a-sync).**

### Option B: Manual Setup

#### 1. Install Python Dependencies

```powershell
cd ai_backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> **Time**: ~2 minutes.

#### 2. Configure Environment

```powershell
copy .env.dentrix.example .env
```

Edit `.env` and fill in:

```ini
# ── Option A: DSN-based (recommended if you set up a System DSN) ──
DENTRIX_ODBC_DSN=DentrixDB

# ── Option B: Driver-based (no DSN required) ──
DENTRIX_ODBC_DRIVER={SQL Server}
DENTRIX_ODBC_SERVER=localhost\INTUIT_DG
DENTRIX_ODBC_DATABASE=DentrixDB
DENTRIX_ODBC_USERNAME=sa
DENTRIX_ODBC_PASSWORD=your_password

# ── Backend ──
DENTRIX_BACKEND_URL=https://your-backend.example.com
DENTRIX_API_KEY=your_api_key
```

Or use the interactive generator:

```powershell
.\scripts\setup_env.ps1
```

> **Time**: ~5 minutes.

#### 3. Set Up Windows ODBC DSN (optional — only if using DSN mode)

1. Press **Win + S**, type **ODBC Data Sources (64-bit)**, open it
2. Go to **System DSN** tab → **Add**
3. Choose **SQL Server** driver
4. Name: `DentrixDB`
5. Server: `localhost\INTUIT_DG` (or the actual Dentrix SQL instance)
6. Authentication: Windows auth or SQL Server auth
7. Default database: `DentrixDB`
8. Click **Test Data Source** → confirm success → **OK**

> **Time**: ~5 minutes.

#### 4. Test Connection

```powershell
python scripts\test_dentrix_connection.py
```

Or the full CLI version:

```powershell
python scripts\sync_dentrix.py --test-connection
```

Expected output:

```
══════════════════════════════════════════════════════════
  Dentrix Connection Test
══════════════════════════════════════════════════════════
  [1/4] Python environment .... ✓ PASS  (3.12.4)
  [2/4] pyodbc installed ...... ✓ PASS  (5.2.0)
  [3/4] Dentrix ODBC .......... ✓ PASS  (12 tables found)
  [4/4] Backend HTTPS ......... ✓ PASS  (https://api.example.com)
══════════════════════════════════════════════════════════
  Result: ALL CHECKS PASSED
══════════════════════════════════════════════════════════
```

> **Time**: ~1 minute.

---

## Run a Sync

### Quick start (PowerShell wrapper)

```powershell
# Sync first 100 patients
.\scripts\run_dentrix_sync.ps1 patients 100

# Sync appointments
.\scripts\run_dentrix_sync.ps1 appointments 200

# Sync all object types
.\scripts\run_dentrix_sync.ps1 all 50

# Dry-run (fetch + normalize, no POST)
.\scripts\run_dentrix_sync.ps1 patients 10 -DryRun
```

### Advanced CLI (Python)

```powershell
# Sync patients (first 100 rows)
python scripts\sync_dentrix.py --object patients --limit 100

# Sync appointments
python scripts\sync_dentrix.py --object appointments --limit 200

# Sync all object types
python scripts\sync_dentrix.py --object all --limit 50

# Incremental sync (only records modified after a timestamp)
python scripts\sync_dentrix.py --object patients --limit 100 --since 2025-06-01T00:00:00

# Dry-run (fetch + normalize, no POST)
python scripts\sync_dentrix.py --object patients --limit 10 --dry-run
```

### First sync recommendations

| Object type    | Suggested limit | Notes                                      |
|---------------|----------------|---------------------------------------------|
| `patients`     | 50             | Start small to verify schema mapping         |
| `appointments` | 50             | Confirm date fields parse correctly          |
| `providers`    | 20             | Typically a small table                      |
| `all`          | 10             | Quick end-to-end smoke test                  |

After confirming fields map correctly with a small batch, increase limits
or remove the `--limit` flag for a full initial load.

---

## Backend API Endpoints

The backend exposes Dentrix-specific routes:

| Method | Path                           | Description                |
|--------|--------------------------------|----------------------------|
| GET    | `/api/v1/dentrix/status`       | Test Dentrix connectivity  |
| POST   | `/api/v1/dentrix/sync/{type}`  | Trigger server-side sync   |

These are useful if the backend can reach Dentrix directly (e.g. self-hosted
backend on the same LAN).  For remote backends, **always use the local CLI
agent** (`sync_dentrix.py` or `run_dentrix_sync.ps1`).

---

## Adapting to Real Dentrix Schema

The SQL queries ship with **placeholder** view names:

```sql
SELECT TOP {limit} * FROM v_patient
SELECT TOP {limit} * FROM v_appointment
SELECT TOP {limit} * FROM v_provider
```

Once you have access to the real Dentrix database:

1. Open `app/providers/adapters/dentrix_connector.py`
2. Update the `DENTRIX_QUERIES` dict with real table / view names
3. Open `app/providers/adapters/dentrix_adapter.py`
4. Update `_FIELD_MAP` with real column names

**No other files need to change.**

### Discovering the real schema

Run this on the Dentrix machine to list all user tables:

```powershell
python -c "
from app.providers.adapters.dentrix_connector import DentrixConnector
with DentrixConnector() as c:
    rows = c.execute_query('', raw_sql=\"\"\"
        SELECT TABLE_SCHEMA, TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    \"\"\")
    for r in rows:
        print(f\"  {r['TABLE_SCHEMA']}.{r['TABLE_NAME']}\")
"
```

---

## Logging

All sync activity is logged to:
- **Console** (stdout)
- **File**: `dentrix_sync.log` (rotating, 5 MB × 3 backups)

Set `DENTRIX_LOG_FILE=` (empty) in `.env` to disable file logging.

Log location: the `ai_backend/` directory where you run the scripts.

---

## Security Notes

- Credentials are **never hard-coded** — always in environment variables
- ODBC connection uses `autocommit=True` (read-only, no writes to Dentrix)
- The agent runs locally inside the office firewall
- HTTPS is **required** for the backend connection in production
- `.env` file should have restricted permissions (`icacls .env /inheritance:r /grant:r "%USERNAME%:R"`)
- For HIPAA compliance, add encryption at rest and audit logging as needed

---

## Scheduled Sync (Optional)

To run automatic syncs, create a Windows **Task Scheduler** entry:

1. Open **Task Scheduler** → **Create Basic Task**
2. Name: `Dentrix Sync`
3. Trigger: **Daily** at a low-traffic time (e.g. 2:00 AM)
4. Action: **Start a program**
   - Program: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File "C:\path\to\ai_backend\scripts\run_dentrix_sync.ps1" all 500`
   - Start in: `C:\path\to\ai_backend`
5. Check **Run whether user is logged on or not**
6. Save and test-run

---

## Post-Deployment Validation Checklist

Run through after setup to confirm everything works end-to-end:

- [ ] `python scripts\test_dentrix_connection.py` — all 4 checks PASS
- [ ] `.\scripts\run_dentrix_sync.ps1 patients 5` — completes without errors
- [ ] Verify records appear in the backend (check `/api/v1/dentrix/status` or the admin UI)
- [ ] `.\scripts\run_dentrix_sync.ps1 patients 5 -DryRun` — dry-run prints normalized JSON
- [ ] Check `dentrix_sync.log` — log file exists and has entries
- [ ] Confirm `.env` has the correct backend URL (production, not localhost)
- [ ] Confirm `.env` is NOT checked into git (`.gitignore` covers it)

---

## Troubleshooting

### Quick Diagnostic Flow

```
Sync failing?
    │
    ├─ ODBC error? ──────────────── Run: python scripts\test_dentrix_connection.py
    │   ├─ "Driver not found"   ── Install ODBC Driver 17 for SQL Server
    │   ├─ "Login failed"       ── Check DENTRIX_ODBC_USERNAME / PASSWORD
    │   ├─ "Server not found"   ── Check DENTRIX_ODBC_SERVER (try sqlcmd -L)
    │   └─ "Timeout"            ── Check SQL Server service is running
    │
    ├─ Backend error? ───────────── Check DENTRIX_BACKEND_URL
    │   ├─ "Connection refused" ── Backend is down or URL is wrong
    │   ├─ "SSL error"          ── Backend cert issue; check HTTPS
    │   └─ "401 / 403"          ── Check DENTRIX_API_KEY
    │
    └─ Data error? ──────────────── Check schema mapping
        ├─ "KeyError: column"   ── Update _FIELD_MAP in dentrix_adapter.py
        └─ "0 rows fetched"     ── Update DENTRIX_QUERIES with real table names
```

### Common Errors

| Error                                    | Cause                                     | Fix                                                                                |
|------------------------------------------|-------------------------------------------|-------------------------------------------------------------------------------------|
| `pyodbc.InterfaceError: ... driver ...`  | ODBC driver not installed                 | Download and install [ODBC Driver 17 for SQL Server](https://aka.ms/downloadmsodbcsql) |
| `Login failed for user 'sa'`            | Wrong username or password                | Verify credentials in `.env`; try Windows auth (leave USERNAME blank)                |
| `Cannot open server ... requested by the login` | Wrong server name / instance     | Run `sqlcmd -L` to discover instances; check `services.msc` for SQL Server           |
| `Connection timeout expired`             | SQL Server service not running            | Open `services.msc`, find SQL Server, start it                                       |
| `[08001] TCP/IP not enabled`            | SQL Server TCP/IP protocol disabled       | Open SQL Server Configuration Manager → Protocols → Enable TCP/IP                     |
| `httpx.ConnectError`                     | Backend URL unreachable                   | Check internet / firewall; verify `DENTRIX_BACKEND_URL`                               |
| `401 Unauthorized`                       | Missing or invalid API key                | Set `DENTRIX_API_KEY` in `.env`                                                       |
| `KeyError: 'patient_id'`                | SQL column names don't match `_FIELD_MAP` | Update `_FIELD_MAP` in `dentrix_adapter.py` with real column names                    |
| `0 rows fetched`                         | Placeholder SQL doesn't match real schema | Update `DENTRIX_QUERIES` in `dentrix_connector.py`                                    |
| `ModuleNotFoundError: pyodbc`            | pyodbc not installed in active venv       | Run `pip install pyodbc` inside the `.venv`                                           |

### Collecting Debug Info

If you need to escalate an issue, gather this:

```powershell
python scripts\test_dentrix_connection.py > dentrix_diag.txt 2>&1
python -c "import pyodbc; print(pyodbc.drivers())" >> dentrix_diag.txt 2>&1
python --version >> dentrix_diag.txt 2>&1
type .env | findstr /V PASSWORD >> dentrix_diag.txt
```

Send `dentrix_diag.txt` to the engineering team (credentials are excluded).

---

## File Reference

| File                                              | Purpose                                |
|--------------------------------------------------|----------------------------------------|
| `scripts/setup_dentrix.ps1`                       | Automated full setup                   |
| `scripts/setup_env.ps1`                           | Interactive `.env` generator           |
| `scripts/test_dentrix_connection.py`              | 4-step connection validator            |
| `scripts/run_dentrix_sync.ps1`                    | Simple sync wrapper                    |
| `scripts/sync_dentrix.py`                         | Full-featured CLI sync tool            |
| `.env.dentrix.example`                            | Environment template                   |
| `app/providers/adapters/dentrix_connector.py`     | Low-level ODBC connector               |
| `app/providers/adapters/dentrix_adapter.py`       | Row normalizer (BaseAdapter)           |
| `app/services/dentrix_sync_service.py`            | Fetch → normalize → POST orchestrator  |
| `app/api/routes/dentrix.py`                       | Backend API routes                     |
| `app/schemas/dentrix.py`                          | Pydantic request/response models       |

---

## Troubleshooting

| Problem                     | Fix                                                        |
|----------------------------|------------------------------------------------------------|
| `pyodbc not installed`     | `pip install pyodbc`                                       |
| ODBC connection timeout    | Check DENTRIX_ODBC_SERVER, firewall, SQL Server running    |
| `[IM002] Data source not found` | Check DSN name in ODBC administrator               |
| Backend POST 422           | Schema mismatch — check record format matches IngestRequest|
| Backend POST 401/403       | Set DENTRIX_API_KEY                                        |
