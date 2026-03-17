# Local PostgreSQL Setup Guide

This guide covers installing PostgreSQL locally with the **pgvector** extension and preparing the `ai_backend` database.

---

## macOS (Homebrew)

### 1. Install PostgreSQL

```bash
brew install postgresql@16
brew services start postgresql@16
```

> After installation, make sure the `psql` binary is on your `PATH`:
>
> ```bash
> echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
> source ~/.zshrc
> ```

### 2. Install pgvector

```bash
brew install pgvector
```

### 3. Create the database

```bash
psql -U postgres -c "CREATE DATABASE ai_backend;"
```

### 4. Enable pgvector

```bash
psql -U postgres -d ai_backend -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## Windows

### 1. Install PostgreSQL

1. Download the installer from <https://www.postgresql.org/download/windows/>.
2. Run the installer — accept defaults and remember the password you set for the `postgres` user.
3. Ensure `psql` is on your `PATH` (the installer usually adds it).

### 2. Install pgvector

pgvector is not bundled with the default Windows installer. You have two options:

**Option A — Use a pre-built binary:**

1. Download the pgvector Windows release matching your PostgreSQL version from <https://github.com/pgvector/pgvector/releases>.
2. Copy the DLL and SQL files into your PostgreSQL `lib` and `share/extension` directories.

**Option B — Build from source (requires Visual Studio Build Tools):**

```powershell
git clone https://github.com/pgvector/pgvector.git
cd pgvector
# Follow the build instructions in the pgvector README for Windows.
```

### 3. Create the database

Open **SQL Shell (psql)** or a terminal:

```sql
CREATE DATABASE ai_backend;
```

### 4. Enable pgvector

```sql
\c ai_backend
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## Verification

Connect to the database and confirm the extension is active:

```bash
psql -U postgres -d ai_backend
```

```sql
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
```

Expected output:

```
 extname | extversion
---------+------------
 vector  | 0.8.0
```

(Version may differ depending on what you installed.)

### Quick connection test from Python

```python
import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/ai_backend")
    version = await conn.fetchval("SELECT version();")
    print(version)
    await conn.close()

asyncio.run(main())
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `psql: command not found` | Add the PostgreSQL `bin` directory to your `PATH`. |
| `FATAL: password authentication failed` | Reset the `postgres` password or check `pg_hba.conf`. |
| `ERROR: could not open extension control file` | pgvector is not installed — follow the steps above. |
| Connection refused on port 5432 | Make sure the PostgreSQL service is running (`brew services list` / `services.msc`). |
