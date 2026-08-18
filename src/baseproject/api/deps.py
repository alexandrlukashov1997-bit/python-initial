from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from baseproject.core.exceptions import Unauthorized
from baseproject.core.security import decode_access_token
from baseproject.db.session import async_session_maker
from baseproject.models.user import User
from baseproject.services import auth as auth_service

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    creds: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise Unauthorized("Not authenticated")
    try:
        user_id = UUID(decode_access_token(creds.credentials))
    except ValueError as exc:
        raise Unauthorized("Invalid token") from exc
    return await auth_service.get_me(db, user_id)


CurrentUser = Annotated[User, Depends(get_current_user)]
