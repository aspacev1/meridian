"""Celery task definitions.

These are intentionally thin stubs for Phase 1 -- they establish the
scheduled entrypoints and per-tenant fan-out pattern. The actual SLA
computation (sla_monitor.py) and ingestion (log_ingestion.py) land in
Phase 2 once real connector data is flowing.
"""

from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.run_sla_check")
def run_sla_check() -> None:
    """Fans out an SLA check across every active organization. Runs every
    5 minutes via Celery Beat. Per-org work happens in a per-org task so
    one tenant's backlog can't starve another's (see SAAS_TRANSFORMATION_PLAN.md
    Phase 2).
    """
    raise NotImplementedError("Phase 2: iterate active orgs, dispatch run_sla_check_for_org")


@celery_app.task(name="app.workers.tasks.run_sla_check_for_org")
def run_sla_check_for_org(org_id: str) -> None:
    raise NotImplementedError("Phase 2: SLA Monitor per ARCHITECTURE.md")


@celery_app.task(name="app.workers.tasks.run_scan_session")
def run_scan_session() -> None:
    """Hourly scan session sweep across all active organizations."""
    raise NotImplementedError("Phase 2: Scan Session Worker per ARCHITECTURE.md")


@celery_app.task(name="app.workers.tasks.ingest_csv_log")
def ingest_csv_log(org_id: str, file_path: str) -> None:
    raise NotImplementedError("Phase 2: Greenplum CSV log ingestion per ARCHITECTURE.md")
