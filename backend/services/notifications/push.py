"""Telegram Bot API push notifications."""

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from core.settings import settings
from db.models import (
    NotificationLog, NotificationStatus, NotificationType, User,
)

log = get_logger(__name__)


async def send_message(
    db: AsyncSession,
    user: User,
    text: str,
    type_: NotificationType = NotificationType.DAILY_HOROSCOPE,
    parse_mode: str = "HTML",
) -> bool:
    """
    Send a message via Telegram Bot API. Logs result to NotificationLog.
    On 403 (user blocked bot) → sets user.push_enabled=False.
    Returns True if sent successfully.
    """
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json={
                "chat_id": user.id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            })
        data = resp.json()
    except Exception as e:
        db.add(NotificationLog(
            user_id=user.id, type=type_,
            status=NotificationStatus.FAILED, error=str(e)[:500],
        ))
        await db.flush()
        log.error("push.network_error", user_id=user.id, error=str(e))
        return False

    if data.get("ok"):
        msg_id = data.get("result", {}).get("message_id")
        db.add(NotificationLog(
            user_id=user.id, type=type_,
            status=NotificationStatus.SENT, tg_message_id=msg_id,
        ))
        await db.flush()
        log.info("push.sent", user_id=user.id, message_id=msg_id)
        return True

    # Not ok
    err_code = data.get("error_code")
    description = data.get("description", "")
    if err_code == 403:
        user.push_enabled = False
        log.warning("push.blocked_by_user", user_id=user.id)

    db.add(NotificationLog(
        user_id=user.id, type=type_,
        status=NotificationStatus.FAILED,
        error=f"{err_code}: {description}"[:500],
    ))
    await db.flush()
    log.error("push.failed", user_id=user.id, code=err_code, description=description)
    return False


def build_daily_message(user: User, sign_ru: str, text_ru: str, energy: dict) -> str:
    """Compose a short daily horoscope push."""
    name = user.tg_first_name or "друг"
    # Clip to a short teaser — Telegram message limit is 4096, keep it snack-sized
    teaser = text_ru[:280] + ("…" if len(text_ru) > 280 else "")
    return (
        f"<b>Доброе утро, {name}!</b>\n"
        f"Ваш гороскоп на сегодня ({sign_ru}):\n\n"
        f"{teaser}\n\n"
        f"❤️ Любовь {energy.get('love', 50)}% · "
        f"💼 Карьера {energy.get('career', 50)}% · "
        f"🍀 Удача {energy.get('luck', 50)}%"
    )
