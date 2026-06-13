"""Refund flow — flip Purchase / Subscription rows when a YuKassa
refund completes.

Two entry points:

* `apply_yukassa_refund_to_db()` — given a YuKassa `payment_id`, mark
  every matching Purchase row as REFUNDED and every Subscription row
  as CANCELLED. Idempotent — re-running with the same id has no effect.

* Webhook handler in `api/routes/payments.py` calls this on every
  `refund.succeeded` notification (also covers refunds the operator
  initiates from the YuKassa cabinet without touching our admin).

The admin "↩️ Возврат" button (see `backend/admin.py`) calls
`yukassa.create_refund()` first, then this helper — that way the DB
flips immediately, without waiting for the webhook round-trip.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from db.models import (
    Purchase,
    PurchaseStatus,
    Subscription,
    SubscriptionStatus,
)

log = get_logger(__name__)


async def apply_yukassa_refund_to_db(
    db: AsyncSession,
    *,
    yukassa_payment_id: str,
) -> tuple[int, int]:
    """Mark every Purchase / Subscription row matching `yukassa_payment_id`
    as refunded. Returns `(purchases_updated, subs_updated)`."""
    now = datetime.now(UTC)
    purchases_updated = 0
    subs_updated = 0

    p_rows = (
        await db.execute(
            select(Purchase).where(
                Purchase.yukassa_payment_id == yukassa_payment_id,
            )
        )
    ).scalars().all()
    for row in p_rows:
        if row.status == PurchaseStatus.REFUNDED:
            continue
        row.status = PurchaseStatus.REFUNDED
        purchases_updated += 1

    s_rows = (
        await db.execute(
            select(Subscription).where(
                Subscription.yukassa_payment_id == yukassa_payment_id,
            )
        )
    ).scalars().all()
    for row in s_rows:
        if row.status == SubscriptionStatus.CANCELLED:
            continue
        row.status = SubscriptionStatus.CANCELLED
        # Cut the access NOW — don't wait for the natural expiry.
        if row.expires_at and row.expires_at > now:
            row.expires_at = now
        subs_updated += 1

    if purchases_updated or subs_updated:
        await db.flush()

    log.info(
        "yukassa.refund_applied",
        payment_id=yukassa_payment_id,
        purchases_updated=purchases_updated,
        subs_updated=subs_updated,
    )
    return purchases_updated, subs_updated
