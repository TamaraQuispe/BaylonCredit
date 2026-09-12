from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_JWT_SECRET = "development-only-secret-change-before-production"


class Settings(BaseSettings):
    app_name: str = "Credify API"
    environment: Literal["development", "test", "staging", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://credify:credify@localhost:5432/credify"
    jwt_secret_key: str = DEVELOPMENT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    login_attempt_limit: int = 5
    login_attempt_window_minutes: int = 15
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    webauthn_rp_id: str = "localhost"
    webauthn_origin: str = "http://localhost:5173"
    webauthn_rp_name: str = "Credify"
    whatsapp_enabled: bool = False
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_api_version: str = "v21.0"
    whatsapp_graph_base_url: str = "https://graph.facebook.com"
    whatsapp_default_country_code: str = "51"
    whatsapp_timeout_seconds: float = 15.0
    whatsapp_notify_evaluations: bool = False
    whatsapp_notify_reminders: bool = False
    whatsapp_notify_payments: bool = False
    whatsapp_reminder_interval_hours: int = 24
    whatsapp_reminder_days_before: int = 3
    whatsapp_template_evaluation: str = "credit_evaluation_result"
    whatsapp_template_reminder: str = "credit_payment_reminder"
    whatsapp_template_payment_confirmation: str = "credit_payment_confirmation"
    openrouter_enabled: bool = False
    openrouter_api_key: str = ""
    openrouter_model: str = "nvidia/nemotron-3-super-120b-a12b:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: str = "https://credifycredit.duckdns.org"
    openrouter_app_name: str = "Credifycredit"
    openrouter_timeout_seconds: float = 10.0

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
        if self.refresh_token_expire_days <= 0:
            raise ValueError("REFRESH_TOKEN_EXPIRE_DAYS must be greater than zero")
        if self.whatsapp_reminder_days_before < 0:
            raise ValueError("WHATSAPP_REMINDER_DAYS_BEFORE cannot be negative")
        if self.whatsapp_reminder_interval_hours < 1:
            raise ValueError("WHATSAPP_REMINDER_INTERVAL_HOURS must be greater than zero")
        if self.openrouter_enabled and not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is required when OpenRouter is enabled")
        if self.openrouter_timeout_seconds <= 0:
            raise ValueError("OPENROUTER_TIMEOUT_SECONDS must be greater than zero")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
