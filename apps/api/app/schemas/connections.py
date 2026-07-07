import uuid
from typing import Literal

from pydantic import BaseModel, Field

ConnectionKind = Literal["openmetadata", "greenplum", "local_disk"]


class OpenMetadataConfig(BaseModel):
    host_url: str = Field(..., description="e.g. https://openmetadata.acme.internal:8585")
    api_token: str = Field(..., description="OpenMetadata bot JWT")


class GreenplumConfig(BaseModel):
    host: str
    port: int = 5432
    database: str
    username: str
    password: str
    sslmode: str = "prefer"


class LocalDiskConfig(BaseModel):
    path: str = Field(
        ...,
        description="Absolute directory path on the server Meridian runs on, "
        "e.g. /data/etl-exports/acme -- scanned for ETL CSV drops",
    )


CONFIG_MODELS: dict[str, type[BaseModel]] = {
    "openmetadata": OpenMetadataConfig,
    "greenplum": GreenplumConfig,
    "local_disk": LocalDiskConfig,
}


class ConnectionCreateIn(BaseModel):
    kind: ConnectionKind
    name: str
    config: dict


class ConnectionUpdateIn(BaseModel):
    name: str
    config: dict


class ConnectionOut(BaseModel):
    id: uuid.UUID
    kind: str
    name: str
    status: str
    last_checked_error: str | None


class ConnectionTestOut(BaseModel):
    status: str
    detail: str
