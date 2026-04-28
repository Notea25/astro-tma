"""User profile endpoints."""

from typing import TypedDict

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from api.schemas.user import (
    SetGenderRequest,
    SetPushRequest,
    SetupBirthDataRequest,
    SetupBirthDataResponse,
    UserProfile,
)
from core.cache import cache_delete, key_natal
from core.logging import get_logger
from db.database import get_db
from db.models import Gender, ZodiacSign
from services.astro.natal import calculate_natal, chart_to_json
from services.users import repository as user_repo

router = APIRouter(prefix="/users", tags=["users"])
log = get_logger(__name__)


class GeoResult(TypedDict):
    city: str
    lat: float
    lng: float
    tz: str


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
        gender=user.gender.value if user.gender else None,
        sun_sign=user.sun_sign.value if user.sun_sign else None,
        birth_city=user.birth_city,
        birth_time_known=user.birth_time_known,
        push_enabled=user.push_enabled,
        is_premium=is_prem,
        created_at=user.created_at,
    )


@router.post("/me/gender", response_model=UserProfile)
async def set_gender(
    body: SetGenderRequest,
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Set user gender."""
    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    gender_enum = Gender(body.gender)
    user.gender = gender_enum
    await db.commit()

    is_prem = await user_repo.is_premium(db, user.id)
    return UserProfile(
        id=user.id,
        name=user.tg_first_name,
        gender=user.gender.value if user.gender else None,
        sun_sign=user.sun_sign.value if user.sun_sign else None,
        birth_city=user.birth_city,
        birth_time_known=user.birth_time_known,
        push_enabled=user.push_enabled,
        is_premium=is_prem,
        created_at=user.created_at,
    )


@router.patch("/me/push", response_model=UserProfile)
async def set_push_enabled(
    body: SetPushRequest,
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle push notifications for the current user."""
    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    user.push_enabled = body.enabled
    await db.commit()

    is_prem = await user_repo.is_premium(db, user.id)
    return UserProfile(
        id=user.id,
        name=user.tg_first_name,
        gender=user.gender.value if user.gender else None,
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

    # Use pre-resolved coordinates if provided, otherwise geocode
    if body.lat is not None and body.lng is not None:
        tz = await _get_timezone(body.lat, body.lng)
        geo: GeoResult = {"city": body.birth_city, "lat": body.lat, "lng": body.lng, "tz": tz}
        log.info("geocode.from_client", city=body.birth_city, lat=body.lat, lng=body.lng)
    else:
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


async def _get_timezone(lat: float, lng: float) -> str:
    """Resolve timezone from coordinates via timeapi.io (free, no key)."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://timeapi.io/api/timezone/coordinate",
                params={"latitude": lat, "longitude": lng},
            )
        data = resp.json()
        return data.get("timeZone", "UTC")
    except Exception:
        return "UTC"


async def _geocode_city(city: str) -> GeoResult:
    """
    Resolve city name to lat/lng/tz via Nominatim (OpenStreetMap).
    Free, no API key required. Falls back to Moscow on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": city,
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 1,
                },
                headers={"User-Agent": "astro-tma/1.0"},
            )
        data = resp.json()
        if data:
            place = data[0]
            lat = float(place["lat"])
            lng = float(place["lon"])
            name = (
                place.get("address", {}).get("city")
                or place.get("address", {}).get("town")
                or place.get("address", {}).get("village")
                or place.get("name")
                or city
            )
            tz = await _get_timezone(lat, lng)
            log.info("geocode.ok", city=name, lat=lat, lng=lng, tz=tz)
            return {"city": name, "lat": lat, "lng": lng, "tz": tz}
    except Exception as e:
        log.warning("geocode.failed", city=city, error=str(e))

    # Default fallback
    log.warning("geocode.fallback_moscow", city=city)
    return {"city": city, "lat": 55.7558, "lng": 37.6176, "tz": "Europe/Moscow"}
