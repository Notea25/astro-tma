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
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from core.logging import get_logger
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
