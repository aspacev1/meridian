from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentPrincipal, get_current_principal, get_org_db
from app.models import DataMart, LayerRun, PipelineRun
from app.schemas.ingestion import IngestionResultOut, WebhookIngestionIn
from app.services.log_ingestion import LAYER_MAP, IngestionError, ingest_csv

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/csv", response_model=IngestionResultOut)
async def ingest_csv_endpoint(
    file: UploadFile,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_org_db),
) -> IngestionResultOut:
    csv_bytes = await file.read()
    try:
        result = await ingest_csv(principal.org_id, session, csv_bytes)
    except IngestionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    await session.commit()
    return IngestionResultOut(
        rows_read=result.rows_read,
        runs_created=result.runs_created,
        runs_updated=result.runs_updated,
        layer_runs_created=result.layer_runs_created,
        layer_runs_updated=result.layer_runs_updated,
        errors=result.errors,
    )


@router.post("/webhook", response_model=IngestionResultOut)
async def ingest_webhook(
    body: WebhookIngestionIn,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_org_db),
) -> IngestionResultOut:
    """Single-layer-run event from an Airflow/dbt pipeline completion hook,
    per API.md. Upserts one PipelineRun + LayerRun rather than parsing a
    full CSV export.
    """
    org_id = principal.org_id

    layer = LAYER_MAP.get(body.layer.strip().lower())
    if layer is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown layer: {body.layer!r}")

    mart_result = await session.execute(
        select(DataMart).where(DataMart.org_id == org_id, DataMart.name == body.mart_name)
    )
    mart = mart_result.scalar_one_or_none()
    if mart is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Unknown mart '{body.mart_name}' -- register it first"
        )

    run_date = body.finished_at.date()
    pr_result = await session.execute(
        select(PipelineRun).where(
            PipelineRun.org_id == org_id,
            PipelineRun.mart_id == mart.id,
            PipelineRun.run_date == run_date,
        )
    )
    pipeline_run = pr_result.scalar_one_or_none()
    runs_created = runs_updated = 0
    if pipeline_run is None:
        pipeline_run = PipelineRun(
            org_id=org_id,
            mart_id=mart.id,
            run_date=run_date,
            job_id=body.job_id,
            status=body.status,
            finished_at=body.finished_at,
        )
        session.add(pipeline_run)
        await session.flush()
        runs_created = 1
    else:
        pipeline_run.status = body.status
        pipeline_run.finished_at = body.finished_at
        runs_updated = 1

    lr_result = await session.execute(
        select(LayerRun).where(
            LayerRun.org_id == org_id,
            LayerRun.pipeline_run_id == pipeline_run.id,
            LayerRun.layer == layer,
        )
    )
    layer_run = lr_result.scalar_one_or_none()
    layer_runs_created = layer_runs_updated = 0
    if layer_run is None:
        session.add(
            LayerRun(
                org_id=org_id,
                pipeline_run_id=pipeline_run.id,
                layer=layer,
                status=body.status,
                finished_at=body.finished_at,
                delivery_time=body.finished_at.time(),
                rows_loaded=body.rows_loaded,
            )
        )
        layer_runs_created = 1
    else:
        layer_run.status = body.status
        layer_run.finished_at = body.finished_at
        layer_run.delivery_time = body.finished_at.time()
        layer_run.rows_loaded = body.rows_loaded
        layer_runs_updated = 1

    await session.commit()
    return IngestionResultOut(
        rows_read=1,
        runs_created=runs_created,
        runs_updated=runs_updated,
        layer_runs_created=layer_runs_created,
        layer_runs_updated=layer_runs_updated,
        errors=[],
    )
