from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from baseproject.core.config import settings
from baseproject.core.exceptions import Unauthorized

ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()

_dummy_hash: str | None = None


def hash_password(plain: str) -> str:
    return password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(plain, hashed)


def dummy_password_hash() -> str:
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password("__dummy_password__")
    return _dummy_hash


def create_access_token(subject: str | UUID) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise Unauthorized("Invalid token") from exc
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise Unauthorized("Invalid token")
    return subject
