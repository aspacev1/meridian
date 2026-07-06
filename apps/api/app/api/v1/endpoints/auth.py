from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from workos import WorkOSClient

from app.api.deps import get_unscoped_db, get_current_user
from app.core.config import settings
from app.models import Membership, Organization, User
from app.schemas.auth import MeOut, MembershipOut

router = APIRouter(prefix="/auth", tags=["auth"])

_workos = WorkOSClient(api_key=settings.workos_api_key, client_id=settings.workos_client_id)


def _initials(first_name: str | None, last_name: str | None, email: str) -> str:
    if first_name and last_name:
        return (first_name[0] + last_name[0]).upper()
    if first_name:
        return first_name[:2].upper()
    return email[:2].upper()


@router.get("/callback")
async def auth_callback(code: str, session: AsyncSession = Depends(get_unscoped_db)) -> dict:
    """WorkOS AuthKit redirects here with a one-time `code` after login/SSO.
    Exchanges it for tokens, upserts the local User row keyed on the stable
    WorkOS user id, and hands the tokens back for the frontend to store.
    """
    try:
        auth_response = _workos.user_management.authenticate_with_code(code=code)
    except Exception as exc:  # noqa: BLE001 -- WorkOS SDK raises its own exception types
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"WorkOS auth failed: {exc}") from exc

    profile = auth_response.user
    result = await session.execute(select(User).where(User.workos_user_id == profile.id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            workos_user_id=profile.id,
            email=profile.email,
            full_name=f"{profile.first_name or ''} {profile.last_name or ''}".strip()
            or profile.email,
            avatar_initials=_initials(profile.first_name, profile.last_name, profile.email),
        )
        session.add(user)
    else:
        user.email = profile.email

    await session.commit()

    return {
        "access_token": auth_response.access_token,
        "refresh_token": auth_response.refresh_token,
    }


@router.get("/me", response_model=MeOut)
async def me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_unscoped_db),
) -> MeOut:
    result = await session.execute(
        select(Membership, Organization)
        .join(Organization, Membership.org_id == Organization.id)
        .where(Membership.user_id == user.id)
    )
    memberships = [
        MembershipOut(org_id=m.org_id, org_name=o.name, org_slug=o.slug, role=m.role)
        for m, o in result.all()
    ]
    return MeOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_initials=user.avatar_initials,
        memberships=memberships,
    )
