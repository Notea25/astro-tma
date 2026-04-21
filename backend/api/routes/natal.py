"""Natal chart endpoints — full chart retrieval and SVG generation."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from core.cache import cache_get, cache_set, key_natal
from core.logging import get_logger
from core.settings import settings
from db.database import get_db
from services.astro.interpreter import get_natal_interpretation
from services.astro.llm_interpreter import generate_natal_reading
from services.users import repository as user_repo

log = get_logger(__name__)

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

    # Full planet positions for wheel
    planets_for_wheel = {}
    raw_planets = chart.chart_data.get("planets", {})
    for name, data in raw_planets.items():
        planets_for_wheel[name] = {
            "degree":      data.get("degree", 0),       # absolute 0–360
            "sign_degree": data.get("sign_degree", 0),  # within-sign 0–30
            "sign":        data.get("sign", ""),
            "house":       data.get("house", 1),
            "retrograde":  data.get("retrograde", False),
        }

    # House cusps with sign
    houses_for_wheel = []
    for h in chart.chart_data.get("houses", []):
        houses_for_wheel.append({
            "number": h.get("number", 0),
            "degree": h.get("degree", 0),
            "sign":   h.get("sign", ""),
        })

    # Birth date / time
    birth_date_str = user.birth_date.strftime("%Y-%m-%d") if user.birth_date else None
    birth_time_str = user.birth_date.strftime("%H:%M") if (user.birth_date and user.birth_time_known) else "12:00"

    return {
        "has_chart":        True,
        "sun_sign":         chart.sun_sign,
        "moon_sign":        chart.moon_sign,
        "ascendant_sign":   chart.ascendant_sign,
        "mc_sign":          chart.chart_data.get("mc_sign"),
        "birth_city":       user.birth_city,
        "birth_time_known": user.birth_time_known,
        "birth_lat":        user.birth_lat,
        "birth_lng":        user.birth_lng,
        "birth_tz":         user.birth_tz,
        "birth_date":       birth_date_str,
        "birth_time":       birth_time_str,
        "planets":          planets_for_wheel,
        "houses":           houses_for_wheel,
        "aspects":          chart.chart_data.get("aspects", []),
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

    # Generate LLM interpretation if API key is set
    llm_reading: str | None = None
    if settings.ANTHROPIC_API_KEY:
        try:
            llm_reading = await generate_natal_reading(
                sun_sign=chart.sun_sign,
                moon_sign=chart.moon_sign,
                ascendant_sign=chart.ascendant_sign,
                planets=planets,
                aspects=chart.chart_data.get("aspects", [])[:10],
                api_key=settings.ANTHROPIC_API_KEY,
            )
        except Exception as e:
            log.error("natal.llm_failed", user_id=user.id, error=str(e))

    result = {
        "sun_sign":       chart.sun_sign,
        "moon_sign":      chart.moon_sign,
        "ascendant_sign": chart.ascendant_sign,
        "planets":        planets,
        "houses":         chart.chart_data.get("houses", []),
        "aspects":        chart.chart_data.get("aspects", [])[:10],
        "interpretations": [
            {"planet": b.planet, "category": b.category, "text": b.text}
            for b in interp_blocks
        ],
        "reading": llm_reading,
    }

    await cache_set(cache_key, result, settings.CACHE_TTL_NATAL)
    return result


@router.get("/pdf")
async def get_natal_pdf(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return natal chart PDF report."""
    from services.natal_pdf import generate_natal_pdf

    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    is_prem = await user_repo.is_premium(db, user.id)
    has_purchase = await user_repo.has_purchased(db, user.id, "natal_full")
    if not (is_prem or has_purchase):
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Premium required")

    if not user.natal_chart:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No birth data")

    chart = user.natal_chart
    planets = chart.chart_data.get("planets", {})
    houses = chart.chart_data.get("houses", [])
    aspects_raw = chart.chart_data.get("aspects", [])
    aspects = [
        {"p1": a.get("p1",""), "p2": a.get("p2",""), "aspect": a.get("aspect",""), "orb": a.get("orb",0)}
        for a in aspects_raw
    ]

    # Get cached reading if available
    cache_key = key_natal(user.id)
    cached = await cache_get(cache_key)
    reading = cached.get("reading") if cached else None

    pdf_bytes = generate_natal_pdf(
        user_name=user.tg_first_name or "User",
        birth_date=str(user.birth_date) if user.birth_date else "",
        birth_time=str(user.birth_time)[:5] if getattr(user, 'birth_time', None) else None,
        birth_city=user.birth_city or "",
        sun_sign=chart.sun_sign or "",
        moon_sign=chart.moon_sign or "",
        asc_sign=chart.ascendant_sign,
        planets=planets,
        houses=houses,
        aspects=aspects,
        reading=reading,
    )

    filename = f"natal_{user.tg_first_name or 'chart'}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
