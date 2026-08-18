import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from baseproject.api.v1 import api_router
from baseproject.core.config import settings
from baseproject.core.exceptions import AppError
from baseproject.db.session import engine


def configure_logging() -> None:
    package_logger = logging.getLogger("baseproject")
    package_logger.setLevel(logging.INFO)
    if not package_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(levelname)s:     %(message)s"))
        package_logger.addHandler(handler)
    package_logger.propagate = False


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    configure_logging()
    application = FastAPI(title="BaseProject", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_exception_handler(AppError, app_error_handler)
    application.include_router(api_router)
    return application


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
        headers=headers,
    )


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run(
        "baseproject.main:app",
        host="127.0.0.1",
        port=8000,
        loop="baseproject.core.asyncio_loop:selector_event_loop",
    )
