import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase


class DQRule(TenantBase):
    """Data quality rule definition, applied at a layer for a table/column."""

    __tablename__ = "dq_rules"
    __table_args__ = (UniqueConstraint("org_id", "rule_code", name="uq_dqrule_org_code"),)

    rule_code: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(200))
    rule_type: Mapped[str] = mapped_column(String(30))
    # rule_type: not_null | unique | range_check | referential | custom_sql
    mart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_marts.id", ondelete="CASCADE"), index=True
    )
    layer: Mapped[str] = mapped_column(String(20))
    table_name: Mapped[str] = mapped_column(String(200))
    column_name: Mapped[str] = mapped_column(String(200))
    sql_expression: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="error")


class DQResult(TenantBase):
    """Execution result of a DQ rule for a specific layer run."""

    __tablename__ = "dq_results"

    layer_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("layer_runs.id", ondelete="CASCADE"), index=True
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dq_rules.id", ondelete="CASCADE")
    )
    passed: Mapped[bool] = mapped_column(Boolean)
    failed_rows: Mapped[int] = mapped_column(Integer, default=0)
    total_rows: Mapped[int | None] = mapped_column(Integer)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    error_detail: Mapped[str | None] = mapped_column(Text)
