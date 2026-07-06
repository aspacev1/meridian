import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Root declarative base. Used directly by Organization/User, which are
    not themselves tenant-scoped rows (Organization *is* the tenant; a User
    can belong to more than one Organization via Membership).
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TenantBase(Base):
    """Base for every table that belongs to a single organization.

    Every subclass gets an org_id column. The Alembic migration adds a
    Postgres Row-Level Security policy on each of these tables scoped to
    `current_setting('app.current_org_id')`, so cross-tenant leakage is
    enforced at the database layer, not just in application code.
    """

    __abstract__ = True

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
