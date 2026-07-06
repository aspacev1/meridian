from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_org_db
from app.models import DataMart, Domain, Incident, LayerRun, PipelineRun, Report, ScanSession
from app.schemas.dashboard import DashboardContextOut, IncidentOut, SLAStatusOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _ordinal(n: int) -> str:
    if 11 <= n % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _delay_label(minutes: int | None) -> str | None:
    if minutes is None or minutes <= 0:
        return None
    hours, mins = divmod(minutes, 60)
    parts = ([f"{hours}h"] if hours else []) + [f"{mins}m"]
    return f"+{' '.join(parts)} overdue"


def _occurrence_label(count: int, window_days: int | None) -> str | None:
    if not count:
        return None
    label = f"{_ordinal(count)} time"
    if window_days:
        months = round(window_days / 30)
        label += f" in {months} months"
    return label


def _dq_delta_label(delta_pp: int | None) -> str | None:
    if delta_pp is None:
        return None
    return f"{delta_pp:+d}pp"


@router.get("/context", response_model=DashboardContextOut)
async def get_context(session: AsyncSession = Depends(get_org_db)) -> DashboardContextOut:
    latest_scan = (
        await session.execute(select(ScanSession).order_by(ScanSession.started_at.desc()).limit(1))
    ).scalar_one_or_none()

    reports_count = (
        await session.execute(select(func.count()).select_from(Report))
    ).scalar_one()
    domains_count = (
        await session.execute(select(func.count()).select_from(Domain))
    ).scalar_one()

    scan_time = scan_date = next_scan_in = None
    if latest_scan is not None:
        if latest_scan.finished_at is not None:
            scan_time = latest_scan.finished_at.strftime("%H:%M")
            scan_date = latest_scan.finished_at.strftime("%a %d %B %Y")
        if latest_scan.next_scheduled_at is not None:
            remaining = latest_scan.next_scheduled_at - datetime.now(timezone.utc)
            total_minutes = max(int(remaining.total_seconds() // 60), 0)
            hours, mins = divmod(total_minutes, 60)
            next_scan_in = f"{hours}h {mins}m" if hours else f"{mins}m"

    return DashboardContextOut(
        scan_time=scan_time,
        scan_date=scan_date,
        reports_count=reports_count,
        domains_count=domains_count,
        next_scan_in=next_scan_in,
    )


@router.get("/sla-status", response_model=SLAStatusOut)
async def get_sla_status(
    run_date: date | None = Query(default=None),
    layer: str = Query(default="dm"),
    session: AsyncSession = Depends(get_org_db),
) -> SLAStatusOut:
    target_date = run_date or date.today()

    result = await session.execute(
        select(LayerRun.sla_status, func.count())
        .join(PipelineRun, LayerRun.pipeline_run_id == PipelineRun.id)
        .where(PipelineRun.run_date == target_date, LayerRun.layer == layer)
        .group_by(LayerRun.sla_status)
    )
    counts = dict(result.all())

    return SLAStatusOut(
        breach=counts.get("breach", 0),
        warning=counts.get("warning", 0),
        healthy=counts.get("healthy", 0),
        total=sum(counts.values()),
        layer=layer,
        as_of=datetime.now(timezone.utc).strftime("%H:%M"),
    )


@router.get("/incidents", response_model=list[IncidentOut])
async def get_incidents(
    run_date: date | None = Query(default=None),
    session: AsyncSession = Depends(get_org_db),
) -> list[IncidentOut]:
    query = (
        select(Incident, DataMart.name)
        .join(DataMart, Incident.mart_id == DataMart.id)
        .where(Incident.status == "active")
        .order_by(Incident.detected_at.desc())
    )
    if run_date is not None:
        query = query.where(func.date(Incident.detected_at) == run_date)

    rows = (await session.execute(query)).all()

    return [
        IncidentOut(
            id=incident.id,
            type=incident.type,
            severity=incident.severity,
            status=incident.status,
            ai_name=incident.ai_name,
            ai_description=incident.ai_description,
            mart_name=mart_name,
            layer_statuses=incident.layer_statuses,
            detected_at=incident.detected_at,
            est_recovery_time=incident.est_recovery_time,
            sla_delay_minutes=incident.sla_delay_minutes,
            dq_actual_pct=incident.dq_actual_pct,
            dq_target_pct=incident.dq_target_pct,
            occurrence_count=incident.occurrence_count,
            occurrence_window_days=incident.occurrence_window_days,
            reports_affected_count=incident.reports_affected_count,
            availability_label=incident.availability_label,
            delay_label=_delay_label(incident.sla_delay_minutes),
            occurrence_label=_occurrence_label(incident.occurrence_count, incident.occurrence_window_days),
            dq_delta_label=_dq_delta_label(incident.dq_delta_pp),
        )
        for incident, mart_name in rows
    ]
