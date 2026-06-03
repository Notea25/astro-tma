"""V3 Destiny Matrix API — 15-section long-form interpretation.

Separate router from `destiny_matrix.py` so the legacy 8-section flow
keeps working while V3 ships. Once the frontend fully migrates, V2 will
be removed (per the V3 plan), but the calculator + positions endpoints
stay shared.

Endpoints:
  GET  /destiny-matrix/v3/sections      — section metadata + free keys
  GET  /destiny-matrix/v3/reading       — full reading (positions + 15 sections)
  POST /destiny-matrix/v3/regenerate    — re-roll specific sections
  GET  /destiny-matrix/v3/year-energy   — current + upcoming year arcana

Free preview: `visitka` + `karmic_tail`. Everything else is masked with
a teaser for non-premium users.
"""

from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from secrets import token_urlsafe
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from core.cache import cache_get, cache_set, key_destiny_pdf_download
from core.logging import get_logger
from core.settings import settings
from db.database import get_db
from db.models import DestinyMatrixReading
from services.destiny_matrix.calculator import calculate_matrix
from services.destiny_matrix.v3_interpreter import (
    MODEL_V3,
    SECTIONS,
    SECTIONS_BY_KEY,
    V3Context,
    get_or_generate,
    load_cached_sections,
    load_v3_context,
    regenerate_sections,
)
from services.destiny_matrix_v3_pdf import generate_destiny_matrix_v3_pdf_html
from services.users import repository as user_repo

router = APIRouter(prefix="/destiny-matrix/v3", tags=["destiny-matrix-v3"])
log = get_logger(__name__)

# 2-section preview for non-premium readers — same split as V2.
FREE_KEYS_V3: tuple[str, ...] = ("visitka", "karmic_tail")
_TEASER = (
    "Этот раздел доступен в полном разборе. Откройте, чтобы прочитать "
    "тёплый персональный анализ по вашим арканам."
)


# ── Schemas ─────────────────────────────────────────────────────────────────


class SectionMeta(BaseModel):
    key: str
    title: str


class SectionsListResponse(BaseModel):
    sections: list[SectionMeta]
    free_keys: list[str]


class PurposeTripleOut(BaseModel):
    name: str
    key: tuple[int, int, int] = Field(..., description="(left, right, total)")


class YearEnergyOut(BaseModel):
    current: int
    upcoming: int


class KarmicProgramOut(BaseModel):
    key: str
    name: str
    description: str
    manifestations: str
    how_to_heal: str


class V3SectionPayload(BaseModel):
    key: str
    title: str
    content: str | None  # None → not yet generated (e.g. LLM failed for this card)
    locked: bool         # gated by premium


class V3ReadingResponse(BaseModel):
    birth_date: date
    positions: dict[str, Any]
    purposes: dict[str, PurposeTripleOut]
    year_energy: YearEnergyOut
    karmic_program: KarmicProgramOut | None
    sections: list[V3SectionPayload]
    has_full_access: bool
    model: str
    generated_at: datetime


class V3RegenerateRequest(BaseModel):
    keys: list[str] = Field(..., min_length=1, max_length=15)


class V3RegenerateResponse(BaseModel):
    updated: dict[str, str]


# ── Helpers ─────────────────────────────────────────────────────────────────


async def _has_full_access(db: AsyncSession, user_id: int) -> bool:
    if await user_repo.is_premium(db, user_id):
        return True
    return await user_repo.has_purchased(db, user_id, "destiny_matrix_full")


async def _resolve_user_and_reading(
    db: AsyncSession, tg_user: dict,
) -> tuple[Any, DestinyMatrixReading]:
    """Common preamble: load user, validate birth date, fetch-or-create
    the user's positions row. Mirrors the V2 endpoints so V3 always
    builds on top of an existing matrix reading (single source of truth
    for the diagram numbers)."""
    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if not user.birth_date:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Заполните дату рождения в профиле",
        )
    birth = (
        user.birth_date.date()
        if isinstance(user.birth_date, datetime)
        else user.birth_date
    )

    result = await db.execute(
        select(DestinyMatrixReading).where(
            DestinyMatrixReading.user_id == user.id,
            DestinyMatrixReading.birth_date == birth,
        )
    )
    reading = result.scalar_one_or_none()
    if reading is None:
        reading = DestinyMatrixReading(
            user_id=user.id, birth_date=birth, positions=calculate_matrix(birth),
        )
        db.add(reading)
        await db.flush()
    return user, reading


def _mask_sections(
    sections: dict[str, str], *, has_full_access: bool,
) -> list[V3SectionPayload]:
    """Build the response list in registry order, replacing locked
    sections with the teaser. Sections missing from `sections` (LLM
    failed for that card) come through as `content=None` so the UI
    can render a 'retry' affordance."""
    out: list[V3SectionPayload] = []
    for spec in SECTIONS:
        body = sections.get(spec.key)
        locked = (not has_full_access) and spec.key not in FREE_KEYS_V3
        if locked:
            out.append(V3SectionPayload(
                key=spec.key, title=spec.title, content=_TEASER, locked=True,
            ))
        else:
            out.append(V3SectionPayload(
                key=spec.key, title=spec.title, content=body, locked=False,
            ))
    return out


def _ctx_to_purpose_payload(ctx: V3Context) -> dict[str, PurposeTripleOut]:
    return {
        k: PurposeTripleOut(name=p.name, key=p.key) for k, p in ctx.purposes.items()
    }


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/sections", response_model=SectionsListResponse)
async def list_sections(_: dict = Depends(get_tg_user)) -> SectionsListResponse:
    """Section metadata for the accordion skeleton. Static, no DB."""
    return SectionsListResponse(
        sections=[SectionMeta(key=s.key, title=s.title) for s in SECTIONS],
        free_keys=list(FREE_KEYS_V3),
    )


@router.get("/reading", response_model=V3ReadingResponse)
async def get_reading(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
) -> V3ReadingResponse:
    """Full V3 reading. Generates any missing sections on the fly (full
    cold start ≈ 60s — frontend should show progress UI). For non-premium
    users we still generate everything in the background so that when
    they upgrade the report is already warm — but the response only
    surfaces the free preview keys plus locked teasers."""
    user, reading = await _resolve_user_and_reading(db, tg_user)
    has_full = await _has_full_access(db, user.id)
    gender = user.gender.value if user.gender else "any"

    ctx = await load_v3_context(
        db,
        user_id=user.id,
        birth_date=reading.birth_date,
        gender=gender,
        name=user.tg_first_name,
        positions=reading.positions,
    )

    # For premium readers, generate all 15. For free readers we still
    # generate just the free preview keys to avoid teasing empty UI
    # cards — the rest are filled lazily once they upgrade.
    if has_full:
        contents = await get_or_generate(db, ctx=ctx)
    else:
        cached = await load_cached_sections(
            db, user_id=user.id, birth_date=reading.birth_date, gender=gender,
        )
        missing_preview = [k for k in FREE_KEYS_V3 if k not in cached]
        if missing_preview:
            fresh = await regenerate_sections(db, ctx=ctx, keys=missing_preview)
            cached.update(fresh)
        contents = cached

    return V3ReadingResponse(
        birth_date=reading.birth_date,
        positions=reading.positions,
        purposes=_ctx_to_purpose_payload(ctx),
        year_energy=YearEnergyOut(
            current=ctx.year_energy.current, upcoming=ctx.year_energy.upcoming,
        ),
        karmic_program=(
            KarmicProgramOut(
                key=ctx.karmic.key,
                name=ctx.karmic.name,
                description=ctx.karmic.description,
                manifestations=ctx.karmic.manifestations,
                how_to_heal=ctx.karmic.how_to_heal,
            ) if ctx.karmic else None
        ),
        sections=_mask_sections(contents, has_full_access=has_full),
        has_full_access=has_full,
        model=MODEL_V3,
        generated_at=datetime.utcnow(),
    )


@router.post("/regenerate", response_model=V3RegenerateResponse)
async def regenerate(
    body: V3RegenerateRequest,
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
) -> V3RegenerateResponse:
    """Re-roll specific sections. Premium-only — free users can't bust
    their preview cache repeatedly to drain LLM budget."""
    user, reading = await _resolve_user_and_reading(db, tg_user)
    if not await _has_full_access(db, user.id):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "Перегенерация разделов доступна в полном разборе",
        )

    invalid = [k for k in body.keys if k not in SECTIONS_BY_KEY]
    if invalid:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Неизвестные разделы: {', '.join(invalid)}",
        )

    gender = user.gender.value if user.gender else "any"
    ctx = await load_v3_context(
        db,
        user_id=user.id,
        birth_date=reading.birth_date,
        gender=gender,
        name=user.tg_first_name,
        positions=reading.positions,
    )
    updated = await regenerate_sections(db, ctx=ctx, keys=body.keys)
    return V3RegenerateResponse(updated=updated)


_PDF_DOWNLOAD_TTL_SECONDS = 300


def _pdf_filename(user) -> str:
    safe = str(user.tg_first_name or "matrix").replace('"', "").strip() or "matrix"
    return f"destiny_matrix_v3_{safe}.pdf"


async def _build_v3_pdf_bytes(db: AsyncSession, user, reading) -> bytes:
    gender = user.gender.value if user.gender else "any"
    ctx = await load_v3_context(
        db,
        user_id=user.id,
        birth_date=reading.birth_date,
        gender=gender,
        name=user.tg_first_name,
        positions=reading.positions,
    )
    # PDF always needs all 15 sections — generate any missing on the fly.
    sections_text = await get_or_generate(db, ctx=ctx)

    purposes_payload = {
        k: {"name": p.name, "key": list(p.key)} for k, p in ctx.purposes.items()
    }
    karmic_payload = (
        {
            "key": ctx.karmic.key,
            "name": ctx.karmic.name,
            "description": ctx.karmic.description,
            "manifestations": ctx.karmic.manifestations,
            "how_to_heal": ctx.karmic.how_to_heal,
        }
        if ctx.karmic else None
    )
    return await generate_destiny_matrix_v3_pdf_html(
        user_name=user.tg_first_name or "User",
        birth_date=str(reading.birth_date),
        positions=reading.positions,
        sections_text=sections_text,
        purposes=purposes_payload,
        karmic_program=karmic_payload,
        year_energy={
            "current": ctx.year_energy.current,
            "upcoming": ctx.year_energy.upcoming,
        },
    )


async def _build_v3_pdf_response(db: AsyncSession, user, reading) -> Response:
    try:
        pdf_bytes = await _build_v3_pdf_bytes(db, user, reading)
    except Exception as e:  # noqa: BLE001
        log.error("destiny_matrix_v3.pdf_build_failed", user_id=user.id, error=str(e)[:500])
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Не удалось собрать PDF-отчёт. Попробуйте ещё раз.",
        ) from e
    filename = _pdf_filename(user)
    return Response(
        content=pdf_bytes,
        media_type="application/octet-stream",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": (
                f'attachment; filename="destiny-matrix-v3.pdf"; '
                f"filename*=UTF-8''{quote(filename)}"
            ),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/pdf")
async def get_v3_pdf(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Build + stream the V3 PDF (premium-only). Heavy: cold-start fires
    all 15 LLM calls if the cache is empty, then Playwright renders ~22
    A4 pages. Subsequent requests hit cached sections — render takes
    ~5-8s."""
    user, reading = await _resolve_user_and_reading(db, tg_user)
    if not await _has_full_access(db, user.id):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "PDF-отчёт доступен в Premium или после покупки полного разбора",
        )
    return await _build_v3_pdf_response(db, user, reading)


@router.post("/pdf-link")
async def create_v3_pdf_link(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Short-lived token URL for WebViews that block blob downloads."""
    user, _ = await _resolve_user_and_reading(db, tg_user)
    if not await _has_full_access(db, user.id):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "PDF-отчёт доступен в Premium или после покупки полного разбора",
        )
    token = token_urlsafe(24)
    await cache_set(
        key_destiny_pdf_download(token) + ":v3",
        {"user_id": user.id},
        _PDF_DOWNLOAD_TTL_SECONDS,
    )
    return {
        "download_url": f"/destiny-matrix/v3/pdf-download/{token}",
        "filename": _pdf_filename(user),
        "expires_in": _PDF_DOWNLOAD_TTL_SECONDS,
    }


@router.get("/pdf-download/{token}")
async def get_v3_pdf_by_token(
    token: str, db: AsyncSession = Depends(get_db),
) -> Response:
    payload = await cache_get(key_destiny_pdf_download(token) + ":v3")
    if not isinstance(payload, dict) or "user_id" not in payload:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Download link expired")
    user = await user_repo.get_by_id(db, int(payload["user_id"]))
    if not user or not user.birth_date:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")
    if not await _has_full_access(db, user.id):
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Access expired")
    birth = (
        user.birth_date.date()
        if isinstance(user.birth_date, datetime)
        else user.birth_date
    )
    result = await db.execute(
        select(DestinyMatrixReading).where(
            DestinyMatrixReading.user_id == user.id,
            DestinyMatrixReading.birth_date == birth,
        )
    )
    reading = result.scalar_one_or_none()
    if reading is None:
        reading = DestinyMatrixReading(
            user_id=user.id, birth_date=birth, positions=calculate_matrix(birth),
        )
        db.add(reading)
        await db.flush()
    return await _build_v3_pdf_response(db, user, reading)


@router.post("/pdf-send")
async def send_v3_pdf_to_telegram(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Build the V3 PDF and deliver it directly to the user's Telegram chat."""
    user, reading = await _resolve_user_and_reading(db, tg_user)
    if not await _has_full_access(db, user.id):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "PDF-отчёт доступен в Premium или после покупки полного разбора",
        )
    try:
        pdf_bytes = await _build_v3_pdf_bytes(db, user, reading)
    except Exception as e:  # noqa: BLE001
        log.error("destiny_matrix_v3.pdf_build_failed", user_id=user.id, error=str(e)[:500])
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Не удалось собрать PDF-отчёт. Попробуйте ещё раз.",
        ) from e

    filename = _pdf_filename(user)
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument"
    data = {
        "chat_id": str(user.id),
        "caption": "Ваш полный PDF-разбор Матрицы Судьбы (V3).",
    }
    files = {"document": (filename, BytesIO(pdf_bytes), "application/pdf")}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, data=data, files=files)
        payload = response.json()
    except Exception as e:  # noqa: BLE001
        log.error("destiny_matrix_v3.pdf_send_failed", user_id=user.id, error=str(e))
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
            "destiny_matrix_v3.pdf_send_rejected",
            user_id=user.id, status_code=response.status_code,
            error=description[:500],
        )
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Telegram не принял PDF. Попробуйте ещё раз.",
        )
    return {"status": "sent", "filename": filename}


@router.get("/year-energy", response_model=YearEnergyOut)
async def get_year_energy(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
) -> YearEnergyOut:
    """Just the current/upcoming arcana numbers. The full interpretation
    is part of the /reading payload — this endpoint is for the home
    widget that shows «энергия года: 7 → 8» without forcing the full
    LLM run."""
    user, reading = await _resolve_user_and_reading(db, tg_user)
    gender = user.gender.value if user.gender else "any"
    ctx = await load_v3_context(
        db,
        user_id=user.id,
        birth_date=reading.birth_date,
        gender=gender,
        name=user.tg_first_name,
        positions=reading.positions,
    )
    return YearEnergyOut(
        current=ctx.year_energy.current, upcoming=ctx.year_energy.upcoming,
    )
