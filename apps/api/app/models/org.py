import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantBase


class Organization(Base):
    """A tenant. Not itself org-scoped -- it *is* the scope."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    workos_organization_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Billing (Phase 5 fleshes this out; placeholders so the column exists now)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100))
    subscription_status: Mapped[str] = mapped_column(String(20), default="trialing")


class Membership(TenantBase):
    """A User's role within one Organization. A User row is global (one
    WorkOS identity); Membership is the tenant-scoped join.
    """

    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("org_id", "user_id", name="uq_membership_org_user"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(50), default="steward")
    # role: steward | data_owner | engineer | admin | org_admin
