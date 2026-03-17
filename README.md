# AI Backend

A production-oriented, async-first backend for an AI-powered enterprise knowledge and query system.

## Architecture Goals

- **Generic & reusable** — no company-specific logic; data adapters normalize any source into an internal indexing layer.
- **Async-first** — built on FastAPI with SQLAlchemy 2.0 async sessions and asyncpg.
- **Vector-ready** — PostgreSQL + pgvector for embedding storage and similarity search.
- **Hybrid retrieval** — combines chunk-level and summary-level semantic search with query-type-aware reranking.
- **Query classification** — automatic intent detection (fact / summary / compare / list) adapts retrieval strategy and prompt style.
- **Full audit logging** — every query interaction is persisted with classification, sources, confidence, and timing.
- **Clean separation of concerns** — routes → services → repositories → database, plus pluggable LLM/embedding providers.
- **Local-first development** — everything runs on your machine with a local PostgreSQL instance.

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI |
| Database | PostgreSQL 16 + pgvector |
| ORM / query | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| LLM provider | Google Gemini 2.5 Pro via `google-genai` SDK |
| Embeddings | Google text-embedding-004 (768 dimensions) |
| Language | Python 3.11+ |

---

## Setup

### 1. Clone and enter the project

```bash
cd ai_backend
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

- **macOS / Linux:** `source .venv/bin/activate`
- **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`
- **Windows (cmd):** `.venv\Scripts\activate.bat`

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up PostgreSQL

Follow the detailed instructions in [`scripts/setup_postgres.md`](scripts/setup_postgres.md).

In short:

1. Install PostgreSQL.
2. Install the pgvector extension.
3. Create the database:
   ```sql
   CREATE DATABASE ai_backend;
   ```
4. Enable pgvector:
   ```sql
   \c ai_backend
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

### 5. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your actual values (database password, Gemini API key, etc.).

---

## Running the Server

```bash
# From the project root
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the dev script (macOS/Linux):

```bash
bash scripts/dev.sh
```

The server will start at **http://localhost:8000**. The background job worker starts automatically with the server to process ingestion jobs.

---

## API Endpoints

### Root

```bash
curl http://localhost:8000/
```

```json
{
  "name": "AI Backend",
  "status": "running",
  "environment": "development"
}
```

### Health check

```bash
curl http://localhost:8000/api/v1/health
```

```json
{ "status": "ok" }
```

### System info

```bash
curl http://localhost:8000/api/v1/system/info
```

```json
{
  "app_name": "AI Backend",
  "version": "0.1.0",
  "environment": "development",
  "debug": true,
  "api_prefix": "/api/v1",
  "database_configured": true,
  "gemini_configured": true
}
```

### Ingest a record

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Example Document",
    "content": "The full text content to index...",
    "type": "document",
    "source": "manual"
  }'
```

```json
{
  "record_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "job_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "status": "queued"
}
```

The background worker will automatically pick up the job and:
1. Chunk the content (word-based splitting, 400 words with 50-word overlap).
2. Embed each chunk via Gemini text-embedding-004.
3. Store embeddings as pgvector columns.
4. Generate a structured summary (short/long summary, keywords, entities) via Gemini.

### Chat (query the knowledge base)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the company refund policy?"}'
```

```json
{
  "answer": "According to the documentation, ...",
  "sources": [
    { "record_id": "...", "title": "Refund Policy" }
  ],
  "confidence": 0.87,
  "notes": "",
  "query_type": "fact"
}
```

The chat pipeline performs:
1. **Query classification** — detects intent type (`fact`, `summary`, `compare`, `list`) via keyword heuristic + LLM fallback.
2. **Hybrid retrieval** — runs chunk-level and summary-level semantic search in parallel, merges and deduplicates by record.
3. **Reranking** — applies heuristic score boosts based on query type (e.g. summary queries boost records with summaries).
4. **Type-adapted prompting** — the LLM receives style instructions tailored to the query type.
5. **Audit logging** — the full interaction (query, classification, sources, answer, timing) is persisted to `query_logs`.

---

## Terminal Chat Client

An interactive CLI client is included for local testing:

```bash
# From the ai_backend directory
PYTHONPATH=. python scripts/chat_client.py
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH = "."
python scripts/chat_client.py
```

Options:

```
--url http://host:port    # default: http://localhost:8000
```

The client provides ANSI-colored output with the answer, sources, confidence score, and detected query type. Type `exit` or `quit` to leave.

---

## Running Tests

```bash
PYTHONPATH=. pytest tests/ -v
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH = "."
pytest tests/ -v
```

---

## Alembic Migrations

Two migrations are included:

| Revision | Description |
|---|---|
| `0001` | Creates `records`, `record_chunks`, `record_summaries`, `jobs` tables + pgvector extension |
| `0002` | Creates `query_logs` table for audit logging |

### Apply migrations

```bash
alembic upgrade head
```

### Create a new migration

```bash
alembic revision --autogenerate -m "description"
```

---

## Database Schema

| Table | Purpose |
|---|---|
| `records` | Normalized ingested documents (title, content, type, source, metadata JSONB) |
| `record_chunks` | Chunked text with `Vector(768)` embedding column for pgvector similarity search |
| `record_summaries` | AI-generated short/long summary, keywords, entities, category per record |
| `jobs` | Async job queue with status lifecycle (pending → running → completed/failed) |
| `query_logs` | Audit log — query text, classification, retrieved records, answer, confidence, duration |

---

## What's Not Implemented Yet

- **Data adapters** — only the abstract `BaseAdapter` is defined; no concrete adapters for specific external sources.
- **Authentication / authorization** — no auth middleware or API keys.
- **Rate limiting** — no request throttling.
- **Adapter-driven ingestion** — ingestion currently accepts raw text; adapters would pull from Confluence, Notion, etc.

---

## Project Structure

```
ai_backend/
├── app/
│   ├── main.py                         # FastAPI application entry point
│   ├── core/
│   │   ├── config.py                   # Pydantic settings (DB, Gemini, embedding dim)
│   │   ├── logging.py                  # Structured logging setup
│   │   └── lifecycle.py                # Async lifespan (starts job worker)
│   ├── api/
│   │   ├── router.py                   # Central router aggregating all routes
│   │   ├── deps.py                     # FastAPI dependencies (get_db)
│   │   └── routes/
│   │       ├── health.py               # GET /health
│   │       ├── system.py               # GET /system/info
│   │       ├── ingest.py               # POST /ingest
│   │       └── chat.py                 # POST /chat
│   ├── db/
│   │   ├── base.py                     # DeclarativeBase + model import helper
│   │   ├── session.py                  # Async engine & session factory
│   │   └── models/
│   │       ├── record.py               # Record (ingested document)
│   │       ├── chunk.py                # RecordChunk (text + Vector embedding)
│   │       ├── summary.py              # RecordSummary (AI-generated)
│   │       ├── job.py                  # Job (async processing queue)
│   │       └── query_log.py            # QueryLog (audit trail)
│   ├── schemas/
│   │   ├── health.py                   # Health response schema
│   │   ├── system.py                   # System info schema
│   │   ├── ingest.py                   # Ingest request/response
│   │   └── chat.py                     # Chat request/response + sources
│   ├── repositories/
│   │   ├── record.py                   # RecordRepository (CRUD + filtering)
│   │   ├── chunk.py                    # ChunkRepository (bulk create, similarity search)
│   │   ├── summary.py                  # SummaryRepository (upsert)
│   │   ├── job.py                      # JobRepository (queue with SELECT FOR UPDATE)
│   │   └── query_log.py               # QueryLogRepository
│   ├── services/
│   │   ├── chunking.py                 # Word-based text chunking with overlap
│   │   ├── ingestion_service.py        # Record creation + job processing pipeline
│   │   ├── retrieval_service.py        # Hybrid search (chunk + summary), reranking
│   │   ├── query_classifier.py         # Query intent classification (keyword + LLM)
│   │   ├── query_service.py            # Full RAG pipeline (classify → retrieve → rerank → answer → log)
│   │   └── query_logging_service.py    # Audit log persistence
│   ├── providers/
│   │   ├── llm/
│   │   │   ├── base.py                 # BaseLLMProvider ABC
│   │   │   └── gemini_provider.py      # Gemini 2.5 Pro (google-genai, native async)
│   │   ├── embeddings/
│   │   │   ├── base.py                 # BaseEmbeddingProvider ABC
│   │   │   └── gemini_embeddings.py    # text-embedding-004 (768d)
│   │   └── adapters/
│   │       └── base.py                 # BaseAdapter ABC
│   ├── jobs/
│   │   └── worker.py                   # Async job worker (polls every 2s)
│   └── utils/                          # Shared utilities
├── alembic/
│   └── versions/
│       ├── 0001_initial.py             # Tables: records, chunks, summaries, jobs
│       └── 0002_add_query_logs.py      # Table: query_logs
├── scripts/
│   ├── dev.sh                          # Dev server launcher
│   ├── setup_postgres.md               # PostgreSQL setup guide
│   └── chat_client.py                  # Interactive terminal chat client
├── tests/
│   └── test_health.py                  # Root, health, system endpoint tests
├── .env.example
├── alembic.ini
├── requirements.txt
└── README.md
```

---

## SAP PLM Integration (Scaffold)

The backend includes a read-only adapter scaffold for SAP Product Lifecycle
Management (PLM).  It is intentionally generic — no company-specific field
mappings or business rules are baked in.

### Architecture

```
SAP PLM (OData / REST)
  └── SAPPLMAdapter           (app/providers/adapters/sap_plm_adapter.py)
        ├── fetch_materials()
        ├── fetch_documents()
        ├── fetch_boms()
        ├── fetch_change_records()
        └── normalize_record()  → internal schema
              └── SAPSyncService  (app/services/sap_sync_service.py)
                    └── IngestionService → chunk / embed / summarise / index
```

### API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/sap/sync/{object_type}` | Fetch and queue SAP records |
| `GET`  | `/api/v1/sap/status` | Test SAP connectivity |

**Supported object types:** `materials`, `documents`, `boms`, `change-records`

```bash
# Sync up to 50 material master records
curl -X POST http://localhost:8000/api/v1/sap/sync/materials \
  -H "Content-Type: application/json" \
  -d '{"limit": 50}'

# Response
{
  "object_type": "materials",
  "requested": 50,
  "fetched": 50,
  "queued": 50,
  "failed": 0
}
```

### Configuration

Add these variables to your `.env` file:

```env
SAP_BASE_URL=https://your-sap-system.example.com
SAP_USERNAME=service_user
SAP_PASSWORD=secret
SAP_CLIENT=100
SAP_AUTH_TYPE=basic          # basic | oauth2
SAP_OAUTH_TOKEN=             # required when SAP_AUTH_TYPE=oauth2
SAP_TIMEOUT_SECONDS=30
```

### Wiring Real Endpoints

All SAP OData paths are centralised in `_SAP_ENDPOINTS` at the top of
`sap_plm_adapter.py`.  Replace the placeholder paths with confirmed paths
from your SAP system's OData service catalogue — no other changes needed.

### Design Constraints

- **Read-only** — the adapter never writes to SAP.
- **Generic normalisation** — only standard OData field conventions are
  assumed; all raw fields are preserved as metadata.
- **No business logic** — filtering, deduplication, and field prioritisation
  belong in a company-specific subclass or configuration layer.

---

## License

Private — not for redistribution.
