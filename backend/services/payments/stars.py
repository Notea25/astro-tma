"""
Telegram Stars payment service.

Flow:
  1. Client requests invoice  →  create_invoice_link()
  2. Client opens invoice     →  WebApp.openInvoice()
  3. Telegram sends webhook   →  handle_pre_checkout() + handle_successful_payment()
  4. We grant access          →  grant_product_access()

ALL access grants happen in webhook handler — never trust client callback alone.
"""

import time
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from core.settings import settings
from db.models import (
    Purchase, PurchaseStatus,
    Subscription, SubscriptionPlan, SubscriptionStatus,
)

log = get_logger(__name__)

# ── Product catalogue ─────────────────────────────────────────────────────────
PRODUCTS: dict[str, dict] = {
    "horoscope_tomorrow": {
        "name": "Гороскоп на завтра",
        "description": "Персональный гороскоп на завтра с анализом транзитов",
        "stars": settings.PRICE_HOROSCOPE_TOMORROW,
        "type": "one_time",
    },
    "horoscope_week": {
        "name": "Гороскоп на неделю",
        "description": "Прогноз на 7 дней с анализом планетарных влияний",
        "stars": settings.PRICE_HOROSCOPE_WEEK,
        "type": "one_time",
    },
    "horoscope_month": {
        "name": "Гороскоп на месяц",
        "description": "Детальный прогноз на весь месяц",
        "stars": settings.PRICE_HOROSCOPE_MONTH,
        "type": "one_time",
    },
    "tarot_celtic": {
        "name": "Расклад Кельтский Крест",
        "description": "Глубокий 10-карточный расклад для детального анализа ситуации",
        "stars": settings.PRICE_TAROT_CELTIC,
        "type": "one_time",
    },
    "tarot_week": {
        "name": "Таро на неделю",
        "description": "Одна карта на каждый день недели",
        "stars": settings.PRICE_TAROT_WEEK,
        "type": "one_time",
    },
    "natal_full": {
        "name": "Полная натальная карта",
        "description": "Детальный анализ всех планет, домов и аспектов + SVG-диаграмма",
        "stars": settings.PRICE_NATAL_FULL,
        "type": "one_time",
    },
    "synastry": {
        "name": "Синастрия — совместимость",
        "description": "Глубокий анализ совместимости двух натальных карт",
        "stars": settings.PRICE_SYNASTRY,
        "type": "one_time",
    },
    "subscription_month": {
        "name": "Premium подписка — 30 дней",
        "description": "Полный доступ ко всем функциям на 30 дней",
        "stars": settings.PRICE_SUBSCRIPTION_MONTH,
        "type": "subscription",
        "duration_days": 30,
        "plan": SubscriptionPlan.PREMIUM_MONTH,
    },
    "subscription_year": {
        "name": "Premium подписка — 365 дней",
        "description": "Полный доступ ко всем функциям на год. Выгода 40%!",
        "stars": settings.PRICE_SUBSCRIPTION_YEAR,
        "type": "subscription",
        "duration_days": 365,
        "plan": SubscriptionPlan.PREMIUM_YEAR,
    },
}


async def create_invoice_link(user_id: int, product_id: str) -> str:
    """
    Call Telegram Bot API to create an invoice link for Stars payment.
    Returns the invoice URL to pass to WebApp.openInvoice().
    """
    if product_id not in PRODUCTS:
        raise ValueError(f"Unknown product: {product_id!r}")

    product = PRODUCTS[product_id]
    # Payload encodes user + product + timestamp for webhook verification
    payload = f"{user_id}:{product_id}:{int(time.time())}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/createInvoiceLink",
            json={
                "title": product["name"],
                "description": product["description"],
                "payload": payload,
                "provider_token": "",   # MUST be empty for Stars
                "currency": "XTR",      # Telegram Stars
                "prices": [{"label": product["name"], "amount": product["stars"]}],
            },
        )

    data = resp.json()
    if not data.get("ok"):
        log.error("stars.invoice_failed", product=product_id, response=data)
        raise RuntimeError(f"Telegram API error: {data.get('description')}")

    invoice_url: str = data["result"]
    log.info("stars.invoice_created", user_id=user_id, product=product_id, stars=product["stars"])
    return invoice_url


async def handle_pre_checkout(query_id: str, ok: bool = True, error: str | None = None) -> None:
    """
    Must be answered within 10 seconds of receiving pre_checkout_query.
    Decline here if product is invalid or user ineligible.
    """
    async with httpx.AsyncClient(timeout=8.0) as client:
        await client.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/answerPreCheckoutQuery",
            json={
                "pre_checkout_query_id": query_id,
                "ok": ok,
                **({"error_message": error} if error else {}),
            },
        )
    log.info("stars.pre_checkout_answered", query_id=query_id, ok=ok)


async def grant_product_access(
    db: AsyncSession,
    user_id: int,
    product_id: str,
    tg_payment_charge_id: str,
    payload: str,
) -> None:
    """
    Called after successful_payment webhook.
    Creates Purchase or Subscription record to unlock content.
    Idempotent — safe to call twice (unique constraint on charge_id).
    """
    if product_id not in PRODUCTS:
        log.warning("stars.unknown_product", product=product_id, user_id=user_id)
        return

    product = PRODUCTS[product_id]
    now = datetime.now(timezone.utc)

    if product["type"] == "subscription":
        sub = Subscription(
            user_id=user_id,
            plan=product["plan"],
            status=SubscriptionStatus.ACTIVE,
            stars_paid=product["stars"],
            tg_payment_charge_id=tg_payment_charge_id,
            starts_at=now,
            expires_at=now + timedelta(days=product["duration_days"]),
        )
        db.add(sub)
    else:
        purchase = Purchase(
            user_id=user_id,
            product_id=product_id,
            status=PurchaseStatus.COMPLETED,
            stars_amount=product["stars"],
            tg_payment_charge_id=tg_payment_charge_id,
            payload=payload,
        )
        db.add(purchase)

    await db.flush()
    log.info(
        "stars.access_granted",
        user_id=user_id,
        product=product_id,
        charge_id=tg_payment_charge_id,
    )
