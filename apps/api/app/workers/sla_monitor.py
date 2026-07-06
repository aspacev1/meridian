"""Core SLA check: computes per-layer SLA status for today's pipeline runs
and raises incidents on breach/warning, per ARCHITECTURE.md.

Invoked per-organization (see app/workers/tasks.py::run_sla_check_for_org) so
one tenant's mart backlog can't starve another's.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models import DataMart, Incident, LayerRun, PipelineRun, Report, SLAConfig
from app.services import ai_service, sla_service

OCCURRENCE_WINDOW_DAYS = 487  # matches the prototype's "3rd time in 16 months" copy


async def _scope_session(session: AsyncSession, org_id: uuid.UUID) -> None:
    await session.execute(
        text("SELECT set_config('app.current_org_id', :org_id, true)"), {"org_id": str(org_id)}
    )


async def check_org(org_id: uuid.UUID, run_date: date | None = None) -> None:
    run_date = run_date or date.today()
    async with async_session_factory() as session:
        await _scope_session(session, org_id)

        marts = (
            await session.execute(
                select(DataMart).where(DataMart.org_id == org_id, DataMart.is_active.is_(True))
            )
        ).scalars().all()

        for mart in marts:
            await _check_mart(session, org_id, mart, run_date)

        await session.commit()


async def _check_mart(
    session: AsyncSession, org_id: uuid.UUID, mart: DataMart, run_date: date
) -> None:
    pr_result = await session.execute(
        select(PipelineRun).where(
            PipelineRun.org_id == org_id,
            PipelineRun.mart_id == mart.id,
            PipelineRun.run_date == run_date,
        )
    )
    pipeline_run = pr_result.scalar_one_or_none()
    if pipeline_run is None:
        return  # nothing ingested for this mart today yet

    sla_configs = {
        c.layer: c
        for c in (
            await session.execute(
                select(SLAConfig).where(
                    SLAConfig.mart_id == mart.id, SLAConfig.is_active.is_(True)
                )
            )
        )
        .scalars()
        .all()
    }

    layer_runs = (
        await session.execute(select(LayerRun).where(LayerRun.pipeline_run_id == pipeline_run.id))
    ).scalars().all()

    layer_statuses: dict[str, str] = {}
    for layer_run in layer_runs:
        config = sla_configs.get(layer_run.layer)
        if config is None:
            continue

        pass_rate = sla_service.dq_pass_rate_pct(layer_run.dq_rules_passed, layer_run.dq_rules_total)
        status = sla_service.compute_sla_status(
            layer_run.delivery_time,
            config.target_time,
            layer_run.status,
            pass_rate,
            config.dq_threshold_pct,
        )
        layer_run.sla_status = status
        layer_statuses[layer_run.layer] = "ok" if status == "healthy" else "failed"

        if layer_run.delivery_time is not None:
            actual_dt = datetime.combine(run_date, layer_run.delivery_time)
            target_dt = datetime.combine(run_date, config.target_time)
            layer_run.sla_delay_minutes = int((actual_dt - target_dt).total_seconds() // 60)

    if not layer_statuses:
        return

    pipeline_run.sla_status = sla_service.worst_status([lr.sla_status for lr in layer_runs])

    if pipeline_run.sla_status not in ("warning", "breach"):
        return

    await _ensure_incident(session, org_id, mart, pipeline_run, layer_runs, layer_statuses, run_date)


async def _ensure_incident(
    session: AsyncSession,
    org_id: uuid.UUID,
    mart: DataMart,
    pipeline_run: PipelineRun,
    layer_runs: list[LayerRun],
    layer_statuses: dict[str, str],
    run_date: date,
) -> None:
    existing = await session.execute(
        select(Incident).where(
            Incident.org_id == org_id,
            Incident.pipeline_run_id == pipeline_run.id,
            Incident.status == "active",
        )
    )
    if existing.scalar_one_or_none() is not None:
        return  # already raised for this run; check_org runs every 5 minutes

    dm_layer = next((lr for lr in layer_runs if lr.layer == "dm"), None)
    delay_minutes = dm_layer.sla_delay_minutes if dm_layer else None

    window_start = run_date - timedelta(days=OCCURRENCE_WINDOW_DAYS)
    past_incidents = (
        await session.execute(
            select(Incident).where(
                Incident.org_id == org_id,
                Incident.mart_id == mart.id,
                Incident.detected_at >= datetime.combine(window_start, datetime.min.time()),
            )
        )
    ).scalars().all()

    reports_affected = (
        await session.execute(
            select(Report).where(Report.org_id == org_id, Report.primary_mart_id == mart.id)
        )
    ).scalars().all()

    narrative = ai_service.name_incident(
        mart_name=mart.name,
        incident_type="pipeline_sla_breach",
        layer_statuses=layer_statuses,
        delay_minutes=delay_minutes,
        job_id=pipeline_run.job_id,
    )

    severity = "critical" if pipeline_run.sla_status == "breach" else "warning"
    session.add(
        Incident(
            org_id=org_id,
            type="pipeline_sla_breach",
            severity=severity,
            status="active",
            mart_id=mart.id,
            pipeline_run_id=pipeline_run.id,
            ai_name=narrative.name,
            ai_description=narrative.description,
            detected_at=datetime.now(timezone.utc),
            sla_delay_minutes=delay_minutes,
            layer_statuses=layer_statuses,
            occurrence_count=len(past_incidents) + 1,
            occurrence_window_days=OCCURRENCE_WINDOW_DAYS,
            reports_affected_count=len(reports_affected),
            availability_label="fully unavailable" if severity == "critical" else "partial data",
        )
    )
