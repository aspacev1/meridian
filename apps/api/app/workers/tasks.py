"""Celery task definitions.

Top-level tasks fan out across active organizations; the per-org tasks do
the real work in an org-scoped session. Celery workers are synchronous, so
each task drives its async DB/service code via asyncio.run().
"""

import asyncio
import uuid

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models import Organization
from app.workers import scan_session, sla_monitor
from app.workers.celery_app import celery_app


async def _active_org_ids() -> list[uuid.UUID]:
    # Organization is not a TenantBase row (it IS the tenant), so no RLS
    # scoping is needed to list them.
    async with async_session_factory() as session:
        result = await session.execute(select(Organization.id).where(Organization.is_active.is_(True)))
        return [row[0] for row in result.all()]


@celery_app.task(name="app.workers.tasks.run_sla_check")
def run_sla_check() -> None:
    for org_id in asyncio.run(_active_org_ids()):
        run_sla_check_for_org.delay(str(org_id))


@celery_app.task(name="app.workers.tasks.run_sla_check_for_org")
def run_sla_check_for_org(org_id: str) -> None:
    asyncio.run(sla_monitor.check_org(uuid.UUID(org_id)))


@celery_app.task(name="app.workers.tasks.run_scan_session")
def run_scan_session() -> None:
    for org_id in asyncio.run(_active_org_ids()):
        run_scan_session_for_org.delay(str(org_id))


@celery_app.task(name="app.workers.tasks.run_scan_session_for_org")
def run_scan_session_for_org(org_id: str) -> None:
    asyncio.run(scan_session.run_for_org(uuid.UUID(org_id)))


@celery_app.task(name="app.workers.tasks.ingest_csv_log")
def ingest_csv_log(org_id: str, csv_bytes: bytes) -> dict:
    from app.core.database import org_scoped_session
    from app.services.log_ingestion import ingest_csv

    async def _run() -> dict:
        async with org_scoped_session(org_id) as session:
            result = await ingest_csv(uuid.UUID(org_id), session, csv_bytes)
            await session.commit()
            return {
                "rows_read": result.rows_read,
                "runs_created": result.runs_created,
                "runs_updated": result.runs_updated,
                "layer_runs_created": result.layer_runs_created,
                "layer_runs_updated": result.layer_runs_updated,
                "errors": result.errors,
            }

    return asyncio.run(_run())
