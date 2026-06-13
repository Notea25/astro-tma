"""Payment endpoints — Telegram Stars + YuKassa (Russian card-payment) flow."""


from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from api.schemas.payments import (
    CreateInvoiceRequest,
    CreateInvoiceResponse,
    ProductInfo,
)
from core.logging import get_logger
from core.settings import settings
from db.database import get_db
from services.payments import yukassa as yk
from services.payments.pricing import get_product_price, get_product_price_rub
from services.payments.stars import (
    PRODUCTS,
    create_invoice_link,
    grant_product_access,
    grant_yukassa_access,
    handle_pre_checkout,
)

router = APIRouter(prefix="/payments", tags=["payments"])
log = get_logger(__name__)


class YukassaCreateRequest(BaseModel):
    product_id: str


class YukassaCreateResponse(BaseModel):
    confirmation_url: str
    payment_id: str
    product_id: str
    rub_amount: int


@router.get("/products", response_model=list[ProductInfo])
async def list_products(tg_user: dict = Depends(get_tg_user)):
    """Return all purchasable products with current effective prices
    (Stars + rubles). Both sides honour the per-product Redis override
    set from the admin UI; ruble price is informational for now (no
    YuKassa flow yet)."""
    out: list[ProductInfo] = []
    for pid, p in PRODUCTS.items():
        stars = await get_product_price(pid, default=p["stars"])
        price_rub = await get_product_price_rub(pid, default=int(p.get("price_rub") or 0))
        out.append(
            ProductInfo(
                id=pid,
                name=p["name"],
                description=p["description"],
                stars=stars,
                price_rub=price_rub,
                type=p["type"],
            )
        )
    return out


@router.post("/invoice", response_model=CreateInvoiceResponse)
async def create_invoice(
    body: CreateInvoiceRequest,
    tg_user: dict = Depends(get_tg_user),
):
    """Create a Telegram Stars invoice link for the given product."""
    invoice_url = await create_invoice_link(tg_user["id"], body.product_id)
    product = PRODUCTS[body.product_id]
    return CreateInvoiceResponse(
        invoice_url=invoice_url,
        product_id=body.product_id,
        stars_amount=product["stars"],
    )


@router.post("/webhook")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Telegram Bot API webhook receiver.
    Handles: pre_checkout_query, successful_payment.

    Security: Telegram signs the webhook URL secret in the header.
    We verify X-Telegram-Bot-Api-Secret-Token matches our configured secret.
    """
    # Verify webhook secret
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        log.warning("webhook.invalid_secret")
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid webhook secret")

    body = await request.json()
    log.debug("webhook.received", update_keys=list(body.keys()))

    # ── Pre-checkout query: must answer within 10 seconds ──────────────────
    if "pre_checkout_query" in body:
        pcq = body["pre_checkout_query"]
        await handle_pre_checkout(pcq["id"], ok=True)
        return {"ok": True}

    # ── Successful payment ─────────────────────────────────────────────────
    message = body.get("message", {})
    if "successful_payment" in message:
        sp = message["successful_payment"]
        user_id = message["from"]["id"]
        payload: str = sp["invoice_payload"]
        charge_id: str = sp["telegram_payment_charge_id"]

        # payload format: "{user_id}:{product_id}:{timestamp}"
        try:
            _, product_id, _ = payload.split(":")
        except ValueError:
            log.error("webhook.bad_payload", payload=payload)
            return {"ok": True}  # Return 200 anyway so Telegram doesn't retry

        try:
            await grant_product_access(db, user_id, product_id, charge_id, payload)
            log.info("webhook.payment_processed", user_id=user_id, product=product_id)
        except IntegrityError:
            # SECURITY_AUDIT.md H2 — Telegram retries successful_payment on
            # any 5xx response; tg_payment_charge_id has UNIQUE constraint
            # so the second INSERT raises IntegrityError. Roll back and
            # ack 200 — the original payment is already granted.
            await db.rollback()
            log.info(
                "webhook.payment_duplicate_ignored",
                user_id=user_id, product=product_id, charge_id=charge_id,
            )

    return {"ok": True}


# ── YuKassa flow ─────────────────────────────────────────────────────────────


@router.post("/yukassa/create", response_model=YukassaCreateResponse)
async def create_yukassa_payment(
    body: YukassaCreateRequest,
    tg_user: dict = Depends(get_tg_user),
):
    """Create a YuKassa payment and return the hosted-payment URL.

    The TMA opens this URL via ``WebApp.openLink`` so the user can enter
    their card on YuKassa's PCI-compliant page. Access is provisioned on
    the webhook callback (`/yukassa/webhook`), not here.
    """
    if not yk.is_configured():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "YuKassa payments are not configured",
        )
    if body.product_id not in PRODUCTS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown product")

    product = PRODUCTS[body.product_id]
    rub_amount = await get_product_price_rub(
        body.product_id, default=int(product.get("price_rub") or 0),
    )
    if rub_amount <= 0:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Ruble price not configured for this product",
        )

    try:
        payment = await yk.create_payment(
            amount_rub=rub_amount,
            description=product["name"],
            metadata={
                "user_id": str(tg_user["id"]),
                "product_id": body.product_id,
            },
        )
    except Exception as e:  # noqa: BLE001
        log.error("yukassa.create_exception", error=str(e))
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Не удалось создать платёж. Попробуйте ещё раз.",
        ) from e

    confirmation = payment.get("confirmation") or {}
    confirmation_url = confirmation.get("confirmation_url")
    if not confirmation_url:
        log.error("yukassa.no_confirmation_url", payment=payment)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Платёжный шлюз не вернул URL — попробуйте позже.",
        )

    return YukassaCreateResponse(
        confirmation_url=confirmation_url,
        payment_id=payment["id"],
        product_id=body.product_id,
        rub_amount=rub_amount,
    )


@router.post("/yukassa/webhook")
async def yukassa_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """YuKassa notification receiver.

    Security model: we DO NOT trust the webhook body. We re-fetch the
    payment from YuKassa by ID and rely on the API's response. This way
    a forged POST can at best trigger an extra lookup, not unlock content.

    YuKassa retries until a 200 is returned, so any temporary failure
    inside this handler should raise — we ack with 200 only on terminal
    states (succeeded / canceled / not-our-payment).
    """
    if not yk.is_configured():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "YuKassa not configured")

    try:
        body_json = await request.json()
    except Exception:  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid JSON") from None

    event = body_json.get("event", "")
    payment_obj = body_json.get("object") or {}
    payment_id = payment_obj.get("id")
    if not payment_id:
        log.warning("yukassa.webhook.no_id", body_keys=list(body_json.keys()))
        return {"ok": True}

    # Re-fetch from YuKassa — authoritative source of truth.
    try:
        fresh = await yk.get_payment(payment_id)
    except Exception as e:  # noqa: BLE001
        log.error("yukassa.webhook.fetch_failed", payment_id=payment_id, error=str(e))
        # 502 makes YuKassa retry — we want to be able to process this.
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Lookup failed") from e

    status_str = fresh.get("status")
    metadata = fresh.get("metadata") or {}
    user_id_raw = metadata.get("user_id")
    product_id = metadata.get("product_id")

    log.info(
        "yukassa.webhook.received",
        event=event,
        payment_id=payment_id,
        status=status_str,
        user_id=user_id_raw,
        product_id=product_id,
    )

    if status_str != "succeeded":
        # canceled / pending / waiting_for_capture — nothing to grant.
        return {"ok": True}

    if not user_id_raw or not product_id:
        log.warning(
            "yukassa.webhook.missing_metadata",
            payment_id=payment_id,
            metadata=metadata,
        )
        return {"ok": True}

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        log.warning("yukassa.webhook.bad_user_id", user_id_raw=user_id_raw)
        return {"ok": True}

    # Net amount paid in kopecks.
    amount = fresh.get("amount") or {}
    try:
        rub_value = float(amount.get("value", "0"))
        rub_amount_kopecks = int(round(rub_value * 100))
    except (TypeError, ValueError):
        rub_amount_kopecks = 0

    try:
        await grant_yukassa_access(
            db,
            user_id,
            product_id,
            yukassa_payment_id=payment_id,
            rub_amount_kopecks=rub_amount_kopecks,
            payload=f"yukassa:{payment_id}",
        )
        log.info("yukassa.webhook.granted", payment_id=payment_id, user_id=user_id)
    except IntegrityError:
        # Duplicate webhook for the same payment — already granted.
        await db.rollback()
        log.info("yukassa.webhook.duplicate_ignored", payment_id=payment_id)

    return {"ok": True}
