import uuid
from datetime import date, datetime, time

from sqlalchemy import DateTime, Date, ForeignKey, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase

LAYERS = ("source", "staging", "ods", "dm")


class SLAConfig(TenantBase):
    """Target delivery time for a mart x layer combination."""

    __tablename__ = "sla_configs"
    __table_args__ = (UniqueConstraint("mart_id", "layer", name="uq_sla_mart_layer"),)

    mart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_marts.id", ondelete="CASCADE"), index=True
    )
    layer: Mapped[str] = mapped_column(String(20))
    target_time: Mapped[time] = mapped_column(Time)
    dq_threshold_pct: Mapped[int] = mapped_column(Integer, default=95)
    owner_team: Mapped[str] = mapped_column(String(100), default="")
    is_active: Mapped[bool] = mapped_column(default=True)


class PipelineRun(TenantBase):
    """One daily execution per mart, ingested from the tenant's ETL logs."""

    __tablename__ = "pipeline_runs"
    __table_args__ = (UniqueConstraint("mart_id", "run_date", name="uq_run_mart_date"),)

    mart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_marts.id", ondelete="CASCADE"), index=True
    )
    run_date: Mapped[date] = mapped_column(Date, index=True)
    job_name: Mapped[str] = mapped_column(String(200), default="")
    job_id: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(20), default="running")
    # status: running | success | failed | skipped
    sla_status: Mapped[str] = mapped_column(String(20), default="no_scan")
    # sla_status: healthy | warning | breach | no_scan
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class LayerRun(TenantBase):
    """Per-layer execution stats within a pipeline run."""

    __tablename__ = "layer_runs"
    __table_args__ = (
        UniqueConstraint("pipeline_run_id", "layer", name="uq_layerrun_run_layer"),
    )

    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="CASCADE"), index=True
    )
    layer: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="running")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_time: Mapped[time | None] = mapped_column(Time)
    rows_loaded: Mapped[int | None] = mapped_column(Integer)
    dq_rules_total: Mapped[int] = mapped_column(Integer, default=0)
    dq_rules_passed: Mapped[int] = mapped_column(Integer, default=0)
    sla_status: Mapped[str] = mapped_column(String(20), default="no_scan")
    sla_delay_minutes: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
