from fastapi import APIRouter

from baseproject.api.v1.auth import router as auth_router
from baseproject.api.v1.health import router as health_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
