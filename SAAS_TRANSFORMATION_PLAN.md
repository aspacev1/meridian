# Meridian — SaaS Transformation Plan

## 0. Where things actually stand

A codebase audit turned up a gap between what the docs claim and what exists in the repo:

| Claimed (README/docs) | Actual |
|---|---|
| `backend/` FastAPI app, SQLAlchemy models, Alembic migrations, Celery workers | **Does not exist.** Zero backend code in the repo. |
| Docker Compose stack (`db`, `redis`, `api`, `worker`, `beat`) | **Does not exist.** No `Dockerfile`, no `docker-compose.yml`. |
| "Backend Quick Start" instructions | Reference files/commands that aren't in the repo. |
| Interactive prototype | **Real.** `index.html` — 5,096 lines of vanilla HTML/CSS/JS, MD3 design, fully clickable, backed entirely by in-memory JS arrays (`REPORTS`, `TASKS`, `USAGE_DATA`, `favourites`). No network calls, no persistence beyond page reload. |
| `ARCHITECTURE.md`, `DATA_MODEL.md`, `API.md`, `FRONTEND.md`, `ROADMAP.md` | **Real and good.** These are well-designed specs for a single-tenant internal tool (one bank, one Greenplum warehouse, one OpenMetadata instance). They are a design doc, not implemented code. |

So this isn't "harden an MVP" — it's a from-scratch build guided by decent specs, plus everything the specs don't cover because they were written for **one bank's internal tool**, not a multi-tenant product other banks could sign up for. The existing `ROADMAP.md` phases (1–5) are a reasonable sequence for the single-tenant backend; this plan wraps around and extends them for the actual ask: **a real SaaS application**.

## 1. Decisions this plan assumes (flag if you want them different)

- **Multi-tenancy model:** shared Postgres, `tenant_id` on every row, enforced with Postgres Row-Level Security — not schema-per-tenant. Cheaper to operate at low tenant counts, and it's a straightforward migration to schema-per-tenant later for a whale customer that demands physical isolation.
- **Frontend:** the 5,096-line single-file prototype gets ported to a componentized app (React + Vite/Next.js) rather than growing in place. The MD3 design system and JS logic in `index.html` are the reference implementation to port from, not thrown away — the visual design is good and shouldn't change, just the delivery mechanism.
- **Backend stack:** keep the documented choice (FastAPI, PostgreSQL, Redis, Celery, Alembic) — it's sound for this workload. Add an auth/identity layer and a billing layer, neither of which existed in the original design because it was scoped to one internal deployment.
- **Per-tenant data sources:** each customer bank has its own Greenplum warehouse and (optionally) OpenMetadata instance. Connection credentials must become tenant-scoped, encrypted config instead of hardcoded environment variables.
- **Cloud target:** containerized, deployable to any of AWS/GCP/Azure. Plan assumes ECS Fargate or Cloud Run to start (avoid Kubernetes until scale/ops headcount justify it).

If any of these are wrong for your situation (e.g., you actually only need this for one bank, not a multi-tenant product), say so — it changes Phases 1 and 6 significantly and removes real work.

---

## Phase 0 — Foundations (1–2 weeks)

Nothing below can be built correctly without these decisions locked in first.

- [ ] Confirm multi-tenancy model (shared-DB+RLS vs. schema-per-tenant vs. DB-per-tenant)
- [ ] Confirm identity/auth approach: build JWT auth in-house vs. buy (Clerk, WorkOS, Auth0) — for a bank-facing B2B product, **buying** (WorkOS/Auth0) buys you SAML/SSO and audit logs you'd otherwise build yourselves
- [ ] Pick billing provider (Stripe recommended) and pricing model (per-seat / per-mart-monitored / per-report / usage-based on AI calls)
- [ ] Stand up monorepo structure: `apps/api`, `apps/web`, `apps/worker`, `packages/shared` (or split repos if you prefer)
- [ ] Choose cloud provider + create dev/staging/prod projects
- [ ] Set up GitHub Actions CI skeleton (lint, typecheck, test) gating merges to `main`

---

## Phase 1 — Backend Core: Auth, Tenancy, Skeleton API (3–4 weeks)

This is the "actually build what `ARCHITECTURE.md` describes" phase, with tenancy bolted on from day one (retrofitting tenancy later is much more expensive than building it in).

- [ ] Scaffold FastAPI app per `ARCHITECTURE.md` project structure (`app/core`, `app/models`, `app/api/v1`, `app/services`, `app/workers`)
- [ ] `organizations` (tenant) table + `users` table with `org_id` FK; every other table in `DATA_MODEL.md` gets an `org_id` column and an RLS policy
- [ ] Auth: signup/login, JWT issuance, session refresh, SSO (SAML/OIDC) for enterprise customers, role-based access control (`steward` / `data_owner` / `engineer` / `admin` / `org_admin`)
- [ ] Org onboarding flow: create org → invite users → assign roles
- [ ] Dockerfile + docker-compose.yml for local dev (db, redis, api, worker, beat) — these literally don't exist yet
- [ ] Alembic migration 001 implementing the full `DATA_MODEL.md` schema, tenant-scoped
- [ ] Seed script parameterized per-org (replace the single-bank seed data assumption)
- [ ] `GET /health`, base error handling (RFC 7807 per `API.md`), request logging, structured logging (JSON)

---

## Phase 2 — Data Ingestion & Connector Framework (3–4 weeks)

The original design hardcodes one bank's Greenplum schema and one OpenMetadata instance. A SaaS product needs this to be configuration, not code.

- [ ] `data_source_connections` table: per-org encrypted credentials (Greenplum/Postgres DSN, OpenMetadata URL+token) — use envelope encryption (KMS) for secrets at rest
- [ ] Generalize `log_ingestion.py` into a connector interface: CSV upload (already speced), SFTP/S3 drop folder, direct DB query against customer's Greenplum, webhook (Airflow/dbt) — per `API.md`'s `/ingestion/webhook`
- [ ] SLA Monitor Celery worker (5-min schedule), tenant-aware task fan-out so one org's backlog doesn't starve another's
- [ ] Scan Session worker (hourly), OpenMetadata sync service
- [ ] `GET /dashboard/context`, `/dashboard/sla-status`, `/dashboard/incidents` — real, tenant-scoped, matching `API.md`
- [ ] Data mart / SLA config registration UI + API (currently only exists as the "Register Mart wizard" mock in `index.html`)

---

## Phase 3 — Frontend Rebuild (4–6 weeks, can overlap Phase 2)

- [ ] Set up React + TypeScript + Vite (or Next.js if SSR/SEO matters for a marketing site too) app
- [ ] Port MD3 design tokens from `index.html`'s `:root` CSS variables into a shared theme/design-system package
- [ ] Componentize by the existing structural boundaries: `NavRail`, `Dashboard`, `IncidentCard`, `CatalogTree`, `ReportCard`, `ReportDetail` (7 tabs), `DataDictionaryField`, `TaskBoard`, `ExecutiveView` (CDO/CRO/CFO), `Chat`
- [ ] Replace all mock arrays (`REPORTS`, `TASKS`, `USAGE_DATA`, `favourites`) with API-backed data fetching (React Query/SWR) against Phase 1–2 endpoints
- [ ] Auth screens: login, SSO redirect, org switcher (users may belong to multiple orgs), invite acceptance
- [ ] Preserve existing UX/interactions exactly (nav behavior, tab switching, expand/collapse, filters) — this is a re-platform, not a redesign
- [ ] E2E smoke tests (Playwright) covering the golden paths: login → dashboard → catalog → report detail → glossary edit

---

## Phase 4 — AI Features, for real (2–3 weeks)

- [ ] `ai_service.py`: real Claude API calls for incident naming/description and glossary drafts (currently: doesn't exist; `index.html` chat is keyword-matching, not an LLM)
- [ ] Per-org API key/BYOK support or centrally-metered usage with cost attribution per tenant (needed for billing in Phase 5)
- [ ] Rate limiting + retry/backoff around the Anthropic API; cache repeated incident-naming prompts where inputs are identical
- [ ] `POST /ai/glossary-draft` per `API.md`
- [ ] Task Board generation tied to real scan sessions, with persistence (currently resets on reload per `ROADMAP.md`'s known limitations)
- [ ] Chat: real Claude conversation grounded in the org's own report/incident context (RAG over that org's `DATA_MODEL.md` tables, not global)
- [ ] Guardrail: confirm no raw customer row data is ever sent to Claude — only metadata (table/column names, counts, samples) as `ARCHITECTURE.md` already specifies; this needs to be enforced in code, not just documented

---

## Phase 5 — Billing & Subscription Management (2–3 weeks)

Doesn't exist in any current doc — this is the actual "SaaS" part.

- [ ] Stripe integration: plans/tiers, metered usage (e.g., AI calls, marts monitored), invoicing
- [ ] Org-level subscription status gating feature access (trial, active, past_due, canceled)
- [ ] Self-serve upgrade/downgrade flow in the app (Settings page)
- [ ] Usage dashboards for org admins (what's consuming the plan's limits)
- [ ] Webhook handling for Stripe events (payment failed, subscription updated)

---

## Phase 6 — Tenant Self-Service Onboarding (2–3 weeks)

- [ ] Signup flow: create org, choose plan, connect first data source, invite team — no manual backend work per new customer
- [ ] "Register Mart" wizard (already mocked in `index.html`) wired to real API, per-org
- [ ] Guided SLA config setup (defaults + override per mart/layer)
- [ ] In-app connection health checks for Greenplum/OpenMetadata credentials (test-connection button, not just "hope it works")
- [ ] Sandbox/demo org with synthetic data so prospects can explore without connecting real infrastructure

---

## Phase 7 — Executive View, Notifications, Lineage (per `ROADMAP.md` Phases 4–5, made multi-tenant)

- [ ] Historical data API for executive view date navigation (currently static mock dates)
- [ ] `cost_per_hour_azn`-style configurable cost field per mart, per org's currency
- [ ] Email/Slack notifications on critical incidents (org-configurable channels)
- [ ] SQL lineage extraction (`sqlglot`) from ingested ETL logs → `lineage_nodes`/`lineage_edges`, impact analysis endpoint
- [ ] Re-evaluate Neo4j only if a tenant's table count exceeds ~200 and Postgres recursive CTEs become the bottleneck (per existing `ROADMAP.md` note — still valid)

---

## Phase 8 — Security, Compliance, Observability (ongoing, front-load before first paying customer)

Non-negotiable for a product selling into banks.

- [ ] Encryption in transit (TLS everywhere) and at rest (DB, backups, secrets via KMS)
- [ ] Audit log of all data-access and admin actions, per org, exportable
- [ ] Tenant isolation testing — write tests that actively try to leak data across `org_id` boundaries via the RLS policies
- [ ] Dependency/SAST scanning in CI, secrets scanning on every push
- [ ] Centralized logging/metrics/tracing (e.g., OpenTelemetry → Grafana/Datadog), uptime alerting, error tracking (Sentry)
- [ ] Incident response runbook, backup/restore drill, RTO/RPO targets documented
- [ ] Start the SOC 2 Type I control set early (access reviews, change management, vendor risk) even if certification comes later — banks will ask before signing

---

## Phase 9 — DevOps & Infra-as-Code (2–3 weeks, can start alongside Phase 1)

- [ ] Terraform for cloud resources (VPC, DB, cache, container service, secrets store)
- [ ] Separate dev/staging/prod environments with promotion pipeline
- [ ] CI/CD: build → test → deploy on merge to `main` (staging), tag-based promotion to prod
- [ ] Database migration safety gates (no destructive migration without a reviewed rollback plan)
- [ ] Autoscaling policy for API and worker tiers; Celery queue depth alerting

---

## Phase 10 — Testing, QA, Launch Readiness

- [ ] Unit tests for SLA computation logic, ingestion idempotency, RLS policies
- [ ] Integration tests for the full ingestion → SLA monitor → incident → dashboard pipeline
- [ ] Load testing the dashboard/catalog endpoints under realistic multi-tenant concurrency
- [ ] Pilot with 1–2 design-partner banks before general availability; use their feedback to correct Phase 6 onboarding friction
- [ ] i18n groundwork (Azerbaijani/Russian per `ROADMAP.md`) if launch customers need it at GA rather than post-launch

---

## Suggested sequencing

Phases 0–2 are strictly sequential (can't build tenant-aware ingestion without tenancy). Phase 3 (frontend) can start as soon as Phase 1's auth API exists — it doesn't need to wait for ingestion to be finished. Phases 4, 5, 6 can run in parallel once Phase 2 is stable. Phase 8 (security) isn't a phase you do once at the end — start the controls in Phase 1 and keep adding to them throughout; treat the checklist above as a running list, not a gate that blocks everything else until Phase 10.

Rough total: **6–9 months** to a real multi-tenant SaaS product with a design-partner pilot, assuming a small team (2–4 engineers) working the phases with the parallelism noted above.
