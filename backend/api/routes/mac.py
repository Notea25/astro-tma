"""MAC (Metaphorical Associative Cards) — Зеркало Души."""

import random

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from api.schemas.mac import MacCardResponse, MacReadingResponse
from core.logging import get_logger
from db.database import get_db
from db.models import MacCard, MacReading
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
    """Last 10 MAC readings."""
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
