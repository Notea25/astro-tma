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


def _build_receipt(
    *,
    amount_rub: int,
    description: str,
    customer_email: str | None = None,
) -> dict[str, Any]:
    """Build the fiscal-receipt object YuKassa requires under 54-ФЗ.

    Live-mode YuKassa rejects any /payments request without a receipt
    that names a customer (email or phone) and at least one line-item.
    Falls back to ``settings.YUKASSA_RECEIPT_DEFAULT_EMAIL`` so payments
    don't break when the caller didn't collect a buyer email.
    """
    email = (customer_email or settings.YUKASSA_RECEIPT_DEFAULT_EMAIL).strip()
    if not email:
        raise RuntimeError(
            "YUKASSA_RECEIPT_DEFAULT_EMAIL not configured — "
            "set it in .env or pass customer_email per call (54-ФЗ requires one)."
        )

    return {
        "customer": {"email": email},
        "items": [
            {
                "description": description[:128],
                "quantity": "1.00",
                "amount": {
                    "value": f"{amount_rub}.00",
                    "currency": "RUB",
                },
                "vat_code": settings.YUKASSA_RECEIPT_VAT_CODE,
                # Digital service paid in full before delivery.
                "payment_mode": "full_prepayment",
                "payment_subject": "service",
            }
        ],
    }


async def create_payment(
    *,
    amount_rub: int,
    description: str,
    metadata: dict[str, str],
    customer_email: str | None = None,
) -> dict[str, Any]:
    """Create a YuKassa payment and return the parsed response.

    ``amount_rub`` is whole rubles (we always charge integer amounts).
    ``metadata`` is echoed back by YuKassa in the webhook payload — we
    stuff ``user_id`` and ``product_id`` into it so the webhook handler
    can match the payment to a Purchase / Subscription row.

    ``customer_email`` is the buyer's address for the fiscal receipt.
    When omitted we fall back to ``YUKASSA_RECEIPT_DEFAULT_EMAIL``.

    Returns the full payment object; callers usually only need
    ``response["id"]`` (UUID) and ``response["confirmation"]["confirmation_url"]``.
    """
    if not is_configured():
        raise RuntimeError("YuKassa not configured")

    payload: dict[str, Any] = {
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
        # 54-ФЗ-mandated fiscal receipt — without this YuKassa returns
        # 400 "Receipt is missing or illegal" in live mode.
        "receipt": _build_receipt(
            amount_rub=amount_rub,
            description=description,
            customer_email=customer_email,
        ),
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


def _build_refund_receipt(
    *,
    amount_rub: int,
    description: str,
    customer_email: str,
) -> dict[str, Any]:
    """Refund-side receipt — YuKassa enforces it under 54-ФЗ.

    NOTE: `payment_mode` must match the ORIGINAL payment's value
    (`full_prepayment` for us — we charge upfront). The /v3/refunds
    endpoint itself signals "this is a refund"; the receipt mirrors
    the payment receipt because it's the line-item being reversed.
    """
    return {
        "customer": {"email": customer_email},
        "items": [
            {
                "description": description[:128],
                "quantity": "1.00",
                "amount": {
                    "value": f"{amount_rub}.00",
                    "currency": "RUB",
                },
                "vat_code": settings.YUKASSA_RECEIPT_VAT_CODE,
                "payment_mode": "full_prepayment",
                "payment_subject": "service",
            }
        ],
    }


async def create_refund(
    *,
    payment_id: str,
    amount_rub: int,
    description: str,
    customer_email: str | None = None,
) -> dict[str, Any]:
    """Issue a refund for an existing YuKassa payment.

    Pass the same `description` as the original payment — receipt
    consistency matters for the tax registrar. `customer_email`
    defaults to ``YUKASSA_RECEIPT_DEFAULT_EMAIL`` because not every
    refund (e.g. one initiated by support) has the buyer's address
    at hand.
    """
    if not is_configured():
        raise RuntimeError("YuKassa not configured")

    email = (customer_email or settings.YUKASSA_RECEIPT_DEFAULT_EMAIL).strip()
    if not email:
        raise RuntimeError(
            "Cannot issue refund: no email available for the refund receipt "
            "(set YUKASSA_RECEIPT_DEFAULT_EMAIL or pass customer_email).",
        )

    payload = {
        "payment_id": payment_id,
        "amount": {
            "value": f"{amount_rub}.00",
            "currency": "RUB",
        },
        "description": description[:128],
        "receipt": _build_refund_receipt(
            amount_rub=amount_rub,
            description=description,
            customer_email=email,
        ),
    }

    headers = {
        "Authorization": _auth_header(),
        "Idempotence-Key": str(uuid.uuid4()),
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{_API_BASE}/refunds", json=payload, headers=headers,
        )

    if resp.status_code >= 400:
        log.error(
            "yukassa.refund_failed",
            payment_id=payment_id,
            status=resp.status_code,
            body=resp.text[:500],
        )
        resp.raise_for_status()

    data = resp.json()
    log.info(
        "yukassa.refund_created",
        payment_id=payment_id,
        refund_id=data.get("id"),
        amount=amount_rub,
    )
    return data


async def get_refund(refund_id: str) -> dict[str, Any]:
    """Re-fetch a refund by ID — used by the webhook handler to confirm
    `refund.succeeded` before flipping our internal status."""
    if not is_configured():
        raise RuntimeError("YuKassa not configured")

    headers = {"Authorization": _auth_header()}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{_API_BASE}/refunds/{refund_id}", headers=headers)

    if resp.status_code >= 400:
        log.error(
            "yukassa.refund_fetch_failed",
            refund_id=refund_id,
            status=resp.status_code,
            body=resp.text[:500],
        )
        resp.raise_for_status()

    return resp.json()
