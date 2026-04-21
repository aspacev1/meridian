# Meridian — Backend Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  Greenplum ETL Logs (CSV)  │  DQ Engine output  │  OpenMetadata API │
└──────────┬─────────────────┴────────┬────────────┴──────────────────┘
           │                          │
           ▼                          ▼
┌──────────────────────┐   ┌──────────────────────┐
│  log_ingestion.py    │   │  dq_aggregator.py    │
│  CSV → pipeline_runs │   │  DQ results →        │
│  + layer_runs        │   │  dq_results table    │
└──────────┬───────────┘   └──────────┬───────────┘
           │                          │
           ▼                          ▼
┌─────────────────────────────────────────────────┐
│              PostgreSQL (Meridian DB)            │
│                                                 │
│  users            sla_configs    incidents      │
│  domains          pipeline_runs  incident_      │
│  data_marts       layer_runs       affected_    │
│  reports          dq_rules          reports     │
│  report_          dq_results    glossary_       │
│    favourites     scan_sessions    entries      │
└──────────────────────────┬──────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
  │ SLA Monitor │  │ FastAPI      │  │ Scan Session │
  │ Celery/5min │  │ REST API     │  │ Worker/hourly│
  └──────┬──────┘  └──────┬───────┘  └──────────────┘
         │                │
         ▼                ▼
  Creates incidents  Dashboard /
  via Claude API     Catalog /
                     Glossary endpoints
```

---

## Services

### SLA Monitor (Celery — every 5 minutes)

The core background service. Runs on a schedule via Celery Beat.

**Flow:**
1. Fetch all active `PipelineRun` records for today
2. For each run, load `LayerRun` records and matching `SLAConfig`
3. Call `compute_sla_status()` for each layer
4. If breach or warning detected:
   - Count past occurrences (`occurrence_count`)
   - Call Claude API → `ai_name` + `ai_description`
   - Create `Incident` row with all computed fields
5. Update `LayerRun.sla_status` and `PipelineRun.sla_status`

**SLA computation logic:**
```python
def compute_sla_status(delivery_time, target_time, run_status, dq_pass_rate_pct, dq_threshold_pct):
    if run_status == 'failed':      return 'breach'
    if delivery_time is None:       return 'breach'
    if delivery_time > target_time: return 'warning'
    if dq_pass_rate_pct < dq_threshold_pct: return 'warning'
    return 'healthy'
```

### Log Ingestion Service

Reads Greenplum ETL logs (CSV format) and populates `pipeline_runs` + `layer_runs`.

**Expected CSV columns:**
```
job_name, job_id, mart_name, layer, started_at, finished_at, rows_affected, status, error_message
```

**Idempotency:** Uses `UNIQUE (mart_id, run_date)` on `pipeline_runs` — safe to re-ingest.

**Layer name mapping:**
```python
LAYER_MAP = {
    'src': 'source', 'source': 'source',
    'stg': 'staging', 'staging': 'staging',
    'ods': 'ods',
    'dm': 'dm', 'dw': 'dm',
}
```

### AI Service (Claude API)

All AI calls use `claude-sonnet-4-20250514` with structured JSON output.

**Incident naming prompt pattern:**
- Input: mart name, incident type, layer statuses, delay minutes, job ID
- Output: `{"name": "Pipeline SLA Breach — dm_market", "description": "..."}`

**Glossary draft prompt pattern:**
- Input: column name, table name, sample values, context
- Output: `{"biz_name": "...", "definition": "...", "calculation": "..."}`

### Scan Session Worker (Celery — hourly)

Creates a `ScanSession` record with aggregate counts:
- `reports_scanned` — active report count
- `domains_scanned` — domain count
- `marts_scanned` — active mart count
- `incidents_created` — incidents from this scan

Powers the dashboard context bar: **"Last scan 06:14 · 24 reports · 6 domains"**

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app, lifespan, CORS, routers
│   ├── core/
│   │   ├── config.py              # Settings (env vars)
│   │   └── database.py            # Async SQLAlchemy session factory
│   ├── models/
│   │   ├── base.py                # Base model (UUID pk, created_at, updated_at)
│   │   ├── user.py                # User / steward
│   │   ├── domain.py              # Domain + DataMart
│   │   ├── report.py              # Report + ReportFavourite + ScanSession
│   │   ├── sla.py                 # SLAConfig + PipelineRun + LayerRun ← core
│   │   ├── dq.py                  # DQRule + DQResult
│   │   ├── incident.py            # Incident + IncidentAffectedReport ← core
│   │   └── glossary.py            # GlossaryEntry
│   ├── schemas/
│   │   └── dashboard.py           # Pydantic response models with computed fields
│   ├── services/
│   │   ├── sla_service.py         # SLA computation, dashboard aggregates
│   │   ├── ai_service.py          # Claude API: incident naming, DD drafts
│   │   └── log_ingestion.py       # Greenplum CSV → pipeline_runs
│   ├── api/v1/endpoints/
│   │   └── dashboard.py           # GET /dashboard/context|sla-status|incidents
│   └── workers/
│       ├── celery_app.py          # Celery config + Beat schedule
│       ├── tasks.py               # Task definitions
│       └── sla_monitor.py         # Core SLA check + incident creation
├── alembic/
│   └── versions/001_initial_schema.py
├── scripts/
│   └── seed.py                    # Reference data (domains, marts, SLA configs, reports)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Infrastructure

### docker-compose.yml Services

| Service | Image | Purpose |
|---|---|---|
| `db` | postgres:16-alpine | Primary database |
| `redis` | redis:7-alpine | Celery broker + cache |
| `api` | ./Dockerfile | FastAPI application |
| `worker` | ./Dockerfile | Celery worker (SLA monitor, ingestion) |
| `beat` | ./Dockerfile | Celery Beat (task scheduler) |

### Celery Beat Schedule

| Task | Schedule | Purpose |
|---|---|---|
| `run_sla_check` | Every 5 minutes | Check SLA, create incidents |
| `run_scan_session` | Every hour | Update report counts, create ScanSession |

### Environment Variables

```env
DATABASE_URL=postgresql+asyncpg://meridian:meridian@localhost:5432/meridian
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=sk-ant-...
DEBUG=false
CORS_ORIGINS=["http://localhost:3000"]
```

---

## Security Considerations

- All financial data stays within the bank's infrastructure
- Claude API receives only metadata (table names, column names, counts) — no actual row data
- Glossary entries stored in Meridian DB, not sent to external APIs
- API authentication: JWT (to be implemented in production)
