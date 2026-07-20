"""Product analytics — record and query funnel events."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import distinct, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from db.models import Purchase, PurchaseStatus, Subscription, SubscriptionStatus, User, UserEvent

log = get_logger(__name__)

# Whitelist — keep the catalogue small and intentional.
ALLOWED_EVENTS = frozenset({
    "app_open",
    "onboarding_start",
    "birth_saved",
    "home_ready",
    "screen_view",
    "paywall_view",
    "checkout_click",
    "payment_ok",
    "payment_cancel",
    "natal_open",
    "natal_pdf_cta",
    "matrix_open",
    "matrix_lock_cta",
    "synastry_open",
    "synastry_invite_create",
    "synastry_invite_accept",
    "tarot_draw",
    "premium_open",
})

FUNNELS: dict[str, list[str]] = {
    "onboarding": [
        "app_open",
        "onboarding_start",
        "birth_saved",
        "home_ready",
    ],
    "pay_generic": [
        "paywall_view",
        "checkout_click",
        "payment_ok",
    ],
    "natal": [
        "natal_open",
        "natal_pdf_cta",
        "paywall_view",
        "checkout_click",
        "payment_ok",
    ],
    "matrix": [
        "matrix_open",
        "matrix_lock_cta",
        "paywall_view",
        "checkout_click",
        "payment_ok",
    ],
    "synastry": [
        "synastry_open",
        "synastry_invite_create",
        "synastry_invite_accept",
        "paywall_view",
        "checkout_click",
        "payment_ok",
    ],
}


async def record_event(
    db: AsyncSession,
    user_id: int,
    event: str,
    *,
    product_id: str | None = None,
    props: dict[str, Any] | None = None,
    commit: bool = False,
) -> bool:
    if event not in ALLOWED_EVENTS:
        log.warning("analytics.unknown_event", event=event, user_id=user_id)
        return False
    db.add(
        UserEvent(
            user_id=user_id,
            event=event,
            product_id=product_id,
            props=props or None,
        )
    )
    if commit:
        await db.commit()
    return True


async def touch_last_seen(db: AsyncSession, user: User) -> None:
    user.last_seen_at = datetime.now(UTC)


async def funnel_counts(
    db: AsyncSession,
    steps: list[str],
    *,
    days: int = 7,
    product_id: str | None = None,
) -> list[dict[str, Any]]:
    """Unique users per funnel step in the window (not sequential cohort)."""
    since = datetime.now(UTC) - timedelta(days=days)
    out: list[dict[str, Any]] = []
    prev: int | None = None
    for step in steps:
        q = (
            select(func.count(distinct(UserEvent.user_id)))
            .where(UserEvent.event == step, UserEvent.created_at >= since)
        )
        if product_id:
            q = q.where(UserEvent.product_id == product_id)
        n = int((await db.execute(q)).scalar_one() or 0)
        drop = None
        if prev is not None and prev > 0:
            drop = round((1 - n / prev) * 100, 1)
        out.append({"event": step, "users": n, "drop_pct": drop})
        prev = n
    return out


async def activity_summary(db: AsyncSession) -> dict[str, Any]:
    now = datetime.now(UTC)
    day = now - timedelta(days=1)
    week = now - timedelta(days=7)
    month = now - timedelta(days=30)

    async def _seen_since(since: datetime) -> int:
        r = await db.execute(
            select(func.count()).select_from(User).where(User.last_seen_at >= since)
        )
        return int(r.scalar_one() or 0)

    total = int(
        (await db.execute(select(func.count()).select_from(User))).scalar_one() or 0
    )
    onboarded = int(
        (
            await db.execute(
                select(func.count()).select_from(User).where(User.sun_sign.is_not(None))
            )
        ).scalar_one()
        or 0
    )
    active_subs = int(
        (
            await db.execute(
                select(func.count())
                .select_from(Subscription)
                .where(
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.expires_at > now,
                )
            )
        ).scalar_one()
        or 0
    )
    paid_week = int(
        (
            await db.execute(
                select(func.count())
                .select_from(Purchase)
                .where(
                    Purchase.status == PurchaseStatus.COMPLETED,
                    Purchase.created_at >= week,
                )
            )
        ).scalar_one()
        or 0
    )

    top_screens = (
        await db.execute(
            text(
                """
                SELECT props->>'screen' AS screen,
                       COUNT(DISTINCT user_id) AS users
                FROM user_events
                WHERE event = 'screen_view'
                  AND created_at >= :since
                  AND props->>'screen' IS NOT NULL
                GROUP BY 1
                ORDER BY users DESC
                LIMIT 12
                """
            ),
            {"since": week},
        )
    ).all()

    return {
        "users_total": total,
        "users_onboarded": onboarded,
        "dau": await _seen_since(day),
        "wau": await _seen_since(week),
        "mau": await _seen_since(month),
        "active_premium": active_subs,
        "purchases_7d": paid_week,
        "top_screens_7d": [
            {"screen": row[0], "users": int(row[1])} for row in top_screens if row[0]
        ],
    }
