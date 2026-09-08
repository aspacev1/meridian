# Meridian — Repository Audit & Backend Build Plan

> Research-only deliverable. No backend code is written yet. This document records what the
> repository actually contains, what the application does, every screen's data needs, the gaps
> between the UI and the documented data model, and a proposed backend structure and build order.

---

## 1. What is actually in the repository

| Path | Size | What it is |
|---|---|---|
| `index.html` | 5,096 lines | The entire application. Vanilla HTML/CSS/JS, MD3 design, fully clickable, all data hard-coded in JS arrays and static markup. Zero network calls. |
| `README.md` | — | Product overview. **Claims `docs/` and `backend/` directories that do not exist.** |
| `ARCHITECTURE.md` | — | Target backend design: FastAPI + PostgreSQL + Redis + Celery. Design only. |
| `DATA_MODEL.md` | — | 13-table schema with UI-to-column mapping. Design only. |
| `API.md` | — | 16 REST endpoints. Design only. |
| `FRONTEND.md` | — | Guide to `index.html` structure. Accurate. |
| `ROADMAP.md` | — | 5-phase single-tenant roadmap. |
| `SAAS_TRANSFORMATION_PLAN.md` | — | 10-phase multi-tenant SaaS plan (added in PR #1). |

There are no `backend/`, `docs/`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`, tests, CI, or `.gitignore`. Git history is four commits. The only external dependency of the prototype is Google Fonts.

**Bottom line:** the backend is a greenfield build. The markdown specs are a good starting point but the prototype UI shows considerably more data than `DATA_MODEL.md` covers (see §5).

---

## 2. What Meridian is

Meridian is an **AI Data Steward** for banks running a Greenplum/PostgreSQL warehouse. It sits beside a metadata catalog (OpenMetadata) and answers one question every morning: *"Which reports can I trust today, and if not, why?"*

Core domain concepts, in dependency order:

```
Domain (Credit Risk, Market Risk, Treasury, Compliance, Retail Banking, …)
  └─ Data Mart (dm_credit, dm_market, dm_treasury …)   ← one Greenplum schema, one nightly pipeline
       ├─ Pipeline layers: Source → Staging → ODS → DM  (+ optional DWH/EDW)
       │    each layer has an SLA config (ready-by time, min rows, min DQ %, survival %, …)
       ├─ Pipeline Run (one per mart per business date) → Layer Runs (one per layer)
       │    ingested from Greenplum ETL logs (CSV) or webhooks (Airflow/dbt)
       ├─ DQ Rules → DQ Results (per layer run)
       ├─ Tables → Columns (physical catalog, from OpenMetadata or schema scan)
       │    └─ Glossary Entry (business name, definition, calculation, regulatory refs; draft/published)
       └─ Reports (Power BI etc.) ← linked to specific tables/columns of the mart
            └─ inherit the DM layer's SLA (+ BI generation offset)

Incident  = SLA Monitor detects breach/warning on a layer run → AI names + describes it,
            computes delay, occurrence count, affected reports, suggested resolution.
Task      = AI-drafted governance item (description, glossary term, classification,
            ownership, lineage) awaiting steward approve/edit/reject.
Scan      = periodic run of the monitor; powers "Last scan 06:14 · 24 reports · 6 domains".
```

Readiness status per report is a three-state traffic light: `go` (Ready) / `warn` (At Risk) / `stop` (Failed). Layer SLA status is `healthy` / `warning` / `breach` / `no_scan`.

---

## 3. Application structure (screen inventory)

`index.html` is one shell with a left navigation rail and eleven "pages" toggled by `nav(pageId)`. Below is every page, what it shows, and which JS data source it reads from today.

| # | Page (`id`) | Reached from | What it shows | Data today |
|---|---|---|---|---|
| 1 | Dashboard `pg-dashboard` | Home | Context bar (steward, date, last scan, counts, next scan), SLA strip (breach/warn/healthy at DM layer), active incident cards (AI name, description, layer status chain, affected-report count, occurrence chip, ETA, "View RCA") | Static HTML |
| 2 | Catalog `pg-catalog` | Catalog | Left tree: search, Favourites (sorted by open count), All Reports, Domain → Report tree with health dots, "+ Add report", steward actions. Main: status filter strip, report cards grouped by domain with per-layer SLA table (rows / actual vs target time / DQ pass-fail) | `REPORTS`, `DOMAINS`, `favourites`, `USAGE_DATA` |
| 3 | Report Detail `pg-detail` | Catalog card | Header (name, badge, meta, favourite button, glossary stats). Seven tabs (below). Side panel: usage today/month, 14-day run trend, report info, 7-day DQ trend, pattern alert, time-to-resolution | `REPORT_DETAILS`, `USAGE_DATA`, static HTML |
| 3a | ↳ Overview | tab | Readiness hero (verdict, reason, DQ score, freshness, pipeline), AI narrative (+confidence, approve/edit/reject), suggested resolution (+assign to team), downstream impact list | `REPORT_DETAILS`, static |
| 3b | ↳ Data Dictionary | tab | Filter (all/published/draft/none), per-table field cards: business name, tech name, type, definition, calculation code, DQ alert, last edited by; Add/Edit/Publish glossary modal | Static HTML (7 fields, 3 tables) |
| 3c | ↳ Lineage & RCA | tab | Node graph Source→Staging→ODS→DM→Report, root cause highlighted; node detail panel with Actual vs SLA Target vs Breach Details | `NODES` |
| 3d | ↳ DQ Rules | tab | All rules across layers with pass/fail and count detail | Static HTML |
| 3e | ↳ Affected Rows | tab | KPI strip (total affected, % of dataset), AI assignment suggestions per DQ issue (→ creates tasks), row-level table of failing records with rule tags, export CSV | `AFF_ROWS`, `assignedTasks` |
| 3f | ↳ History | tab | Incident timeline (date, title, detail, resolution/time), pattern detection note | Static HTML |
| 3g | ↳ Ownership | tab | Data owner, steward, domain, department, classification, retention, regulatory refs | Static HTML |
| 4 | Task Board `pg-tasks` | Tasks | Group filter (Descriptions / Glossary Terms / Classifications / Ownership / Lineage) with counts; task cards: asset, column, AI draft, confidence %, regulatory tags, target report; approve / edit / reject; bulk approve ≥90% | `TASKS`, `approvedTasks` |
| 5 | Chat `pg-chat` | Chat | AI steward chat with greeting summary, suggestion chips, deep-links into reports/tasks | `CHAT_RESP` (keyword match, not an LLM) |
| 6 | Settings `pg-settings` | Settings | Link to Register Mart; connector config (metadata source, log source, DQ source, catalog backend); scan schedule | Static HTML |
| 7 | Data Marts `pg-marts` | (not linked from rail) | Mart cards: status Active/Onboarding, tables/cols/reports counts, per-layer SLA status today, onboarding step progress | Static HTML |
| 8 | Register Mart `pg-register` | Settings / Catalog | 5-step wizard: Connection (name, type, host, db, schemas, log source, DQ source) → Pipeline & SLA (toggle 5 layers incl. optional DWH; per-layer thresholds; scan schedule) → BI Connector (Power BI tenant/client/secret/workspace, test connection) → Ownership (owner, steward, domain, classification, retention, regulatory refs, per-layer team + on-call) → Review | `REG_LAYERS`, `MART_STEPS` |
| 9 | Register Report `pg-register-report` | Catalog "+ Add report" | 4-step wizard: Source method (Power BI scan / paste SQL / stored procedure → parsed tables+columns) → confirm attributes & mart mapping → business context (name, description, type, criticality, owner, audience, domain, regs) → SLA (inherited DM SLA + BI generation minutes → available-by) & review | `rrParsedAttrs`, `REPORT_STEPS` |
| 10 | Executive `pg-executive` | rail bottom | Fullscreen overlay with date navigation and three role views: **CDO** (governance maturity by domain, glossary coverage, pending reviews, actions needed), **CRO** (report reliability table, DQ by regulatory framework, active incidents), **CFO** (downtime cost, portfolio at risk, RWA impact, incident recurrence, recommendation) | `exvCDO/CRO/CFO` inline data, `exvDates` |

Interaction primitives the backend must support: favourite toggle, report-open counting, glossary save/publish, task approve/reject/edit, AI narrative approve/reject, resolution assign, affected-row task assignment, CSV export, chat send, wizard submit, connection test, Power BI workspace scan, SQL/procedure parse.

Prototype defects worth knowing: `showAddReportModal` is defined twice (the second definition, an `alert`, wins, so the Register Report wizard is only reachable via `initRegisterReport` directly); the Data Marts page is not linked from the rail; the "24 reports / 6 domains" figures in the header are not derived from the 10-report / 5-domain mock data.

---

## 4. Screen-to-endpoint map

This is the contract the backend has to serve. Endpoints marked **(new)** are not in `API.md`.

| Screen / element | Endpoint | Notes |
|---|---|---|
| Dashboard context bar | `GET /dashboard/context` | from latest `scan_sessions` + current user |
| SLA strip | `GET /dashboard/sla-status?run_date=` | DM-layer aggregation over `layer_runs` |
| Incident cards | `GET /dashboard/incidents?run_date=` | includes `layer_statuses`, labels, ETA, affected count |
| Incident → "View RCA" | `GET /incidents/{id}` **(new)** | full incident incl. narrative, resolution, affected reports |
| Catalog tree + cards | `GET /catalog/domains` **(new)**, `GET /catalog/reports?domain_id&status&q` | reports carry `sla_layers[]` for today |
| Favourites | `POST/DELETE /catalog/reports/{id}/favourite`, `POST /catalog/reports/{id}/open` | open increments usage |
| Report detail header + Overview | `GET /catalog/reports/{id}` | verdict, reason, DQ score, freshness, pipeline, narrative, resolution, impact list |
| Narrative / resolution actions | `POST /reports/{id}/narrative/{approve\|reject}` **(new)**, `POST /incidents/{id}/resolution/assign` **(new)** | |
| Data Dictionary tab | `GET /dd/{report_id}/tables` | tables → columns → glossary + DQ alerts |
| Glossary modal | `PUT /dd/{table}/{field}/glossary`, `POST /dd/{table}/{field}/publish` | |
| Lineage & RCA tab | `GET /lineage/report/{report_id}` **(new)** | nodes with actual / SLA target / breach details |
| DQ Rules tab | `GET /reports/{id}/dq-rules` **(new)** | rules across layers with latest result |
| Affected Rows tab | `GET /reports/{id}/affected-rows?page=`, `GET …/affected-rows/export.csv`, `POST /work-items` **(new)** | |
| History tab | `GET /reports/{id}/incidents?days=90` **(new)** | timeline + occurrence pattern |
| Ownership tab | part of `GET /catalog/reports/{id}` | |
| Side panel usage & trends | `GET /reports/{id}/usage?days=14`, `GET /reports/{id}/dq-trend?days=7` **(new)** | |
| Task Board | `GET /tasks?group=&status=pending`, `POST /tasks/{id}/{approve\|reject}`, `PATCH /tasks/{id}`, `POST /tasks/bulk-approve?min_confidence=90` **(new)** | approve writes back to glossary / classification / ownership |
| Chat | `POST /chat/sessions`, `POST /chat/sessions/{id}/messages` **(new)** | Claude with org context; streaming optional |
| Settings connectors | `GET/PUT /settings/connectors`, `POST /settings/connectors/test` **(new)** | |
| Scan schedule | `GET/PUT /settings/scan-schedule` **(new)**, `POST /scans/trigger` **(new)** | |
| Data Marts page | `GET /marts` **(new)** | with counts + today's layer status |
| Register Mart wizard | `POST /marts` **(new)** (single payload from step 5), `POST /marts/test-connection`, `POST /marts/{id}/scan` | creates mart + sla_configs + connection + ownership |
| Register Report wizard | `POST /bi/powerbi/scan` **(new)**, `POST /parse/sql` **(new)**, `POST /parse/procedure` **(new)**, `POST /reports` **(new)** | parse returns `{tables:[{table, mart, cols[]}]}` |
| Executive view | `GET /executive/{cdo\|cro\|cfo}?date=` **(new)**, `GET /executive/dates` **(new)** | served from daily snapshots |
| Ingestion | `POST /ingestion/csv`, `POST /ingestion/webhook` | existing spec |
| AI | `POST /ai/glossary-draft` | existing spec |
| Auth | `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me` **(new)** | JWT; SSO later |

---

## 5. Gaps between the UI and `DATA_MODEL.md`

`DATA_MODEL.md` covers the dashboard and catalog card well. The following UI data has **no home** in the documented schema and must be added.

| UI element | Missing model | Proposed table(s) |
|---|---|---|
| Register Mart: connection type, host, db, schemas, log source, DQ source, BI credentials | Mart connectivity | `data_source_connections` (encrypted), `bi_connections` |
| Register Mart: optional DWH layer; per-layer min rows, row-survival %, max null %, max drop %, max data age, escalation level, on-call contact | SLA thresholds beyond `target_time` + `dq_threshold_pct` | extend `sla_configs`; add `dwh` to layer enum |
| Register Mart: scan frequency, scan time, business calendar; onboarding status "Step 3/5 — AI enrichment" | Mart schedule and lifecycle | columns on `data_marts` (`scan_cron`, `calendar`, `onboarding_status`, `onboarding_step`, `cost_per_hour`) |
| Register Report: detected tables and columns; method used; BI generation minutes; available-by; type, criticality, audience, description | Report ↔ physical asset mapping and report metadata | `report_tables`, `report_columns`, extra columns on `reports` |
| Data Dictionary: table row count, table description, column data type, "N fields used" | Physical catalog | `catalog_tables`, `catalog_columns` (synced from OpenMetadata / information_schema) |
| Lineage graph + node detail (Actual vs Target vs Breach) | Lineage | `lineage_nodes`, `lineage_edges` (roadmap Phase 5; needed earlier for RCA tab) |
| AI narrative, suggested resolution, confidence %, approve/reject state, downstream impact | Incident AI artefacts | columns on `incidents` (`ai_narrative`, `ai_resolution`, `narrative_confidence`, `resolution_confidence`, `narrative_status`, `assigned_team`) |
| History tab: resolution note, resolution duration, "false positive" | Incident lifecycle | `resolution_note`, `resolution_minutes`, `is_false_positive` on `incidents` |
| Task Board cards | Governance tasks | `governance_tasks` (group, asset, column, draft, confidence, regulatory_refs, target_report_id, status, reviewed_by, reviewed_at, payload JSON) |
| Affected Rows: table, row sample, failing rule tags, assignment | DQ failure detail | `dq_failed_rows` (or `dq_result_samples`) keyed by `dq_result_id` |
| "Assign →" / "Create task for selected rows" | Operational work items | `work_items` (name, assignee, priority, due, status, source incident / dq result) |
| Side panel usage today / month / 14-day trend; favourites sort | Usage events | `report_open_events` (user, report, opened_at); aggregate on read |
| DQ trend 7 days | Per-report daily DQ score | derived from `layer_runs`; optionally `report_daily_snapshots` |
| Executive date navigation; CDO/CRO/CFO KPIs; regulatory framework coverage; portfolio-at-risk AZN | Daily snapshots and finance config | `executive_snapshots` (date, view, payload JSON) written by the scan worker; `regulatory_frameworks`, `report_regulations` |
| Ownership tab: data owner, department, classification, retention | Governance attributes | columns on `reports` / `data_marts`, `owner_id` FK to `users` |
| Chat | Conversations | `chat_sessions`, `chat_messages` |
| Nav badge "20" | Pending task count | derived |
| Multiple stewards (Alim Salahov, Kamran Aliyev, Fuad Mammadov) | Users | already in `users`; needs seeding and auth |

Two enum corrections: layer enum needs `dwh`; incident `type` needs `pipeline_delay` (used on the CFO view) alongside `pipeline_sla_breach`, `dq_sla_breach`, `data_freshness`.

---

## 6. Proposed backend structure

Keep the documented stack (FastAPI, Python 3.12, PostgreSQL 16, Redis 7, Celery + Beat, Alembic, Anthropic SDK). Place it at `backend/` so the README becomes true. Structure below expands `ARCHITECTURE.md` to cover every screen in §3.

```
meridian/
├── index.html                       # prototype (unchanged for now; later ported to apps/web)
├── docs/                            # move the six *.md specs here (README already points here)
├── backend/
│   ├── pyproject.toml               # deps + ruff + mypy + pytest config
│   ├── Dockerfile
│   ├── docker-compose.yml           # db, redis, api, worker, beat
│   ├── .env.example
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 0001_initial.py
│   ├── scripts/
│   │   ├── seed.py                  # domains, marts, sla_configs, users, reports = the prototype data
│   │   └── sample_logs/etl_2026-03-30.csv
│   ├── app/
│   │   ├── main.py                  # app factory, lifespan, CORS, routers, RFC 7807 handlers
│   │   ├── core/
│   │   │   ├── config.py            # pydantic-settings
│   │   │   ├── database.py          # async engine + session dependency
│   │   │   ├── security.py          # JWT, password hashing, current_user dependency, RBAC
│   │   │   ├── crypto.py            # envelope encryption for connection secrets
│   │   │   ├── errors.py            # ProblemDetails exceptions
│   │   │   └── logging.py           # structured JSON logging
│   │   ├── models/                  # SQLAlchemy 2.0 declarative
│   │   │   ├── base.py              # UUID pk, created_at, updated_at, (org_id)
│   │   │   ├── user.py
│   │   │   ├── domain.py            # Domain
│   │   │   ├── mart.py              # DataMart, DataSourceConnection, BIConnection
│   │   │   ├── sla.py               # SLAConfig, PipelineRun, LayerRun
│   │   │   ├── catalog.py           # CatalogTable, CatalogColumn
│   │   │   ├── report.py            # Report, ReportTable, ReportColumn, ReportFavourite, ReportOpenEvent
│   │   │   ├── dq.py                # DQRule, DQResult, DQFailedRow
│   │   │   ├── incident.py          # Incident, IncidentAffectedReport
│   │   │   ├── glossary.py          # GlossaryEntry
│   │   │   ├── lineage.py           # LineageNode, LineageEdge
│   │   │   ├── task.py              # GovernanceTask, WorkItem
│   │   │   ├── scan.py              # ScanSession, ExecutiveSnapshot
│   │   │   ├── regulation.py        # RegulatoryFramework, ReportRegulation
│   │   │   └── chat.py              # ChatSession, ChatMessage
│   │   ├── schemas/                 # Pydantic v2 request/response models, one module per router
│   │   │   ├── dashboard.py, catalog.py, report.py, dd.py, lineage.py, dq.py,
│   │   │   ├── tasks.py, marts.py, settings.py, executive.py, chat.py, ingestion.py, ai.py, auth.py
│   │   ├── api/
│   │   │   ├── deps.py              # db session, current user, pagination
│   │   │   └── v1/
│   │   │       ├── router.py        # includes all routers under /api/v1
│   │   │       └── endpoints/
│   │   │           ├── auth.py          dashboard.py     catalog.py      reports.py
│   │   │           ├── dd.py            lineage.py       dq.py           tasks.py
│   │   │           ├── marts.py         settings.py      executive.py    chat.py
│   │   │           ├── ingestion.py     ai.py            parse.py        health.py
│   │   ├── services/                # business logic, no HTTP concerns
│   │   │   ├── sla_service.py       # compute_sla_status, dashboard aggregates, report readiness
│   │   │   ├── readiness_service.py # go/warn/stop per report from DM layer + DQ + freshness
│   │   │   ├── incident_service.py  # create/update incidents, occurrence counting, impact
│   │   │   ├── ai_service.py        # Claude: incident naming, narrative, resolution, glossary draft, task drafts, chat
│   │   │   ├── ai_guardrails.py     # allow-list of what may be sent to Claude (metadata only)
│   │   │   ├── log_ingestion.py     # CSV / webhook → pipeline_runs + layer_runs (idempotent)
│   │   │   ├── dq_aggregator.py     # DQ results → layer_run denormalised counts, failed-row samples
│   │   │   ├── catalog_sync.py      # OpenMetadata / information_schema → catalog_tables/columns
│   │   │   ├── lineage_service.py   # sqlglot parse of ETL SQL → nodes/edges; report lineage view
│   │   │   ├── sql_parse_service.py # Register Report: SQL / procedure → tables+columns
│   │   │   ├── powerbi_service.py   # Register Report: workspace scan via Power BI REST API
│   │   │   ├── task_service.py      # governance task generation + approve write-back
│   │   │   ├── glossary_service.py
│   │   │   ├── usage_service.py     # open events → today / month / 14-day trend
│   │   │   ├── executive_service.py # build CDO/CRO/CFO payloads; snapshot per day
│   │   │   ├── connection_service.py# test Greenplum / OpenMetadata / Power BI credentials
│   │   │   └── export_service.py    # affected rows → CSV
│   │   ├── connectors/              # thin clients to external systems
│   │   │   ├── greenplum.py         # asyncpg/psycopg against customer warehouse (read-only)
│   │   │   ├── openmetadata.py
│   │   │   ├── powerbi.py
│   │   │   └── anthropic_client.py  # retries, rate limit, cost accounting
│   │   └── workers/
│   │       ├── celery_app.py        # config + Beat schedule
│   │       ├── sla_monitor.py       # every 5 min
│   │       ├── scan_session.py      # hourly / per mart schedule; writes scan_sessions + executive_snapshots
│   │       ├── catalog_sync.py      # daily
│   │       ├── task_generator.py    # after each scan
│   │       └── ingestion.py         # CSV drop folder / on-demand
│   └── tests/
│       ├── conftest.py              # testcontainers Postgres, factories
│       ├── unit/                    # sla_service, readiness, ingestion idempotency, sql parse
│       ├── api/                     # endpoint contract tests against API.md examples
│       └── integration/             # csv → sla monitor → incident → dashboard
├── .github/workflows/ci.yml         # ruff, mypy, pytest, alembic check
└── Makefile                         # up, migrate, seed, test, lint
```

### Design notes

- **Readiness is computed, not stored.** `reports.current_status` in `DATA_MODEL.md` should be a materialised cache written by the SLA monitor from: DM layer SLA status of the primary mart, DQ pass rate vs threshold, freshness (max data age), and pipeline run status. Keep the rule in one place (`readiness_service.py`) so the dashboard, catalog, executive view and chat agree.
- **Layer runs are the hot table.** Every dashboard/catalog read is "today's layer runs joined to sla_configs". Index `(mart_id, run_date)` on `pipeline_runs` and `(pipeline_run_id, layer)` on `layer_runs` as the doc says, and materialise `sla_status`, `sla_delay_minutes`, `dq_rules_passed/total` on `layer_runs` at monitor time.
- **AI outputs are first-class rows with review state.** Narrative, resolution, glossary drafts, task drafts all carry `confidence`, `status` (`draft` / `approved` / `rejected` / `edited`), `reviewed_by`, `reviewed_at`. The Task Board is a view over `governance_tasks WHERE status='pending'`.
- **Guardrail in code.** `ai_guardrails.py` builds every Claude prompt from an allow-listed set of fields (names, counts, timestamps, statuses). Row values from `dq_failed_rows` never enter a prompt.
- **Wizard submissions are single transactional payloads.** `POST /marts` receives the whole five-step form and creates mart + connection + sla_configs + ownership in one transaction, then enqueues a first scan. Same for `POST /reports`.
- **Executive view reads snapshots.** The scan worker writes one `executive_snapshots` row per date and view. Date navigation then costs one indexed read and historical values do not drift as data is re-ingested.
- **Tenancy.** Even for a single bank, put `org_id` on every table via the base model and scope every query through a dependency from day one. Defer Row-Level Security, SSO and billing until the multi-tenant decision in `SAAS_TRANSFORMATION_PLAN.md` is made. This is cheap now and very expensive later.
- **Secrets.** Warehouse and Power BI credentials live in `data_source_connections` / `bi_connections` encrypted with a KMS-wrapped data key, never in `.env`.

---

## 7. Build order

Each step ends with something the prototype can be pointed at. Steps 1 to 3 make the Dashboard and Catalog real, which is the visible milestone `ROADMAP.md` Phase 1 asks for.

| Step | Scope | Output |
|---|---|---|
| 0 | Repo hygiene: move specs to `docs/`, add `.gitignore`, `backend/` skeleton, Docker Compose, CI, pre-commit | `docker compose up` gives a healthy `/health` |
| 1 | Models + Alembic 0001 for the full schema in §5 (not just the 13 documented tables); seed script reproducing the prototype's 10 reports, 5 domains, 3 marts, 7 glossary fields, 8 tasks, incidents | `alembic upgrade head && python scripts/seed.py` |
| 2 | Auth (JWT, roles), users, `GET /auth/me`; RFC 7807 errors; request logging | login works |
| 3 | Ingestion (CSV + webhook) → `sla_service` → SLA monitor worker → incidents (AI naming stubbed behind an interface) → `dashboard/*`, `catalog/*`, favourites, open events | Dashboard + Catalog served from Postgres |
| 4 | Report detail: readiness service, overview, DQ rules, history, ownership, usage, DQ trend | Report detail tabs 1, 4, 6, 7 + side panel |
| 5 | Catalog sync (OpenMetadata or information_schema) + glossary CRUD + publish | Data Dictionary tab |
| 6 | Marts page, Register Mart (`POST /marts`, test connection), Settings connectors + scan schedule | Onboarding without touching the DB by hand |
| 7 | Register Report: SQL/procedure parse (`sqlglot`), Power BI scan, `POST /reports`, `report_tables/columns` | Reports linked to physical columns |
| 8 | Lineage nodes/edges from ETL SQL + report mapping; `GET /lineage/report/{id}` with Actual/Target/Breach | Lineage & RCA tab |
| 9 | Real Claude integration: incident naming, narrative, resolution, glossary draft, task generation after scan, chat grounded in org data; guardrails; cost accounting | Task Board and Chat live |
| 10 | Affected rows: failed-row sampling from warehouse per DQ result, assignment → work items, CSV export | Affected Rows tab |
| 11 | Executive snapshots (CDO/CRO/CFO), regulatory frameworks, `cost_per_hour` on marts, date navigation | Executive view |
| 12 | Notifications (email/Slack), hardening, load test, tenant-scoping tests | Production readiness |

Steps 4 and 5 can run in parallel with 3 once the schema exists; 6 and 7 are independent of 8 to 11.

---

## 8. Decisions to confirm before step 1

1. **Single-tenant now, multi-tenant later?** This plan assumes single bank with `org_id` present but no RLS or billing. Say if the SaaS plan should drive scope instead.
2. **Source of physical metadata:** OpenMetadata REST API (documented) or direct `information_schema` on Greenplum? The Register Mart wizard offers both catalog backends. Recommend supporting `information_schema` first as the zero-dependency path.
3. **Pipeline log source:** CSV export (documented) versus direct query of Greenplum ETL control tables or Airflow webhook. The ingestion interface should be a connector so all three can coexist.
4. **DQ engine:** rules are stored and evaluated by Meridian (`custom_sql` against the warehouse), or results are imported from OpenMetadata DQ / Great Expectations / Soda? Determines whether `dq_results` is written by a worker or by an importer.
5. **Frontend path:** keep `index.html` and add a `fetch` layer behind the existing render functions, or start the React port from `SAAS_TRANSFORMATION_PLAN.md` Phase 3. The backend contract in §4 is the same either way.
6. **Currency and cost:** CFO view is in AZN; make currency an org setting.
