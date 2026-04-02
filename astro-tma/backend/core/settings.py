"""Single source of truth for all configuration. Values from env vars / .env file."""
from functools import lru_cache
from typing import Literal
from pydantic import PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    # App
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_DEBUG: bool = False
    APP_SECRET_KEY: str

    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_WEBHOOK_SECRET: str
    TELEGRAM_WEBHOOK_URL: str

    # Database
    DATABASE_URL: PostgresDsn
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: RedisDsn = "redis://localhost:6379/0"  # type: ignore[assignment]

    # Cache TTLs (seconds)
    CACHE_TTL_HOROSCOPE: int = 86400    # 24h
    CACHE_TTL_MOON: int = 3600          # 1h
    CACHE_TTL_NATAL: int = 604800       # 7d — natal never changes
    CACHE_TTL_COMPATIBILITY: int = 86400

    # GeoNames
    GEONAMES_USERNAME: str = "demo"

    # Stars pricing
    PRICE_HOROSCOPE_TOMORROW: int = 25
    PRICE_HOROSCOPE_WEEK: int = 50
    PRICE_HOROSCOPE_MONTH: int = 75
    PRICE_TAROT_CELTIC: int = 30
    PRICE_TAROT_WEEK: int = 40
    PRICE_NATAL_FULL: int = 150
    PRICE_SYNASTRY: int = 100
    PRICE_SUBSCRIPTION_MONTH: int = 299
    PRICE_SUBSCRIPTION_YEAR: int = 1990

    # Feature flags
    FEATURE_PUSH_NOTIFICATIONS: bool = True
    FEATURE_SYNASTRY: bool = True

    @field_validator("APP_SECRET_KEY")
    @classmethod
    def secret_key_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("APP_SECRET_KEY must be at least 32 characters")
        return v

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

settings = get_settings()
