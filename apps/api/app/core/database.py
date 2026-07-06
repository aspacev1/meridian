from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def org_scoped_session(org_id: str | None) -> AsyncGenerator[AsyncSession, None]:
    """Yield a session with app.current_org_id set for the duration of the
    transaction, so Postgres row-level security policies scope every query
    to the caller's organization. org_id=None is used for org-less
    operations (e.g. signup, before an Organization row exists).
    """
    async with async_session_factory() as session:
        if org_id is not None:
            await session.execute(
                text("SELECT set_config('app.current_org_id', :org_id, true)"), {"org_id": org_id}
            )
        yield session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for endpoints that set org scope themselves
    (e.g. via app.api.deps.get_db) rather than needing it pre-set here.
    """
    async with async_session_factory() as session:
        yield session
