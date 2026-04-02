"""Natal chart endpoints — full chart retrieval and SVG generation."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from core.cache import cache_get, cache_set, key_natal
from core.settings import settings
from db.database import get_db
from services.astro.interpreter import get_natal_interpretation
from services.users import repository as user_repo

router = APIRouter(prefix="/natal", tags=["natal"])


@router.get("/summary")
async def get_natal_summary(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Basic (free) natal summary — sun, moon, ascendant.
    No birth time required for sun sign.
    """
    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    if not user.natal_chart:
        return {
            "has_chart": False,
            "sun_sign": user.sun_sign.value if user.sun_sign else None,
        }

    chart = user.natal_chart
    return {
        "has_chart": True,
        "sun_sign":       chart.sun_sign,
        "moon_sign":      chart.moon_sign,
        "ascendant_sign": chart.ascendant_sign,
        "birth_city":     user.birth_city,
        "birth_time_known": user.birth_time_known,
    }


@router.get("/full")
async def get_natal_full(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Full natal chart — premium or one-time purchase required.
    Returns all planetary positions + interpretations.
    """
    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    is_prem = await user_repo.is_premium(db, user.id)
    has_purchase = await user_repo.has_purchased(db, user.id, "natal_full")
    if not (is_prem or has_purchase):
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Premium or natal_full purchase required")

    if not user.natal_chart:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No birth data — set birth data first")

    # Check cache
    cache_key = key_natal(user.id)
    cached = await cache_get(cache_key)
    if cached:
        return cached

    chart = user.natal_chart
    planets = chart.chart_data.get("planets", {})

    # Fetch interpretations for each planet
    planet_signs = {
        planet: data["sign"].lower()
        for planet, data in planets.items()
        if planet not in ("sun", "moon")
    }

    interp_blocks = await get_natal_interpretation(
        db,
        sun_sign=chart.sun_sign.lower(),
        moon_sign=chart.moon_sign.lower(),
        asc_sign=chart.ascendant_sign.lower() if chart.ascendant_sign else None,
        planet_signs=planet_signs,
    )

    result = {
        "sun_sign":       chart.sun_sign,
        "moon_sign":      chart.moon_sign,
        "ascendant_sign": chart.ascendant_sign,
        "planets":        planets,
        "houses":         chart.chart_data.get("houses", []),
        "aspects":        chart.chart_data.get("aspects", [])[:10],  # top 10
        "interpretations": [
            {"planet": b.planet, "category": b.category, "text": b.text}
            for b in interp_blocks
        ],
    }

    await cache_set(cache_key, result, settings.CACHE_TTL_NATAL)
    return result
