import uuid

from pydantic import BaseModel


class MembershipOut(BaseModel):
    org_id: uuid.UUID
    org_name: str
    org_slug: str
    role: str


class MeOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    avatar_initials: str
    memberships: list[MembershipOut]


class CreateOrganizationIn(BaseModel):
    name: str
    slug: str


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    subscription_status: str
