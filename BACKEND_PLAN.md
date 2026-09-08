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
| Settings connectors | `GET/PUT /connections`, `POST /connections/{id}/test`, `GET /sync-runs` **(new)** | see §6.3 |
| Scan schedule | `GET/PUT /settings/scan-schedule` **(new)**, `POST /scans/trigger` **(new)** | |
| Data Marts page | `GET /marts` **(new)** | with counts + today's layer status |
| Register Mart wizard | `POST /marts` **(new)** (single payload from step 5), `POST /connections/{id}/test`, `POST /marts/{id}/scan` | creates mart + sla_configs + connection + ownership |
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

## 6. Connector layer (the core of the product)

Everything Meridian shows is a view over two external systems. OpenMetadata supplies *meaning*: catalog, ownership, tags, glossary, DQ definitions and results, lineage. Greenplum supplies *truth about tonight's run*: what loaded, when, how many rows, which rows failed, how fresh each table is. Meridian's value is the join. The connector layer is therefore built first, tested hardest, and exposed to the rest of the backend only through interfaces.

### 6.1 Responsibility split

| Meridian needs | OpenMetadata | Greenplum |
|---|---|---|
| Tables, columns, types, descriptions | `GET /api/v1/tables` with `fields=columns,owners,tags,domain` | fallback: `information_schema.tables` / `columns`, `pg_description` |
| Row counts, table size | table profile (`/tables/{id}/tableProfile/latest`) | `pg_class.reltuples`, `gp_toolkit.gp_size_of_table_disk` |
| Freshness (last load time) | profile timestamp at best | `pg_stat_last_operation` (Greenplum-specific: last INSERT / ANALYZE / TRUNCATE per table), `max(snapshot_date)` |
| Ownership, tier, PII classification | `owners`, `tags` (`PII.Sensitive`, `Tier.Tier1`) | none |
| Glossary terms | `GET /api/v1/glossaryTerms`; write-back via `POST/PATCH` | none |
| DQ rule definitions | `GET /api/v1/dataQuality/testCases?entityLink=…` | Meridian's own `custom_sql` rules run against the warehouse |
| DQ results per run | `GET /api/v1/dataQuality/testCases/{fqn}/testCaseResult?startTs&endTs` | result of running `custom_sql` rules; bank's own rule-result tables if present |
| Lineage | `GET /api/v1/lineage/table/name/{fqn}?upstreamDepth&downstreamDepth` | sqlglot over ETL SQL text from logs |
| Pipeline runs per layer (start, end, status, rows) | `GET /api/v1/pipelines/{fqn}/status?startTs&endTs` only if ETL is registered there | primary: ETL control / log tables queried directly; CSV export; Airflow or dbt webhook |
| Failed-row samples (Affected Rows tab) | none | diagnostic query per failed rule, limited and paginated |
| Schema drift alerts | `columns` diff between syncs | `information_schema` diff between syncs |

### 6.2 Package layout

```
backend/app/connectors/
├── base.py                 # capability interfaces (Protocols) + canonical models
│   CatalogSource      list_tables(schemas) -> [ExtTable(ExtColumn…)]
│   ProfileSource      table_stats(fqns)    -> [ExtTableStats(row_count, size, last_modified)]
│   DQSource           list_rules(), results(since) -> [ExtDQRule], [ExtDQResult]
│   LineageSource      edges(fqns)          -> [ExtLineageEdge]
│   PipelineLogSource  events(since)        -> [ExtPipelineEvent(mart, layer, job, start, end, rows, status, error, sql)]
│   RowSampler         failed_rows(rule, limit, offset) -> [dict]
│   GlossarySink       upsert_term(entry)   (write-back, later)
├── registry.py             # resolves which implementation serves which capability for an org
├── health.py               # probe() per connection; writes connection_health
├── openmetadata/
│   ├── client.py           # httpx, bearer bot token, pagination (`after` cursor), retries, rate limit
│   ├── catalog.py          # CatalogSource + ProfileSource
│   ├── dq.py               # DQSource
│   ├── lineage.py          # LineageSource
│   ├── glossary.py         # GlossarySink
│   └── mapping.py          # FQN  <->  (service, database, schema, table, column)
├── greenplum/
│   ├── client.py           # psycopg 3 pool, read-only role, statement_timeout, resource queue
│   ├── catalog.py          # CatalogSource + ProfileSource via pg_catalog / gp_toolkit
│   ├── pipeline_logs.py    # PipelineLogSource: control-table adapter (configurable SQL mapping)
│   ├── dq_runner.py        # DQSource: executes Meridian custom_sql rules
│   ├── row_sampler.py      # RowSampler with allow-listed diagnostic SQL
│   └── queries.py          # every SQL string in one reviewed file
├── csv_logs/               # PipelineLogSource from CSV (API.md /ingestion/csv)
├── webhook/                # PipelineLogSource from Airflow / dbt POSTs
├── powerbi/                # report scan for Register Report (secondary)
└── testing/
    ├── fake_openmetadata.py    # in-memory implementations for unit tests
    ├── fake_greenplum.py
    └── fixtures/               # recorded OpenMetadata JSON responses
```

Canonical models (`ExtTable`, `ExtColumn`, `ExtDQRule`, `ExtDQResult`, `ExtLineageEdge`, `ExtPipelineEvent`, `ExtTableStats`) are Pydantic and system-neutral. Sync services consume only these, so a second warehouse or catalog later is a new subpackage, not a rewrite.

### 6.3 Connection registry and secrets

`connections` table: `org_id`, `kind` (`openmetadata` | `greenplum` | `powerbi` | `webhook`), `name`, `config` (JSON, non-secret: host, port, database, schemas, service name), `secret_ciphertext` (envelope-encrypted DSN / token / client secret), `status`, `last_health_check_at`, `last_error`, `last_sync_at`. The Register Mart wizard step 1 and the Settings connector card write here. "Test Connection" runs `health.probe()` synchronously and stores the result. Nothing secret ever lives in `.env` except the KMS key reference.

### 6.4 Sync engine

- `sync_runs` table: one row per (connection, capability, started, finished, status, counts, error). Powers "catalog synced 05:40 · pipeline logs 06:14" and the health card on Settings.
- Every synced row in `catalog_tables`, `catalog_columns`, `dq_rules`, `dq_results`, `lineage_nodes`, `lineage_edges`, `pipeline_runs`, `layer_runs` carries `external_source` and `external_id` / `external_fqn`, and sync is an upsert on that key. Re-running is always safe.
- Incremental where the source allows it: OpenMetadata `updatedAt` via the search API, Greenplum control-table watermark (`max(finished_at)` seen so far), CSV file hash. Full re-sync nightly as a safety net.
- Schedules (Celery Beat): catalog and profile every 6 h, DQ results and pipeline logs every 5 min feeding the SLA monitor, lineage daily, glossary hourly.
- Resilience: exponential backoff, per-connection circuit breaker, bounded concurrency per org, timeouts on every call.

### 6.5 Reconciliation

Greenplum knows `schema.table`; OpenMetadata knows `service.database.schema.table`. A `reconcile` step maps every Greenplum table to its OpenMetadata FQN using the connection's declared `service` and `database`, and records mismatches (`present_in_warehouse_only`, `present_in_catalog_only`, `column_drift`). These surface as governance tasks on the Task Board. Most real-world bugs will live here, so it gets its own test suite.

### 6.6 Safety on the warehouse side

- Dedicated read-only Greenplum role for Meridian, `default_transaction_read_only = on`, `statement_timeout` (30 s default, longer for row sampling), a low-priority resource queue or resource group.
- All SQL lives in `greenplum/queries.py` and is reviewed; the row sampler and DQ runner only execute templates with bound parameters.
- Row values from `RowSampler` are stored in Postgres and rendered in the Affected Rows tab. They never enter a Claude prompt; `ai_guardrails.py` builds prompts from an allow-list of metadata fields only.

---

## 7. Backend structure

Same stack as `ARCHITECTURE.md` (FastAPI, Python 3.12, PostgreSQL 16, Redis 7, Celery + Beat, Alembic, Anthropic SDK), placed at `backend/` so the README becomes true.

```
meridian/
├── index.html                       # prototype (visual spec; kept until the port reaches parity)
├── docs/                            # the existing *.md specs move here
├── backend/
│   ├── pyproject.toml  Dockerfile  docker-compose.yml  .env.example  Makefile
│   ├── alembic/versions/0001_initial.py
│   ├── scripts/seed.py              # reproduces the prototype data exactly
│   ├── scripts/seed_warehouse.sql   # fake Greenplum: sample marts + etl_control schema
│   ├── app/
│   │   ├── main.py                  # app factory, CORS, routers, RFC 7807 handlers
│   │   ├── core/                    # config, database, security (JWT + RBAC), crypto (envelope), errors, logging
│   │   ├── connectors/              # §6.2
│   │   ├── models/                  # user, domain, mart, connection, sync_run, sla, catalog, report, dq,
│   │   │                            # incident, glossary, lineage, task, scan, regulation, chat
│   │   ├── schemas/                 # Pydantic v2, one module per router
│   │   ├── api/v1/endpoints/        # auth dashboard catalog reports dd lineage dq tasks marts
│   │   │                            # connections settings executive chat ingestion ai parse health
│   │   ├── services/
│   │   │   ├── sync/                # catalog_sync, dq_sync, lineage_sync, pipeline_sync, reconcile
│   │   │   ├── sla_service.py       # compute_sla_status, dashboard aggregates
│   │   │   ├── readiness_service.py # go / warn / stop per report, single source of truth
│   │   │   ├── incident_service.py  # detection, occurrence counting, affected reports
│   │   │   ├── ai_service.py  ai_guardrails.py
│   │   │   ├── glossary_service.py  task_service.py  usage_service.py  executive_service.py
│   │   │   ├── sql_parse_service.py # Register Report: sqlglot over SQL / procedures
│   │   │   └── export_service.py
│   │   └── workers/                 # celery_app, sync_tasks, sla_monitor, scan_session, task_generator
│   └── tests/
│       ├── unit/                    # connectors against fakes, sla, readiness, parse
│       ├── contract/                # same Meridian rows from OM and GP implementations
│       ├── integration/             # compose: fake warehouse + OpenMetadata → sync → monitor → dashboard
│       └── api/                     # endpoint responses match API.md examples
├── frontend/                        # React + TypeScript + Vite port of index.html
│   └── src/{theme,api,components,pages,features}
├── infra/                           # compose overrides, Terraform later
└── .github/workflows/ci.yml
```

---

## 8. Build plan (connector-first)

Each phase ends with a demo. Backend and frontend pair on each phase; the frontend port starts in Phase 0 and lands one screen per phase. Estimates assume two engineers.

| Phase | Weeks | Scope | Demo |
|---|---|---|---|
| **0 Foundation** | 1–2 | Repo split (`backend/`, `frontend/`, `docs/`), Compose (Postgres, Redis, api, worker, beat, **fake warehouse** Postgres with `etl_control` schema, OpenMetadata container), migration 0001 for the full schema in §5, seed script, CI, frontend shell with MD3 tokens, nav rail, router, auth screens, typed API client from OpenAPI | `docker compose up`, login, empty dashboard |
| **1 Connections** | 1 | `connections` + `sync_runs` tables, envelope encryption, `health.probe()` for OpenMetadata and Greenplum, `GET/PUT /connections`, `POST /connections/{id}/test`, Settings connector card | Test Connection button works against the compose stack |
| **2 Greenplum connector** | 2–3 | `client.py`, catalog + profile via `pg_catalog` / `gp_toolkit` / `pg_stat_last_operation`, control-table `PipelineLogSource` with configurable column mapping, CSV and webhook sources, `pipeline_sync` → `pipeline_runs` / `layer_runs`, SLA monitor worker, incidents (AI naming behind an interface, stubbed), `dashboard/*`, `catalog/*`, Dashboard + Catalog pages | Real nightly runs on the Dashboard and Catalog cards |
| **3 OpenMetadata connector** | 2–3 | client with pagination and retries, catalog + owners + tags, DQ test cases and results, lineage edges, glossary read, `catalog_sync` / `dq_sync` / `lineage_sync`, reconciliation + drift tasks, Data Dictionary tab (read), DQ Rules tab, Lineage & RCA tab with Actual / Target / Breach | Report detail shows catalog, DQ and lineage from OpenMetadata joined to Greenplum runs |
| **4 Readiness & report detail** | 1–2 | `readiness_service`, report overview, history, ownership, usage events and trends, favourites, Report Detail Overview / History / Ownership tabs + side panel | Every catalog card opens to a real, consistent detail |
| **5 Glossary & tasks** | 1–2 | glossary CRUD, publish, OpenMetadata write-back (`GlossarySink`), governance task model, Task Board, drift tasks from reconciliation | Stewards edit and publish, changes reach OpenMetadata |
| **6 Onboarding wizards** | 2 | `POST /marts` (whole 5-step payload), per-layer SLA thresholds incl. DWH, mart scan trigger, Marts page, Register Mart wizard, `sql_parse_service`, Power BI scan, `POST /reports` with `report_tables` / `report_columns`, Register Report wizard | New mart and report onboarded end to end without SQL |
| **7 AI** | 2 | Claude integration for incident naming, narrative, resolution, glossary drafts, post-scan task generation, chat grounded in org data; guardrails; cost accounting; approve / reject flows | Task Board and Chat live on real metadata |
| **8 Affected rows** | 1 | `RowSampler`, `dq_failed_rows`, work items and assignment, CSV export, Affected Rows tab | Row-level triage |
| **9 Executive** | 1–2 | daily `executive_snapshots`, regulatory frameworks, `cost_per_hour`, date navigation, CDO / CRO / CFO views | Executive overlay on real history |
| **10 Hardening** | 2 | notifications (email, Slack), audit log, org-scoping tests, load test of dashboard and sync, backups, staging and prod deploy, pilot with the bank's real Greenplum and OpenMetadata | Production pilot |

Total is about 16 to 20 weeks. Phases 2 and 3 are the critical path; 4 and 5 can start once 3's schema exists; 6 to 9 are independent of each other.

### Definition of done for the connector phases

- Contract tests: the same `ExtTable` / `ExtDQResult` / `ExtPipelineEvent` rows from the fake and the real implementation.
- Integration test in CI: seed the fake warehouse and OpenMetadata, run sync, run the SLA monitor, assert the dashboard JSON matches the `API.md` example shape.
- Idempotency test: sync twice, row counts unchanged.
- Failure tests: unreachable host, expired token, timeout, partial page. Each produces a `sync_runs` row with the error and never a half-written state.
- Reconciliation test: table in one system only, renamed column, type change, each yields the expected drift task.
- Security review of `greenplum/queries.py` and `ai_guardrails.py`.

---

## 9. Decisions to confirm before Phase 1

1. **Greenplum pipeline logs.** Does the bank's ETL write a control or log table Meridian can query (job, mart, layer, start, end, rows, status)? If yes, the control-table adapter is primary and CSV becomes a fallback. If no, CSV export plus an Airflow or dbt webhook is the path. This decides most of Phase 2.
2. **OpenMetadata coverage.** Are the marts already ingested with DQ test cases and lineage, or is OpenMetadata only a table catalog today? If only a catalog, Meridian runs its own `custom_sql` DQ rules and derives lineage from ETL SQL, and Phase 3 shrinks while Phase 2 grows.
3. **Greenplum version.** 6 (PostgreSQL 9.4 base) or 7 (PostgreSQL 12 base). Affects `pg_stat_last_operation` columns and psycopg feature use.
4. **Access.** A read-only Greenplum role and an OpenMetadata bot token for a dev environment, so Phases 2 and 3 can be validated against real systems, not only the compose fakes.
5. **Tenancy.** Single bank now, `org_id` present everywhere, no RLS or billing until a second customer exists.
6. **Frontend.** React + TypeScript + Vite port starting in Phase 0, `index.html` kept as the visual spec until parity.
