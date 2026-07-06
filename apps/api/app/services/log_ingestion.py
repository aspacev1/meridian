"""Greenplum ETL CSV log ingestion -> pipeline_runs + layer_runs.

Per ARCHITECTURE.md: reads CSV logs exported from a tenant's warehouse and
builds pipeline run history. Idempotent -- safe to re-ingest the same file,
since PipelineRun is unique on (mart_id, run_date) and LayerRun is unique
on (pipeline_run_id, layer); re-ingestion updates the existing row instead
of duplicating it.
"""

import csv
import io
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DataMart, LayerRun, PipelineRun

LAYER_MAP = {
    "src": "source",
    "source": "source",
    "stg": "staging",
    "staging": "staging",
    "ods": "ods",
    "dm": "dm",
    "dw": "dm",
}

STATUS_VALUES = {"running", "success", "failed", "skipped"}

TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M",
    "%m/%d/%Y %H:%M:%S",
)

REQUIRED_COLUMNS = {
    "job_name",
    "job_id",
    "mart_name",
    "layer",
    "started_at",
    "finished_at",
    "rows_affected",
    "status",
    "error_message",
}


class IngestionError(Exception):
    pass


@dataclass
class IngestionResult:
    rows_read: int = 0
    runs_created: int = 0
    runs_updated: int = 0
    layer_runs_created: int = 0
    layer_runs_updated: int = 0
    errors: list[str] = field(default_factory=list)


def _parse_timestamp(raw: str | None) -> datetime | None:
    if not raw or not raw.strip():
        return None
    raw = raw.strip()
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        raise IngestionError(f"Unrecognized timestamp format: {raw!r}") from None


def _canonical_layer(raw: str) -> str:
    key = raw.strip().lower()
    if key not in LAYER_MAP:
        raise IngestionError(f"Unknown layer name: {raw!r}")
    return LAYER_MAP[key]


async def ingest_csv(org_id: uuid.UUID, session: AsyncSession, csv_bytes: bytes) -> IngestionResult:
    """Parses a CSV log export and upserts PipelineRun/LayerRun rows for
    `org_id`. Caller is responsible for the session already being
    org-scoped (RLS-wise) and for committing/rolling back the transaction.
    """
    result = IngestionResult()
    text_stream = io.StringIO(csv_bytes.decode("utf-8-sig"))
    reader = csv.DictReader(text_stream)

    if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        raise IngestionError(f"CSV missing required columns: {sorted(missing)}")

    mart_cache: dict[str, DataMart | None] = {}
    # (mart_id, run_date) -> PipelineRun, loaded lazily and reused across rows
    run_cache: dict[tuple[uuid.UUID, date], PipelineRun] = {}

    for row_num, row in enumerate(reader, start=2):  # header is line 1
        result.rows_read += 1
        try:
            mart_name = row["mart_name"].strip()
            if mart_name not in mart_cache:
                mart_result = await session.execute(
                    select(DataMart).where(
                        DataMart.org_id == org_id, DataMart.name == mart_name
                    )
                )
                mart_cache[mart_name] = mart_result.scalar_one_or_none()
            mart = mart_cache[mart_name]
            if mart is None:
                raise IngestionError(f"Unknown mart '{mart_name}' -- register it first")

            layer = _canonical_layer(row["layer"])
            started_at = _parse_timestamp(row.get("started_at"))
            finished_at = _parse_timestamp(row.get("finished_at"))
            status = row["status"].strip().lower()
            if status not in STATUS_VALUES:
                raise IngestionError(f"Unknown status: {row['status']!r}")

            run_date = (started_at or finished_at or datetime.utcnow()).date()
            cache_key = (mart.id, run_date)

            if cache_key not in run_cache:
                pr_result = await session.execute(
                    select(PipelineRun).where(
                        PipelineRun.org_id == org_id,
                        PipelineRun.mart_id == mart.id,
                        PipelineRun.run_date == run_date,
                    )
                )
                pipeline_run = pr_result.scalar_one_or_none()
                if pipeline_run is None:
                    pipeline_run = PipelineRun(
                        org_id=org_id,
                        mart_id=mart.id,
                        run_date=run_date,
                        job_name=row["job_name"],
                        job_id=row["job_id"],
                        status=status,
                        started_at=started_at,
                        finished_at=finished_at,
                        error_message=row.get("error_message") or None,
                    )
                    session.add(pipeline_run)
                    await session.flush()
                    result.runs_created += 1
                else:
                    pipeline_run.job_name = row["job_name"]
                    pipeline_run.job_id = row["job_id"]
                    pipeline_run.status = status
                    pipeline_run.started_at = started_at
                    pipeline_run.finished_at = finished_at
                    pipeline_run.error_message = row.get("error_message") or None
                    result.runs_updated += 1
                run_cache[cache_key] = pipeline_run

            pipeline_run = run_cache[cache_key]

            lr_result = await session.execute(
                select(LayerRun).where(
                    LayerRun.org_id == org_id,
                    LayerRun.pipeline_run_id == pipeline_run.id,
                    LayerRun.layer == layer,
                )
            )
            layer_run = lr_result.scalar_one_or_none()
            rows_affected = int(row["rows_affected"]) if row.get("rows_affected") else None
            delivery_time = finished_at.time() if finished_at else None

            if layer_run is None:
                layer_run = LayerRun(
                    org_id=org_id,
                    pipeline_run_id=pipeline_run.id,
                    layer=layer,
                    status=status,
                    started_at=started_at,
                    finished_at=finished_at,
                    delivery_time=delivery_time,
                    rows_loaded=rows_affected,
                    error_message=row.get("error_message") or None,
                )
                session.add(layer_run)
                result.layer_runs_created += 1
            else:
                layer_run.status = status
                layer_run.started_at = started_at
                layer_run.finished_at = finished_at
                layer_run.delivery_time = delivery_time
                layer_run.rows_loaded = rows_affected
                layer_run.error_message = row.get("error_message") or None
                result.layer_runs_updated += 1

        except IngestionError as exc:
            result.errors.append(f"line {row_num}: {exc}")

    await session.flush()
    return result
