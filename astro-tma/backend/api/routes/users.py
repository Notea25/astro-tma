"""User profile endpoints."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from api.schemas.user import SetupBirthDataRequest, SetupBirthDataResponse, UserProfile
from core.cache import cache_delete, key_natal, key_user_premium
from core.logging import get_logger
from core.settings import settings
from db.database import get_db
from db.models import ZodiacSign
from services.astro.natal import calculate_natal, chart_to_json
from services.users import repository as user_repo

router = APIRouter(prefix="/users", tags=["users"])
log = get_logger(__name__)

# Sun sign → ZodiacSign enum mapping (Kerykeion returns English names)
_SIGN_MAP: dict[str, ZodiacSign] = {s.value: s for s in ZodiacSign}
_KERY_TO_ENUM: dict[str, ZodiacSign] = {
    "Aries": ZodiacSign.ARIES, "Taurus": ZodiacSign.TAURUS,
    "Gemini": ZodiacSign.GEMINI, "Cancer": ZodiacSign.CANCER,
    "Leo": ZodiacSign.LEO, "Virgo": ZodiacSign.VIRGO,
    "Libra": ZodiacSign.LIBRA, "Scorpio": ZodiacSign.SCORPIO,
    "Sagittarius": ZodiacSign.SAGITTARIUS, "Capricorn": ZodiacSign.CAPRICORN,
    "Aquarius": ZodiacSign.AQUARIUS, "Pisces": ZodiacSign.PISCES,
}


@router.post("/me", response_model=UserProfile)
async def upsert_me(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Called on every Mini App launch to sync Telegram user data.
    Creates user on first launch, updates Telegram fields on subsequent ones.
    """
    user, created = await user_repo.get_or_create(
        db,
        tg_user_id=tg_user["id"],
        first_name=tg_user.get("first_name", ""),
        username=tg_user.get("username"),
        last_name=tg_user.get("last_name"),
        language_code=tg_user.get("language_code", "ru"),
        is_premium=tg_user.get("is_premium", False),
    )

    is_prem = await user_repo.is_premium(db, user.id)

    return UserProfile(
        id=user.id,
        name=user.tg_first_name,
        sun_sign=user.sun_sign.value if user.sun_sign else None,
        birth_city=user.birth_city,
        birth_time_known=user.birth_time_known,
        push_enabled=user.push_enabled,
        is_premium=is_prem,
        created_at=user.created_at,
    )


@router.post("/me/birth", response_model=SetupBirthDataResponse)
async def setup_birth_data(
    body: SetupBirthDataRequest,
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Set or update user's birth data.
    Triggers natal chart (re)calculation.
    Geocodes city via GeoNames API.
    """
    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    # Geocode birth city
    geo = await _geocode_city(body.birth_city)

    # Calculate natal chart
    chart = None
    try:
        chart = calculate_natal(
            name=user.tg_first_name,
            birth_dt=body.birth_date,
            lat=geo["lat"],
            lng=geo["lng"],
            tz_str=geo["tz"],
            birth_time_known=body.birth_time_known,
        )
    except Exception as e:
        log.error("natal.calculation_failed", user_id=user.id, error=str(e))

    sun_sign_enum = (
        _KERY_TO_ENUM.get(chart.sun.sign, ZodiacSign.ARIES)
        if chart and chart.sun and chart.sun.sign
        else ZodiacSign.ARIES
    )

    # Persist birth data
    await user_repo.update_birth_data(
        db, user,
        birth_date=body.birth_date,
        birth_time_known=body.birth_time_known,
        birth_city=geo["city"],
        lat=geo["lat"],
        lng=geo["lng"],
        tz_str=geo["tz"],
        sun_sign=sun_sign_enum,
    )

    # Persist natal chart only if calculation succeeded
    if chart:
        await user_repo.save_natal_chart(
            db,
            user_id=user.id,
            sun_sign=chart.sun.sign if chart.sun else "",
            moon_sign=chart.moon.sign if chart.moon else "",
            ascendant_sign=chart.ascendant_sign,
            chart_data=chart_to_json(chart),
        )

    # Invalidate caches
    await cache_delete(key_natal(user.id))

    return SetupBirthDataResponse(
        sun_sign=sun_sign_enum.value,
        moon_sign=chart.moon.sign if chart and chart.moon else "",
        ascendant_sign=chart.ascendant_sign if chart else None,
        city_resolved=geo["city"],
        lat=geo["lat"],
        lng=geo["lng"],
    )


async def _geocode_city(city: str) -> dict:
    """
    Resolve city name to lat/lng/tz via GeoNames free API.
    Falls back to Moscow if resolution fails.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "http://api.geonames.org/searchJSON",
                params={
                    "q": city,
                    "maxRows": 1,
                    "username": settings.GEONAMES_USERNAME,
                    "style": "FULL",
                },
            )
        data = resp.json()
        if data.get("geonames"):
            geo = data["geonames"][0]
            return {
                "city": geo.get("name", city),
                "lat": float(geo["lat"]),
                "lng": float(geo["lng"]),
                "tz": geo.get("timezone", {}).get("timeZoneId", "UTC"),
            }
    except Exception as e:
        log.warning("geocode.failed", city=city, error=str(e))

    # Default fallback
    return {"city": city, "lat": 55.7558, "lng": 37.6176, "tz": "Europe/Moscow"}
