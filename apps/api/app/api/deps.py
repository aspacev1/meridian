import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.security import InvalidTokenError, TokenClaims, verify_access_token
from app.models import Membership, Organization, User


async def get_bearer_claims(
    authorization: str | None = Header(default=None),
) -> TokenClaims:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        return verify_access_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}") from exc


async def get_unscoped_db() -> AsyncGenerator[AsyncSession, None]:
    """Unscoped session -- only for looking up the user's own memberships
    before an org has been selected. Never used for tenant data reads.
    """
    async with async_session_factory() as session:
        yield session


async def get_current_user(
    claims: TokenClaims = Depends(get_bearer_claims),
    session: AsyncSession = Depends(get_unscoped_db),
) -> User:
    result = await session.execute(
        select(User).where(User.workos_user_id == claims.user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No Meridian account for this identity yet -- complete signup first",
        )
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")
    return user


@dataclass(frozen=True)
class CurrentPrincipal:
    user: User
    org_id: uuid.UUID
    role: str


async def get_current_principal(
    x_org_id: uuid.UUID = Header(..., alias="X-Org-Id"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_unscoped_db),
) -> CurrentPrincipal:
    """Resolves the caller's role in the requested org. Rejects the request
    if the user has no Membership there -- this check happens *before* RLS
    scoping even applies, so it's the first line of tenant isolation.
    """
    result = await session.execute(
        select(Membership).where(
            Membership.org_id == x_org_id, Membership.user_id == user.id
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this organization")
    return CurrentPrincipal(user=user, org_id=x_org_id, role=membership.role)


async def get_org_db(
    principal: CurrentPrincipal = Depends(get_current_principal),
) -> AsyncGenerator[AsyncSession, None]:
    """The dependency every tenant-data endpoint should use. Sets
    app.current_org_id for the transaction so RLS policies apply, on top
    of the application-level membership check in get_current_principal.
    """
    async with async_session_factory() as session:
        await session.execute(
            text("SELECT set_config('app.current_org_id', :org_id, true)"),
            {"org_id": str(principal.org_id)},
        )
        yield session


def require_role(*allowed: str):
    """Usage: Depends(require_role("admin", "org_admin"))"""

    def _check(
        principal: CurrentPrincipal = Depends(get_current_principal),
    ) -> CurrentPrincipal:
        if principal.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role for this action")
        return principal

    return _check
