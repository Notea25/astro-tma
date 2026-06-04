"""
Support bot webhook — a separate Telegram bot for user questions.

Flow:
  - User DMs @SUPPORT_BOT → bot forwards the message to SUPPORT_GROUP_CHAT_ID
    with a header line ("From <name> · id=…") and saves a Redis mapping
    {forwarded_msg_id → original_user_id} so replies can be routed back.
  - Admin replies in the group using Telegram's native "Reply" to the
    forwarded message → bot sends the reply text back to the original user
    via DM.
  - /start in a DM gets a short welcome.

Disabled (404) when SUPPORT_BOT_TOKEN is not configured.
"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request, status

from core.cache import cache_get, cache_set
from core.logging import get_logger
from core.settings import settings

log = get_logger(__name__)
router = APIRouter(prefix="/support", tags=["support"])

_FWD_TTL = 60 * 60 * 24 * 30  # 30 days
_WELCOME = (
    "Здравствуйте! Это поддержка приложения «Астрология».\n\n"
    "Опишите вопрос одним сообщением — мы ответим здесь же, в этом чате. "
    "Можно прикреплять скриншоты."
)


def _key_fwd(group_msg_id: int) -> str:
    return f"support:fwd:{group_msg_id}"


def _telegram_url(method: str) -> str:
    return f"https://api.telegram.org/bot{settings.SUPPORT_BOT_TOKEN}/{method}"


async def _tg(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(_telegram_url(method), json=payload)
    return resp.json()


@router.post("/webhook")
async def support_webhook(request: Request) -> dict[str, bool]:
    if not settings.SUPPORT_BOT_TOKEN:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Support bot not configured")

    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if secret != settings.SUPPORT_WEBHOOK_SECRET:
        log.warning("support.invalid_secret")
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid webhook secret")

    body = await request.json()
    msg = body.get("message") or body.get("edited_message")
    if not msg:
        return {"ok": True}

    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    chat_type = chat.get("type")
    text: str = msg.get("text") or msg.get("caption") or ""

    # ── Group reply → relay back to original user ─────────────────────────
    if (
        settings.SUPPORT_GROUP_CHAT_ID
        and chat_id == settings.SUPPORT_GROUP_CHAT_ID
        and (reply := msg.get("reply_to_message"))
    ):
        target_user_id = await cache_get(_key_fwd(reply["message_id"]))
        if not target_user_id:
            log.info(
                "support.reply.no_mapping",
                reply_to=reply.get("message_id"),
            )
            return {"ok": True}

        # Plain text reply only (no markdown to avoid escape issues).
        copy_payload: dict[str, Any] = {
            "chat_id": int(target_user_id),
            "from_chat_id": chat_id,
            "message_id": msg["message_id"],
        }
        result = await _tg("copyMessage", copy_payload)
        if not result.get("ok"):
            log.error(
                "support.reply.send_failed",
                error=result.get("description"),
                user_id=target_user_id,
            )
            return {"ok": True}

        log.info("support.reply.sent", user_id=target_user_id)

        # Mark the user's forwarded message with ✅ so the team can see at
        # a glance which questions still need attention. Best-effort —
        # reactions can fail (e.g. emoji not allowed in chat) without
        # impacting the reply itself.
        reaction_result = await _tg(
            "setMessageReaction",
            {
                "chat_id": chat_id,
                "message_id": reply["message_id"],
                "reaction": [{"type": "emoji", "emoji": "✅"}],
            },
        )
        if not reaction_result.get("ok"):
            log.warning(
                "support.reply.reaction_failed",
                error=reaction_result.get("description"),
            )
        return {"ok": True}

    # ── User DM → forward to support group ────────────────────────────────
    if chat_type != "private":
        # Random group activity we don't care about.
        return {"ok": True}

    user = msg.get("from") or {}
    user_id = user.get("id")
    if not user_id:
        return {"ok": True}

    # /start gets a welcome instead of being forwarded as text.
    if text.strip() == "/start":
        await _tg("sendMessage", {"chat_id": user_id, "text": _WELCOME})
        return {"ok": True}

    if not settings.SUPPORT_GROUP_CHAT_ID:
        # Token is set but group isn't — tell the user we noted the question
        # so they don't think the bot is dead.
        await _tg(
            "sendMessage",
            {
                "chat_id": user_id,
                "text": (
                    "Спасибо! Мы получили ваше сообщение и скоро ответим."
                ),
            },
        )
        log.error("support.no_group_configured", user_id=user_id)
        return {"ok": True}

    # Header that sits above the forwarded content in the group, so the
    # admin sees who's writing without having to click into the profile.
    name = user.get("first_name") or "Пользователь"
    if last := user.get("last_name"):
        name = f"{name} {last}"
    handle = f"@{user['username']}" if user.get("username") else f"id={user_id}"
    header = f"📩 <b>{name}</b> · {handle}"

    # Send the header as a regular message and then forward the user's
    # original message right after. Using forwardMessage means stickers,
    # photos, voice notes, documents all carry over without us needing to
    # special-case media types. The forwarded message_id becomes the
    # mapping key — that's what Reply attaches to.
    await _tg(
        "sendMessage",
        {
            "chat_id": settings.SUPPORT_GROUP_CHAT_ID,
            "text": header,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
    )

    fwd_result = await _tg(
        "forwardMessage",
        {
            "chat_id": settings.SUPPORT_GROUP_CHAT_ID,
            "from_chat_id": user_id,
            "message_id": msg["message_id"],
        },
    )
    if not fwd_result.get("ok"):
        log.error(
            "support.forward_failed",
            user_id=user_id,
            error=fwd_result.get("description"),
        )
        return {"ok": True}

    forwarded_msg_id = fwd_result["result"]["message_id"]
    await cache_set(_key_fwd(forwarded_msg_id), user_id, _FWD_TTL)

    # Acknowledge to the user so they know the message was received.
    await _tg(
        "sendMessage",
        {
            "chat_id": user_id,
            "text": "✓ Получили ваше сообщение. Ответим здесь же.",
        },
    )

    log.info("support.user_msg.forwarded", user_id=user_id, fwd_id=forwarded_msg_id)
    return {"ok": True}


async def setup_support_webhook() -> None:
    """
    Called from app startup. Idempotent — Telegram accepts repeated
    setWebhook calls with the same URL. No-op if the support bot is not
    configured.
    """
    if not (
        settings.SUPPORT_BOT_TOKEN
        and settings.SUPPORT_WEBHOOK_SECRET
        and settings.TELEGRAM_WEBHOOK_URL
    ):
        log.info("support.webhook.not_configured")
        return

    webhook_url = settings.TELEGRAM_WEBHOOK_URL.rstrip("/")
    # TELEGRAM_WEBHOOK_URL points at the main bot's /api/payments/webhook;
    # derive the support URL by replacing the last path segment.
    if webhook_url.endswith("/payments/webhook"):
        webhook_url = webhook_url[: -len("/payments/webhook")] + "/support/webhook"
    elif not webhook_url.endswith("/support/webhook"):
        # Fall back to appending — works when TELEGRAM_WEBHOOK_URL is the
        # bare base URL (e.g. https://api.example.com/api).
        webhook_url = webhook_url + "/support/webhook"

    payload = {
        "url": webhook_url,
        "secret_token": settings.SUPPORT_WEBHOOK_SECRET,
        "allowed_updates": ["message", "edited_message"],
        "drop_pending_updates": False,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_telegram_url("setWebhook"), json=payload)
        data = resp.json()
        if data.get("ok"):
            log.info("support.webhook.set", url=webhook_url)
        else:
            log.error("support.webhook.set_failed", error=data.get("description"))
    except Exception as e:  # noqa: BLE001
        log.error("support.webhook.set_exception", error=str(e))
