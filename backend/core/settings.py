"""Single source of truth for all configuration. Values from env vars / .env file."""

from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # App
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_DEBUG: bool = False
    APP_SECRET_KEY: str

    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_BOT_USERNAME: str = ""
    TELEGRAM_WEBHOOK_SECRET: str
    TELEGRAM_WEBHOOK_URL: str
    # URL the Mini App is served from — used in push notifications' inline
    # "Открыть в приложении" button (web_app field). Must be HTTPS and
    # configured as the bot's WebApp URL in @BotFather.
    TELEGRAM_WEBAPP_URL: str = "https://astro-tma.vercel.app/"

    # Support bot — a separate Telegram bot used for user questions.
    # Empty token disables the feature (webhook returns 404). When set,
    # incoming user messages are forwarded to SUPPORT_GROUP_CHAT_ID; admin
    # replies in that group (using Telegram's native Reply to forwarded
    # message) are routed back to the original user.
    SUPPORT_BOT_TOKEN: str = ""
    SUPPORT_BOT_USERNAME: str = ""
    SUPPORT_GROUP_CHAT_ID: int = 0
    SUPPORT_WEBHOOK_SECRET: str = ""

    # YuKassa — Russian card-payment gateway. Empty SHOP_ID disables the
    # card-payment flow; the PaymentSheet button on the frontend will
    # fall back to a "Скоро" alert (see paymentsApi.createYukassaInvoice).
    YUKASSA_SHOP_ID: str = ""
    YUKASSA_SECRET_KEY: str = ""
    # User-facing return URL after the YuKassa hosted-payment page.
    # Deep-links back into the Telegram Mini App.
    YUKASSA_RETURN_URL: str = "https://t.me/astrologiyatut_bot/app"
    # Fiscal-receipt defaults (54-ФЗ compliance). YuKassa rejects
    # live-mode payments without a receipt object that names a customer
    # (email or phone) and at least one line-item. Until we collect the
    # buyer's email in the PaymentSheet UI we send fiscal receipts to
    # the shop owner's address — fully legal, the customer can still
    # request a copy via support.
    YUKASSA_RECEIPT_DEFAULT_EMAIL: str = ""
    # VAT code per the YuKassa receipt schema. 1 = no VAT (simplest;
    # correct for most individual entrepreneurs and УСН-merchants).
    YUKASSA_RECEIPT_VAT_CODE: int = 1

    # Push scheduling
    PUSH_DAILY_HOUR: int = 9

    # Database
    DATABASE_URL: PostgresDsn
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: RedisDsn = "redis://localhost:6379/0"  # type: ignore[assignment]

    # Natal-PDF queue + provider-neutral LLM limits
    LLM_OUTPUT_TPM: int = 100000
    LLM_CONCURRENCY: int = 6
    LLM_TIMEOUT_SECONDS: float = 120.0
    ARQ_MAX_JOBS: int = 10  # jobs a single worker pulls at once
    ARQ_JOB_TIMEOUT: int = 600  # seconds; free-tier generation can be slow

    # Cache TTLs (seconds)
    CACHE_TTL_HOROSCOPE: int = 86400  # 24h
    CACHE_TTL_MOON: int = 3600  # 1h
    CACHE_TTL_NATAL: int = 604800  # 7d — natal never changes
    CACHE_TTL_TAROT_INTERPRET: int = 2592000  # 30d — readings are immutable

    # Admin panel — no defaults. If these are missing from .env, Pydantic
    # fails loudly at startup instead of booting with weak well-known creds
    # (SECURITY_AUDIT.md C2).
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str

    # OpenAI-compatible LLM provider. Switching provider requires only env changes.
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com"
    LLM_MODEL: str = "deepseek-v4-flash"

    # GeoNames
    GEONAMES_USERNAME: str = "demo"

    # Stars pricing — boot defaults match the launch monetization spec.
    # Production prices live in .env / admin Redis overrides.
    PRICE_TAROT_CELTIC: int = 29  # retired SKU, kept for back-compat
    PRICE_NATAL_FULL: int = 149
    PRICE_SYNASTRY: int = 79  # bumped from 49 (see UNIT_ECONOMICS.md §6)
    PRICE_DESTINY_MATRIX_FULL: int = 150
    PRICE_SUBSCRIPTION_MONTH: int = 199
    PRICE_SUBSCRIPTION_YEAR: int = 1490

    # Ruble pricing (whole rubles). Displayed alongside the Stars price
    # as a second payment option; YuKassa flow is not wired yet — the
    # frontend currently shows an "Скоро" alert on click. Bootstrap
    # defaults are ~3.3× the Stars price (rough RU market parity at
    # launch). Override in .env and via the admin /products endpoint
    # (Redis cache, applies live).
    PRICE_NATAL_FULL_RUB: int = 490
    PRICE_SYNASTRY_RUB: int = 290
    PRICE_DESTINY_MATRIX_FULL_RUB: int = 490
    PRICE_SUBSCRIPTION_MONTH_RUB: int = 650
    PRICE_SUBSCRIPTION_YEAR_RUB: int = 4900

    # Referrals still record who-invited-whom for the stats panel, but
    # without any trial-day rewards. Kept as a flag in case the share
    # feature itself needs to be turned off.
    FEATURE_REFERRAL_PROGRAM: bool = True

    # URL of the bot WebApp deeplink (e.g. "https://t.me/<bot>/app").
    # Used in referrer-reward Telegram notifications.
    MINIAPP_URL: str = ""

    # Feature flags
    FEATURE_PUSH_NOTIFICATIONS: bool = True
    FEATURE_SYNASTRY: bool = True

    # Dev-only: skip Telegram initData verification and inject a mock user.
    # Never honored in production.
    AUTH_BYPASS: bool = False
    AUTH_BYPASS_USER_ID: int = 777777777
    AUTH_BYPASS_FIRST_NAME: str = "Dev"

    @field_validator("APP_SECRET_KEY")
    @classmethod
    def secret_key_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("APP_SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("TELEGRAM_WEBHOOK_SECRET")
    @classmethod
    def webhook_secret_strength(cls, v: str) -> str:
        """SECURITY_AUDIT.md C3 — an empty TELEGRAM_WEBHOOK_SECRET turns the
        payments webhook into an open endpoint (anyone can POST a fake
        successful_payment). Require at least 16 chars of entropy."""
        if not v or len(v) < 16:
            raise ValueError("TELEGRAM_WEBHOOK_SECRET must be set and at least 16 chars long")
        return v

    @field_validator("ADMIN_PASSWORD")
    @classmethod
    def admin_password_strength(cls, v: str) -> str:
        """SECURITY_AUDIT.md C2 — reject the historic 'changeme' default and
        any obviously short password, even when read from .env."""
        if not v or len(v) < 12 or v.lower() in {"changeme", "admin", "password"}:
            raise ValueError("ADMIN_PASSWORD is missing or too weak — set ≥12 random chars")
        return v

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
