from fastapi import APIRouter, status

from baseproject.api.deps import CurrentUser, DbSession
from baseproject.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from baseproject.schemas.user import UserPublic
from baseproject.services import auth as auth_service

router = APIRouter()


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
