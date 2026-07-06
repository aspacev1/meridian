from datetime import datetime

from pydantic import BaseModel


class IngestionResultOut(BaseModel):
    rows_read: int
    runs_created: int
    runs_updated: int
    layer_runs_created: int
    layer_runs_updated: int
    errors: list[str]


class WebhookIngestionIn(BaseModel):
    mart_name: str
    layer: str
    job_id: str
    status: str
    rows_loaded: int | None = None
    finished_at: datetime
