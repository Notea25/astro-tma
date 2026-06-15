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

from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.cache import cache_get, cache_set
from core.logging import get_logger
from core.settings import settings
from db.database import get_db
from db.models import SupportTicket, SupportTicketStatus

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
async def support_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
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
        mapping = await cache_get(_key_fwd(reply["message_id"]))
        if not mapping:
            log.info(
                "support.reply.no_mapping",
                reply_to=reply.get("message_id"),
            )
            return {"ok": True}

        # Backwards-compat: older mappings stored just an int user_id.
        if isinstance(mapping, dict):
            target_user_id = mapping.get("user_id")
            header_msg_id = mapping.get("header_msg_id")
            header_text = mapping.get("header_text")
        else:
            target_user_id = mapping
            header_msg_id = None
            header_text = None

        if not target_user_id:
            log.info("support.reply.no_user_id")
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

        # Persist the answer to the matching ticket so it survives Redis
        # eviction. Match by forwarded_msg_id (= the reply target).
        try:
            admin = msg.get("from") or {}
            ticket = (
                await db.execute(
                    select(SupportTicket).where(
                        SupportTicket.forwarded_msg_id == reply["message_id"],
                    )
                )
            ).scalar_one_or_none()
            if ticket and ticket.status != SupportTicketStatus.ANSWERED:
                ticket.status = SupportTicketStatus.ANSWERED
                ticket.admin_reply = text or msg.get("caption") or ""
                ticket.admin_user_id = admin.get("id")
                ticket.admin_username = admin.get("username")
                ticket.answered_at = datetime.now(UTC)
                await db.commit()
                log.info(
                    "support.ticket.answered",
                    ticket_id=ticket.id, user_id=target_user_id,
                )
        except Exception as e:  # noqa: BLE001
            await db.rollback()
            log.error("support.ticket.answer_persist_failed", error=str(e))

        # Mark the question as answered by flipping the header's 📩 → ✅.
        # Basic groups don't support setMessageReaction (REACTION_INVALID),
        # so we edit the header message we sent ourselves — works in any
        # chat type. Best-effort: failure shouldn't break the reply.
        if header_msg_id and header_text:
            new_text = header_text.replace("📩", "✅", 1)
            if new_text != header_text:
                edit_result = await _tg(
                    "editMessageText",
                    {
                        "chat_id": chat_id,
                        "message_id": header_msg_id,
                        "text": new_text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                )
                if not edit_result.get("ok"):
                    log.warning(
                        "support.reply.header_edit_failed",
                        error=edit_result.get("description"),
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
    # mapping key — that's what Reply attaches to. We also remember the
    # header's message_id so we can flip its 📩 → ✅ once an admin replies.
    header_result = await _tg(
        "sendMessage",
        {
            "chat_id": settings.SUPPORT_GROUP_CHAT_ID,
            "text": header,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
    )
    header_msg_id = (
        header_result["result"]["message_id"]
        if header_result.get("ok")
        else None
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
    await cache_set(
        _key_fwd(forwarded_msg_id),
        {
            "user_id": user_id,
            "header_msg_id": header_msg_id,
            "header_text": header,
        },
        _FWD_TTL,
    )

    # Persist the ticket so questions outlive Redis TTL and admins can
    # search/triage in /admin. Best-effort — a DB hiccup must not break
    # the user-facing flow (Redis mapping above is still authoritative
    # for the immediate reply roundtrip).
    try:
        ticket = SupportTicket(
            user_id=user_id,
            tg_username=user.get("username"),
            tg_first_name=user.get("first_name"),
            tg_last_name=user.get("last_name"),
            user_message=text,
            user_message_id=msg.get("message_id"),
            forwarded_msg_id=forwarded_msg_id,
            header_msg_id=header_msg_id,
            status=SupportTicketStatus.OPEN,
        )
        db.add(ticket)
        await db.commit()
        log.info("support.ticket.created", ticket_id=ticket.id, user_id=user_id)
    except Exception as e:  # noqa: BLE001
        await db.rollback()
        log.error("support.ticket.persist_failed", user_id=user_id, error=str(e))

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
