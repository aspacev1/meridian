import uuid
from datetime import datetime

from pydantic import BaseModel


class CatalogReportOut(BaseModel):
    id: uuid.UUID
    name: str
    icon: str
    domain_name: str
    owner_team: str
    refresh_schedule: str
    last_run_at: datetime | None
    current_status: str
