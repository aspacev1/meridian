# Meridian — AI Data Steward

> Intelligent data governance platform built on top of OpenMetadata. Monitors pipeline SLA, detects data quality incidents, and assists stewards through AI-generated insights.

![Status](https://img.shields.io/badge/status-prototype-blue)
![Version](https://img.shields.io/badge/version-v43-informational)
![Stack](https://img.shields.io/badge/stack-FastAPI%20%7C%20PostgreSQL%20%7C%20Celery-lightgrey)

---

## Live Demo

🔗 **[Open Prototype →](https://aspacev1.github.io/meridian/)**

The prototype is a fully interactive single-page application with mock data. No backend required to explore the UI.

---

## What is Meridian?

Meridian is a Data Steward platform designed for banks and financial institutions running Greenplum/PostgreSQL data warehouses. It sits on top of OpenMetadata and provides:

- **Real-time SLA monitoring** across pipeline layers (Source → Staging → ODS → DM)
- **AI-generated incident cards** with root cause analysis
- **Data Quality tracking** at every layer with rule-level detail
- **Data Dictionary** with glossary management and calculation documentation
- **Executive View** with role-specific dashboards (CDO / CRO / CFO)
- **Task Board** for AI-drafted governance items awaiting steward review
- **Report Catalog** with favourites, lineage, and ownership

---

## Screenshots

### Dashboard — Data Readiness
Active incidents with AI-generated names and descriptions, SLA status strip, and pipeline layer health.

### Catalog — Report Cards
Per-report SLA breakdown across Source / Staging / ODS / DM layers with row counts and DQ pass rates.

### Data Dictionary
Expandable field cards with business names, definitions, calculation code blocks, and DQ alerts.

### Executive View — CDO / CRO / CFO
Role-specific dashboards: governance maturity, regulatory DQ coverage, and financial exposure from data incidents.

---

## Repository Structure

```
meridian/
├── index.html              # Full interactive prototype (single file)
├── README.md               # This file
├── docs/
│   ├── ARCHITECTURE.md     # Backend architecture & data model
│   ├── DATA_MODEL.md       # Database schema with field-level mapping to UI
│   ├── API.md              # REST API endpoints
│   ├── FRONTEND.md         # UI structure, navigation, component guide
│   └── ROADMAP.md          # Feature roadmap & implementation plan
└── backend/                # Backend source code (FastAPI)
    ├── app/
    │   ├── models/         # SQLAlchemy ORM models
    │   ├── services/       # Business logic (SLA, AI, log ingestion)
    │   ├── api/            # FastAPI endpoint routers
    │   └── workers/        # Celery background workers
    ├── alembic/            # Database migrations
    ├── scripts/            # Seed data & utilities
    ├── requirements.txt
    ├── Dockerfile
    └── docker-compose.yml
```

---

## Quick Start (Prototype)

No installation needed. Just open `index.html` in any browser:

```bash
git clone https://github.com/aspacev1/meridian.git
cd meridian
open index.html   # macOS
# or double-click index.html on Windows/Linux
```

---

## Backend Quick Start

```bash
cd backend

# 1. Copy environment config
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

# 2. Start all services
docker compose up -d

# 3. Run migrations
docker compose exec api alembic upgrade head

# 4. Seed reference data
docker compose exec api python scripts/seed.py

# 5. Ingest a Greenplum CSV log
docker compose exec worker celery call app.workers.tasks.ingest_csv_log \
  --args='["/app/logs/etl_2026-03-30.csv"]'

# 6. Open API docs
open http://localhost:8000/docs
```

---

## Tech Stack

### Frontend (Prototype)
- Vanilla HTML/CSS/JavaScript — single file, zero dependencies
- Material Design 3 (Material You) design system
- Roboto + Roboto Mono typography

### Backend (Production)
| Layer | Technology |
|---|---|
| API | FastAPI (Python 3.12) |
| Database | PostgreSQL 16 |
| Cache / Broker | Redis 7 |
| Background workers | Celery + Celery Beat |
| Migrations | Alembic |
| AI | Anthropic Claude API |
| DW Source | Greenplum / PostgreSQL |
| Metadata | OpenMetadata REST API |

---

## Key Concepts

### Pipeline Layers
Every data mart is monitored at four layers:

```
Source → Staging → ODS → DM
```

Each layer has its own SLA target time, DQ threshold, and row count expectation. The DM layer SLA is inherited by all reports built on that mart.

### SLA Status
Computed for each `LayerRun` by comparing actual delivery time against `SLAConfig` targets:

| Condition | Status |
|---|---|
| Delivered on time, DQ ≥ threshold | ✅ Healthy |
| Delivered late OR DQ below threshold | ⚠ Warning |
| Pipeline failed OR not delivered | ❌ Breach |

### Incidents
Auto-created by the SLA Monitor worker (runs every 5 minutes). Each incident includes:
- AI-generated name and description (Claude API)
- Layer status map (`{"source": "ok", "staging": "failed", ...}`)
- SLA delay in minutes → formatted as "+1h 54m overdue"
- Occurrence count → "3rd time in 16 months"
- Affected reports count and availability label

---

## Dashboard → Database Mapping

| UI element | Table | Column |
|---|---|---|
| "Steward: Alim Salahov" | `users` | `full_name` |
| "Last scan 06:14" | `scan_sessions` | `finished_at` |
| "24 reports · 6 domains" | `scan_sessions` | `reports_scanned`, `domains_scanned` |
| "1 Breach" | `layer_runs` | COUNT WHERE `sla_status='breach'` AND `layer='dm'` |
| Incident title | `incidents` | `ai_name` |
| "+1h 54m overdue" | `incidents` | `sla_delay_minutes` |
| "3rd time in 16 months" | `incidents` | `occurrence_count`, `occurrence_window_days` |
| "Staging ✕ › ODS ✕" | `incidents` | `layer_statuses` (JSON) |

---

## Greenplum CSV Log Ingestion

Meridian reads ETL logs exported from Greenplum as CSV files and builds the pipeline run history automatically.

Expected CSV columns:
```
job_name, job_id, mart_name, layer, started_at, finished_at, rows_affected, status, error_message
```

The ingestion service (`app/services/log_ingestion.py`) handles:
- Parsing timestamps in multiple formats
- Mapping layer names to canonical enum values
- Idempotent upsert (safe to re-ingest the same file)
- Grouping rows by `(mart_name, run_date)` into `PipelineRun` records

---

## AI Features

All AI features use the **Claude claude-sonnet-4-20250514** model via the Anthropic API.

| Feature | Trigger | Output |
|---|---|---|
| Incident naming | SLA breach detected | Short title: "Pipeline SLA Breach — dm_market" |
| Incident description | SLA breach detected | 1-2 sentence technical description |
| Glossary draft | New field discovered | Business name, definition, calculation hint |
| Task board | Scan completion | Governance items (descriptions, classifications, ownership) |

---

## Contributing

This project is in active prototype phase. Contributions welcome:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Contact

Built by the Data Governance team at **International Bank of Azerbaijan**.  
Steward: Alim Salahov · Platform: Meridian v43
