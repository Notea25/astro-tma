"""Referral programme endpoints — "share with a friend" only.

Tracks who-invited-whom for the stats panel ("X friends invited"). Does
NOT grant any trial days or Premium bonuses — that experiment was rolled
back, every user is now free-tier by default with paid features always
paywalled. The earlier `is_trial`, `trial_reason`, `days_granted`,
`referred_by_processed` plumbing in the DB schema stays for history.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from core.logging import get_logger
from core.settings import settings
from db.database import get_db
from db.models import (
    Purchase,
    PurchaseStatus,
    User,
)
from services.referrals.code import get_or_create_referral_code
from services.users import repository as user_repo

log = get_logger(__name__)
router = APIRouter(prefix="/referrals", tags=["referrals"])


class ApplyReferralRequest(BaseModel):
    code: str


class ApplyReferralResponse(BaseModel):
    success: bool
    message: str


class ReferralStats(BaseModel):
    invited_total: int
    purchased: int


class ReferralInfoResponse(BaseModel):
    code: str
    invite_url: str
    stats: ReferralStats


def _build_invite_url(code: str) -> str:
    bot = (settings.TELEGRAM_BOT_USERNAME or "").lstrip("@")
    if not bot:
        return ""
    return f"https://t.me/{bot}?start=ref_{code}"


@router.get("/me", response_model=ReferralInfoResponse)
async def get_my_referral_info(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = tg_user["id"]
    user = await user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    code = await get_or_create_referral_code(db, user_id)
    await db.commit()

    invited_total = (
        await db.execute(select(func.count(User.id)).where(User.referred_by == user_id))
    ).scalar_one() or 0
    purchased = (
        await db.execute(
            select(func.count(distinct(User.id)))
            .select_from(User)
            .join(Purchase, Purchase.user_id == User.id)
            .where(
                User.referred_by == user_id,
                Purchase.status == PurchaseStatus.COMPLETED,
                Purchase.stars_amount > 0,
            )
        )
    ).scalar_one() or 0
    return ReferralInfoResponse(
        code=code,
        invite_url=_build_invite_url(code),
        stats=ReferralStats(
            invited_total=int(invited_total),
            purchased=int(purchased),
        ),
    )


@router.post("/apply", response_model=ApplyReferralResponse)
async def apply_referral(
    body: ApplyReferralRequest,
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Frontend posts here once on first launch if start_param starts with
    `ref_`. Just records who-invited-whom for the stats panel — no Premium
    days are granted (the trial system was removed)."""
    referral_code = body.code.lower().strip()
    user_id = tg_user["id"]

    referrer = (
        await db.execute(select(User).where(User.referral_code == referral_code))
    ).scalar_one_or_none()
    if not referrer:
        return ApplyReferralResponse(success=False, message="Код не найден")

    if referrer.id == user_id:
        return ApplyReferralResponse(
            success=False, message="Нельзя пригласить самого себя",
        )

    referee = await user_repo.get_by_id(db, user_id)
    if not referee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    if referee.referred_by is not None:
        return ApplyReferralResponse(success=False, message="Код уже применён ранее")

    created_at = referee.created_at
    if created_at and (datetime.now(UTC) - created_at).total_seconds() > 86400:
        return ApplyReferralResponse(
            success=False,
            message="Код можно применить только в первые 24 часа после регистрации",
        )

    referee.referred_by = referrer.id
    referee.referred_by_processed = True
    await db.commit()
    log.info("referral.applied", referrer=referrer.id, referee=referee.id)
    return ApplyReferralResponse(success=True, message="Спасибо за приглашение!")
