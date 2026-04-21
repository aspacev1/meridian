# Meridian — Data Model

## Entity Relationship Overview

```
users ──────────────────────────────────────────────────────────┐
  │                                                              │
  ├── glossary_entries (edited_by_id, published_by_id)          │
  └── report_favourites (user_id)                               │
                                                                 │
domains ──┐                                                      │
          ├── data_marts ──┐                                     │
          └── reports      │                                     │
                           ├── sla_configs (mart_id × layer)    │
                           ├── pipeline_runs ──┐                 │
                           │                  ├── layer_runs ──┐ │
                           │                  │               └── dq_results
                           │                  └── incidents ──────────────┐
                           └── dq_rules                                   │
                                                                          │
reports ──────────────────────────────── incident_affected_reports ───────┘
  └── report_favourites

scan_sessions (standalone — aggregate snapshot)
glossary_entries (table_name × column_name)
```

---

## Tables

### `users`
Stewards and data owners who work in Meridian.

| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `email` | VARCHAR(255) UNIQUE | Login / identity |
| `full_name` | VARCHAR(255) | Shown in context bar: "Steward: Alim Salahov" |
| `role` | VARCHAR(50) | `steward` \| `data_owner` \| `engineer` \| `admin` |
| `is_active` | BOOLEAN | |
| `avatar_initials` | VARCHAR(4) | "AL" shown in nav rail avatar |

---

### `domains`
Business domains grouping marts and reports.

| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `name` | VARCHAR(100) UNIQUE | "Credit Risk", "Market Risk", etc. |
| `icon` | VARCHAR(10) | Emoji: "💳" |
| `owner_id` | UUID FK → users | |

**Seed data:** Credit Risk, Market Risk, Treasury, Compliance, Retail Banking

---

### `data_marts`
A data mart is the top-level pipeline unit. Maps to a Greenplum schema.

| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `name` | VARCHAR(100) UNIQUE | `dm_credit`, `dm_market` — must match Greenplum schema |
| `domain_id` | UUID FK → domains | |
| `is_active` | BOOLEAN | |

**UI mapping:** Incident location "🗄 dm_market", SLA strip per mart

---

### `sla_configs`
Target delivery time for each mart × layer combination. Configured once.

| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `mart_id` | UUID FK → data_marts | |
| `layer` | ENUM | `source` \| `staging` \| `ods` \| `dm` |
| `target_time` | TIME | When layer should be ready |
| `dq_threshold_pct` | INTEGER | Min DQ pass rate (default 95) |
| `owner_team` | VARCHAR(100) | Team responsible for this layer |
| `is_active` | BOOLEAN | |

**Unique constraint:** `(mart_id, layer)`

**Example data:**
```
dm_market | source  | 02:00 | 95
dm_market | staging | 03:00 | 95
dm_market | ods     | 04:00 | 95
dm_market | dm      | 05:30 | 95
dm_credit | dm      | 05:30 | 95
```

---

### `pipeline_runs`
One daily execution per mart. Ingested from Greenplum CSV logs.

| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `mart_id` | UUID FK → data_marts | |
| `run_date` | DATE | Business date of the run |
| `job_name` | VARCHAR(200) | ETL job name from logs |
| `job_id` | VARCHAR(100) | "etl_job_4405" — shown in incident description |
| `status` | ENUM | `running` \| `success` \| `failed` \| `skipped` |
| `sla_status` | ENUM | `healthy` \| `warning` \| `breach` \| `no_scan` |
| `started_at` | TIMESTAMPTZ | |
| `finished_at` | TIMESTAMPTZ | |
| `error_message` | TEXT | |

**Unique constraint:** `(mart_id, run_date)` — idempotent ingestion

**UI mapping:** "etl_job_4405 timed out at 07:54 AM"

---

### `layer_runs`
Per-layer execution stats within a pipeline run. One row per (pipeline_run × layer).

| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `pipeline_run_id` | UUID FK → pipeline_runs | |
| `layer` | ENUM | `source` \| `staging` \| `ods` \| `dm` |
| `status` | ENUM | `running` \| `success` \| `failed` \| `skipped` |
| `started_at` | TIMESTAMPTZ | |
| `finished_at` | TIMESTAMPTZ | |
| `delivery_time` | TIME | Time of delivery (from `finished_at`) |
| `rows_loaded` | INTEGER | Row count after load |
| `dq_rules_total` | INTEGER | Total DQ rules checked |
| `dq_rules_passed` | INTEGER | Rules that passed |
| `sla_status` | ENUM | Computed by SLA Monitor |
| `sla_delay_minutes` | INTEGER | Minutes late (negative = early) |
| `error_message` | TEXT | |

**Unique constraint:** `(pipeline_run_id, layer)`

**UI mapping (catalog report card SLA section):**
```
Source: 148k rows / SLA 01:30/02:00 / DQ 12/12
Staging: 148k / 02:45/03:00 / DQ 8/8
ODS: 148k / 03:50/04:00 / DQ 7/8
DM: 145k / 06:14/05:30 / DQ 5/8 ✕3
```

**UI mapping (SLA strip):**
```sql
-- "1 Breach"
SELECT COUNT(*) FROM layer_runs lr
JOIN pipeline_runs pr ON lr.pipeline_run_id = pr.id
WHERE pr.run_date = TODAY AND lr.layer = 'dm' AND lr.sla_status = 'breach'
```

---

### `incidents`
Auto-generated when SLA is breached or DQ threshold crossed.

| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `type` | ENUM | `pipeline_sla_breach` \| `dq_sla_breach` \| `data_freshness` |
| `severity` | ENUM | `critical` \| `warning` |
| `status` | ENUM | `active` \| `resolved` \| `suppressed` |
| `mart_id` | UUID FK → data_marts | |
| `pipeline_run_id` | UUID FK → pipeline_runs | |
| `ai_name` | VARCHAR(300) | "Pipeline SLA Breach — dm_market" |
| `ai_description` | TEXT | Full incident description |
| `detected_at` | TIMESTAMPTZ | |
| `resolved_at` | TIMESTAMPTZ | |
| `est_recovery_time` | VARCHAR(20) | "~04:00" |
| `sla_delay_minutes` | INTEGER | Powers "+1h 54m overdue" |
| `dq_actual_pct` | INTEGER | 71 |
| `dq_target_pct` | INTEGER | 95 |
| `dq_delta_pp` | INTEGER | -24 (percentage points) |
| `layer_statuses` | JSON | `{"source": "ok", "staging": "failed", "ods": "failed", "dm": "failed"}` |
| `occurrence_count` | INTEGER | 3 — powers "3rd time in 16 months" |
| `occurrence_window_days` | INTEGER | 487 (≈ 16 months) |
| `reports_affected_count` | INTEGER | 2 |
| `availability_label` | VARCHAR(50) | "fully unavailable" \| "partial data" |

---

### `dq_rules`
Data quality rule definitions, applied at a specific layer for a specific table/column.

| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `rule_code` | VARCHAR(20) UNIQUE | "dq_001" |
| `name` | VARCHAR(200) | "null collateral_code" |
| `rule_type` | ENUM | `not_null` \| `unique` \| `range_check` \| `referential` \| `custom_sql` |
| `mart_id` | UUID FK → data_marts | |
| `layer` | VARCHAR(20) | Layer where rule is applied |
| `table_name` | VARCHAR(200) | "dm_credit.fact_loan_balance" |
| `column_name` | VARCHAR(200) | "collateral_code" |
| `sql_expression` | TEXT | For `custom_sql` type |
| `severity` | VARCHAR(20) | "error" \| "warning" |

---

### `dq_results`
Execution result of a DQ rule for a specific layer run.

| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `layer_run_id` | UUID FK → layer_runs | |
| `rule_id` | UUID FK → dq_rules | |
| `passed` | BOOLEAN | |
| `failed_rows` | INTEGER | 3,240 |
| `total_rows` | INTEGER | |
| `checked_at` | TIMESTAMPTZ | |
| `error_detail` | TEXT | |

**Denormalization:** `LayerRun.dq_rules_passed` / `dq_rules_total` are computed from this table and stored for fast reads.

---

### `reports`
Business reports powered by one or more data marts.

| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `name` | VARCHAR(300) | "Monthly Credit Portfolio Report" |
| `icon` | VARCHAR(10) | "📊" |
| `domain_id` | UUID FK → domains | |
| `primary_mart_id` | UUID FK → data_marts | |
| `owner_team` | VARCHAR(200) | "Risk Analytics" |
| `refresh_schedule` | VARCHAR(100) | "Daily 06:00" |
| `last_run_at` | TIMESTAMPTZ | "today 06:14" |
| `current_status` | VARCHAR(10) | "go" \| "warn" \| "stop" |

---

### `report_favourites`
Per-user favourites with usage tracking for sorting.

| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `report_id` | UUID FK → reports | |
| `open_count` | INTEGER | Incremented on every `openReport()` call |
| `added_at` | TIMESTAMPTZ | |

**Unique constraint:** `(user_id, report_id)`

**Catalog sorting:** `ORDER BY open_count DESC, added_at DESC`

---

### `scan_sessions`
One record per Meridian scan. Powers the dashboard context bar.

| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `started_at` | TIMESTAMPTZ | |
| `finished_at` | TIMESTAMPTZ | "Last scan: 06:14" |
| `next_scheduled_at` | TIMESTAMPTZ | "Next scan in 3h 46m" |
| `status` | VARCHAR(20) | "running" \| "completed" \| "failed" |
| `reports_scanned` | INTEGER | "24 reports" |
| `domains_scanned` | INTEGER | "6 domains" |
| `triggered_by` | VARCHAR(50) | "schedule" \| "manual" \| "webhook" |

---

### `glossary_entries`
Business glossary definitions for table columns. Stored in Meridian DB (not OpenMetadata) for full write control.

| Column | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `table_name` | VARCHAR(300) | "dm_credit.fact_loan_balance" |
| `column_name` | VARCHAR(200) | "balance_amount" |
| `biz_name` | VARCHAR(300) | "Outstanding Principal Balance" |
| `definition` | TEXT | Business definition |
| `calculation` | TEXT | SQL formula or business rule |
| `regulatory_refs` | TEXT | "Basel IV Art.123, BCBS 239" |
| `status` | ENUM | `draft` \| `published` |
| `is_ai_draft` | BOOLEAN | True if generated by Claude |
| `edited_by_id` | UUID FK → users | |
| `edited_at` | TIMESTAMPTZ | "Last edited: Mar 20 · Kamran Aliyev" |
| `published_by_id` | UUID FK → users | |
| `mart_id` | UUID FK → data_marts | |

**Unique constraint:** `(table_name, column_name)`

---

## Indexes

```sql
-- Hot paths for dashboard queries
CREATE INDEX ON layer_runs(pipeline_run_id);
CREATE INDEX ON pipeline_runs(mart_id);
CREATE INDEX ON pipeline_runs(run_date);          -- daily dashboard
CREATE INDEX ON incidents(mart_id);
CREATE INDEX ON incidents(status);                -- active incidents filter
CREATE INDEX ON dq_results(layer_run_id);
CREATE INDEX ON glossary_entries(table_name);
```
