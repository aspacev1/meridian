"""Seed a demo organization with reference data.

Unlike the single-bank prototype's seed data, this is parameterized per-org
so onboarding a new tenant (or spinning up a demo/sandbox org) doesn't
require hardcoding a schema for one customer.

Usage:
    python -m scripts.seed --org-name "Acme Bank" --org-slug acme-bank \
        --admin-email admin@acme.example --admin-name "Ada Lovelace"
"""

import argparse
import asyncio
import uuid
from datetime import time

from sqlalchemy import select, text

from app.core.database import async_session_factory
from app.models import DataMart, Domain, Membership, Organization, SLAConfig, User

DEFAULT_DOMAINS = [
    ("Credit Risk", "\U0001f4b3"),
    ("Market Risk", "\U0001f4c8"),
    ("Treasury", "\U0001f3e6"),
    ("Compliance", "\U0001f4cb"),
    ("Retail Banking", "\U0001f3e7"),
]

DEFAULT_MARTS = ["dm_credit", "dm_market"]

DEFAULT_SLA_TARGETS = [
    ("source", time(2, 0)),
    ("staging", time(3, 0)),
    ("ods", time(4, 0)),
    ("dm", time(5, 30)),
]


async def seed(org_name: str, org_slug: str, admin_email: str, admin_name: str) -> None:
    async with async_session_factory() as session:
        result = await session.execute(select(Organization).where(Organization.slug == org_slug))
        org = result.scalar_one_or_none()
        if org is None:
            org = Organization(name=org_name, slug=org_slug)
            session.add(org)
            await session.flush()

        await session.execute(
            text("SELECT set_config('app.current_org_id', :org_id, true)"), {"org_id": str(org.id)}
        )

        result = await session.execute(select(User).where(User.email == admin_email))
        user = result.scalar_one_or_none()
        if user is None:
            initials = "".join(p[0] for p in admin_name.split()[:2]).upper() or "AD"
            user = User(
                workos_user_id=f"seed_{uuid.uuid4()}",
                email=admin_email,
                full_name=admin_name,
                avatar_initials=initials,
            )
            session.add(user)
            await session.flush()

        result = await session.execute(
            select(Membership).where(Membership.org_id == org.id, Membership.user_id == user.id)
        )
        if result.scalar_one_or_none() is None:
            session.add(Membership(org_id=org.id, user_id=user.id, role="org_admin"))

        domains_by_name = {}
        for name, icon in DEFAULT_DOMAINS:
            result = await session.execute(
                select(Domain).where(Domain.org_id == org.id, Domain.name == name)
            )
            domain = result.scalar_one_or_none()
            if domain is None:
                domain = Domain(org_id=org.id, name=name, icon=icon, owner_id=user.id)
                session.add(domain)
                await session.flush()
            domains_by_name[name] = domain

        credit_domain = domains_by_name["Credit Risk"]
        market_domain = domains_by_name["Market Risk"]
        mart_domains = {"dm_credit": credit_domain, "dm_market": market_domain}

        for mart_name in DEFAULT_MARTS:
            result = await session.execute(
                select(DataMart).where(DataMart.org_id == org.id, DataMart.name == mart_name)
            )
            mart = result.scalar_one_or_none()
            if mart is None:
                mart = DataMart(
                    org_id=org.id,
                    name=mart_name,
                    domain_id=mart_domains[mart_name].id,
                )
                session.add(mart)
                await session.flush()

            for layer, target_time in DEFAULT_SLA_TARGETS:
                result = await session.execute(
                    select(SLAConfig).where(
                        SLAConfig.mart_id == mart.id, SLAConfig.layer == layer
                    )
                )
                if result.scalar_one_or_none() is None:
                    session.add(
                        SLAConfig(
                            org_id=org.id,
                            mart_id=mart.id,
                            layer=layer,
                            target_time=target_time,
                        )
                    )

        await session.commit()
        print(f"Seeded organization '{org.name}' ({org.slug}), admin={admin_email}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org-name", required=True)
    parser.add_argument("--org-slug", required=True)
    parser.add_argument("--admin-email", required=True)
    parser.add_argument("--admin-name", required=True)
    args = parser.parse_args()
    asyncio.run(seed(args.org_name, args.org_slug, args.admin_email, args.admin_name))


if __name__ == "__main__":
    main()
