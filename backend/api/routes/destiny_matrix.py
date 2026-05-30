"""Destiny Matrix endpoints — calculate, fetch, look up an arcana."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from api.schemas.destiny_matrix import (
    ArcanaResponse,
    DestinyMatrixPositions,
    DestinyMatrixResponse,
    InterpretationResponse,
)
from core.logging import get_logger
from core.settings import settings
from db.database import get_db
from db.models import (
    ArcanaMeaning,
    DestinyMatrixInterpretation,
    DestinyMatrixReading,
)
from services.destiny_matrix.arcana_names import (
    ARCANA_KEYWORDS_RU,
    CONTEXTS,
    GENERIC_DESC_RU,
    arcana_name,
)
from services.destiny_matrix.calculator import calculate_matrix
from services.destiny_matrix.interpreter import generate_interpretation
from services.users import repository as user_repo

router = APIRouter(prefix="/destiny-matrix", tags=["destiny-matrix"])
log = get_logger(__name__)


async def _has_full_access(db: AsyncSession, user_id: int) -> bool:
    """Premium subscription OR a one-time destiny_matrix_full purchase."""
    is_prem = await user_repo.is_premium(db, user_id)
    if is_prem:
        return True
    return await user_repo.has_purchased(db, user_id, "destiny_matrix_full")


@router.post("/calculate", response_model=DestinyMatrixResponse)
async def calculate(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Idempotent: returns the existing reading for the user's current
    birth_date or creates one. The matrix is pure-math, so the result
    is deterministic — same birth_date always yields the same numbers."""
    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if not user.birth_date:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Заполните дату рождения в профиле",
        )

    birth_date = user.birth_date.date() if isinstance(user.birth_date, datetime) else user.birth_date

    # Try existing reading first
    result = await db.execute(
        select(DestinyMatrixReading).where(
            DestinyMatrixReading.user_id == user.id,
            DestinyMatrixReading.birth_date == birth_date,
        )
    )
    reading = result.scalar_one_or_none()
    if reading is None:
        positions = calculate_matrix(birth_date)
        reading = DestinyMatrixReading(
            user_id=user.id,
            birth_date=birth_date,
            positions=positions,
        )
        db.add(reading)
        try:
            await db.flush()
        except IntegrityError:
            # Concurrent insert from a duplicate /calculate — fetch the
            # winner. Same input → same positions, so it's fine.
            await db.rollback()
            result = await db.execute(
                select(DestinyMatrixReading).where(
                    DestinyMatrixReading.user_id == user.id,
                    DestinyMatrixReading.birth_date == birth_date,
                )
            )
            reading = result.scalar_one()

    return DestinyMatrixResponse(
        positions=DestinyMatrixPositions.model_validate(reading.positions),
        birth_date=reading.birth_date,
        computed_at=reading.computed_at,
        has_full_access=await _has_full_access(db, user.id),
    )


@router.get("/me", response_model=DestinyMatrixResponse)
async def get_me(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch the user's current matrix. Recomputes if birth_date has changed
    since the last reading (stale row gets ignored — a new row is added)."""
    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if not user.birth_date:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Заполните дату рождения в профиле",
        )

    birth_date = user.birth_date.date() if isinstance(user.birth_date, datetime) else user.birth_date

    result = await db.execute(
        select(DestinyMatrixReading).where(
            DestinyMatrixReading.user_id == user.id,
            DestinyMatrixReading.birth_date == birth_date,
        )
    )
    reading = result.scalar_one_or_none()
    if reading is None:
        # First visit / birth_date changed — compute now.
        positions = calculate_matrix(birth_date)
        reading = DestinyMatrixReading(
            user_id=user.id,
            birth_date=birth_date,
            positions=positions,
        )
        db.add(reading)
        await db.flush()

    return DestinyMatrixResponse(
        positions=DestinyMatrixPositions.model_validate(reading.positions),
        birth_date=reading.birth_date,
        computed_at=reading.computed_at,
        has_full_access=await _has_full_access(db, user.id),
    )


@router.get("/arcana/{num}", response_model=ArcanaResponse)
async def get_arcana(
    num: int,
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """All 8 context meanings for one arcana — used by the bottom-sheet.
    If a context row isn't in arcana_meanings yet (DB not seeded), returns
    GENERIC_DESC_RU as the meaning so the UI still shows something."""
    if not 1 <= num <= 22:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Arcana num must be 1..22")

    _ = tg_user  # auth only — no per-user data leaves this endpoint

    rows = await db.execute(
        select(ArcanaMeaning).where(ArcanaMeaning.arcana_num == num)
    )
    by_ctx: dict[str, str] = {}
    name_db: str | None = None
    for row in rows.scalars():
        by_ctx[row.context] = row.meaning
        name_db = row.arcana_name

    contexts: dict[str, str] = {}
    for ctx in CONTEXTS:
        contexts[ctx] = by_ctx.get(ctx, GENERIC_DESC_RU)

    return ArcanaResponse(
        arcana_num=num,
        arcana_name=name_db or arcana_name(num),
        keywords=ARCANA_KEYWORDS_RU.get(num, []),
        contexts=contexts,
    )


@router.get("/interpretation", response_model=InterpretationResponse)
async def get_interpretation(
    tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    """LLM-generated 7-section personal narrative. Premium-gated.
    Lazily generated on first request, cached per reading_id forever."""
    user = await user_repo.get_by_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    if not await _has_full_access(db, user.id):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "Полный разбор Матрицы доступен в Premium или после покупки",
        )

    if not user.birth_date:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Заполните дату рождения в профиле",
        )

    birth_date = user.birth_date.date() if hasattr(user.birth_date, "date") else user.birth_date

    # Find the user's current reading (must exist — frontend always calls
    # /calculate before /interpretation).
    result = await db.execute(
        select(DestinyMatrixReading).where(
            DestinyMatrixReading.user_id == user.id,
            DestinyMatrixReading.birth_date == birth_date,
        )
    )
    reading = result.scalar_one_or_none()
    if reading is None:
        # Edge case: race with /calculate. Build one now.
        positions = calculate_matrix(birth_date)
        reading = DestinyMatrixReading(
            user_id=user.id,
            birth_date=birth_date,
            positions=positions,
        )
        db.add(reading)
        await db.flush()

    # Cached interpretation?
    cached_result = await db.execute(
        select(DestinyMatrixInterpretation).where(
            DestinyMatrixInterpretation.reading_id == reading.id,
        )
    )
    cached = cached_result.scalar_one_or_none()
    if cached:
        return InterpretationResponse(
            reading_id=reading.id,
            sections=cached.sections,
            model=cached.model,
            generated_at=cached.generated_at,
        )

    # First time — call LLM.
    sections, model = await generate_interpretation(
        positions=reading.positions,
        first_name=user.tg_first_name,
        api_key=settings.ANTHROPIC_API_KEY,
    )

    # Don't cache the static fallback — that locks every future request
    # into the placeholder text. Return it once; the next visit retries
    # the LLM.
    if model == "fallback":
        log.warning("destiny_matrix.interp.fallback_no_cache", reading_id=reading.id)
        return InterpretationResponse(
            reading_id=reading.id,
            sections=sections,
            model=model,
            generated_at=datetime.utcnow(),
        )

    interp = DestinyMatrixInterpretation(
        reading_id=reading.id,
        sections=sections,
        model=model,
    )
    db.add(interp)
    try:
        await db.flush()
        await db.refresh(interp)
    except IntegrityError:
        # Lost a race with a parallel request — fetch the winner.
        await db.rollback()
        cached_result = await db.execute(
            select(DestinyMatrixInterpretation).where(
                DestinyMatrixInterpretation.reading_id == reading.id,
            )
        )
        interp = cached_result.scalar_one()

    return InterpretationResponse(
        reading_id=reading.id,
        sections=interp.sections,
        model=interp.model,
        generated_at=interp.generated_at,
    )
