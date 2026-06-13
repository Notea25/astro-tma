"""YuKassa (Russian card-payment gateway) wrapper.

Two responsibilities:

  1. Create a payment for a Telegram user: returns the
     ``confirmation_url`` they should be redirected to. The Telegram
     Mini App opens this URL via ``WebApp.openLink``.

  2. Resolve an incoming webhook: re-fetches the payment object from
     YuKassa by ID (NOT trusting the webhook body) and reports the
     authoritative status. This avoids accepting forged webhooks
     without depending on YuKassa's optional Ed25519 signature.

API reference: https://yookassa.ru/developers/api

Auth: HTTP Basic with ``shopId:secret_key``. Idempotency keys are
required for create-payment requests — we generate a UUID4 per call.
"""

from __future__ import annotations

import base64
import uuid
from typing import Any

import httpx

from core.logging import get_logger
from core.settings import settings

log = get_logger(__name__)

_API_BASE = "https://api.yookassa.ru/v3"


def _auth_header() -> str:
    """Pre-built Basic-Auth header value."""
    pair = f"{settings.YUKASSA_SHOP_ID}:{settings.YUKASSA_SECRET_KEY}"
    return "Basic " + base64.b64encode(pair.encode()).decode()


def is_configured() -> bool:
    return bool(settings.YUKASSA_SHOP_ID and settings.YUKASSA_SECRET_KEY)


async def create_payment(
    *,
    amount_rub: int,
    description: str,
    metadata: dict[str, str],
) -> dict[str, Any]:
    """Create a YuKassa payment and return the parsed response.

    ``amount_rub`` is whole rubles (we always charge integer amounts).
    ``metadata`` is echoed back by YuKassa in the webhook payload — we
    stuff ``user_id`` and ``product_id`` into it so the webhook handler
    can match the payment to a Purchase / Subscription row.

    Returns the full payment object; callers usually only need
    ``response["id"]`` (UUID) and ``response["confirmation"]["confirmation_url"]``.
    """
    if not is_configured():
        raise RuntimeError("YuKassa not configured")

    payload = {
        "amount": {
            "value": f"{amount_rub}.00",
            "currency": "RUB",
        },
        "capture": True,  # auto-capture on successful payment
        "confirmation": {
            "type": "redirect",
            "return_url": settings.YUKASSA_RETURN_URL,
        },
        "description": description[:128],
        "metadata": {k: str(v)[:128] for k, v in metadata.items()},
    }

    headers = {
        "Authorization": _auth_header(),
        "Idempotence-Key": str(uuid.uuid4()),
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{_API_BASE}/payments", json=payload, headers=headers,
        )

    if resp.status_code >= 400:
        log.error(
            "yukassa.create_failed",
            status=resp.status_code,
            body=resp.text[:500],
        )
        resp.raise_for_status()

    data = resp.json()
    log.info(
        "yukassa.created",
        payment_id=data.get("id"),
        amount=amount_rub,
        metadata=metadata,
    )
    return data


async def get_payment(payment_id: str) -> dict[str, Any]:
    """Re-fetch a payment by ID — authoritative source on its status.

    Webhook handler MUST call this before granting access so a forged
    webhook body can't unlock content.
    """
    if not is_configured():
        raise RuntimeError("YuKassa not configured")

    headers = {"Authorization": _auth_header()}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{_API_BASE}/payments/{payment_id}", headers=headers)

    if resp.status_code >= 400:
        log.error(
            "yukassa.fetch_failed",
            payment_id=payment_id,
            status=resp.status_code,
            body=resp.text[:500],
        )
        resp.raise_for_status()

    return resp.json()
