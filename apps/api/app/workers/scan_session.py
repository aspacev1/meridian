"""Hourly scan session sweep, per ARCHITECTURE.md. Creates a ScanSession
snapshot per org powering the dashboard context bar ("Last scan 06:14 ·
24 reports · 6 domains").
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models import DataMart, Domain, Report, ScanSession


async def run_for_org(org_id: uuid.UUID) -> None:
    async with async_session_factory() as session:
        await _scope_session(session, org_id)

        started_at = datetime.now(timezone.utc)

        reports_scanned = (
            await session.execute(
                select(func.count()).select_from(Report).where(Report.org_id == org_id)
            )
        ).scalar_one()
        domains_scanned = (
            await session.execute(
                select(func.count()).select_from(Domain).where(Domain.org_id == org_id)
            )
        ).scalar_one()
        # Marts aren't stored on ScanSession per DATA_MODEL.md, but active-mart
        # count is cheap context for anyone reading logs during Phase 2 testing.
        await session.execute(
            select(func.count()).select_from(DataMart).where(DataMart.org_id == org_id)
        )

        session.add(
            ScanSession(
                org_id=org_id,
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
                next_scheduled_at=started_at + timedelta(hours=1),
                status="completed",
                reports_scanned=reports_scanned,
                domains_scanned=domains_scanned,
                triggered_by="schedule",
            )
        )
        await session.commit()


async def _scope_session(session: AsyncSession, org_id: uuid.UUID) -> None:
    await session.execute(
        text("SELECT set_config('app.current_org_id', :org_id, true)"), {"org_id": str(org_id)}
    )
