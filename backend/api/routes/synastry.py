"""Synastry endpoints — invite-based compatibility flow between two users."""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from api.schemas.synastry import (
    SynastryAspectOut, SynastryManualInput, SynastryPending, SynastryRequestOut,
    SynastryResult, SynastryScores,
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

_PLANET_RU: dict[str, str] = {
    "sun": "Солнце", "moon": "Луна", "mercury": "Меркурий", "venus": "Венера",
    "mars": "Марс", "jupiter": "Юпитер", "saturn": "Сатурн",
    "uranus": "Уран", "neptune": "Нептун", "pluto": "Плутон",
}

_ASPECT_RU: dict[str, str] = {
    "conjunction": "Соединение", "opposition": "Оппозиция", "square": "Квадрат",
    "trine": "Трин", "sextile": "Секстиль",
}


def _invite_url(token: str) -> str:
    bot = settings.TELEGRAM_BOT_USERNAME or "astro_bot"
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

    now = datetime.now(timezone.utc)

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
        invite_url=_invite_url(req.token),
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
    now = datetime.now(timezone.utc)
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

    now = datetime.now(timezone.utc)
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

    raw = calculate_synastry(
        user_a={
            "name": initiator.tg_first_name,
            "birth_dt": initiator.birth_date,
            "lat": initiator.birth_lat or 0.0,
            "lng": initiator.birth_lng or 0.0,
            "tz_str": initiator.birth_tz,
            "birth_time_known": initiator.birth_time_known,
        },
        user_b={
            "name": partner.tg_first_name,
            "birth_dt": partner.birth_date,
            "lat": partner.birth_lat or 0.0,
            "lng": partner.birth_lng or 0.0,
            "tz_str": partner.birth_tz,
            "birth_time_known": partner.birth_time_known,
        },
    )

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

    # Resolve partner timezone from coords if not provided by the client.
    partner_tz = payload.birth_tz
    if not partner_tz:
        from api.routes.users import _get_timezone  # late import to avoid cycles
        partner_tz = await _get_timezone(payload.birth_lat, payload.birth_lng)

    raw = calculate_synastry(
        user_a={
            "name": initiator.tg_first_name,
            "birth_dt": initiator.birth_date,
            "lat": initiator.birth_lat or 0.0,
            "lng": initiator.birth_lng or 0.0,
            "tz_str": initiator.birth_tz,
            "birth_time_known": initiator.birth_time_known,
        },
        user_b={
            "name": payload.partner_name,
            "birth_dt": partner_dt,
            "lat": payload.birth_lat,
            "lng": payload.birth_lng,
            "tz_str": partner_tz,
            "birth_time_known": payload.birth_time_known,
        },
    )

    log.info(
        "synastry.manual_computed",
        initiator_id=initiator.id,
        partner_name=payload.partner_name,
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
