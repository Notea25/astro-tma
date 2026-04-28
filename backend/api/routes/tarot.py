"""Tarot spread endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from api.schemas.tarot import (
    _IMAGE_BASE,
    DrawSpreadRequest,
    TarotCardDetail,
    TarotHistoryItem,
    TarotInterpretationResponse,
    TarotPositionNarrative,
    TarotSpreadResponse,
)
from core.cache import cache_get, cache_set, key_tarot_interpret
from core.logging import get_logger
from core.settings import settings
from db.database import get_db
from db.models import TarotCard, TarotPositionMeaning, TarotReading
from services.tarot.engine import (
    PREMIUM_SPREADS,
    draw_spread,
    to_reading_json,
)
from services.tarot.interpreter import (
    expected_card_count,
    generate_spread_interpretation,
    is_supported_spread,
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
            image_url=(_IMAGE_BASE + card.image_key) if card.image_key else None,
        ))

    return TarotSpreadResponse(
        reading_id=reading.id,
        spread_type=spread_type,
        cards=card_details,
        is_premium=spread_type in PREMIUM_SPREADS,
    )


@router.get("/history", response_model=list[TarotHistoryItem])
async def get_reading_history(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Last 30 readings for this user with card name previews."""
    result = await db.execute(
        select(TarotReading)
        .where(TarotReading.user_id == tg_user["id"])
        .order_by(TarotReading.created_at.desc())
        .limit(30)
    )
    readings = list(result.scalars())
    if not readings:
        return []

    # Gather all card ids referenced, then resolve names in one query
    all_ids: set[int] = set()
    for r in readings:
        for c in (r.cards_json or []):
            all_ids.add(c["card_id"])

    names_result = await db.execute(
        select(TarotCard.id, TarotCard.name_ru).where(TarotCard.id.in_(all_ids))
    )
    names = {row[0]: row[1] for row in names_result.all()}

    items: list[TarotHistoryItem] = []
    for r in readings:
        cards_json = r.cards_json or []
        sorted_cards = sorted(cards_json, key=lambda x: x.get("position", 0))
        previews = [names.get(c["card_id"], "?") for c in sorted_cards[:3]]
        items.append(
            TarotHistoryItem(
                reading_id=r.id,
                spread_type=r.spread_type,
                card_count=len(cards_json),
                card_previews=previews,
                created_at=r.created_at,
            )
        )
    return items


@router.get("/readings/{reading_id}", response_model=TarotSpreadResponse)
async def get_reading_by_id(
    reading_id: int,
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-open a past reading with full card details."""
    reading = await db.get(TarotReading, reading_id)
    if not reading or reading.user_id != tg_user["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reading not found")

    cards_json = reading.cards_json or []
    drawn_ids = [c["card_id"] for c in cards_json]

    cards_result = await db.execute(
        select(TarotCard).where(TarotCard.id.in_(drawn_ids))
    )
    cards_map: dict[int, TarotCard] = {c.id: c for c in cards_result.scalars()}

    pos_result = await db.execute(
        select(TarotPositionMeaning).where(
            TarotPositionMeaning.spread_type == reading.spread_type,
            TarotPositionMeaning.card_id.in_(drawn_ids),
        )
    )
    pos_meanings: dict[tuple[int, int], str] = {}
    pos_names: dict[tuple[int, int], str] = {}
    for pm in pos_result.scalars():
        pos_meanings[(pm.card_id, pm.position)] = pm.meaning_ru
        pos_names[(pm.card_id, pm.position)] = pm.position_name_ru

    card_details: list[TarotCardDetail] = []
    for drawn in sorted(cards_json, key=lambda x: x.get("position", 0)):
        card = cards_map.get(drawn["card_id"])
        if not card:
            continue
        reversed_flag = bool(drawn.get("reversed"))
        meaning = card.reversed_ru if reversed_flag else card.upright_ru
        card_details.append(
            TarotCardDetail(
                id=card.id,
                name_ru=card.name_ru,
                name_en=card.name_en,
                emoji=card.emoji,
                arcana=card.arcana.value,
                reversed=reversed_flag,
                meaning_ru=meaning,
                position_name_ru=pos_names.get((card.id, drawn["position"]), ""),
                position_meaning_ru=pos_meanings.get((card.id, drawn["position"])),
                keywords_ru=card.keywords_ru or [],
                image_url=(_IMAGE_BASE + card.image_key) if card.image_key else None,
            )
        )

    return TarotSpreadResponse(
        reading_id=reading.id,
        spread_type=reading.spread_type,
        cards=card_details,
        is_premium=reading.spread_type in PREMIUM_SPREADS,
    )


@router.post("/interpret/{reading_id}", response_model=TarotInterpretationResponse)
async def interpret_reading(
    reading_id: int,
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate (or return cached) LLM narrative interpretation for a reading.
    Supports three_card, celtic_cross, week, relationship. Each subsequent
    card is read in the context of previously drawn ones.
    """
    # Load reading and verify ownership
    reading = await db.get(TarotReading, reading_id)
    if not reading or reading.user_id != tg_user["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reading not found")

    if not is_supported_spread(reading.spread_type):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Interpretation not supported for {reading.spread_type}",
        )

    # Cache by reading_id — interpretation is deterministic for a given reading
    cache_key = key_tarot_interpret(reading.id)
    cached = await cache_get(cache_key)
    if cached:
        return TarotInterpretationResponse(**cached)

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Interpretation service is not configured",
        )

    # Resolve cards_json -> card details needed for the prompt
    cards_json = reading.cards_json or []
    expected_n = expected_card_count(reading.spread_type)
    drawn_ids = [c["card_id"] for c in cards_json]
    if len(drawn_ids) != expected_n:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Reading has unexpected card count (got {len(drawn_ids)}, expected {expected_n})",
        )

    cards_result = await db.execute(select(TarotCard).where(TarotCard.id.in_(drawn_ids)))
    cards_map: dict[int, TarotCard] = {c.id: c for c in cards_result.scalars()}

    prompt_cards: list[dict] = []
    for drawn in sorted(cards_json, key=lambda x: x["position"]):
        card = cards_map.get(drawn["card_id"])
        if not card:
            continue
        prompt_cards.append(
            {
                "name_ru": card.name_ru,
                "reversed": bool(drawn.get("reversed")),
                "keywords_ru": card.keywords_ru or [],
            }
        )

    try:
        parsed = await generate_spread_interpretation(
            spread_type=reading.spread_type,
            cards=prompt_cards,
            api_key=settings.ANTHROPIC_API_KEY,
        )
    except Exception as e:  # noqa: BLE001
        log.error(
            "tarot.interpret.failed",
            reading_id=reading.id,
            spread=reading.spread_type,
            error=str(e),
        )
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Interpretation failed — please try again",
        ) from e

    response = TarotInterpretationResponse(
        reading_id=reading.id,
        spread_type=reading.spread_type,
        positions=[TarotPositionNarrative(**p) for p in parsed["positions"]],
        summary=parsed["summary"],
    )

    await cache_set(cache_key, response.model_dump(), settings.CACHE_TTL_TAROT_INTERPRET)
    return response
