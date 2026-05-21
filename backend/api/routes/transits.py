"""Transit endpoints — current planetary positions vs user's natal chart."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from api.schemas.transits import (
    EnergyScores,
    RetrogradeInfo,
    SkyPosition,
    TransitAspect,
    TransitCategory,
    TransitDetailsRequest,
    TransitDetailsResponse,
    TransitsResponse,
)
from core.cache import cache_get, cache_set
from core.logging import get_logger
from core.settings import settings
from db.database import get_db
from services.astro.transit_interpreter import (
    get_or_generate_transit_texts,
    get_transit_details,
)
from services.astro.transits import (
    build_energy_scores,
    calculate_transits,
    get_current_sky,
)
from services.users import repository as user_repo

log = get_logger(__name__)
router = APIRouter(prefix="/transits", tags=["transits"])

_PLANET_RU: dict[str, str] = {
    "sun": "Солнце", "moon": "Луна", "mercury": "Меркурий", "venus": "Венера",
    "mars": "Марс", "jupiter": "Юпитер", "saturn": "Сатурн",
    "uranus": "Уран", "neptune": "Нептун", "pluto": "Плутон",
    # Chart axes
    "ascendant": "Асцендент",
    "descendant": "Десцендент",
    "medium_coeli": "Середина неба",
    "imum_coeli": "Глубина неба",
    # Lunar nodes (kerykeion uses several variants)
    "mean_node": "Северный узел",
    "true_node": "Северный узел",
    "mean_lunar_node": "Северный узел",
    "true_lunar_node": "Северный узел",
    "mean_north_lunar_node": "Северный узел",
    "true_north_lunar_node": "Северный узел",
    "mean_south_node": "Южный узел",
    "true_south_node": "Южный узел",
    "mean_south_lunar_node": "Южный узел",
    "true_south_lunar_node": "Южный узел",
    # Lilith (Black Moon)
    "mean_lilith": "Лилит",
    "true_lilith": "Лилит",
    "black_moon_lilith": "Лилит",
    # Other points
    "chiron": "Хирон",
}

_ASPECT_RU: dict[str, str] = {
    "conjunction": "Соединение", "opposition": "Оппозиция", "square": "Квадрат",
    "trine": "Трин", "sextile": "Секстиль",
}

_SIGN_RU: dict[str, str] = {
    "aries": "Овен", "taurus": "Телец", "gemini": "Близнецы",
    "cancer": "Рак", "leo": "Лев", "virgo": "Дева",
    "libra": "Весы", "scorpio": "Скорпион", "sagittarius": "Стрелец",
    "capricorn": "Козерог", "aquarius": "Водолей", "pisces": "Рыбы",
}

_SIGN_ABBR: dict[str, str] = {
    "Ari": "aries", "Tau": "taurus", "Gem": "gemini", "Can": "cancer",
    "Leo": "leo",   "Vir": "virgo",  "Lib": "libra",  "Sco": "scorpio",
    "Sag": "sagittarius", "Cap": "capricorn", "Aqu": "aquarius", "Pis": "pisces",
}

_PLANET_GLYPH: dict[str, str] = {
    "sun": "☉", "moon": "☽", "mercury": "☿", "venus": "♀", "mars": "♂",
    "jupiter": "♃", "saturn": "♄", "uranus": "♅", "neptune": "♆", "pluto": "♇",
    "ascendant": "Asc", "descendant": "Dsc",
    "medium_coeli": "MC", "imum_coeli": "IC",
    "mean_node": "☊", "true_node": "☊",
    "mean_lunar_node": "☊", "true_lunar_node": "☊",
    "mean_north_lunar_node": "☊", "true_north_lunar_node": "☊",
    "mean_south_node": "☋", "true_south_node": "☋",
    "mean_south_lunar_node": "☋", "true_south_lunar_node": "☋",
    "mean_lilith": "⚸", "true_lilith": "⚸", "black_moon_lilith": "⚸",
    "chiron": "⚷",
}

# Short, viral-friendly retrograde blurbs — written for a general audience.
_RETRO_BLURB: dict[str, str] = {
    "mercury": "Двойная проверка переписки и техники не повредит. Старые разговоры могут всплыть — есть шанс закрыть их по-новому.",
    "venus": "Старые чувства просыпаются: бывшие пишут, забытые вкусы возвращаются. Не торопитесь с новыми покупками и обещаниями.",
    "mars": "Дайте себе паузу: резкие решения и спор сейчас обходятся дороже. Лучше доделать начатое, чем рваться вперёд.",
    "jupiter": "Хорошее время сверить ориентиры — куда вы вообще идёте и что из старых планов ещё ваше. С большими шагами можно подождать.",
    "saturn": "Всё, что давно требовало внимания — обязательства, дисциплина, границы — даст о себе знать. Самое время навести порядок.",
    "uranus": "Внутри что-то меняется быстрее, чем снаружи. Можно неожиданно понять, что устарело, и без шума отпустить лишнее.",
    "neptune": "Мечтать и фантазировать — пожалуйста. А вот подписывать важное и верить на слово — лучше потом, когда туман рассеется.",
    "pluto": "Глубинные темы поднимаются: старые страхи, привязанности, контроль. Не бойтесь смотреть — это и есть взросление.",
}

_SUPPORT_PLANETS = {"venus", "jupiter"}
_TENSION_PLANETS = {"mars", "saturn"}
_TRANSFORMATION_PLANETS = {"pluto", "uranus", "neptune"}
_SOFT_ASPECTS = {"trine", "sextile"}
_HARD_ASPECTS = {"square", "opposition"}


def _classify_transit(transit_planet: str, natal_planet: str, aspect: str) -> TransitCategory:
    """Categorize transit per spec §6:
    - Transformation — any aspect with outer planets (Pluto/Uranus/Neptune)
    - Support — trine/sextile, OR conjunction with Venus/Jupiter
    - Tension — square/opposition with Mars/Saturn/Moon
    - Neutral — everything else
    """
    tp = transit_planet.lower()
    np = natal_planet.lower()
    ap = aspect.lower()

    if tp in _TRANSFORMATION_PLANETS or np in _TRANSFORMATION_PLANETS:
        return "transformation"

    if ap in _SOFT_ASPECTS:
        return "support"
    if ap == "conjunction" and (tp in _SUPPORT_PLANETS or np in _SUPPORT_PLANETS):
        return "support"

    if ap in _HARD_ASPECTS and (
        tp in _TENSION_PLANETS or np in _TENSION_PLANETS or tp == "moon" or np == "moon"
    ):
        return "tension"

    return "neutral"


_TRANSITS_TTL = 21600  # 6h


def _key(user_id: int, d: str) -> str:
    return f"transits:{user_id}:{d}"


def _normalize_sign(raw: str) -> str:
    if not raw:
        return "unknown"
    if raw in _SIGN_ABBR:
        return _SIGN_ABBR[raw]
    return raw.lower()


async def _build_response(
    db: AsyncSession,
    raw_transits: list[dict],
    sign: str,
    response_date: date | None = None,
) -> TransitsResponse:
    scores = build_energy_scores(raw_transits, sign)
    sky_raw = get_current_sky()

    # Per-pair interpretations — cached in transit_interpretations by
    # (transit_planet, natal_planet, aspect). Replaces the old static
    # ASPECT_HINT that gave one text for every trine, every square, etc.
    texts = await get_or_generate_transit_texts(
        db, raw_transits, settings.ANTHROPIC_API_KEY
    )

    aspects = []
    for t in raw_transits:
        tp = t["transit_planet"].lower()
        np = t["natal_planet"].lower()
        ap = t["aspect"]
        aspects.append(
            TransitAspect(
                transit_planet=t["transit_planet"],
                natal_planet=t["natal_planet"],
                aspect=ap,
                orb=t["orb"],
                weight=t["weight"],
                transit_planet_ru=_PLANET_RU.get(tp, t["transit_planet"]),
                natal_planet_ru=_PLANET_RU.get(np, t["natal_planet"]),
                aspect_ru=_ASPECT_RU.get(ap, ap),
                transit_retrograde=t.get("transit_retrograde", False),
                applying=t.get("applying"),
                text_ru=texts.get((tp, np, ap)) or None,
                category=_classify_transit(tp, np, ap),
            )
        )

    sky: dict[str, SkyPosition] = {}
    retrogrades: list[RetrogradeInfo] = []
    for planet, data in sky_raw.items():
        s = _normalize_sign(data["sign"])
        sky[planet] = SkyPosition(
            sign=s,
            sign_ru=_SIGN_RU.get(s, s),
            degree=data["degree"],
            retrograde=data["retrograde"],
        )
        if data["retrograde"] and planet.lower() in _RETRO_BLURB:
            retrogrades.append(
                RetrogradeInfo(
                    planet=planet,
                    planet_ru=_PLANET_RU.get(planet.lower(), planet),
                    glyph=_PLANET_GLYPH.get(planet.lower(), "●"),
                    sign=s,
                    sign_ru=_SIGN_RU.get(s, s),
                    description_ru=_RETRO_BLURB[planet.lower()],
                )
            )

    return TransitsResponse(
        date=response_date or date.today(),
        aspects=aspects,
        energy=EnergyScores(**scores),
        sky=sky,
        retrogrades=retrogrades,
    )


@router.get("/current", response_model=TransitsResponse)
async def get_current_transits(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Current transits against user's natal chart + energy scores."""
    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if not user.natal_chart or not user.birth_date or not user.birth_tz:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "No birth data — complete profile first",
        )

    today_str = date.today().isoformat()
    cache_key = _key(user.id, today_str)
    cached = await cache_get(cache_key)
    if cached:
        return TransitsResponse(**cached)

    raw_transits = calculate_transits(
        birth_dt=user.birth_date,
        lat=user.birth_lat or 0.0,
        lng=user.birth_lng or 0.0,
        tz_str=user.birth_tz,
        birth_time_known=user.birth_time_known,
    )

    sign = user.sun_sign.value if user.sun_sign else "aries"
    response = await _build_response(db, raw_transits, sign)

    await cache_set(cache_key, response.model_dump(mode="json"), _TRANSITS_TTL)
    return response


@router.get("/date", response_model=TransitsResponse)
async def get_transits_by_date(
    date_str: str = Query(..., alias="date", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Transits for arbitrary date (YYYY-MM-DD)."""
    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if not user.natal_chart or not user.birth_date or not user.birth_tz:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "No birth data — complete profile first",
        )

    try:
        target = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid date format")

    cache_key = _key(user.id, date_str)
    cached = await cache_get(cache_key)
    if cached:
        return TransitsResponse(**cached)

    raw_transits = calculate_transits(
        birth_dt=user.birth_date,
        lat=user.birth_lat or 0.0,
        lng=user.birth_lng or 0.0,
        tz_str=user.birth_tz,
        birth_time_known=user.birth_time_known,
        dt=target,
    )

    sign = user.sun_sign.value if user.sun_sign else "aries"
    response = await _build_response(db, raw_transits, sign, response_date=target.date())

    await cache_set(cache_key, response.model_dump(mode="json"), _TRANSITS_TTL)
    return response


@router.post("/details", response_model=TransitDetailsResponse)
async def get_transit_details_endpoint(
    payload: TransitDetailsRequest,
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Deep-dive for the "What does this mean for me" CTA on the Transits hero.
    Returns the cached blurb plus practical do/avoid advice and the life-sphere
    (natal house) that the transit activates. Advice is lazy-generated and
    cached per (transit_planet, natal_planet, aspect) triple.
    """
    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    chart = user.natal_chart.chart_data if user.natal_chart else None

    details = await get_transit_details(
        db,
        transit_planet=payload.transit_planet,
        natal_planet=payload.natal_planet,
        aspect=payload.aspect,
        natal_chart=chart,
        api_key=settings.ANTHROPIC_API_KEY,
    )
    return TransitDetailsResponse(**details)
