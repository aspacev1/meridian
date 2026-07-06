import uuid

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase


class Domain(TenantBase):
    """Business domain grouping marts and reports, e.g. 'Credit Risk'."""

    __tablename__ = "domains"
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_domain_org_name"),)

    name: Mapped[str] = mapped_column(String(100))
    icon: Mapped[str] = mapped_column(String(10), default="")
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )


class DataMart(TenantBase):
    """Top-level pipeline unit. Maps to a schema in the tenant's warehouse."""

    __tablename__ = "data_marts"
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_mart_org_name"),)

    name: Mapped[str] = mapped_column(String(100))
    domain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("domains.id", ondelete="CASCADE"), index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Tenant's local currency; used for CFO executive-view exposure figures
    cost_per_hour: Mapped[float | None] = mapped_column(Numeric(12, 2), default=None)
