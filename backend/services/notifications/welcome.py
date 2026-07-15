"""Mini App entry card for private messages to the main Telegram bot."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import httpx

from core.logging import get_logger
from core.settings import settings

log = get_logger(__name__)

WELCOME_BUTTON_LABEL = "✨ Открыть Astro"
WELCOME_TEXT = (
    "👋 <b>Добро пожаловать в Astro!</b>\n\n"
    "Натальная карта, гороскопы, Таро, Матрица судьбы "
    "и другие персональные разборы уже ждут вас.\n\n"
    "Нажмите кнопку ниже, чтобы начать 👇"
)


def build_welcome_markup() -> dict[str, Any] | None:
    webapp_url = (settings.TELEGRAM_WEBAPP_URL or "").strip()
    if not webapp_url:
        return None
    return {
        "inline_keyboard": [
            [
                {
                    "text": WELCOME_BUTTON_LABEL,
                    "web_app": {"url": webapp_url},
                }
            ]
        ]
    }


def build_welcome_photo_payload(chat_id: int) -> dict[str, Any] | None:
    """Build a Telegram photo card using the deployed Astro splash image."""
    webapp_url = (settings.TELEGRAM_WEBAPP_URL or "").strip()
    markup = build_welcome_markup()
    if not webapp_url or markup is None:
        return None
    return {
        "chat_id": chat_id,
        "photo": urljoin(f"{webapp_url.rstrip('/')}/", "/splash-bg.jpg"),
        "caption": WELCOME_TEXT,
        "parse_mode": "HTML",
        "reply_markup": markup,
    }


def build_welcome_text_payload(chat_id: int) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": WELCOME_TEXT,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if markup := build_welcome_markup():
        payload["reply_markup"] = markup
    return payload


async def _telegram_call(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}"
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.post(url, json=payload)
    return response.json()


async def send_welcome_card(chat_id: int) -> bool:
    """Send the branded card; use a text CTA when Telegram rejects the image."""
    try:
        photo_payload = build_welcome_photo_payload(chat_id)
        if photo_payload is not None:
            photo_result = await _telegram_call("sendPhoto", photo_payload)
            if photo_result.get("ok"):
                log.info("welcome.photo_sent", user_id=chat_id)
                return True
            log.warning(
                "welcome.photo_failed",
                user_id=chat_id,
                error=photo_result.get("description"),
            )

        text_result = await _telegram_call(
            "sendMessage",
            build_welcome_text_payload(chat_id),
        )
        if text_result.get("ok"):
            log.info("welcome.text_sent", user_id=chat_id)
            return True
        log.warning(
            "welcome.text_failed",
            user_id=chat_id,
            error=text_result.get("description"),
        )
    except Exception as exc:  # noqa: BLE001
        log.error("welcome.send_exception", user_id=chat_id, error=str(exc))
    return False
