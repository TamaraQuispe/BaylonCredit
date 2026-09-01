from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_JWT_SECRET = "development-only-secret-change-before-production"


class Settings(BaseSettings):
    app_name: str = "BaylonCredit API"
    environment: Literal["development", "test", "staging", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://baylon:baylon@localhost:5432/bayloncredit"
    jwt_secret_key: str = DEVELOPMENT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        unsafe_production_secret = (
            self.environment in {"staging", "production"}
            and self.jwt_secret_key == DEVELOPMENT_JWT_SECRET
        )
        if unsafe_production_secret:
            raise ValueError("JWT_SECRET_KEY must be configured outside development")
        if self.access_token_expire_minutes <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than zero")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
