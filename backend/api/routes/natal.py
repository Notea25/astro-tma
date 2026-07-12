"""Natal chart endpoints — full chart retrieval and SVG generation."""

import re
from io import BytesIO
from secrets import token_urlsafe
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from core.cache import (
    cache_get,
    cache_set,
    get_redis,
    key_natal,
    key_natal_pdf_download,
    key_natal_pdf_job,
    key_natal_wheel_svg,
)
from core.logging import get_logger
from core.settings import settings
from db.database import get_db
from services.astro.dominants import compute_dominants
from services.astro.interpreter import get_natal_interpretation
from services.astro.key_aspects import top_n_aspects
from services.astro.llm_interpreter import (
    generate_natal_mini_reading,
    generate_natal_reading,
)
from services.astro.natal_descriptions import generate_natal_descriptions
from services.astro.natal_hero import (
    build_aspects_hero,
    build_elements_hero,
    build_houses_hero,
    build_planets_hero,
)
from services.users import repository as user_repo

log = get_logger(__name__)

router = APIRouter(prefix="/natal", tags=["natal"])
_PDF_DOWNLOAD_TTL_SECONDS = 300
_WHEEL_SVG_MAX_BYTES = 512 * 1024
_WHEEL_SVG_TTL_SECONDS = 24 * 60 * 60
_PDF_DESCRIPTION_ASPECT_LIMIT = 12

_SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script\s*>", re.IGNORECASE | re.DOTALL)
_ON_HANDLER_RE = re.compile(r"\son[a-z]+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", re.IGNORECASE)


def _sanitize_wheel_svg(svg: str) -> str:
    """Strip scripts and inline event handlers before storing — the SVG is
    later injected into our own Chromium HTML, so keep it inert."""
    svg = _SCRIPT_RE.sub("", svg)
    svg = _ON_HANDLER_RE.sub("", svg)
    return svg


class WheelSvgPayload(BaseModel):
    svg: str = Field(min_length=1)


# Bumped when description style rules change — old rows render as stale on
# first read so they regenerate with current length, variety and gender rules.
NATAL_DESCRIPTIONS_VERSION = 14
# Bumped when the full PDF reading contract changes. v2 makes lunar nodes
# binary: render a concrete nodes section only when positions exist; otherwise
# omit the section instead of showing a paid-report apology/fallback.
NATAL_READING_VERSION = 2
MIN_EXPANDED_READING_HEADINGS = 7
MIN_EXPANDED_READING_WORDS = 1050


def _empty_descriptions() -> dict[str, Any]:
    return {"_version": NATAL_DESCRIPTIONS_VERSION, "planets": {}, "houses": {}, "aspects": []}


def _has_any(descriptions: dict[str, Any]) -> bool:
    return bool(
        descriptions.get("planets") or descriptions.get("houses") or descriptions.get("aspects")
    )


def _descriptions_shape_valid(descriptions: Any) -> bool:
    if not isinstance(descriptions, dict):
        return False
    planets = descriptions.get("planets")
    houses = descriptions.get("houses")
    aspects = descriptions.get("aspects")
    if planets is not None and not isinstance(planets, dict):
        return False
    if houses is not None and not isinstance(houses, dict):
        return False
    if aspects is not None and not isinstance(aspects, list):
        return False
    # Houses MUST be a subset of "1".."12", but can be partial — the LLM
    # only writes descriptions for houses that actually contain planets.
    # The previous check required EXACTLY the 12 keys, which is impossible
    # for any chart with an empty house (e.g. 4/8/12 unoccupied) and
    # caused a permanent «still being generated» loop: worker emits the
    # correct partial dict, validator rejects, system regenerates the
    # same partial, validator rejects again, ad infinitum.
    if isinstance(houses, dict) and houses:
        valid = {str(i) for i in range(1, 13)}
        if not set(houses.keys()).issubset(valid):
            return False
    return True


def _pdf_description_aspects(aspects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Personal LLM copy is generated for the strongest aspects only.

    Rendering still receives the full aspect list, but the expensive generated
    prose is limited to the aspects a reader is most likely to care about.
    """
    if len(aspects) <= _PDF_DESCRIPTION_ASPECT_LIMIT:
        return aspects
    return top_n_aspects(aspects, n=_PDF_DESCRIPTION_ASPECT_LIMIT)


def _is_expanded_reading(reading: Any) -> bool:
    if not isinstance(reading, str) or not reading.strip():
        return False
    headings = sum(
        1
        for line in reading.splitlines()
        if line.strip().startswith("**") and line.strip().endswith("**")
    )
    words = len(reading.split())
    return headings >= MIN_EXPANDED_READING_HEADINGS and words >= MIN_EXPANDED_READING_WORDS


async def _get_or_generate_descriptions(
    db: AsyncSession,
    user,
) -> dict[str, Any]:
    """
    Persistent (DB-backed) descriptions for the user's chart.

    Stored inside ``user.natal_chart.chart_data["descriptions"]`` so that
    they live alongside the chart itself: when birth data changes, the
    whole chart_data is replaced via ``save_natal_chart`` and descriptions
    are naturally invalidated, triggering a fresh LLM generation.
    """
    if not user.natal_chart:
        return _empty_descriptions()

    chart = user.natal_chart
    chart_data = chart.chart_data or {}
    stored = chart_data.get("descriptions")
    current_gender = _user_gender(user)
    if (
        isinstance(stored, dict)
        and stored.get("_version") == NATAL_DESCRIPTIONS_VERSION
        and stored.get("_gender_used") == current_gender
        and _descriptions_shape_valid(stored)
        and _has_any(stored)
    ):
        return stored

    if not settings.LLM_API_KEY:
        return _empty_descriptions()

    planets = chart_data.get("planets", {})
    houses = chart_data.get("houses", [])
    aspects = _pdf_description_aspects(chart_data.get("aspects", []))

    try:
        result = await generate_natal_descriptions(
            planets=planets,
            houses=houses,
            aspects=aspects,
            api_key=settings.LLM_API_KEY,
            gender=current_gender,
        )
    except Exception as e:
        log.error("natal.descriptions_failed", user_id=user.id, error=str(e))
        return _empty_descriptions()

    if _has_any(result):
        result = {
            "_version": NATAL_DESCRIPTIONS_VERSION,
            "_gender_used": current_gender,
            **result,
        }
        # Reassign the whole dict so SQLAlchemy detects the change (default
        # JSON columns don't track mutations to nested keys).
        chart.chart_data = {**chart_data, "descriptions": result}
        await db.commit()
        log.info(
            "natal.descriptions_persisted",
            user_id=user.id,
            gender=current_gender,
        )

    return result


async def _get_pdf_user_or_error(db: AsyncSession, user_id: int):
    user = await user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    is_prem = await user_repo.is_premium(db, user.id)
    has_purchase = await user_repo.has_purchased(db, user.id, "natal_full")
    if not (is_prem or has_purchase):
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Premium required")

    if not user.natal_chart:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No birth data")

    return user


def _natal_pdf_filename(user) -> str:
    safe_name = str(user.tg_first_name or "chart").replace('"', "").strip() or "chart"
    return f"natal_{safe_name}.pdf"


def _user_gender(user) -> str | None:
    return user.gender.value if user.gender else None


def _reading_is_fresh(cached: Any, current_gender: str | None) -> str | None:
    """Return the cached reading text only if it matches the reader's
    current gender. The cache payload is a dict with `reading` plus a
    `reading_gender` marker recorded at write time; mismatch ⇒ stale.

    Also runs `polish_natal_text` on the way out so retroactively-known
    typos («козеджий», «стерельцовский»…) are cleaned from any reading
    written before the polishing hooks landed.
    """
    if not isinstance(cached, dict):
        return None
    reading = cached.get("reading")
    if not isinstance(reading, str) or not reading.strip():
        return None
    if cached.get("reading_version") != NATAL_READING_VERSION:
        return None
    if cached.get("reading_gender") != current_gender:
        return None
    if not _is_expanded_reading(reading):
        return None
    from services.astro.text_polish import polish_natal_text
    reading, _ = polish_natal_text(reading)
    return reading


def _mini_is_fresh(cached: Any, current_gender: str | None) -> str | None:
    """Return the cached mini-reading only if it matches the reader's
    current gender. Stored in the same `key_natal` payload as the full
    reading, under `mini_reading` / `mini_reading_gender`."""
    if not isinstance(cached, dict):
        return None
    mini = cached.get("mini_reading")
    if not isinstance(mini, str) or not mini.strip():
        return None
    if cached.get("mini_reading_gender") != current_gender:
        return None
    from services.astro.text_polish import polish_natal_text
    mini, _ = polish_natal_text(mini)
    return mini


async def _load_db_interpretations(db: AsyncSession, chart) -> list[dict[str, Any]]:
    """DB-backed per-planet interpretation blocks (no LLM). Shared by the
    full-chart and mini endpoints so the on-screen slider has content
    without triggering the expensive reading generation."""
    planets = chart.chart_data.get("planets", {})
    planet_signs = {
        planet: data["sign"].lower()
        for planet, data in planets.items()
        if planet not in ("sun", "moon")
    }
    planet_houses = {
        planet: int(data["house"]) for planet, data in planets.items() if data.get("house")
    }
    interp_blocks = await get_natal_interpretation(
        db,
        sun_sign=chart.sun_sign.lower(),
        moon_sign=chart.moon_sign.lower(),
        asc_sign=chart.ascendant_sign.lower() if chart.ascendant_sign else None,
        planet_signs=planet_signs,
        planet_houses=planet_houses,
        aspects=chart.chart_data.get("aspects", []),
    )
    return [{"planet": b.planet, "category": b.category, "text": b.text} for b in interp_blocks]


async def _get_or_generate_pdf_reading(
    user,
    chart,
    planets: dict[str, Any],
    aspects: list[dict[str, Any]],
) -> str | None:
    cache_key = key_natal(user.id)
    cached = await cache_get(cache_key)
    current_gender = _user_gender(user)
    fresh = _reading_is_fresh(cached, current_gender)
    if fresh:
        return fresh

    if not settings.LLM_API_KEY:
        return None

    try:
        reading = await generate_natal_reading(
            sun_sign=chart.sun_sign,
            moon_sign=chart.moon_sign,
            ascendant_sign=chart.ascendant_sign,
            planets=planets,
            aspects=aspects,
            api_key=settings.LLM_API_KEY,
            gender=current_gender,
            nodes=(getattr(chart, "chart_data", None) or {}).get("nodes"),
        )
    except Exception as e:
        log.error("natal.pdf_reading_failed", user_id=user.id, error=str(e))
        return None

    if reading and reading.strip():
        cached_payload = cached if isinstance(cached, dict) else {}
        await cache_set(
            cache_key,
            {
                **cached_payload,
                "reading": reading,
                "reading_gender": current_gender,
                "reading_version": NATAL_READING_VERSION,
            },
            settings.CACHE_TTL_NATAL,
        )

    return reading


async def _get_cached_pdf_reading(user) -> str | None:
    cached = await cache_get(key_natal(user.id))
    return _reading_is_fresh(cached, _user_gender(user))


# Guards so a burst of PDF downloads doesn't kick off several identical
# generations for the same user at once.
_MINI_INFLIGHT: set[int] = set()


def _get_stored_descriptions(user) -> dict[str, Any]:
    """Return persisted descriptions only if the version AND the gender they
    were generated for match the reader's current profile. Mismatch falls
    back to empty so the PDF renders its own per-item fallback copy
    instead of stale-gender text — regen happens when the user next opens
    /natal/descriptions."""
    if not user.natal_chart:
        return _empty_descriptions()

    chart_data = user.natal_chart.chart_data or {}
    stored = chart_data.get("descriptions")
    if (
        isinstance(stored, dict)
        and stored.get("_version") == NATAL_DESCRIPTIONS_VERSION
        and stored.get("_gender_used") == _user_gender(user)
        and _descriptions_shape_valid(stored)
        and _has_any(stored)
    ):
        return stored
    return _empty_descriptions()


async def _build_natal_pdf_bytes(
    db: AsyncSession,
    user,
    *,
    require_ready_cache: bool = False,
) -> bytes:
    from services.natal_pdf import generate_natal_pdf
    from services.natal_pdf_html import generate_natal_pdf_html

    chart = user.natal_chart
    planets = chart.chart_data.get("planets", {})
    houses = chart.chart_data.get("houses", [])
    # Рендерим ТОЛЬКО те аспекты, для которых генерится персональный текст
    # (top-N сильнейших). Иначе слабые аспекты без LLM-описания падали в
    # шаблонный _aspect_fallback — а шаблоны в платном PDF мы не показываем.
    aspects_raw = _pdf_description_aspects(chart.chart_data.get("aspects", []))
    aspects = [
        {
            "p1": a.get("p1", ""),
            "p2": a.get("p2", ""),
            "aspect": a.get("aspect", ""),
            "orb": a.get("orb", 0),
        }
        for a in aspects_raw
    ]

    if require_ready_cache:
        descriptions = _get_stored_descriptions(user)
        reading = await _get_cached_pdf_reading(user)
        if not _has_any(descriptions) or not reading:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "PDF report is still being generated",
            )
    else:
        descriptions = await _get_or_generate_descriptions(db, user)
        reading = await _get_or_generate_pdf_reading(user, chart, planets, aspects)

    # Prefer the hot Redis copy, but fall back to the DB-persisted SVG so the
    # PDF embeds the exact frontend wheel even when generated outside the UI
    # (curl/worker/tests) or after a Redis flush/TTL.
    wheel_svg = None
    cached_wheel = await cache_get(key_natal_wheel_svg(user.id))
    if isinstance(cached_wheel, dict):
        wheel_svg = cached_wheel.get("svg")
    if not wheel_svg:
        stored_wheel = (chart.chart_data or {}).get("wheel_svg")
        if isinstance(stored_wheel, str) and stored_wheel.startswith("<svg"):
            wheel_svg = stored_wheel

    pdf_kwargs = dict(
        user_name=user.tg_first_name or "User",
        birth_date=str(user.birth_date) if user.birth_date else "",
        birth_time=(
            user.birth_date.strftime("%H:%M") if user.birth_date and user.birth_time_known else None
        ),
        birth_city=user.birth_city or "",
        sun_sign=chart.sun_sign or "",
        moon_sign=chart.moon_sign or "",
        asc_sign=chart.ascendant_sign,
        planets=planets,
        houses=houses,
        aspects=aspects,
        reading=reading,
        descriptions=descriptions,
        wheel_svg=wheel_svg,
    )
    try:
        pdf_bytes = await generate_natal_pdf_html(**pdf_kwargs)
        log.info(
            "natal.pdf_built_html",
            user_id=user.id,
            renderer="html_playwright",
            pdf_bytes=len(pdf_bytes),
        )
        return pdf_bytes
    except Exception as e:  # noqa: BLE001
        # The HTML/Chromium path is the intended renderer. Falling back to
        # ReportLab still returns a PDF, but it is the degraded layout — so
        # log loudly (with type + traceback) to make every fallback visible
        # and actionable in prod, not silent.
        log.error(
            "natal.pdf_html_failed_fallback_reportlab",
            user_id=user.id,
            error_type=type(e).__name__,
            error=str(e),
            exc_info=True,
        )
        reportlab_bytes = generate_natal_pdf(**pdf_kwargs)
        log.warning(
            "natal.pdf_built_reportlab_fallback",
            user_id=user.id,
            renderer="reportlab_fallback",
            pdf_bytes=len(reportlab_bytes),
        )
        return reportlab_bytes


async def _build_natal_pdf_response(db: AsyncSession, user) -> Response:
    pdf_bytes = await _build_natal_pdf_bytes(db, user)
    filename = _natal_pdf_filename(user)
    return Response(
        content=pdf_bytes,
        media_type="application/octet-stream",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": (
                f"attachment; filename=\"natal-chart.pdf\"; filename*=UTF-8''{quote(filename)}"
            ),
            "X-Content-Type-Options": "nosniff",
        },
    )


async def _send_natal_pdf_document(user, pdf_bytes: bytes) -> None:
    filename = _natal_pdf_filename(user)
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument"
    data = {
        "chat_id": str(user.id),
        "caption": "Ваш полный PDF-отчёт по натальной карте.",
    }
    files = {
        "document": (
            filename,
            BytesIO(pdf_bytes),
            "application/pdf",
        )
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, data=data, files=files)
        payload = response.json()
    except Exception as e:  # noqa: BLE001
        log.error("natal.pdf_send_failed", user_id=user.id, error=str(e))
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Не удалось отправить PDF в Telegram. Попробуйте ещё раз.",
        ) from e

    if response.status_code == 403:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Сначала откройте чат с ботом и нажмите /start, затем попробуйте снова.",
        )

    if not response.is_success or not payload.get("ok"):
        description = str(payload.get("description") or response.text)
        log.error(
            "natal.pdf_send_rejected",
            user_id=user.id,
            status_code=response.status_code,
            error=description[:500],
        )
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Telegram не принял PDF. Попробуйте ещё раз.",
        )


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
            "degree": data.get("degree", 0),  # absolute 0–360
            "sign_degree": data.get("sign_degree", 0),  # within-sign 0–30
            "sign": data.get("sign", ""),
            "sign_ru": data.get("sign_ru", ""),
            "house": data.get("house", 1),
            "retrograde": data.get("retrograde", False),
            "speed": data.get("speed", 0),
        }

    # House cusps with sign
    houses_for_wheel = []
    for h in chart.chart_data.get("houses", []):
        houses_for_wheel.append(
            {
                "number": h.get("number", 0),
                "degree": h.get("degree", 0),
                "sign": h.get("sign", ""),
                "sign_ru": h.get("sign_ru", ""),
            }
        )

    # Birth date / time
    birth_date_str = user.birth_date.strftime("%Y-%m-%d") if user.birth_date else None
    birth_time_str = (
        user.birth_date.strftime("%H:%M")
        if (user.birth_date and user.birth_time_known)
        else "12:00"
    )

    raw_aspects = chart.chart_data.get("aspects", [])
    try:
        dominants = compute_dominants(
            planets=raw_planets,
            ascendant_sign=chart.ascendant_sign if user.birth_time_known else None,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("natal.dominants_failed", user_id=user.id, error=str(e))
        dominants = None

    try:
        key_aspects = top_n_aspects(raw_aspects, n=5)
    except Exception as e:  # noqa: BLE001
        log.warning("natal.key_aspects_failed", user_id=user.id, error=str(e))
        key_aspects = []

    hero_info: dict[str, Any] | None = None
    if dominants:
        try:
            hero_info = {
                "elements": build_elements_hero(dominants),
                "planets": build_planets_hero(raw_planets, dominants),
                "houses": build_houses_hero(raw_planets),
                "aspects": build_aspects_hero(raw_aspects, key_aspects),
            }
        except Exception as e:  # noqa: BLE001
            log.warning("natal.hero_failed", user_id=user.id, error=str(e))

    return {
        "has_chart": True,
        "sun_sign": chart.sun_sign,
        "moon_sign": chart.moon_sign,
        "ascendant_sign": chart.ascendant_sign,
        "mc_sign": chart.chart_data.get("mc_sign"),
        "birth_city": user.birth_city,
        "birth_time_known": user.birth_time_known,
        "birth_lat": user.birth_lat,
        "birth_lng": user.birth_lng,
        "birth_tz": user.birth_tz,
        "birth_date": birth_date_str,
        "birth_time": birth_time_str,
        "planets": planets_for_wheel,
        "houses": houses_for_wheel,
        "aspects": raw_aspects,
        "dominants": dominants,
        "key_aspects": key_aspects,
        "hero_info": hero_info,
    }


@router.get("/mini")
async def get_natal_mini(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cheap teaser reading (Sun/Moon/Ascendant) + DB interpretation blocks.
    No premium gate — shown on the natal screen before the user requests
    the full PDF reading. Spends ~700 tokens at most (vs 7000 for /full),
    cached in the same `key_natal` payload under `mini_reading`.
    """
    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    if not user.natal_chart:
        return {
            "mini_reading": None,
            "mini_reading_gender": None,
            "interpretations": [],
            "has_chart": False,
        }

    chart = user.natal_chart
    current_gender = _user_gender(user)
    interpretations = await _load_db_interpretations(db, chart)

    cache_key = key_natal(user.id)
    cached = await cache_get(cache_key)
    fresh = _mini_is_fresh(cached, current_gender)
    if fresh:
        return {
            "mini_reading": fresh,
            "mini_reading_gender": current_gender,
            "interpretations": interpretations,
            "has_chart": True,
        }

    mini_reading: str | None = None
    if settings.LLM_API_KEY and user.id not in _MINI_INFLIGHT:
        _MINI_INFLIGHT.add(user.id)
        try:
            mini_reading = await generate_natal_mini_reading(
                sun_sign=chart.sun_sign,
                moon_sign=chart.moon_sign,
                ascendant_sign=chart.ascendant_sign,
                api_key=settings.LLM_API_KEY,
                gender=current_gender,
            )
        except Exception as e:
            log.error("natal.mini_failed", user_id=user.id, error=str(e))
        finally:
            _MINI_INFLIGHT.discard(user.id)

        if mini_reading and mini_reading.strip():
            cached_payload = cached if isinstance(cached, dict) else {}
            await cache_set(
                cache_key,
                {
                    **cached_payload,
                    "mini_reading": mini_reading,
                    "mini_reading_gender": current_gender,
                },
                settings.CACHE_TTL_NATAL,
            )

    return {
        "mini_reading": mini_reading,
        "mini_reading_gender": current_gender if mini_reading else None,
        "interpretations": interpretations,
        "has_chart": True,
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
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED, "Premium or natal_full purchase required"
        )

    if not user.natal_chart:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "No birth data — set birth data first"
        )

    chart = user.natal_chart
    planets = chart.chart_data.get("planets", {})
    aspects = chart.chart_data.get("aspects", [])

    current_gender = _user_gender(user)

    # Check cache. Older cached readings were intentionally short; refresh
    # them on the full-chart view so PDF downloads can stay non-blocking.
    # Also refresh whenever the cached `reading_gender` no longer matches
    # the reader's current profile setting.
    cache_key = key_natal(user.id)
    cached = await cache_get(cache_key)
    if isinstance(cached, dict):
        cached_gender = cached.get("reading_gender")
        gender_matches = cached_gender == current_gender
        if _reading_is_fresh(cached, current_gender) or (
            gender_matches and not settings.LLM_API_KEY
        ):
            return cached
        if not settings.LLM_API_KEY:
            return cached
        try:
            refreshed_reading = await generate_natal_reading(
                sun_sign=chart.sun_sign,
                moon_sign=chart.moon_sign,
                ascendant_sign=chart.ascendant_sign,
                planets=planets,
                aspects=aspects[:10],
                api_key=settings.LLM_API_KEY,
                gender=current_gender,
                nodes=chart.chart_data.get("nodes"),
            )
        except Exception as e:
            log.error("natal.llm_refresh_failed", user_id=user.id, error=str(e))
            return cached
        refreshed = {
            **cached,
            "reading": refreshed_reading,
            "reading_gender": current_gender,
            "reading_version": NATAL_READING_VERSION,
        }
        await cache_set(cache_key, refreshed, settings.CACHE_TTL_NATAL)
        return refreshed
    if cached:
        return cached

    interpretations = await _load_db_interpretations(db, chart)

    # Generate LLM interpretation if API key is set
    llm_reading: str | None = None
    if settings.LLM_API_KEY:
        try:
            llm_reading = await generate_natal_reading(
                sun_sign=chart.sun_sign,
                moon_sign=chart.moon_sign,
                ascendant_sign=chart.ascendant_sign,
                planets=planets,
                aspects=chart.chart_data.get("aspects", [])[:10],
                api_key=settings.LLM_API_KEY,
                gender=current_gender,
                nodes=chart.chart_data.get("nodes"),
            )
        except Exception as e:
            log.error("natal.llm_failed", user_id=user.id, error=str(e))

    result = {
        "sun_sign": chart.sun_sign,
        "moon_sign": chart.moon_sign,
        "ascendant_sign": chart.ascendant_sign,
        "planets": planets,
        "houses": chart.chart_data.get("houses", []),
        "aspects": chart.chart_data.get("aspects", [])[:10],
        "reading_version": NATAL_READING_VERSION,
        "reading_gender": current_gender,
        "interpretations": interpretations,
        "reading": llm_reading,
    }

    await cache_set(cache_key, result, settings.CACHE_TTL_NATAL)
    return result


@router.get("/descriptions")
async def get_natal_descriptions(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Personal short+full descriptions for every planet, house and aspect.
    Persisted in the natal chart row — regenerated only when the user
    updates their birth data (which replaces the whole chart_data blob).
    """
    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    if not user.natal_chart:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No birth data")

    return await _get_or_generate_descriptions(db, user)


@router.post("/wheel-svg")
async def upload_natal_wheel_svg(
    payload: WheelSvgPayload,
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Store the frontend-rendered natal wheel SVG so the PDF can embed the
    exact same chart. Cached per-user in Redis."""
    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    svg = payload.svg.strip()
    if not svg.startswith("<svg"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Not an SVG")
    if len(svg.encode("utf-8")) > _WHEEL_SVG_MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "SVG too large")

    svg = _sanitize_wheel_svg(svg)
    await cache_set(key_natal_wheel_svg(user.id), {"svg": svg}, _WHEEL_SVG_TTL_SECONDS)

    # Also persist to the DB so any later generation path (curl/worker/tests,
    # or after a Redis flush/TTL) still embeds this exact frontend wheel.
    if user.natal_chart:
        chart_data = user.natal_chart.chart_data or {}
        if chart_data.get("wheel_svg") != svg:
            user.natal_chart.chart_data = {**chart_data, "wheel_svg": svg}
            await db.commit()
    return {"status": "stored"}


@router.get("/pdf")
async def get_natal_pdf(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return natal chart PDF report."""
    user = await _get_pdf_user_or_error(db, tg_user["id"])
    return await _build_natal_pdf_response(db, user)


@router.post("/pdf-link")
async def create_natal_pdf_link(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a short-lived direct download URL for WebViews that block blob downloads."""
    user = await _get_pdf_user_or_error(db, tg_user["id"])
    token = token_urlsafe(24)
    await cache_set(
        key_natal_pdf_download(token),
        {"user_id": user.id},
        _PDF_DOWNLOAD_TTL_SECONDS,
    )
    return {
        "download_url": f"/natal/pdf-download/{token}",
        "filename": _natal_pdf_filename(user),
        "expires_in": _PDF_DOWNLOAD_TTL_SECONDS,
    }


@router.post("/pdf-send")
async def send_natal_pdf_to_telegram(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a natal PDF and send it to the user's Telegram chat as a document."""
    user = await _get_pdf_user_or_error(db, tg_user["id"])
    pdf_bytes = await _build_natal_pdf_bytes(db, user)
    await _send_natal_pdf_document(user, pdf_bytes)
    return {"status": "sent", "filename": _natal_pdf_filename(user)}


@router.get("/pdf-download/{token}")
async def get_natal_pdf_by_token(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Download a natal PDF using a temporary token created by /pdf-link."""
    payload = await cache_get(key_natal_pdf_download(token))
    if not isinstance(payload, dict) or "user_id" not in payload:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Download link expired")

    user = await _get_pdf_user_or_error(db, int(payload["user_id"]))
    require_ready_cache = payload.get("ready") is True
    pdf_bytes = await _build_natal_pdf_bytes(db, user, require_ready_cache=require_ready_cache)
    filename = _natal_pdf_filename(user)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
            "X-Content-Type-Options": "nosniff",
        },
    )


# ── Queued PDF generation (scales to many concurrent users) ──────────────────
# Heavy LLM work runs in the arq worker, not the HTTP request. The client polls
# status, then downloads via the existing /pdf-download/{token} once ready.

_PDF_JOB_LOCK_TTL = settings.ARQ_JOB_TIMEOUT + 100  # outlives a running job


class PdfGenerateResponse(BaseModel):
    job_id: str
    status: str
    download_token: str | None = None
    filename: str | None = None


class PdfStatusResponse(BaseModel):
    status: str
    error: str | None = None
    download_token: str | None = None
    filename: str | None = None


@router.post("/pdf/generate", response_model=PdfGenerateResponse)
async def start_natal_pdf(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Kick off (or reuse) a natal-PDF generation job. Returns immediately."""
    from services.arq_pool import get_arq_pool
    from services.job_status import get_job_status, set_job_status

    user = await _get_pdf_user_or_error(db, tg_user["id"])

    # Fast-path: texts already fresh → mint a token and report ready, no queue.
    descriptions = _get_stored_descriptions(user)
    cached_reading = _reading_is_fresh(await cache_get(key_natal(user.id)), _user_gender(user))
    if _has_any(descriptions) and cached_reading:
        token = token_urlsafe(24)
        await cache_set(
            key_natal_pdf_download(token),
            {"user_id": user.id, "ready": True},
            _PDF_DOWNLOAD_TTL_SECONDS,
        )
        return PdfGenerateResponse(
            job_id=f"ready-{user.id}",
            status="ready",
            download_token=token,
            filename=_natal_pdf_filename(user),
        )

    # Dedup: one active job per user. Atomic SET NX (same pattern as the
    # scheduler leader lock). value = job_id.
    job_id = token_urlsafe(16)
    redis = get_redis()
    acquired = await redis.set(key_natal_pdf_job(user.id), job_id, nx=True, ex=_PDF_JOB_LOCK_TTL)
    if not acquired:
        existing = await redis.get(key_natal_pdf_job(user.id))
        st = await get_job_status(existing) if existing else None
        return PdfGenerateResponse(
            job_id=existing or job_id,
            status=(st or {}).get("status", "processing"),
            download_token=(st or {}).get("download_token"),
            filename=(st or {}).get("filename"),
        )

    await set_job_status(job_id, "queued")
    # Pass our app-level job_id so the worker writes status under the same key
    # the client polls. _job_id dedups on arq's side too (no second task while
    # one is queued).
    await get_arq_pool().enqueue_job(
        "generate_natal_pdf_task", user.id, job_id, _job_id=f"natalpdf:{user.id}"
    )
    return PdfGenerateResponse(job_id=job_id, status="queued")


@router.get("/pdf/status/{job_id}", response_model=PdfStatusResponse)
async def natal_pdf_status(
    job_id: str,
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll a PDF job's status.

    The status blob (keyed by the opaque job_id) is the source of truth. The
    per-user lock is short-lived (released the moment the worker finishes), so
    we must NOT 404 just because the lock is gone — the blob lives 30 min. A
    missing blob is reported as still-processing rather than a hard 404, to ride
    out the brief window between enqueue and the worker's first status write.
    """
    from services.job_status import get_job_status

    # ready-{uid} jobs are synthetic (fast-path) — accept them for the owner.
    if job_id == f"ready-{tg_user['id']}":
        return PdfStatusResponse(status="ready")

    st = await get_job_status(job_id)
    if not st:
        # Blob not written yet (or expired). Treat as still in flight so the
        # client keeps polling instead of erroring on a transient gap.
        return PdfStatusResponse(status="processing")
    return PdfStatusResponse(
        status=st["status"],
        error=st.get("error"),
        download_token=st.get("download_token"),
        filename=st.get("filename"),
    )
