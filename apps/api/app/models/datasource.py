from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase


class DataSourceConnection(TenantBase):
    """A tenant's connection to their own warehouse / metadata store.

    Credentials are stored as an opaque, already-encrypted blob
    (`encrypted_config`) -- encryption/decryption happens in
    app/services/secrets.py via a KMS-backed envelope key, never in this
    model or in plaintext at rest.
    """

    __tablename__ = "data_source_connections"

    kind: Mapped[str] = mapped_column(String(30))
    # kind: greenplum | postgres | openmetadata | s3_dropfolder | sftp | webhook
    name: Mapped[str] = mapped_column(String(200))
    encrypted_config: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # status: pending | connected | error
    last_checked_error: Mapped[str | None] = mapped_column(Text)
