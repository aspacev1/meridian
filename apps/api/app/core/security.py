"""JWT verification for WorkOS AuthKit access tokens.

WorkOS AuthKit issues short-lived JWT access tokens signed with the org's
JWKS, obtainable at https://api.workos.com/sso/jwks/{client_id}. We verify
signature + expiry here and hand back the claims; app.api.deps turns those
into the current User/Organization for a request.
"""

from dataclasses import dataclass
from functools import lru_cache

import jwt
from jwt import PyJWKClient

from app.core.config import settings


class InvalidTokenError(Exception):
    pass


@dataclass(frozen=True)
class TokenClaims:
    user_id: str
    email: str
    org_id: str | None
    role: str | None


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    jwks_url = f"https://api.workos.com/sso/jwks/{settings.workos_client_id}"
    return PyJWKClient(jwks_url)


def verify_access_token(token: str) -> TokenClaims:
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    return TokenClaims(
        user_id=payload["sub"],
        email=payload.get("email", ""),
        org_id=payload.get("org_id"),
        role=payload.get("role"),
    )
