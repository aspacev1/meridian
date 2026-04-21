# Meridian — REST API

Base URL: `http://localhost:8000/api/v1`

Interactive docs: `http://localhost:8000/docs` (Swagger UI)

---

## Dashboard

### `GET /dashboard/context`

Powers the context bar at the top of the dashboard.

**Response:**
```json
{
  "scan_time": "06:14",
  "scan_date": "Mon 30 March 2026",
  "reports_count": 24,
  "domains_count": 6,
  "next_scan_in": "3h 46m"
}
```

---

### `GET /dashboard/sla-status`

Powers the SLA status strip: **1 Breach · 2 Warnings · 3 Healthy**

**Query params:** `run_date` (optional, ISO date, defaults to today)

**Response:**
```json
{
  "breach": 1,
  "warning": 2,
  "healthy": 3,
  "total": 6,
  "layer": "dm",
  "as_of": "06:14"
}
```

---

### `GET /dashboard/incidents`

Active incident cards for the dashboard feed.

**Query params:** `run_date` (optional)

**Response:**
```json
[
  {
    "id": "uuid",
    "type": "pipeline_sla_breach",
    "severity": "critical",
    "status": "active",
    "ai_name": "Pipeline SLA Breach — dm_market",
    "ai_description": "Pipeline SLA breached · +1h 54m overdue. etl_job_4405 timed out...",
    "mart_name": "dm_market",
    "layer_statuses": {
      "source": "ok",
      "staging": "failed",
      "ods": "failed",
      "dm": "failed"
    },
    "detected_at": "2026-03-30T06:14:00Z",
    "est_recovery_time": "~04:00",
    "sla_delay_minutes": 114,
    "dq_actual_pct": null,
    "dq_target_pct": null,
    "occurrence_count": 3,
    "occurrence_window_days": 487,
    "reports_affected_count": 2,
    "availability_label": "fully unavailable",
    "delay_label": "+1h 54m overdue",
    "occurrence_label": "3rd time in 16 months",
    "dq_delta_label": null
  }
]
```

---

## Catalog

### `GET /catalog/reports`

Full report list for the catalog.

**Query params:**
- `domain_id` — filter by domain
- `status` — `go` | `warn` | `stop`
- `user_id` — for favourites sorting

**Response:** Array of `ReportCardOut`:
```json
[
  {
    "id": "uuid",
    "name": "Monthly Credit Portfolio Report",
    "icon": "📊",
    "domain_name": "Credit Risk",
    "owner_team": "Risk Analytics",
    "refresh_schedule": "Daily 06:00",
    "last_run_at": "2026-03-30T06:14:00Z",
    "current_status": "warn",
    "sla_layers": [
      {
        "layer": "source",
        "status": "healthy",
        "rows_loaded": 148420,
        "actual_time": "01:30",
        "target_time": "02:00",
        "dq_passed": 12,
        "dq_total": 12,
        "rows_label": "148k",
        "dq_label": "DQ 12/12"
      },
      {
        "layer": "dm",
        "status": "warning",
        "rows_loaded": 145180,
        "actual_time": "06:14",
        "target_time": "05:30",
        "dq_passed": 5,
        "dq_total": 8,
        "rows_label": "145k",
        "dq_label": "DQ 5/8 ✕3"
      }
    ]
  }
]
```

---

### `GET /catalog/reports/{id}`

Single report detail.

---

### `POST /catalog/reports/{id}/favourite`

Add report to user's favourites.

**Body:** `{"user_id": "uuid"}`

---

### `DELETE /catalog/reports/{id}/favourite`

Remove from favourites.

---

### `POST /catalog/reports/{id}/open`

Increment open count for usage tracking (for favourite sorting).

---

## Data Dictionary

### `GET /dd/{report_id}/tables`

Tables and fields used by a report, enriched with glossary entries.

**Response:**
```json
[
  {
    "table_name": "dm_credit.fact_loan_balance",
    "table_meta": "Core loan balance fact table · 144,760 rows",
    "fields_count": 4,
    "fields": [
      {
        "column_name": "balance_amount",
        "biz_name": "Outstanding Principal Balance",
        "data_type": "NUMERIC(18,2)",
        "glossary_status": "published",
        "definition": "The outstanding principal debt...",
        "calculation": "balance_amount = disbursed_amount - cumulative_principal_repaid\n-- Applied after ODS→DM transform...",
        "edited_by": "Kamran Aliyev",
        "edited_at": "2026-03-20T00:00:00Z",
        "dq_alerts": [
          {
            "rule_code": "dq_019",
            "name": "negative balance_amount",
            "failed_rows": 12,
            "severity": "warning"
          }
        ]
      }
    ]
  }
]
```

---

### `PUT /dd/{table}/{field}/glossary`

Save or update a glossary entry.

**Body:**
```json
{
  "biz_name": "Outstanding Principal Balance",
  "definition": "The outstanding principal debt...",
  "calculation": "balance_amount = disbursed_amount - cumulative_principal_repaid",
  "regulatory_refs": "Basel IV CRR3 Art. 111",
  "status": "draft"
}
```

---

### `POST /dd/{table}/{field}/publish`

Publish a draft glossary entry.

---

## Ingestion

### `POST /ingestion/csv`

Trigger CSV log ingestion manually.

**Body:** `multipart/form-data` with `file` field (CSV)

**Response:**
```json
{
  "rows_read": 48,
  "runs_created": 6,
  "layer_runs_created": 22,
  "errors": []
}
```

---

### `POST /ingestion/webhook`

Webhook endpoint for Airflow/dbt to trigger ingestion after a pipeline completes.

**Body:**
```json
{
  "mart_name": "dm_credit",
  "layer": "dm",
  "job_id": "etl_job_4421",
  "status": "success",
  "rows_loaded": 145180,
  "finished_at": "2026-03-30T06:14:00Z"
}
```

---

## AI

### `POST /ai/glossary-draft`

Generate a glossary draft for a column using Claude API.

**Body:**
```json
{
  "column_name": "collateral_code",
  "table_name": "dm_credit.fact_loan_balance",
  "sample_values": ["RE", "FI", "GU", null, null],
  "context_hint": "Used in Basel IV RWA calculation"
}
```

**Response:**
```json
{
  "biz_name": "Collateral Asset Type",
  "definition": "Standardised classification code identifying the type of asset pledged as collateral...",
  "calculation": "RWA_collateral = exposure × risk_weight(collateral_code) × (1 − haircut)"
}
```

---

## Health

### `GET /health`

```json
{"status": "ok", "service": "meridian-api"}
```

---

## Error Responses

All errors follow RFC 7807 Problem Details:

```json
{
  "status": 404,
  "title": "Not Found",
  "detail": "Report with id 'xyz' not found"
}
```

| Status | Meaning |
|---|---|
| 400 | Validation error |
| 404 | Resource not found |
| 422 | Unprocessable entity (Pydantic) |
| 500 | Internal server error |
