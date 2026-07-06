from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_unscoped_db
from app.models import Membership, Organization, User
from app.schemas.auth import CreateOrganizationIn, OrganizationOut

router = APIRouter(prefix="/orgs", tags=["orgs"])


@router.post("", response_model=OrganizationOut)
async def create_organization(
    body: CreateOrganizationIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_unscoped_db),
) -> OrganizationOut:
    """Creates a new tenant and makes the calling user its first org_admin.

    This is the one place that legitimately writes a Membership row before
    an org context exists. org.id is generated client-side (uuid4 default)
    before flush, so we can set app.current_org_id to it immediately and
    satisfy the RLS WITH CHECK policy on `memberships` within the same
    transaction, instead of needing a superuser bypass.
    """
    org = Organization(name=body.name, slug=body.slug)
    session.add(org)
    await session.flush()

    await session.execute(
        text("SELECT set_config('app.current_org_id', :org_id, true)"), {"org_id": str(org.id)}
    )
    session.add(Membership(org_id=org.id, user_id=user.id, role="org_admin"))
    await session.commit()

    return OrganizationOut(
        id=org.id,
        name=org.name,
        slug=org.slug,
        subscription_status=org.subscription_status,
    )
