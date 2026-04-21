# Meridian — Roadmap

## Current State: Interactive Prototype (v43)

Fully clickable single-file prototype with mock data. Covers all major screens and interactions.

---

## Phase 1 — MVP with Real Data (Month 1–2)

**Goal:** Dashboard and Catalog working with real Greenplum pipeline data.

### Backend
- [ ] Deploy FastAPI + PostgreSQL + Redis via Docker
- [ ] Run Alembic migrations and seed reference data
- [ ] Implement Greenplum CSV log ingestion (`log_ingestion.py`)
- [ ] SLA Monitor worker — check pipelines every 5 minutes
- [ ] `GET /dashboard/context` — real scan session data
- [ ] `GET /dashboard/sla-status` — real layer_runs aggregation
- [ ] `GET /dashboard/incidents` — real incidents with AI names

### Frontend
- [ ] Connect dashboard to live API (replace mock `REPORTS` array)
- [ ] Replace hardcoded incident cards with API data
- [ ] Implement auth (JWT or SSO)

### Data
- [ ] Map actual Greenplum ETL log CSV columns to ingestion schema
- [ ] Configure SLA targets per mart × layer in `sla_configs`
- [ ] Register all active data marts and reports

---

## Phase 2 — Catalog + Data Dictionary (Month 2–3)

**Goal:** Catalog shows live report statuses. Data Dictionary is editable.

### Backend
- [ ] `GET /catalog/reports` with SLA layer data
- [ ] `GET /dd/{report_id}/tables` from OpenMetadata API + Meridian glossary
- [ ] `PUT /dd/{table}/{field}/glossary` — write glossary entries
- [ ] `POST /dd/{table}/{field}/publish` — publish workflow
- [ ] OpenMetadata sync service — pull table metadata on schedule

### Frontend
- [ ] Real report cards with live SLA data
- [ ] Glossary edit/publish workflow persisted to backend
- [ ] Data Dictionary filter (Published / Draft / No glossary) on real data

---

## Phase 3 — AI Features (Month 3–4)

**Goal:** AI incident naming, glossary drafting, and task board live.

### Backend
- [ ] AI incident naming on breach detection (already designed, needs testing on real data)
- [ ] `POST /ai/glossary-draft` endpoint
- [ ] Task board: generate governance items after each scan
- [ ] Validate AI output quality on real Greenplum schema

### Frontend
- [ ] Task Board connected to backend task queue
- [ ] Approve/Reject writes back to glossary or DQ config
- [ ] Chat: connect to Claude API with real report context

---

## Phase 4 — Executive View + Notifications (Month 4–5)

### Backend
- [ ] Historical data API for executive view date navigation
- [ ] `cost_per_hour_azn` field on `data_marts` for CFO view AZN calculations
- [ ] Email/Slack notifications on critical incidents
- [ ] Webhook receiver for Airflow/dbt pipeline events

### Frontend
- [ ] Executive view date navigation shows real historical data
- [ ] CFO view AZN costs populated from mart config
- [ ] Notification badge on dashboard nav item

---

## Phase 5 — Lineage from Greenplum Logs (Month 5–6)

**Goal:** Build SQL lineage graph from CSV ETL logs.

### Backend
- [ ] SQL parser integration (`sqllineage` / `sqlglot`)
- [ ] Lineage node/edge extraction from ETL log SQL text
- [ ] `lineage_nodes` and `lineage_edges` tables
- [ ] `GET /lineage/{table}` — upstream/downstream traversal
- [ ] Impact analysis: "if dm_market.fact_fx_position breaks, which reports are affected?"

### Frontend
- [ ] Lineage graph driven by real lineage data
- [ ] Impact analysis panel in report detail

---

## Future Considerations

### Neo4j for Lineage (when scale demands it)
Currently PostgreSQL recursive CTE handles lineage traversal. When table count exceeds ~200, consider migrating lineage graph to Neo4j for:
- Real-time impact analysis queries
- Multi-hop traversal performance
- Graph visualization APIs

### OpenMetadata deeper integration
- Write glossary entries back to OpenMetadata
- Pull column-level lineage from OpenMetadata
- Sync DQ rule results to OpenMetadata quality framework

### DQ Engine integration
Options for connecting a real DQ engine:
- **Great Expectations** — mature Python framework
- **Soda** — cloud-native, good Greenplum support
- **dbt tests** — if dbt is already in the stack
- **Custom SQL rules** — defined in `dq_rules` table, executed by Meridian worker

### Multi-language support
Interface currently in English. Bank operates in Azerbaijani and Russian. Planned: i18n with locale switching.

---

## Known Limitations of Prototype

| Area | Limitation | Fix in Phase |
|---|---|---|
| Dashboard | Mock data only | 1 |
| Executive View | Date navigation shows same mock data | 4 |
| Lineage graph | Static, hardcoded nodes | 5 |
| Chat | Keyword-matching, not real Claude API | 3 |
| Task Board | No persistence — resets on reload | 2 |
| Glossary | Modal saves visually, no backend | 2 |
| CFO cost/hr | Shows "—", not configurable | 4 |
