"""Synastry endpoints — invite-based compatibility flow between two users."""

import secrets
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from api.schemas.synastry import (
    SynastryAspectOut,
    SynastryManualInput,
    SynastryPending,
    SynastryRequestOut,
    SynastryResult,
    SynastryScores,
)
from core.logging import get_logger
from core.settings import settings
from db.database import get_db
from db.models import SynastryRequest, SynastryRequestStatus, User
from services.astro.synastry import calculate_synastry
from services.users import repository as user_repo

log = get_logger(__name__)
router = APIRouter(prefix="/synastry", tags=["synastry"])

_TOKEN_TTL_DAYS = 7
_BOT_USERNAME_CACHE: str | None = None
_BOT_USERNAME_PLACEHOLDERS = {
    "",
    "astro_bot",
    "bot_username",
    "your_bot_username",
    "telegram_bot_username",
    "changeme",
}

_PLANET_RU: dict[str, str] = {
    "sun": "Солнце", "moon": "Луна", "mercury": "Меркурий", "venus": "Венера",
    "mars": "Марс", "jupiter": "Юпитер", "saturn": "Сатурн",
    "uranus": "Уран", "neptune": "Нептун", "pluto": "Плутон",
}

_ASPECT_RU: dict[str, str] = {
    "conjunction": "Соединение", "opposition": "Оппозиция", "square": "Квадрат",
    "trine": "Трин", "sextile": "Секстиль",
}


def _clean_bot_username(value: str | None) -> str:
    return (value or "").strip().lstrip("@")


def _is_placeholder_bot_username(value: str) -> bool:
    return value.lower() in _BOT_USERNAME_PLACEHOLDERS


async def _resolve_bot_username() -> str:
    global _BOT_USERNAME_CACHE

    bot = (settings.TELEGRAM_BOT_USERNAME or "").strip().lstrip("@")
    if bot and not _is_placeholder_bot_username(bot):
        return bot

    if _BOT_USERNAME_CACHE:
        return _BOT_USERNAME_CACHE

    token = (settings.TELEGRAM_BOT_TOKEN or "").strip()
    if not token:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "TELEGRAM_BOT_TOKEN не настроен",
        )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            resp.raise_for_status()
            payload = resp.json()
    except httpx.HTTPError as e:
        log.warning("synastry.bot_username_resolve_failed", error=str(e))
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Не удалось определить Telegram bot username",
        ) from e

    resolved = _clean_bot_username(payload.get("result", {}).get("username"))
    if not resolved:
        log.warning("synastry.bot_username_missing", payload_ok=payload.get("ok"))
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Telegram bot username не найден",
        )

    _BOT_USERNAME_CACHE = resolved
    return resolved


async def _invite_url(token: str) -> str:
    bot = await _resolve_bot_username()
    return f"https://t.me/{bot}?startapp=syn_{token}"


def _aspects_to_schema(raw: list[dict]) -> list[SynastryAspectOut]:
    return [
        SynastryAspectOut(
            p1_name=a["p1_name"],
            p2_name=a["p2_name"],
            p1_name_ru=_PLANET_RU.get(a["p1_name"].lower(), a["p1_name"]),
            p2_name_ru=_PLANET_RU.get(a["p2_name"].lower(), a["p2_name"]),
            aspect=a["aspect"],
            aspect_ru=_ASPECT_RU.get(a["aspect"], a["aspect"]),
            orb=a["orb"],
            weight=a["weight"],
        )
        for a in raw
    ]


def _coord_or_default(value: float | None) -> float:
    return value if value is not None else 0.0


def _is_valid_timezone(value: str | None) -> bool:
    if not value:
        return False
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError:
        return False
    return True


async def _resolve_synastry_timezone(
    tz: str | None,
    lat: float | None,
    lng: float | None,
) -> str:
    if _is_valid_timezone(tz):
        return str(tz)

    if lat is not None and lng is not None:
        from api.routes.users import _get_timezone  # late import to avoid cycles

        resolved = await _get_timezone(lat, lng)
        if _is_valid_timezone(resolved):
            return resolved

    return "UTC"


def _synastry_user_payload(user: User, tz: str) -> dict:
    return {
        "name": user.tg_first_name,
        "birth_dt": user.birth_date,
        "lat": _coord_or_default(user.birth_lat),
        "lng": _coord_or_default(user.birth_lng),
        "tz_str": tz,
        "birth_time_known": user.birth_time_known,
    }


async def _require_user_with_chart(db: AsyncSession, user_id: int) -> User:
    user = await user_repo.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if not user.natal_chart or not user.birth_date or not user.birth_tz:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Заполните данные рождения в профиле",
        )
    return user


@router.post("/request", response_model=SynastryRequestOut)
async def create_request(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate (or reuse) an invite token for synastry. Requires prior synastry purchase."""
    user = await _require_user_with_chart(db, tg_user["id"])

    if not await user_repo.has_purchased(db, user.id, "synastry"):
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Покупка Синастрии обязательна")

    now = datetime.now(UTC)

    result = await db.execute(
        select(SynastryRequest)
        .where(
            SynastryRequest.initiator_user_id == user.id,
            SynastryRequest.status == SynastryRequestStatus.PENDING,
            SynastryRequest.expires_at > now,
        )
        .order_by(SynastryRequest.created_at.desc())
    )
    req = result.scalars().first()

    if req is None:
        req = SynastryRequest(
            initiator_user_id=user.id,
            token=secrets.token_urlsafe(12),
            status=SynastryRequestStatus.PENDING,
            expires_at=now + timedelta(days=_TOKEN_TTL_DAYS),
        )
        db.add(req)
        await db.flush()
        log.info("synastry.request_created", user_id=user.id, token=req.token)

    await db.commit()

    return SynastryRequestOut(
        id=req.id,
        token=req.token,
        invite_url=await _invite_url(req.token),
        status=req.status.value,
        expires_at=req.expires_at,
        initiator_name=user.tg_first_name,
    )


@router.get("/pending", response_model=list[SynastryPending])
async def get_pending(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Inbound pending invitations where current user is the partner."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(SynastryRequest, User)
        .join(User, User.id == SynastryRequest.initiator_user_id)
        .where(
            SynastryRequest.partner_user_id == tg_user["id"],
            SynastryRequest.status == SynastryRequestStatus.PENDING,
            SynastryRequest.expires_at > now,
        )
    )
    out = []
    for req, initiator in result.all():
        out.append(SynastryPending(
            id=req.id,
            token=req.token,
            initiator_name=initiator.tg_first_name,
            expires_at=req.expires_at,
        ))
    return out


@router.post("/accept/{token}", response_model=SynastryResult)
async def accept_request(
    token: str,
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Partner accepts the invitation. Both users must have natal charts."""
    partner = await _require_user_with_chart(db, tg_user["id"])

    now = datetime.now(UTC)
    result = await db.execute(
        select(SynastryRequest).where(SynastryRequest.token == token)
    )
    req = result.scalar_one_or_none()
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Приглашение не найдено")

    if req.initiator_user_id == partner.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Нельзя принять собственное приглашение")

    if req.expires_at <= now:
        req.status = SynastryRequestStatus.EXPIRED
        await db.commit()
        raise HTTPException(status.HTTP_410_GONE, "Срок действия приглашения истёк")

    if req.status == SynastryRequestStatus.COMPLETED and req.result_json:
        initiator = await user_repo.get_by_id(db, req.initiator_user_id)
        data = req.result_json
        return SynastryResult(
            aspects=_aspects_to_schema(data["aspects"]),
            scores=SynastryScores(**data["scores"]),
            total_aspects=data["total_aspects"],
            initiator_name=initiator.tg_first_name if initiator else None,
            partner_name=partner.tg_first_name,
        )

    initiator = await _require_user_with_chart(db, req.initiator_user_id)

    initiator_tz = await _resolve_synastry_timezone(
        initiator.birth_tz,
        initiator.birth_lat,
        initiator.birth_lng,
    )
    partner_tz = await _resolve_synastry_timezone(
        partner.birth_tz,
        partner.birth_lat,
        partner.birth_lng,
    )

    try:
        raw = calculate_synastry(
            user_a=_synastry_user_payload(initiator, initiator_tz),
            user_b=_synastry_user_payload(partner, partner_tz),
        )
    except Exception as exc:
        log.exception(
            "synastry.accept_calculation_failed",
            request_id=req.id,
            initiator=initiator.id,
            partner=partner.id,
            error=str(exc),
        )
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Не удалось рассчитать совместимость. Проверьте данные рождения в профиле.",
        ) from exc

    req.partner_user_id = partner.id
    req.status = SynastryRequestStatus.COMPLETED
    req.result_json = raw
    await db.commit()
    log.info("synastry.completed", request_id=req.id, initiator=initiator.id, partner=partner.id)

    return SynastryResult(
        aspects=_aspects_to_schema(raw["aspects"]),
        scores=SynastryScores(**raw["scores"]),
        total_aspects=raw["total_aspects"],
        initiator_name=initiator.tg_first_name,
        partner_name=partner.tg_first_name,
    )


@router.post("/manual", response_model=SynastryResult)
async def manual_synastry(
    payload: SynastryManualInput,
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Compute synastry between current user and a manually-entered partner.
    No invite flow — the partner isn't required to be a Telegram user.
    Result is returned directly; not persisted to the database.
    """
    initiator = await _require_user_with_chart(db, tg_user["id"])

    if not await user_repo.has_purchased(db, initiator.id, "synastry"):
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Покупка Синастрии обязательна")

    # Combine birth_date + birth_time into a single datetime
    try:
        hh, mm = payload.birth_time.split(":", 1)
        partner_dt = datetime(
            payload.birth_date.year,
            payload.birth_date.month,
            payload.birth_date.day,
            int(hh),
            int(mm),
        )
    except (ValueError, IndexError) as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Некорректный формат времени рождения (ожидается HH:MM)",
        ) from exc

    # Resolve partner coordinates from city if not provided by the client.
    partner_lat = payload.birth_lat
    partner_lng = payload.birth_lng
    partner_city = payload.birth_city
    if partner_lat is None or partner_lng is None:
        from api.routes.users import _geocode_city  # late import to avoid cycles
        geo = await _geocode_city(payload.birth_city)
        partner_lat = geo["lat"]
        partner_lng = geo["lng"]
        partner_city = geo.get("city") or partner_city

    # Resolve and validate timezones. Older profiles may contain stale/invalid
    # timezone strings, so we recover from coordinates before calculating.
    initiator_tz = await _resolve_synastry_timezone(
        initiator.birth_tz,
        initiator.birth_lat,
        initiator.birth_lng,
    )
    partner_tz = await _resolve_synastry_timezone(
        payload.birth_tz,
        partner_lat,
        partner_lng,
    )

    try:
        raw = calculate_synastry(
            user_a=_synastry_user_payload(initiator, initiator_tz),
            user_b={
                "name": payload.partner_name,
                "birth_dt": partner_dt,
                "lat": partner_lat,
                "lng": partner_lng,
                "tz_str": partner_tz,
                "birth_time_known": payload.birth_time_known,
            },
        )
    except Exception as exc:
        log.exception(
            "synastry.manual_calculation_failed",
            initiator_id=initiator.id,
            partner_name=payload.partner_name,
            partner_city=partner_city,
            error=str(exc),
        )
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Не удалось рассчитать совместимость. Проверьте дату, время и город рождения.",
        ) from exc

    log.info(
        "synastry.manual_computed",
        initiator_id=initiator.id,
        partner_name=payload.partner_name,
        partner_city=partner_city,
        total=raw["total_aspects"],
    )

    return SynastryResult(
        aspects=_aspects_to_schema(raw["aspects"]),
        scores=SynastryScores(**raw["scores"]),
        total_aspects=raw["total_aspects"],
        initiator_name=initiator.tg_first_name,
        partner_name=payload.partner_name,
    )


@router.get("/result/{request_id}", response_model=SynastryResult)
async def get_result(
    request_id: int,
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch the synastry result — accessible to both initiator and partner."""
    user_id = tg_user["id"]
    result = await db.execute(
        select(SynastryRequest).where(SynastryRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Результат не найден")

    if user_id not in (req.initiator_user_id, req.partner_user_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нет доступа")

    if req.status != SynastryRequestStatus.COMPLETED or not req.result_json:
        raise HTTPException(status.HTTP_409_CONFLICT, "Расчёт ещё не готов")

    initiator = await user_repo.get_by_id(db, req.initiator_user_id)
    partner = await user_repo.get_by_id(db, req.partner_user_id) if req.partner_user_id else None
    data = req.result_json

    return SynastryResult(
        aspects=_aspects_to_schema(data["aspects"]),
        scores=SynastryScores(**data["scores"]),
        total_aspects=data["total_aspects"],
        initiator_name=initiator.tg_first_name if initiator else None,
        partner_name=partner.tg_first_name if partner else None,
    )
