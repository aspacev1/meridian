from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """A global identity (backed by a WorkOS user). Scoped to organizations
    only through Membership rows -- a user can belong to more than one org.
    """

    __tablename__ = "users"

    workos_user_id: Mapped[str] = mapped_column(String(100), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(255))
    avatar_initials: Mapped[str] = mapped_column(String(4), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
