import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase


class Incident(TenantBase):
    """Auto-generated when SLA is breached or a DQ threshold is crossed."""

    __tablename__ = "incidents"

    type: Mapped[str] = mapped_column(String(30))
    # type: pipeline_sla_breach | dq_sla_breach | data_freshness
    severity: Mapped[str] = mapped_column(String(20))
    # severity: critical | warning
    status: Mapped[str] = mapped_column(String(20), default="active")
    # status: active | resolved | suppressed
    mart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_marts.id", ondelete="CASCADE"), index=True
    )
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="SET NULL")
    )
    ai_name: Mapped[str] = mapped_column(String(300))
    ai_description: Mapped[str] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    est_recovery_time: Mapped[str | None] = mapped_column(String(20))
    sla_delay_minutes: Mapped[int | None] = mapped_column(Integer)
    dq_actual_pct: Mapped[int | None] = mapped_column(Integer)
    dq_target_pct: Mapped[int | None] = mapped_column(Integer)
    dq_delta_pp: Mapped[int | None] = mapped_column(Integer)
    layer_statuses: Mapped[dict] = mapped_column(JSONB, default=dict)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    occurrence_window_days: Mapped[int | None] = mapped_column(Integer)
    reports_affected_count: Mapped[int] = mapped_column(Integer, default=0)
    availability_label: Mapped[str | None] = mapped_column(String(50))


class IncidentAffectedReport(TenantBase):
    """Join table: which reports an incident impacts."""

    __tablename__ = "incident_affected_reports"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), index=True
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), index=True
    )
