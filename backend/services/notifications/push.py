"""Telegram Bot API push notifications."""

import hashlib
from datetime import date

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from core.settings import settings
from db.models import (
    NotificationLog,
    NotificationStatus,
    NotificationType,
    User,
)

log = get_logger(__name__)

_MONTHS_RU = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)

_GREETINGS = (
    "Доброе утро, {name}.",
    "{name}, доброе утро.",
    "С новым утром, {name}.",
    "{name}, пусть утро начнется мягко.",
    "Доброе утро, {name}: сегодня важно услышать себя.",
    "{name}, утро уже подсказывает направление.",
)

_INTROS = (
    "Астрологический акцент на {day} для знака {sign}:",
    "Гороскоп для знака {sign} на {day}:",
    "Сегодняшний настрой для знака {sign} на {day}:",
    "Что стоит взять с собой в этот день: знак {sign}, {day}:",
    "Космическая заметка для знака {sign} на {day}:",
    "Главный тон дня для знака {sign} на {day}:",
)

_BRIDGES = (
    "Обратите внимание на главное:",
    "Коротко о том, как прожить день внимательнее:",
    "Вот что может стать полезным ориентиром:",
    "Сегодня лучше держать в фокусе это:",
    "Для более спокойного ритма дня:",
    "Пусть это будет вашей точкой опоры:",
)

_CLOSINGS = (
    "Пусть день сложится без лишней спешки.",
    "Берегите темп и выбирайте то, что действительно важно.",
    "Дайте себе немного пространства перед важными решениями.",
    "Пусть сегодня будет больше ясности, чем шума.",
    "Сделайте один точный шаг, а остальное выстроится легче.",
    "Не торопите события: день лучше раскрывается постепенно.",
)


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


def _daily_variant(user_id: int, sign_ru: str, target_date: date) -> int:
    seed = f"{user_id}:{sign_ru}:{target_date.isoformat()}".encode()
    return int(hashlib.blake2s(seed, digest_size=4).hexdigest(), 16)


def _pick(options: tuple[str, ...], variant: int, salt: int) -> str:
    return options[(variant >> salt) % len(options)]


def _format_ru_date(target_date: date) -> str:
    return f"{target_date.day} {_MONTHS_RU[target_date.month - 1]}"


def build_daily_message(
    user: User,
    sign_ru: str,
    text_ru: str,
    energy: dict,
    *,
    message_date: date | None = None,
) -> str:
    """Compose a short daily horoscope push."""
    name = user.tg_first_name or "друг"
    target_date = message_date or date.today()
    variant = _daily_variant(user.id, sign_ru, target_date)
    day = _format_ru_date(target_date)
    # Clip to a short teaser — Telegram message limit is 4096, keep it snack-sized
    teaser = text_ru[:280] + ("…" if len(text_ru) > 280 else "")
    greeting = _pick(_GREETINGS, variant, 0).format(name=name)
    intro = _pick(_INTROS, variant, 5).format(sign=sign_ru, day=day)
    bridge = _pick(_BRIDGES, variant, 10)
    closing = _pick(_CLOSINGS, variant, 15)

    return (
        f"<b>{greeting}</b>\n"
        f"{intro}\n\n"
        f"{bridge}\n"
        f"{teaser}\n\n"
        f"{closing}"
    )
