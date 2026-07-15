"""Tests for the main bot's Mini App entry card."""

from unittest.mock import AsyncMock

import pytest

from services.notifications.welcome import (
    WELCOME_BUTTON_LABEL,
    build_welcome_photo_payload,
    build_welcome_text_payload,
    send_welcome_card,
)


def test_welcome_photo_payload_contains_image_and_webapp_button(monkeypatch):
    from core.settings import settings

    monkeypatch.setattr(settings, "TELEGRAM_WEBAPP_URL", "https://example.com/app")

    payload = build_welcome_photo_payload(12345)

    assert payload is not None
    assert payload["chat_id"] == 12345
    assert payload["photo"] == "https://example.com/splash-bg.jpg"
    assert "Нажмите кнопку ниже" in payload["caption"]
    button = payload["reply_markup"]["inline_keyboard"][0][0]
    assert button["text"] == WELCOME_BUTTON_LABEL
    assert button["web_app"]["url"] == "https://example.com/app"


def test_welcome_text_payload_omits_button_without_webapp_url(monkeypatch):
    from core.settings import settings

    monkeypatch.setattr(settings, "TELEGRAM_WEBAPP_URL", "")

    assert build_welcome_photo_payload(12345) is None
    assert "reply_markup" not in build_welcome_text_payload(12345)


@pytest.mark.asyncio
async def test_welcome_falls_back_to_text_when_photo_is_rejected(monkeypatch):
    from core.settings import settings

    monkeypatch.setattr(settings, "TELEGRAM_WEBAPP_URL", "https://example.com/app")
    telegram_call = AsyncMock(
        side_effect=[
            {"ok": False, "description": "wrong file identifier"},
            {"ok": True},
        ]
    )
    monkeypatch.setattr(
        "services.notifications.welcome._telegram_call",
        telegram_call,
    )

    assert await send_welcome_card(12345) is True
    assert [call.args[0] for call in telegram_call.await_args_list] == [
        "sendPhoto",
        "sendMessage",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message_content",
    [
        {"text": "/start referral-token"},
        {"text": "Куда нажимать?"},
        {"photo": [{"file_id": "photo-id"}]},
        {"sticker": {"file_id": "sticker-id"}},
    ],
)
async def test_main_webhook_sends_welcome_for_every_private_message(
    monkeypatch,
    message_content,
):
    from api.routes.payments import telegram_webhook
    from core.settings import settings

    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "test-secret")
    send_welcome = AsyncMock(return_value=True)
    monkeypatch.setattr("api.routes.payments.send_welcome_card", send_welcome)

    class PrivateMessageRequest:
        headers = {"X-Telegram-Bot-Api-Secret-Token": "test-secret"}

        async def json(self):
            return {
                "message": {
                    **message_content,
                    "chat": {"id": 12345, "type": "private"},
                    "from": {"id": 12345, "is_bot": False},
                }
            }

    assert await telegram_webhook(PrivateMessageRequest(), AsyncMock()) == {"ok": True}
    send_welcome.assert_awaited_once_with(12345)


@pytest.mark.asyncio
async def test_successful_payment_does_not_send_welcome(monkeypatch):
    from api.routes.payments import telegram_webhook
    from core.settings import settings

    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "test-secret")
    send_welcome = AsyncMock(return_value=True)
    grant_access = AsyncMock(return_value=None)
    monkeypatch.setattr("api.routes.payments.send_welcome_card", send_welcome)
    monkeypatch.setattr("api.routes.payments.grant_product_access", grant_access)

    class PaymentRequest:
        headers = {"X-Telegram-Bot-Api-Secret-Token": "test-secret"}

        async def json(self):
            return {
                "message": {
                    "chat": {"id": 12345, "type": "private"},
                    "from": {"id": 12345, "is_bot": False},
                    "successful_payment": {
                        "invoice_payload": "12345:natal_full:1234567890",
                        "telegram_payment_charge_id": "charge-id",
                    },
                }
            }

    db = AsyncMock()
    assert await telegram_webhook(PaymentRequest(), db) == {"ok": True}
    send_welcome.assert_not_awaited()
    grant_access.assert_awaited_once_with(
        db,
        12345,
        "natal_full",
        "charge-id",
        "12345:natal_full:1234567890",
    )
