import uuid

import asyncpg
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_org_db, require_role
from app.models import DataSourceConnection
from app.schemas.connections import (
    CONFIG_MODELS,
    ConnectionCreateIn,
    ConnectionOut,
    ConnectionTestOut,
    ConnectionUpdateIn,
)
from app.services.secrets import DecryptionError, decrypt_config, encrypt_config

router = APIRouter(prefix="/connections", tags=["connections"])

_MUTATE_ROLES = ("org_admin", "engineer")


def _to_out(conn: DataSourceConnection) -> ConnectionOut:
    return ConnectionOut(
        id=conn.id,
        kind=conn.kind,
        name=conn.name,
        status=conn.status,
        last_checked_error=conn.last_checked_error,
    )


def _validate_config(kind: str, config: dict) -> dict:
    model = CONFIG_MODELS.get(kind)
    if model is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown connection kind: {kind!r}")
    try:
        return model(**config).model_dump()
    except ValidationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid config for {kind}: {exc}") from exc


async def _get_or_404(session: AsyncSession, connection_id: uuid.UUID) -> DataSourceConnection:
    result = await session.execute(
        select(DataSourceConnection).where(DataSourceConnection.id == connection_id)
    )
    conn = result.scalar_one_or_none()
    if conn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")
    return conn


@router.get("", response_model=list[ConnectionOut])
async def list_connections(session: AsyncSession = Depends(get_org_db)) -> list[ConnectionOut]:
    result = await session.execute(select(DataSourceConnection).order_by(DataSourceConnection.name))
    return [_to_out(c) for c in result.scalars().all()]


@router.post("", response_model=ConnectionOut, status_code=status.HTTP_201_CREATED)
async def create_connection(
    body: ConnectionCreateIn,
    principal=Depends(require_role(*_MUTATE_ROLES)),
    session: AsyncSession = Depends(get_org_db),
) -> ConnectionOut:
    validated = _validate_config(body.kind, body.config)
    conn = DataSourceConnection(
        org_id=principal.org_id,
        kind=body.kind,
        name=body.name,
        encrypted_config=encrypt_config(validated),
        status="pending",
    )
    session.add(conn)
    await session.commit()
    return _to_out(conn)


@router.put("/{connection_id}", response_model=ConnectionOut)
async def update_connection(
    connection_id: uuid.UUID,
    body: ConnectionUpdateIn,
    principal=Depends(require_role(*_MUTATE_ROLES)),
    session: AsyncSession = Depends(get_org_db),
) -> ConnectionOut:
    del principal
    conn = await _get_or_404(session, connection_id)
    validated = _validate_config(conn.kind, body.config)
    conn.name = body.name
    conn.encrypted_config = encrypt_config(validated)
    conn.status = "pending"
    conn.last_checked_error = None
    await session.commit()
    return _to_out(conn)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: uuid.UUID,
    principal=Depends(require_role(*_MUTATE_ROLES)),
    session: AsyncSession = Depends(get_org_db),
) -> None:
    del principal
    conn = await _get_or_404(session, connection_id)
    await session.delete(conn)
    await session.commit()


@router.post("/{connection_id}/test", response_model=ConnectionTestOut)
async def test_connection(
    connection_id: uuid.UUID,
    principal=Depends(require_role(*_MUTATE_ROLES)),
    session: AsyncSession = Depends(get_org_db),
) -> ConnectionTestOut:
    del principal
    conn = await _get_or_404(session, connection_id)
    try:
        config = decrypt_config(conn.encrypted_config)
    except DecryptionError as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc

    test_fn = _TEST_FUNCS.get(conn.kind)
    if test_fn is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"No test available for kind {conn.kind!r}")

    result = await test_fn(config)
    conn.status = result.status
    conn.last_checked_error = None if result.status == "connected" else result.detail
    await session.commit()
    return result


async def _test_openmetadata(config: dict) -> ConnectionTestOut:
    host = config["host_url"].rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{host}/api/v1/system/version",
                headers={"Authorization": f"Bearer {config['api_token']}"},
            )
    except httpx.HTTPError as exc:
        return ConnectionTestOut(status="error", detail=f"Could not reach OpenMetadata: {exc}")

    if resp.status_code == 200:
        version = resp.json().get("version", "unknown")
        return ConnectionTestOut(status="connected", detail=f"OpenMetadata reachable (version {version})")
    return ConnectionTestOut(status="error", detail=f"OpenMetadata returned HTTP {resp.status_code}")


async def _test_greenplum(config: dict) -> ConnectionTestOut:
    ssl = False if config.get("sslmode") == "disable" else None
    try:
        conn = await asyncpg.connect(
            host=config["host"],
            port=config.get("port", 5432),
            database=config["database"],
            user=config["username"],
            password=config["password"],
            ssl=ssl,
            timeout=5,
        )
    except (OSError, asyncpg.PostgresError) as exc:
        return ConnectionTestOut(status="error", detail=str(exc))

    try:
        await conn.execute("SELECT 1")
    finally:
        await conn.close()
    return ConnectionTestOut(status="connected", detail="Connected and ran SELECT 1")


async def _test_local_disk(config: dict) -> ConnectionTestOut:
    import os

    path = config["path"]
    if not os.path.isdir(path):
        return ConnectionTestOut(status="error", detail=f"Path does not exist or is not a directory: {path}")
    if not os.access(path, os.R_OK):
        return ConnectionTestOut(status="error", detail=f"Path exists but is not readable: {path}")
    return ConnectionTestOut(status="connected", detail=f"Directory is readable: {path}")


_TEST_FUNCS = {
    "openmetadata": _test_openmetadata,
    "greenplum": _test_greenplum,
    "local_disk": _test_local_disk,
}
