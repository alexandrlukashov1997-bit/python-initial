from fastapi import APIRouter, status

from baseproject.api.deps import CurrentUser, DbSession, EmailSenderDep
from baseproject.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from baseproject.schemas.user import UserPublic
from baseproject.services import auth as auth_service

router = APIRouter()

_FORGOT_PASSWORD_DETAIL = (
    "If an account exists for this email, a reset link has been sent."
)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(body: RegisterRequest, db: DbSession) -> TokenResponse:
    return await auth_service.register(db, body)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbSession) -> TokenResponse:
    return await auth_service.authenticate(db, body)


@router.get("/me", response_model=UserPublic)
async def read_me(current_user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: DbSession,
    email_sender: EmailSenderDep,
) -> dict[str, str]:
    await auth_service.forgot_password(db, body, email_sender)
    return {"detail": _FORGOT_PASSWORD_DETAIL}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(body: ResetPasswordRequest, db: DbSession) -> None:
    await auth_service.reset_password(db, body)
