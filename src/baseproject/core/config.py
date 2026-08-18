import json
from typing import Annotated

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _parse_cors_origins(value: object) -> object:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("["):
            return json.loads(stripped)
        return [item.strip() for item in stripped.split(",") if item.strip()]
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg://baseproject:baseproject@localhost:5432/baseproject"
    )
    jwt_secret: str = Field(
        default="change-me-to-a-long-random-string",
        min_length=16,
    )
    jwt_expire_minutes: int = 30
    cors_origins: Annotated[
        list[str],
        NoDecode,
        BeforeValidator(_parse_cors_origins),
    ] = [
        "http://localhost:4200",
    ]
    mail_from: str = "noreply@localhost"
    frontend_url: str = "http://localhost:4200/reset-password"
    password_reset_expire_minutes: int = 60

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


settings = Settings()
