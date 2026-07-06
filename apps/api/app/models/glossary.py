import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase


class GlossaryEntry(TenantBase):
    """Business glossary definition for a table column."""

    __tablename__ = "glossary_entries"
    __table_args__ = (
        UniqueConstraint("org_id", "table_name", "column_name", name="uq_glossary_org_col"),
    )

    table_name: Mapped[str] = mapped_column(String(300))
    column_name: Mapped[str] = mapped_column(String(200))
    biz_name: Mapped[str] = mapped_column(String(300), default="")
    definition: Mapped[str | None] = mapped_column(Text)
    calculation: Mapped[str | None] = mapped_column(Text)
    regulatory_refs: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    # status: draft | published
    is_ai_draft: Mapped[bool] = mapped_column(Boolean, default=False)
    edited_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    mart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_marts.id", ondelete="CASCADE"), index=True
    )
