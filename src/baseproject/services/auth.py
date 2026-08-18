import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from baseproject.core.config import settings
from baseproject.core.email import EmailSender
from baseproject.core.exceptions import BadRequest, Conflict, Unauthorized
from baseproject.core.security import (
    create_access_token,
    dummy_password_hash,
    hash_password,
    hash_reset_token,
    verify_password,
)
from baseproject.models.password_reset_token import PasswordResetToken
from baseproject.models.user import User, UserRole
from baseproject.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)

_RESET_TOKEN_INVALID = "Invalid or expired reset token"


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
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        role=UserRole.CLIENT,
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


async def forgot_password(
    db: AsyncSession,
    data: ForgotPasswordRequest,
    email_sender: EmailSender,
) -> None:
    email = str(data.email).lower()
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active:
        return

    raw_token = secrets.token_urlsafe(32)
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_reset_token(raw_token),
        expires_at=datetime.now(UTC)
        + timedelta(minutes=settings.password_reset_expire_minutes),
    )
    db.add(reset)
    await db.flush()

    link = f"{settings.frontend_url}?token={raw_token}"
    await email_sender.send(
        to=user.email,
        subject="Password reset",
        text=(
            "Use this link to reset your password:\n"
            f"{link}\n\n"
            "If you did not request a reset, you can ignore this email."
        ),
    )


async def reset_password(db: AsyncSession, data: ResetPasswordRequest) -> None:
    token_hash = hash_reset_token(data.token)
    reset = await db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    now = datetime.now(UTC)
    if reset is None or reset.used_at is not None or reset.expires_at <= now:
        raise BadRequest(_RESET_TOKEN_INVALID)

    user = await db.get(User, reset.user_id)
    if user is None or not user.is_active:
        raise BadRequest(_RESET_TOKEN_INVALID)

    user.hashed_password = hash_password(data.new_password)
    reset.used_at = now
    await db.execute(
        delete(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.id != reset.id,
        )
    )
