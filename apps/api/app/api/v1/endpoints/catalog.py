from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_org_db
from app.models import Domain, Report
from app.schemas.catalog import CatalogReportOut

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/reports", response_model=list[CatalogReportOut])
async def list_reports(
    status: str | None = Query(default=None, description="go | warn | stop"),
    domain_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_org_db),
) -> list[CatalogReportOut]:
    query = select(Report, Domain.name).join(Domain, Report.domain_id == Domain.id)
    if status is not None:
        query = query.where(Report.current_status == status)
    if domain_id is not None:
        query = query.where(Report.domain_id == domain_id)
    query = query.order_by(Report.name)

    rows = (await session.execute(query)).all()
    return [
        CatalogReportOut(
            id=report.id,
            name=report.name,
            icon=report.icon,
            domain_name=domain_name,
            owner_team=report.owner_team,
            refresh_schedule=report.refresh_schedule,
            last_run_at=report.last_run_at,
            current_status=report.current_status,
        )
        for report, domain_name in rows
    ]
