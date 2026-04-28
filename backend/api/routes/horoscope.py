"""Horoscope, moon phase, and natal chart endpoints."""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from api.schemas.horoscope import (
    EnergyScores, HoroscopeResponse, MoonCalendarDay,
    MoonCalendarResponse, MoonPhaseResponse,
)
from core.cache import (
    cache_get, cache_set,
    key_horoscope, key_moon, key_natal,
)
from core.logging import get_logger
from core.settings import settings
from db.database import get_db
from db.models import DailyHoroscope, HoroscopePeriod, NatalChart, ZodiacSign
from services.astro.moon import get_moon_phase, get_monthly_calendar
from services.astro.natal import NatalChartData, chart_to_json
from services.astro.transits import build_energy_scores
from services.users import repository as user_repo

router = APIRouter(prefix="/horoscope", tags=["horoscope"])
log = get_logger(__name__)

# Russian sign names
_SIGN_RU: dict[str, str] = {
    "aries": "Овен", "taurus": "Телец", "gemini": "Близнецы",
    "cancer": "Рак", "leo": "Лев", "virgo": "Дева",
    "libra": "Весы", "scorpio": "Скорпион", "sagittarius": "Стрелец",
    "capricorn": "Козерог", "aquarius": "Водолей", "pisces": "Рыбы",
}

# Generic daily texts (fallback when no personalised text available)
_GENERIC_TEXTS: dict[str, str] = {
    "aries": "Сегодня Марс придаёт вам энергию и решимость. Идеальный день для новых начинаний.",
    "taurus": "Венера благоволит вашим финансовым делам. Будьте внимательны к деталям.",
    "gemini": "Меркурий активизирует общение. Важные переговоры пройдут успешно.",
    "cancer": "Луна в гармонии с вашим знаком усиливает интуицию. Доверяйте чувствам.",
    "leo": "Солнце освещает ваш творческий путь. Время заявить о себе.",
    "virgo": "Практичность и внимание к деталям принесут плоды. Ваш труд замечен.",
    "libra": "Венера создаёт гармонию в отношениях. Время для важных разговоров.",
    "scorpio": "Плутон усиливает вашу проницательность. Тайное становится явным.",
    "sagittarius": "Юпитер открывает новые горизонты. Расширяйте границы привычного.",
    "capricorn": "Сатурн укрепляет ваши позиции. Дисциплина принесёт результат.",
    "aquarius": "Уран приносит неожиданные озарения. Будьте открыты переменам.",
    "pisces": "Нептун усиливает творческое вдохновение. Следуйте своей мечте.",
}


@router.get("/today", response_model=HoroscopeResponse)
async def get_today_horoscope(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Today's horoscope. Personalised if user has birth data, generic otherwise.
    Free for all users. Response is cached per sign per day.
    """
    user = await user_repo.get_by_id(db, tg_user["id"])
    sign = user.sun_sign.value if (user and user.sun_sign) else "aries"
    today = date.today().isoformat()

    # Try personalised (if natal chart exists)
    if user and user.natal_chart:
        return await _personalised_horoscope(user, sign, today, "today")

    # Generic sign horoscope — check cache first
    cache_key = key_horoscope(sign, today, "today")
    cached = await cache_get(cache_key)
    if cached:
        return HoroscopeResponse(**cached)

    # Try LLM generation
    from services.astro.llm_horoscope import (
        generate_daily_horoscope, generate_energy_scores_llm,
    )
    text = await generate_daily_horoscope(sign, date.today(), "today")
    if not text:
        text = _GENERIC_TEXTS.get(sign, _GENERIC_TEXTS["aries"])
    scores = await generate_energy_scores_llm(sign, date.today())

    response = HoroscopeResponse(
        sign=sign,
        sign_ru=_SIGN_RU.get(sign, sign),
        date=date.today(),
        period="today",
        text_ru=text,
        energy=EnergyScores(**scores),
        is_personalised=False,
    )
    await cache_set(cache_key, response.model_dump(mode="json"), settings.CACHE_TTL_HOROSCOPE)
    return response


@router.get("/period", response_model=HoroscopeResponse)
async def get_period_horoscope(
    period: str = Query(..., pattern="^(tomorrow|week|month)$"),
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Premium endpoint — requires active subscription or period purchase."""
    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    product_map = {
        "tomorrow": "horoscope_tomorrow",
        "week": "horoscope_week",
        "month": "horoscope_month",
    }
    is_prem = await user_repo.is_premium(db, user.id)
    has_purchase = await user_repo.has_purchased(db, user.id, product_map[period])

    if not (is_prem or has_purchase):
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Premium required")

    sign = user.sun_sign.value if user.sun_sign else "aries"
    today = date.today()

    # Check cache
    cache_key = key_horoscope(sign, today.isoformat(), period)
    cached = await cache_get(cache_key)
    if cached:
        return HoroscopeResponse(**cached)

    # Generate via LLM
    from services.astro.llm_horoscope import (
        generate_daily_horoscope, generate_energy_scores_llm,
    )
    text = await generate_daily_horoscope(sign, today, period)
    if not text:
        text = _GENERIC_TEXTS.get(sign, "")
    scores = await generate_energy_scores_llm(sign, today)

    response = HoroscopeResponse(
        sign=sign,
        sign_ru=_SIGN_RU.get(sign, sign),
        date=today,
        period=period,
        text_ru=text,
        energy=EnergyScores(**scores),
        is_personalised=bool(user.natal_chart),
    )
    await cache_set(cache_key, response.model_dump(mode="json"), settings.CACHE_TTL_HOROSCOPE)
    return response


@router.get("/moon", response_model=MoonPhaseResponse)
async def get_moon_today(tg_user: dict = Depends(get_tg_user)):
    """Current moon phase — free for all users."""
    today = date.today().isoformat()
    cache_key = key_moon(today)

    cached = await cache_get(cache_key)
    if cached:
        return MoonPhaseResponse(**cached)

    phase = get_moon_phase()
    response = MoonPhaseResponse(
        phase_name=phase.phase_name,
        phase_name_ru=phase.phase_name_ru,
        emoji=phase.emoji,
        description_ru=phase.description_ru,
        illumination=phase.illumination,
        date=phase.date,
        favorable_actions=phase.favorable_actions,
        avoid_actions=phase.avoid_actions,
    )
    await cache_set(cache_key, response.model_dump(mode="json"), settings.CACHE_TTL_MOON)
    return response


@router.get("/moon/calendar", response_model=MoonCalendarResponse)
async def get_moon_calendar(
    year: int = Query(default=None),
    month: int = Query(default=None),
    tg_user: dict = Depends(get_tg_user),
):
    """Monthly lunar calendar. Free."""
    now = datetime.now(timezone.utc)
    y = year or now.year
    m = month or now.month

    cache_key = key_moon(f"{y}-{m:02d}")
    cached = await cache_get(cache_key)
    if cached:
        return MoonCalendarResponse(**cached)

    days_data = get_monthly_calendar(y, m)
    response = MoonCalendarResponse(
        year=y, month=m,
        days=[MoonCalendarDay(**d) for d in days_data],
    )
    await cache_set(cache_key, response.model_dump(mode="json"), settings.CACHE_TTL_MOON)
    return response


async def _personalised_horoscope(
    user, sign: str, today: str, period: str
) -> HoroscopeResponse:
    """Build a personalised horoscope via LLM, with transit fallback."""
    from services.astro.llm_horoscope import (
        generate_daily_horoscope, generate_energy_scores_llm,
    )

    # Check cache first
    cache_key = key_horoscope(sign, today, period)
    cached = await cache_get(cache_key)
    if cached:
        # Mark as personalised
        cached["is_personalised"] = True
        return HoroscopeResponse(**cached)

    # Generate via LLM
    text = await generate_daily_horoscope(sign, date.today(), period)
    if not text:
        text = _GENERIC_TEXTS.get(sign, _GENERIC_TEXTS["aries"])
    scores = await generate_energy_scores_llm(sign, date.today())

    response = HoroscopeResponse(
        sign=sign,
        sign_ru=_SIGN_RU.get(sign, sign),
        date=date.today(),
        period=period,
        text_ru=text,
        energy=EnergyScores(**scores),
        is_personalised=True,
    )
    await cache_set(cache_key, response.model_dump(mode="json"), settings.CACHE_TTL_HOROSCOPE)
    return response
