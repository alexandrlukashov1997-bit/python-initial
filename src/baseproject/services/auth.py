from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from baseproject.core.exceptions import Conflict, Unauthorized
from baseproject.core.security import (
    create_access_token,
    dummy_password_hash,
    hash_password,
    verify_password,
)
from baseproject.models.user import User, UserRole
from baseproject.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


def _token_for(user: User) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(user.id))


async def register(db: AsyncSession, data: RegisterRequest) -> TokenResponse:
    email = str(data.email).lower()
    existing = await db.scalar(select(User.id).where(User.email == email))
    if existing is not None:
        raise Conflict("Email already registered")

    user = User(
        email=email,
        hashed_password=hash_password(data.password),
        role=UserRole.USER,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise Conflict("Email already registered") from exc
    return _token_for(user)


async def authenticate(db: AsyncSession, data: LoginRequest) -> TokenResponse:
    email = str(data.email).lower()
    user = await db.scalar(select(User).where(User.email == email))
    hashed = user.hashed_password if user is not None else dummy_password_hash()
    password_ok = verify_password(data.password, hashed)
    if not password_ok or user is None or not user.is_active:
        raise Unauthorized("Invalid email or password")
    return _token_for(user)


async def get_me(db: AsyncSession, user_id: UUID) -> User:
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise Unauthorized("Invalid token")
    return user
