import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase


class Report(TenantBase):
    """Business report powered by one or more data marts."""

    __tablename__ = "reports"

    name: Mapped[str] = mapped_column(String(300))
    icon: Mapped[str] = mapped_column(String(10), default="")
    domain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("domains.id", ondelete="CASCADE"), index=True
    )
    primary_mart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_marts.id", ondelete="CASCADE"), index=True
    )
    owner_team: Mapped[str] = mapped_column(String(200), default="")
    refresh_schedule: Mapped[str] = mapped_column(String(100), default="")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_status: Mapped[str] = mapped_column(String(10), default="go")
    # current_status: go | warn | stop


class ReportFavourite(TenantBase):
    """Per-user favourites with usage tracking for catalog sorting."""

    __tablename__ = "report_favourites"
    __table_args__ = (
        UniqueConstraint("user_id", "report_id", name="uq_favourite_user_report"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), index=True
    )
    open_count: Mapped[int] = mapped_column(Integer, default=0)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ScanSession(TenantBase):
    """One record per Meridian scan. Powers the dashboard context bar."""

    __tablename__ = "scan_sessions"

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running")
    reports_scanned: Mapped[int] = mapped_column(Integer, default=0)
    domains_scanned: Mapped[int] = mapped_column(Integer, default=0)
    triggered_by: Mapped[str] = mapped_column(String(50), default="schedule")
    # triggered_by: schedule | manual | webhook
