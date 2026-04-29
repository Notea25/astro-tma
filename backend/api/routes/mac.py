"""MAC (Metaphorical Associative Cards) — Зеркало Души."""

import random

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from api.schemas.mac import (
    MacCardResponse,
    MacPickHistoryItem,
    MacPickRequest,
    MacPickResponse,
    MacReadingResponse,
    MacTodayResponse,
)
from core.logging import get_logger
from core.periods import DAILY, is_active_period, next_reset_at, now_utc
from db.database import get_db
from db.models import MacCard, MacPick, MacReading
from services.users import repository as user_repo

router = APIRouter(prefix="/mac", tags=["mac"])
log = get_logger(__name__)


@router.post("/draw", response_model=MacReadingResponse)
async def draw_mac_card(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Draw a single metaphorical card. Free, once per day."""
    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    # Pick a random card
    result = await db.execute(select(MacCard))
    all_cards = list(result.scalars())
    if not all_cards:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "MAC deck not seeded")

    card = random.choice(all_cards)

    # Save reading
    reading = MacReading(user_id=user.id, card_id=card.id)
    db.add(reading)
    await db.flush()

    return MacReadingResponse(
        reading_id=reading.id,
        card=MacCardResponse(
            id=card.id,
            name_ru=card.name_ru,
            category=card.category.value,
            emoji=card.emoji,
            description_ru=card.description_ru,
            question_ru=card.question_ru,
            affirmation_ru=card.affirmation_ru,
            image_url=None,
        ),
    )


@router.get("/history", response_model=list[MacCardResponse])
async def mac_history(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Last 10 MAC readings (legacy endpoint, kept for backward compat)."""
    result = await db.execute(
        select(MacReading)
        .where(MacReading.user_id == tg_user["id"])
        .order_by(MacReading.created_at.desc())
        .limit(10)
    )
    readings = list(result.scalars())
    cards = []
    for r in readings:
        await db.refresh(r, ["card"])
        c = r.card
        cards.append(MacCardResponse(
            id=c.id, name_ru=c.name_ru, category=c.category.value,
            emoji=c.emoji, description_ru=c.description_ru,
            question_ru=c.question_ru, affirmation_ru=c.affirmation_ru,
            image_url=None,
        ))
    return cards


# ── Client-driven 48-card deck (new flow) ────────────────────────────────────

_VALID_CATEGORIES = {
    "inner_world",
    "relationships",
    "path",
    "fears",
    "resources",
    "transformation",
}


def _pick_history_item(pick: MacPick) -> MacPickHistoryItem:
    return MacPickHistoryItem(
        pick_id=pick.id,
        card_number=pick.card_number,
        card_name=pick.card_name,
        category=pick.category,
        created_at=pick.created_at,
    )


def _pick_response(pick: MacPick, *, reused_existing: bool = False) -> MacPickResponse:
    return MacPickResponse(
        pick_id=pick.id,
        card_number=pick.card_number,
        card_name=pick.card_name,
        category=pick.category,
        created_at=pick.created_at,
        next_reset_at=next_reset_at(pick.created_at, DAILY),
        reused_existing=reused_existing,
    )


async def _latest_active_pick(db: AsyncSession, user_id: int) -> MacPick | None:
    result = await db.execute(
        select(MacPick)
        .where(MacPick.user_id == user_id)
        .order_by(MacPick.created_at.desc())
        .limit(1)
    )
    pick = result.scalar_one_or_none()
    if pick and is_active_period(pick.created_at, DAILY, now=now_utc()):
        return pick
    return None


@router.get("/today", response_model=MacTodayResponse)
async def mac_today(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Return today's MAC pick, if one exists, plus the next daily reset time."""
    pick = await _latest_active_pick(db, tg_user["id"])
    reset_base = pick.created_at if pick else now_utc()
    return MacTodayResponse(
        pick=_pick_history_item(pick) if pick else None,
        next_reset_at=next_reset_at(reset_base, DAILY),
    )


@router.post("/pick", response_model=MacPickResponse)
async def log_mac_pick(
    body: MacPickRequest,
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a pick from the client-side 48-card MAC deck."""
    if not (1 <= body.card_number <= 48):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "card_number must be 1..48"
        )
    if body.category not in _VALID_CATEGORIES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"unknown category: {body.category}"
        )

    existing = await _latest_active_pick(db, tg_user["id"])
    if existing:
        return _pick_response(existing, reused_existing=True)

    pick = MacPick(
        user_id=tg_user["id"],
        card_number=body.card_number,
        card_name=body.card_name[:100],
        category=body.category,
    )
    db.add(pick)
    await db.flush()
    await db.refresh(pick)
    log.info(
        "mac.pick",
        user_id=tg_user["id"],
        card=body.card_number,
        category=body.category,
    )
    return _pick_response(pick)


@router.get("/picks", response_model=list[MacPickHistoryItem])
async def mac_picks_history(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Last 30 MAC picks for this user, newest first."""
    result = await db.execute(
        select(MacPick)
        .where(MacPick.user_id == tg_user["id"])
        .order_by(MacPick.created_at.desc())
        .limit(30)
    )
    return [
        _pick_history_item(p)
        for p in result.scalars()
    ]
