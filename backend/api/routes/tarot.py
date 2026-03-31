"""Tarot spread endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from api.schemas.tarot import DrawSpreadRequest, TarotCardDetail, TarotSpreadResponse
from core.logging import get_logger
from db.database import get_db
from db.models import TarotCard, TarotPositionMeaning, TarotReading
from services.tarot.engine import (
    FREE_SPREADS, PREMIUM_SPREADS, draw_spread, to_reading_json,
)
from services.users import repository as user_repo

router = APIRouter(prefix="/tarot", tags=["tarot"])
log = get_logger(__name__)


@router.post("/draw", response_model=TarotSpreadResponse)
async def draw_tarot(
    body: DrawSpreadRequest,
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Draw a tarot spread.
    Free spreads: three_card (once per day).
    Premium spreads: celtic_cross, week, relationship.
    """
    spread_type = body.spread_type
    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    # Access control
    if spread_type in PREMIUM_SPREADS:
        is_prem = await user_repo.is_premium(db, user.id)
        has_purchase = await user_repo.has_purchased(db, user.id, f"tarot_{spread_type}")
        if not (is_prem or has_purchase):
            raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, f"{spread_type} requires Premium")

    # Load all card IDs
    result = await db.execute(select(TarotCard.id))
    card_ids = [row[0] for row in result.all()]

    if not card_ids:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Tarot deck not seeded")

    # Draw cards
    drawn = draw_spread(spread_type, card_ids)

    # Save reading to history
    reading = TarotReading(
        user_id=user.id,
        spread_type=spread_type,
        cards_json=to_reading_json(drawn),
    )
    db.add(reading)
    await db.flush()

    # Load card details + position meanings
    drawn_ids = [c.card_id for c in drawn.cards]
    cards_result = await db.execute(select(TarotCard).where(TarotCard.id.in_(drawn_ids)))
    cards_map: dict[int, TarotCard] = {c.id: c for c in cards_result.scalars()}

    # Load position meanings for this spread
    pos_result = await db.execute(
        select(TarotPositionMeaning).where(
            TarotPositionMeaning.spread_type == spread_type,
            TarotPositionMeaning.card_id.in_(drawn_ids),
        )
    )
    pos_meanings: dict[tuple[int, int], str] = {}
    for pm in pos_result.scalars():
        pos_meanings[(pm.card_id, pm.position)] = pm.meaning_ru

    # Build response
    card_details: list[TarotCardDetail] = []
    for drawn_card in drawn.cards:
        card = cards_map[drawn_card.card_id]
        meaning = card.reversed_ru if drawn_card.reversed else card.upright_ru
        pos_meaning = pos_meanings.get((drawn_card.card_id, drawn_card.position))

        card_details.append(TarotCardDetail(
            id=card.id,
            name_ru=card.name_ru,
            name_en=card.name_en,
            emoji=card.emoji,
            arcana=card.arcana.value,
            reversed=drawn_card.reversed,
            meaning_ru=meaning,
            position_name_ru=drawn_card.position_name_ru,
            position_meaning_ru=pos_meaning,
            keywords_ru=card.keywords_ru,
        ))

    return TarotSpreadResponse(
        reading_id=reading.id,
        spread_type=spread_type,
        cards=card_details,
        is_premium=spread_type in PREMIUM_SPREADS,
    )


@router.get("/history", response_model=list[dict])
async def get_reading_history(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Last 10 readings for this user."""
    result = await db.execute(
        select(TarotReading)
        .where(TarotReading.user_id == tg_user["id"])
        .order_by(TarotReading.created_at.desc())
        .limit(10)
    )
    return [r.to_dict() for r in result.scalars()]
