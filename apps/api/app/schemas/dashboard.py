import uuid
from datetime import datetime

from pydantic import BaseModel


class DashboardContextOut(BaseModel):
    scan_time: str | None
    scan_date: str | None
    reports_count: int
    domains_count: int
    next_scan_in: str | None


class SLAStatusOut(BaseModel):
    breach: int
    warning: int
    healthy: int
    total: int
    layer: str
    as_of: str | None


class IncidentOut(BaseModel):
    id: uuid.UUID
    type: str
    severity: str
    status: str
    ai_name: str
    ai_description: str
    mart_name: str
    layer_statuses: dict
    detected_at: datetime
    est_recovery_time: str | None
    sla_delay_minutes: int | None
    dq_actual_pct: int | None
    dq_target_pct: int | None
    occurrence_count: int
    occurrence_window_days: int | None
    reports_affected_count: int
    availability_label: str | None
    delay_label: str | None
    occurrence_label: str | None
    dq_delta_label: str | None
