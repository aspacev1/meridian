# Report Detail — Requirements

Full analysis of the prototype's 7-tab Report Detail screen (`index.html`, `#pg-detail`, ~950 lines of markup/CSS plus ~600 lines of supporting JS) and what it takes to build it for real against the multi-tenant backend from `SAAS_TRANSFORMATION_PLAN.md` Phases 1–3. This is a requirements spec, not an implementation — no code changes are included here.

## 0. Where this sits today

Nothing. `apps/web`'s `CatalogPage` renders report cards with no `onClick` and no link; `App.tsx` has no `/reports/:id` route, not even a placeholder. Report Detail is the single largest gap between the re-platformed frontend and the original prototype's feature surface.

## 1. What the prototype actually does (not just what `FRONTEND.md` summarizes)

Three findings from reading the actual markup/JS that change the shape of the real requirements:

1. **Only the Overview tab is per-report.** `openReport(id)` looks up `REPORT_DETAILS[id]` and populates the header, readiness hero, AI narrative, and resolution text — genuinely per-report mock data for `credit`, `fx`, `liquidity`, `npl`. Every other tab (Lineage & RCA, DQ Rules, Affected Rows, Data Dictionary, History, Ownership) renders **the same hardcoded `dm_credit` / Credit Portfolio content regardless of which report you opened**. Opening the FX Exposure report and clicking "DQ Rules" still shows `dm_credit.fact_loan_balance` rules. The real implementation must fix this — every tab needs to be genuinely scoped to the opened report's mart/domain.
2. **The Affected Rows table has dead code.** `renderAffectedRows()` targets `document.getElementById('aff-rows-1')`, but no element with that ID exists in the tab's markup — the `<table>` was never finished (the HTML comment `<!-- TABLE 1: dm_credit.fact_loan_balance -->` is followed immediately by the closing `</div>`). The KPI strip and AI Assignment panel render; the actual row-level table never has anywhere to mount. Treat "render an actual affected-rows table" as new work, not a port.
3. **"Export CSV" is `alert(...)`.** `showExportModal()` just pops a browser alert with a fake filename. No real export exists to port.

## 2. Tab-by-tab specification

### 2.1 Header (applies to all tabs)

| Element | Source (prototype) | Real data source |
|---|---|---|
| Breadcrumb (`Catalog / {report title}`) | `r.title` | `Report.name` |
| Report name (italic serif, 22px) | `r.title` | `Report.name` |
| Meta row: `📁 domain · 👤 owner · 🔄 refresh · 🕐 last run` | `r.domain/owner/refresh/run` | `Domain.name`, `Report.owner_team`, `Report.refresh_schedule`, `Report.last_run_at` |
| Status badge (`✓ Ready` / `⚠ At Risk` / `✕ Failed`) | `r.status` | `Report.current_status` |
| **Add to Favourites** toggle | `toggleFavourite(id)` / `favourites` object (localStorage) | `ReportFavourite` — **exists in the schema, has no endpoints yet.** Need `POST/DELETE /catalog/reports/{id}/favourite` per the original `API.md` spec (never built in Phase 2/3). |

### 2.2 Tab 1 — Overview

| Element | Prototype field | Real data source | Gap |
|---|---|---|---|
| Readiness ring + verdict + reason | `ringClass/ringIco`, `verdict`, `reason` | Derivable: ring/verdict from `Report.current_status` + latest `Incident` for the report's mart; reason from `Incident.ai_description` | None — computable from existing tables |
| DQ Score metric | `dq`, `dqSub` | `LayerRun.dq_rules_passed/dq_rules_total` for the report's primary mart's DM layer, today | None |
| Freshness metric | hardcoded `✓ 06:14 AM` | `Report.last_run_at` vs `refresh_schedule` target | None |
| Pipeline metric | `pipe`, `pipeSub` | `PipelineRun.status` / `sla_status` for today | None |
| **AI Narrative** block + confidence badge | `narrative` (HTML string with `<code>` tags), hardcoded `87%` | `Incident.ai_description` | Confidence score doesn't exist anywhere in the schema — **new field** or drop the confidence badge (recommend dropping; Claude doesn't return a calibrated confidence today, don't fabricate one) |
| Approve / Edit / Reject buttons on narrative | no-op in prototype | Needs a **new** incident-review workflow: an action here should set a state on `Incident` (e.g., `steward_reviewed_at`, `review_status`) | **New**: no review/approval state exists on `Incident` today |
| **Suggested Resolution** block + assignee dropdown + confidence | `resolution` (HTML string), hardcoded `74%` | Same as narrative — no "resolution suggestion" or "assignee" concept exists | **New**: needs an assignee field and a "suggested team" concept, most naturally as a governance/task item (see §5) |
| **Impact Map** (other reports affected by the same root cause) | hardcoded 3 items, `onclick="openReport(...)"` | `IncidentAffectedReport` join table **already exists and is unused** — this is exactly what it's for | None — just needs a query + endpoint |

### 2.3 Tab 2 — Data Dictionary

Already the best-covered tab by the existing schema. `GlossaryEntry` (`table_name`, `column_name`, `biz_name`, `definition`, `calculation`, `regulatory_refs`, `status`, `is_ai_draft`, `edited_by_id`, `edited_at`, `published_by_id`) maps almost 1:1 to every field the prototype renders per column: business name, tech name pill, data type, definition, calculation code block (expand/collapse), DQ alert (joined from `DQRule`/`DQResult` by `table_name`+`column_name`), footer "Last edited: {date} · {user}", Edit/Publish/Add-to-Glossary actions, and the All/Published/Draft/Undefined filter chips (`data-glossary` attribute).

**Real gap:** nothing tells the backend *which columns a report actually uses*. `Report` only has `primary_mart_id` — there's no `report_id → (table_name, column_name, data_type)` mapping. Options, in order of preference:
1. **Pull from OpenMetadata** via the connection type just built in `SAAS_TRANSFORMATION_PLAN.md`'s connection-management work — OpenMetadata already models table/column schemas and can answer "what does this report/dashboard read from." This is the intended long-term source per `ARCHITECTURE.md`.
2. New table `report_fields (report_id, table_name, column_name, data_type, ordinal)` populated by an OpenMetadata sync job, as a materialized/cached view of (1).
3. Fallback: use `DQRule.table_name`/`column_name` for the mart as a proxy for "fields that matter" (incomplete — only covers columns with a DQ rule, not every field a report surfaces).

Field-level DQ alert text ("dq_001 · null collateral_code — 3,240 rows … root cause of today's SLA breach · etl_job_4421") needs `DQResult.failed_rows` + `DQRule.name` + the owning `PipelineRun.job_id` joined together — all present, just needs the join.

### 2.4 Tab 3 — Lineage & RCA

The lineage canvas is a fixed 5-node flow: `source → staging → ods → dm → report`, each node showing an icon, physical name, row count/status, and an SLA-met/breached/failed dot. Clicking a node renders an "Actual vs SLA Target" comparison grid, plus a "Breach Details" column when applicable (see the `NODES` object: `actual`, `sla`, and `breach` are each arrays of `[label, value]` pairs).

**What's covered by existing schema:** `LayerRun` + `SLAConfig` already carry actual-vs-target data for 4 of the 5 nodes (source/staging/ods/dm) — delivery time, rows loaded, DQ pass count, and the computed `sla_status`/`sla_delay_minutes`. The 5th node (the report itself) is derivable from `Report.refresh_schedule` + `last_run_at` + the incident chain.

**Real gap:** `LayerRun.layer` is just the enum (`source`/`staging`/`ods`/`dm`) — there's no physical table name (`cbs.raw_loans`, `stg.loans`, etc.) to label the lineage nodes with, and no actual graph edges. This needs either:
- A new config table `mart_layer_tables (mart_id, layer, schema_name, table_name)` (static, admin-configured) to at least label the fixed 4-layer flow with real names — cheapest option, ships the visual immediately.
- Or the real table/column-level lineage graph from `SAAS_TRANSFORMATION_PLAN.md` Phase 5 (`lineage_nodes`/`lineage_edges`, built via `sqlglot` over ETL log SQL or pulled from OpenMetadata's lineage API) — the correct long-term answer, bigger lift.

**Recommendation:** ship the 4-layer fixed-flow version against `mart_layer_tables` first (small, unblocks the tab); treat true multi-hop lineage graphs as the Phase 5 work it already was.

### 2.5 Tab 4 — DQ Rules

Flat list of every rule across all layers for the mart: layer badge, rule code + name, pass/fail badge, result detail ("148,000 rows" / "3,240 nulls"). This is a direct join of `DQRule` (definition) with the latest `DQResult` (outcome) for the mart's most recent `PipelineRun` — **fully covered by the existing schema**, just needs the endpoint: `GET /reports/{id}/dq-rules` (or `/marts/{mart_id}/dq-rules`).

### 2.6 Tab 5 — Affected Rows

The tab the prototype itself never finished. Structure to build:
- **KPI strip:** total affected rows, % of dataset — aggregable from `DQResult.failed_rows`/`total_rows` for the mart's latest run. Covered.
- **AI Assignment Suggestions panel:** groups failures by root cause with a suggested owning team and an assign action. This is governance-workflow territory — see §5, same dependency as the Overview tab's resolution suggestions.
- **Row-level table** (the part with no DOM target in the prototype): loan ID, the failing column's value, other row context columns, which rules failed, per-row assignment. **This is the architecturally sensitive part** — see §4 below before building it.
- **Export CSV:** needs a real implementation (streamed CSV response), replacing the prototype's `alert()`.

### 2.7 Tab 6 — History

90-day incident timeline: date, title (color-coded by severity), detail, and resolution status/time — a straight query against `Incident` filtered to the report's mart, ordered by `detected_at` descending. **Fully covered by the existing schema** for the incident list itself.

**Real gap:** the "Pattern detected" callout ("this failure type has occurred 3× in 16 months") reuses `Incident.occurrence_count`/`occurrence_window_days`, which the SLA monitor already computes (Phase 2) — no new field needed. But **`Incident.resolved_at` is never set anywhere in the current codebase** — there's no resolution workflow yet, so "✓ Resolved in 2h" style entries have no real data to render from. Needs an incident-resolution action (who resolved it, when, and optionally a resolution note) before History can show anything but "still active."

### 2.8 Tab 7 — Ownership

Owner/steward/domain/department/classification/retention grid, plus a regulatory-reference badge list (Basel IV, CRR3, BCBS 239, GDPR Art.5, ...).

**Real gap:** none of this exists at the `Report` level today. `Domain.owner_id` covers domain-level ownership only; `SLAConfig.owner_team` covers layer-level ownership. Report-level ownership/classification/retention needs new columns on `Report` (or a `report_ownership` side table if it grows): `data_owner_id`, `data_classification`, `retention_period`, `regulatory_refs`.

### 2.9 Side panel (296px, persists across all tabs)

| Widget | Prototype data | Real data source | Gap |
|---|---|---|---|
| Usage today / this month + 14-day run-frequency bars | `USAGE_DATA[id]` — a per-report array of daily *report-open* counts, incremented client-side every time `openReport()` fires | **Nothing today.** This tracks user engagement (page views of the report), not pipeline runs — completely different signal from `PipelineRun` history. | **New**: needs a `report_view_events` table (or a daily rollup `report_usage_daily(report_id, date, view_count)`) written to on every "open report" API call |
| Report info (refresh, last run, source mart, tables used) | static per report | `Report.refresh_schedule/last_run_at/primary_mart_id` + count from `report_fields` (§2.3) | Depends on §2.3's table-mapping decision |
| DQ trend — 7 days | 7 hardcoded bar heights | Derivable from 7 days of historical `LayerRun.dq_rules_passed/total` for the mart's DM layer — **we already retain this history** (`PipelineRun` is unique per mart+date, never overwritten) | None, just an aggregation query |
| Pattern alert | same occurrence data as History tab | `Incident.occurrence_count`/`occurrence_window_days` | None |
| Time to resolution (avg/last/ETA) | hardcoded `4.2h` / `6h` / `~04:00` | Needs `Incident.resolved_at` populated (see §2.7) to compute real averages; ETA is `Incident.est_recovery_time`, which already exists as a field but nothing ever sets it | **Blocked on** the same incident-resolution workflow gap as History |

## 3. Cross-cutting gap: tabs must become per-report, not globally hardcoded

Every backend endpoint built for this feature must take a `report_id` (or the mart/domain it resolves to) and scope its query accordingly — the prototype's "just show the Credit Portfolio data regardless of context" behavior (finding #1 in §1) is a bug to fix, not a behavior to replicate.

## 4. Security/compliance: Affected Rows needs a real design decision, not just an endpoint

`ARCHITECTURE.md` already commits to a principle: *"All financial data stays within the bank's infrastructure... Claude API receives only metadata... no actual row data."* The Affected Rows tab is the one place the UI needs to show literal customer/loan-level data (loan IDs, balances, collateral codes) that currently isn't stored in Meridian's own database anywhere — and per that principle, it shouldn't be persisted there either.

**Recommended design:** live query-time fetch, not storage.
- Each `DQRule` gains a `diagnostic_sql` field (or a small templated query per `rule_type`) that, given a rule, produces "show me the rows that failed this check."
- The Affected Rows endpoint uses the org's registered **Greenplum connection** (built in the connection-management work) to run that diagnostic query directly against the tenant's own warehouse at request time, returns a paginated result, and **never writes the row contents to Meridian's Postgres**.
- Access to this endpoint should be more tightly role-gated than the rest of Report Detail (this is the one screen that can show PII/financial-row detail) and every access should be audit-logged (who viewed which rows, when) — this is exactly the kind of thing `SAAS_TRANSFORMATION_PLAN.md`'s Phase 8 (security/audit) anticipates, but it needs to land *with* this feature, not after it, because the data sensitivity exists the moment this tab is built.
- Export CSV should stream from the same live query rather than exporting anything Meridian stored.

This also means Affected Rows has a **hard dependency on the connection-management feature already shipped** — there's no Affected Rows tab for an org that hasn't registered (and successfully tested) a Greenplum connection. The empty/error state for that case needs to be designed too ("Connect your warehouse in Settings to see affected rows").

## 5. Cross-cutting gap: governance/task workflow

Three places in this one screen assume a task/governance-item system that doesn't exist yet:
- Overview tab's Approve/Edit/Reject on the AI narrative, and Approve & Assign on the suggested resolution
- Affected Rows tab's AI Assignment Suggestions (assign a failure cluster to a team) and per-row assignment dropdown
- The original prototype's separate Task Board nav destination, already deferred as a placeholder in the current frontend

Recommendation: don't build a parallel, Report-Detail-specific assignment mechanism. Treat "Approve & Assign" anywhere in Report Detail as *creating a task-board item scoped to this incident/report*, and build (or at least schema-design) the task/governance backend once, shared by both surfaces. Concretely this likely needs a new `tasks` table (`org_id`, `type`, `report_id`/`incident_id`, `assignee_team`, `status`, `priority`, `due_date`, `created_from` — narrative-approval vs. row-assignment vs. manual) rather than bolting ad hoc assignment fields onto `Incident`.

## 6. Proposed new/changed schema (summary)

| Table | Change | Used by |
|---|---|---|
| `report_favourites` | *(no schema change — just missing endpoints)* | Header star toggle |
| `incidents` | add `resolved_by_id`, `resolution_note`; ensure `resolved_at`/`est_recovery_time` are actually written somewhere | History tab, side panel time-to-resolution, Overview approve/reject |
| `reports` | add `data_owner_id`, `data_classification`, `retention_period`, `regulatory_refs` | Ownership tab |
| `dq_rules` | add `diagnostic_sql` (or templated-by-`rule_type` equivalent) | Affected Rows live query |
| **`report_fields`** *(new)* | `report_id, table_name, column_name, data_type, ordinal` — or replaced entirely by a live OpenMetadata call | Data Dictionary, side panel "tables used" |
| **`mart_layer_tables`** *(new)* | `mart_id, layer, schema_name, table_name` | Lineage node labels |
| **`report_usage_daily`** *(new)* | `report_id, date, view_count` | Side panel usage/run-frequency |
| **`tasks`** *(new, shared with Task Board)* | see §5 | Overview approve/assign, Affected Rows assignment |

## 7. Proposed API surface

```
GET    /catalog/reports/{id}                     -- header + overview (extends existing GET /catalog/reports)
POST   /catalog/reports/{id}/favourite            -- (missing since Phase 2/3, per original API.md)
DELETE /catalog/reports/{id}/favourite
POST   /catalog/reports/{id}/open                 -- increments usage + report_usage_daily (also drives favourites sort)

GET    /reports/{id}/dictionary                   -- Data Dictionary tab
GET    /reports/{id}/lineage                      -- Lineage & RCA tab
GET    /reports/{id}/dq-rules                      -- DQ Rules tab
GET    /reports/{id}/affected-rows?rule_id=...     -- live warehouse query, paginated
GET    /reports/{id}/affected-rows/export          -- streamed CSV, same live query
GET    /reports/{id}/history                       -- History tab
GET    /reports/{id}/ownership                     -- Ownership tab
GET    /reports/{id}/usage                         -- side panel usage/trend/DQ-trend/time-to-resolution

POST   /incidents/{id}/review                      -- approve/edit/reject the AI narrative (Overview)
POST   /incidents/{id}/resolve                     -- sets resolved_at/resolved_by/resolution_note

POST   /tasks                                      -- create from "Approve & Assign" / row assignment (see §5)
```

## 8. Frontend requirements

- New route `/reports/:id`, reached by making `ReportCard` in `CatalogPage` a real link (currently a static `<div>`).
- A `ReportDetailPage` with the header (breadcrumb, name, meta, status badge, favourite toggle) and a 7-tab component matching `dtab()`'s switching behavior, each tab lazy-loaded (`react-query`, fetch-on-tab-activate rather than all 7 endpoints on page load).
- Side panel as a persistent sibling to the tab content (matches the prototype's `.detail-main` / `.detail-side` split), not per-tab.
- Every tab needs its own loading/empty/error state — several of these (Affected Rows especially) have a real "not available" case (no warehouse connection registered) that isn't just a network error.
- Data Dictionary keeps the existing prototype's UX contract exactly (expand/collapse rows, calculation code block expand, filter chips, glossary add/edit modal) since `GlossaryEntry` already backs it almost entirely — this tab is the cheapest to get pixel-faithful.
- Lineage node-click detail panel, Affected Rows row-selection + bulk-assign, and the assignment dropdowns all need real mutation calls once §5's task backend exists — don't wire them to no-ops the way the prototype does.

## 9. Suggested build order

Roughly cheapest-and-most-covered-by-existing-schema first:

1. **Favourites endpoints + report-open tracking** — small, unblocks header star and starts collecting real usage data immediately (the earlier this starts writing `report_usage_daily`, the sooner the side panel trend chart has real history instead of a cold start).
2. **DQ Rules tab + History tab** — pure reads over existing tables, no new schema.
3. **Data Dictionary tab** — existing schema, but blocked on deciding how `report_fields` (or the OpenMetadata alternative) gets populated.
4. **Overview tab's Impact Map + AI narrative display** — existing schema (`IncidentAffectedReport`); the Approve/Reject *actions* wait on §5.
5. **Ownership tab** — small schema addition, no dependencies.
6. **Lineage & RCA (fixed 4-layer version)** — needs `mart_layer_tables`, otherwise existing schema.
7. **Incident resolution workflow** (`resolved_at`/`resolved_by`/`resolution_note`) — unblocks the History tab's resolution entries and the side panel's time-to-resolution stats.
8. **Task/governance backend** (§5) — unblocks the remaining Overview/Affected-Rows actions and the deferred Task Board nav item at the same time.
9. **Affected Rows live-query tab** — largest single piece of new design (§4); do this last since it depends on the connection-management feature, needs its own security review, and every other tab ships value without it.

## 10. Open questions for you

1. **Data Dictionary field mapping**: pull from OpenMetadata live, or maintain a synced `report_fields` table? (Affects build order item 3.)
2. **Lineage**: ship the fixed 4-layer version now, or wait and build real multi-hop lineage graphs (original Phase 5 scope) directly?
3. **Affected Rows**: confirm the live-query-only, never-persisted design in §4 before any of it is built — this is the one part of Report Detail that touches real customer data, and it's worth being deliberate rather than defaulting to "just add a table for it."
4. **Task/governance backend**: build it now as a prerequisite for Report Detail's action buttons, or ship Report Detail with those specific buttons temporarily disabled/hidden and build the shared task system separately when Task Board itself is prioritized?
