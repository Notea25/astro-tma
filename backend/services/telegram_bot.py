"""Shared helpers for resolving the Telegram bot identity at runtime.

Extracted from `api/routes/synastry.py` so the same fallback logic can
be reused by other invite-URL builders (referrals, share buttons, etc.)
without cross-route imports. Behaviour is unchanged.
"""

from __future__ import annotations

import httpx
from fastapi import HTTPException, status

from core.logging import get_logger
from core.settings import settings

log = get_logger(__name__)

_BOT_USERNAME_CACHE: str | None = None
_BOT_USERNAME_PLACEHOLDERS = {
    "",
    "astro_bot",
    "bot_username",
    "your_bot_username",
    "telegram_bot_username",
    "changeme",
}


def _clean_bot_username(value: str | None) -> str:
    return (value or "").strip().lstrip("@")


def _is_placeholder_bot_username(value: str) -> bool:
    return value.lower() in _BOT_USERNAME_PLACEHOLDERS


async def resolve_bot_username() -> str:
    """Return the bot's @username, preferring the ENV var but falling
    back to a live `getMe` call if the ENV value is missing or looks
    like a placeholder. Result is cached process-wide."""
    global _BOT_USERNAME_CACHE

    bot = (settings.TELEGRAM_BOT_USERNAME or "").strip().lstrip("@")
    if bot and not _is_placeholder_bot_username(bot):
        return bot

    if _BOT_USERNAME_CACHE:
        return _BOT_USERNAME_CACHE

    token = (settings.TELEGRAM_BOT_TOKEN or "").strip()
    if not token:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "TELEGRAM_BOT_TOKEN не настроен",
        )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            resp.raise_for_status()
            payload = resp.json()
    except httpx.HTTPError as e:
        log.warning("bot_username.resolve_failed", error=str(e))
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Не удалось определить Telegram bot username",
        ) from e

    resolved = _clean_bot_username(payload.get("result", {}).get("username"))
    if not resolved:
        log.warning("bot_username.missing", payload_ok=payload.get("ok"))
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Telegram bot username не найден",
        )

    _BOT_USERNAME_CACHE = resolved
    return resolved
