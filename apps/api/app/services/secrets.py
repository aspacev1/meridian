"""Encrypts connection config (Greenplum passwords, OpenMetadata tokens,
etc.) before it touches the database.

Interim implementation: a single symmetric Fernet key from settings
(SECRETS_ENCRYPTION_KEY), not per-tenant envelope encryption via a real KMS.
Swapping to KMS later means replacing `_fernet()` with a call that
decrypts a per-org data key from KMS and constructing Fernet(that key) --
the encrypt_config/decrypt_config call sites and the DB column don't change.
"""

import json
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class SecretsNotConfiguredError(Exception):
    pass


class DecryptionError(Exception):
    pass


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    if not settings.secrets_encryption_key:
        raise SecretsNotConfiguredError(
            "SECRETS_ENCRYPTION_KEY is not set -- generate one with "
            "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"`"
        )
    return Fernet(settings.secrets_encryption_key.encode())


def encrypt_config(config: dict) -> str:
    payload = json.dumps(config, separators=(",", ":")).encode()
    return _fernet().encrypt(payload).decode()


def decrypt_config(encrypted: str) -> dict:
    try:
        payload = _fernet().decrypt(encrypted.encode())
    except InvalidToken as exc:
        raise DecryptionError("Stored config could not be decrypted") from exc
    return json.loads(payload)
