"""Initial multi-tenant schema (organizations, users, and the full
DATA_MODEL.md domain schema), with Postgres Row-Level Security enabling
tenant isolation on every org-scoped table.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Every table below except `organizations` and `users` carries org_id and
# gets RLS enabled + a tenant-isolation policy applied to it.
TENANT_TABLES = [
    "memberships",
    "domains",
    "data_marts",
    "data_source_connections",
    "sla_configs",
    "pipeline_runs",
    "layer_runs",
    "dq_rules",
    "dq_results",
    "reports",
    "report_favourites",
    "scan_sessions",
    "incidents",
    "incident_affected_reports",
    "glossary_entries",
]


def _timestamps():
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def _org_fk():
    return sa.Column(
        "org_id",
        pg.UUID(as_uuid=True),
        sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("workos_organization_id", sa.String(100), unique=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("stripe_customer_id", sa.String(100)),
        sa.Column(
            "subscription_status", sa.String(20), nullable=False, server_default="trialing"
        ),
        *_timestamps(),
    )

    op.create_table(
        "users",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("workos_user_id", sa.String(100), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("avatar_initials", sa.String(4), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        *_timestamps(),
    )

    op.create_table(
        "memberships",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        _org_fk(),
        sa.Column(
            "user_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(50), nullable=False, server_default="steward"),
        *_timestamps(),
        sa.UniqueConstraint("org_id", "user_id", name="uq_membership_org_user"),
    )
    op.create_index("ix_memberships_org_id", "memberships", ["org_id"])
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])

    op.create_table(
        "domains",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        _org_fk(),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("icon", sa.String(10), nullable=False, server_default=""),
        sa.Column("owner_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        *_timestamps(),
        sa.UniqueConstraint("org_id", "name", name="uq_domain_org_name"),
    )
    op.create_index("ix_domains_org_id", "domains", ["org_id"])

    op.create_table(
        "data_marts",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        _org_fk(),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "domain_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("domains.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("cost_per_hour", sa.Numeric(12, 2)),
        *_timestamps(),
        sa.UniqueConstraint("org_id", "name", name="uq_mart_org_name"),
    )
    op.create_index("ix_data_marts_org_id", "data_marts", ["org_id"])
    op.create_index("ix_data_marts_domain_id", "data_marts", ["domain_id"])

    op.create_table(
        "data_source_connections",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        _org_fk(),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("encrypted_config", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("last_checked_error", sa.Text),
        *_timestamps(),
    )
    op.create_index(
        "ix_data_source_connections_org_id", "data_source_connections", ["org_id"]
    )

    op.create_table(
        "sla_configs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        _org_fk(),
        sa.Column(
            "mart_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("data_marts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("layer", sa.String(20), nullable=False),
        sa.Column("target_time", sa.Time, nullable=False),
        sa.Column("dq_threshold_pct", sa.Integer, nullable=False, server_default="95"),
        sa.Column("owner_team", sa.String(100), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        *_timestamps(),
        sa.UniqueConstraint("mart_id", "layer", name="uq_sla_mart_layer"),
    )
    op.create_index("ix_sla_configs_org_id", "sla_configs", ["org_id"])
    op.create_index("ix_sla_configs_mart_id", "sla_configs", ["mart_id"])

    op.create_table(
        "pipeline_runs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        _org_fk(),
        sa.Column(
            "mart_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("data_marts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("run_date", sa.Date, nullable=False),
        sa.Column("job_name", sa.String(200), nullable=False, server_default=""),
        sa.Column("job_id", sa.String(100), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("sla_status", sa.String(20), nullable=False, server_default="no_scan"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text),
        *_timestamps(),
        sa.UniqueConstraint("mart_id", "run_date", name="uq_run_mart_date"),
    )
    op.create_index("ix_pipeline_runs_org_id", "pipeline_runs", ["org_id"])
    op.create_index("ix_pipeline_runs_mart_id", "pipeline_runs", ["mart_id"])
    op.create_index("ix_pipeline_runs_run_date", "pipeline_runs", ["run_date"])

    op.create_table(
        "layer_runs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        _org_fk(),
        sa.Column(
            "pipeline_run_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("layer", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("delivery_time", sa.Time),
        sa.Column("rows_loaded", sa.Integer),
        sa.Column("dq_rules_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("dq_rules_passed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sla_status", sa.String(20), nullable=False, server_default="no_scan"),
        sa.Column("sla_delay_minutes", sa.Integer),
        sa.Column("error_message", sa.Text),
        *_timestamps(),
        sa.UniqueConstraint("pipeline_run_id", "layer", name="uq_layerrun_run_layer"),
    )
    op.create_index("ix_layer_runs_org_id", "layer_runs", ["org_id"])
    op.create_index("ix_layer_runs_pipeline_run_id", "layer_runs", ["pipeline_run_id"])

    op.create_table(
        "dq_rules",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        _org_fk(),
        sa.Column("rule_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("rule_type", sa.String(30), nullable=False),
        sa.Column(
            "mart_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("data_marts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("layer", sa.String(20), nullable=False),
        sa.Column("table_name", sa.String(200), nullable=False),
        sa.Column("column_name", sa.String(200), nullable=False),
        sa.Column("sql_expression", sa.Text),
        sa.Column("severity", sa.String(20), nullable=False, server_default="error"),
        *_timestamps(),
        sa.UniqueConstraint("org_id", "rule_code", name="uq_dqrule_org_code"),
    )
    op.create_index("ix_dq_rules_org_id", "dq_rules", ["org_id"])
    op.create_index("ix_dq_rules_mart_id", "dq_rules", ["mart_id"])

    op.create_table(
        "dq_results",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        _org_fk(),
        sa.Column(
            "layer_run_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("layer_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "rule_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("dq_rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("passed", sa.Boolean, nullable=False),
        sa.Column("failed_rows", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_rows", sa.Integer),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_detail", sa.Text),
        *_timestamps(),
    )
    op.create_index("ix_dq_results_org_id", "dq_results", ["org_id"])
    op.create_index("ix_dq_results_layer_run_id", "dq_results", ["layer_run_id"])

    op.create_table(
        "reports",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        _org_fk(),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("icon", sa.String(10), nullable=False, server_default=""),
        sa.Column(
            "domain_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("domains.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "primary_mart_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("data_marts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("owner_team", sa.String(200), nullable=False, server_default=""),
        sa.Column("refresh_schedule", sa.String(100), nullable=False, server_default=""),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("current_status", sa.String(10), nullable=False, server_default="go"),
        *_timestamps(),
    )
    op.create_index("ix_reports_org_id", "reports", ["org_id"])
    op.create_index("ix_reports_domain_id", "reports", ["domain_id"])
    op.create_index("ix_reports_primary_mart_id", "reports", ["primary_mart_id"])

    op.create_table(
        "report_favourites",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        _org_fk(),
        sa.Column(
            "user_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "report_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("open_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("user_id", "report_id", name="uq_favourite_user_report"),
    )
    op.create_index("ix_report_favourites_org_id", "report_favourites", ["org_id"])
    op.create_index("ix_report_favourites_user_id", "report_favourites", ["user_id"])
    op.create_index("ix_report_favourites_report_id", "report_favourites", ["report_id"])

    op.create_table(
        "scan_sessions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        _org_fk(),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("next_scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("reports_scanned", sa.Integer, nullable=False, server_default="0"),
        sa.Column("domains_scanned", sa.Integer, nullable=False, server_default="0"),
        sa.Column("triggered_by", sa.String(50), nullable=False, server_default="schedule"),
        *_timestamps(),
    )
    op.create_index("ix_scan_sessions_org_id", "scan_sessions", ["org_id"])

    op.create_table(
        "incidents",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        _org_fk(),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column(
            "mart_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("data_marts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pipeline_run_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
        ),
        sa.Column("ai_name", sa.String(300), nullable=False),
        sa.Column("ai_description", sa.Text, nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("est_recovery_time", sa.String(20)),
        sa.Column("sla_delay_minutes", sa.Integer),
        sa.Column("dq_actual_pct", sa.Integer),
        sa.Column("dq_target_pct", sa.Integer),
        sa.Column("dq_delta_pp", sa.Integer),
        sa.Column("layer_statuses", pg.JSONB, nullable=False, server_default="{}"),
        sa.Column("occurrence_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("occurrence_window_days", sa.Integer),
        sa.Column("reports_affected_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("availability_label", sa.String(50)),
        *_timestamps(),
    )
    op.create_index("ix_incidents_org_id", "incidents", ["org_id"])
    op.create_index("ix_incidents_mart_id", "incidents", ["mart_id"])
    op.create_index("ix_incidents_status", "incidents", ["status"])

    op.create_table(
        "incident_affected_reports",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        _org_fk(),
        sa.Column(
            "incident_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "report_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        *_timestamps(),
    )
    op.create_index(
        "ix_incident_affected_reports_org_id", "incident_affected_reports", ["org_id"]
    )
    op.create_index(
        "ix_incident_affected_reports_incident_id",
        "incident_affected_reports",
        ["incident_id"],
    )

    op.create_table(
        "glossary_entries",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        _org_fk(),
        sa.Column("table_name", sa.String(300), nullable=False),
        sa.Column("column_name", sa.String(200), nullable=False),
        sa.Column("biz_name", sa.String(300), nullable=False, server_default=""),
        sa.Column("definition", sa.Text),
        sa.Column("calculation", sa.Text),
        sa.Column("regulatory_refs", sa.Text),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("is_ai_draft", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("edited_by_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("edited_at", sa.DateTime(timezone=True)),
        sa.Column("published_by_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column(
            "mart_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("data_marts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        *_timestamps(),
        sa.UniqueConstraint(
            "org_id", "table_name", "column_name", name="uq_glossary_org_col"
        ),
    )
    op.create_index("ix_glossary_entries_org_id", "glossary_entries", ["org_id"])
    op.create_index("ix_glossary_entries_table_name", "glossary_entries", ["table_name"])
    op.create_index("ix_glossary_entries_mart_id", "glossary_entries", ["mart_id"])

    # --- Row-Level Security -------------------------------------------------
    # Every tenant table is locked down so a session can only see rows for
    # the org set via `SET LOCAL app.current_org_id` (see app/core/database.py).
    # FORCE ROW LEVEL SECURITY means even the table owner is bound by it,
    # so a bug that connects as a superuser can't accidentally bypass isolation.
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (org_id = current_setting('app.current_org_id', true)::uuid)
            WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)
            """
        )


def downgrade() -> None:
    for table in reversed(TENANT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")

    op.drop_table("glossary_entries")
    op.drop_table("incident_affected_reports")
    op.drop_table("incidents")
    op.drop_table("scan_sessions")
    op.drop_table("report_favourites")
    op.drop_table("reports")
    op.drop_table("dq_results")
    op.drop_table("dq_rules")
    op.drop_table("layer_runs")
    op.drop_table("pipeline_runs")
    op.drop_table("sla_configs")
    op.drop_table("data_source_connections")
    op.drop_table("data_marts")
    op.drop_table("domains")
    op.drop_table("memberships")
    op.drop_table("users")
    op.drop_table("organizations")
