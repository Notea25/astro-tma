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
)
from core.logging import get_logger
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

    pick = MacPick(
        user_id=tg_user["id"],
        card_number=body.card_number,
        card_name=body.card_name[:100],
        category=body.category,
    )
    db.add(pick)
    await db.flush()
    log.info(
        "mac.pick",
        user_id=tg_user["id"],
        card=body.card_number,
        category=body.category,
    )
    return MacPickResponse(pick_id=pick.id)


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
        MacPickHistoryItem(
            pick_id=p.id,
            card_number=p.card_number,
            card_name=p.card_name,
            category=p.category,
            created_at=p.created_at,
        )
        for p in result.scalars()
    ]
