"""Glossary endpoints — read-only, public (no auth-gated features)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from api.schemas.glossary import GlossaryTermFull, GlossaryTermShort
from db.database import get_db
from db.models import GlossaryCategory, GlossaryTerm

router = APIRouter(prefix="/glossary", tags=["glossary"])


def _to_short(t: GlossaryTerm) -> GlossaryTermShort:
    return GlossaryTermShort(
        slug=t.slug,
        title_ru=t.title_ru,
        category=t.category.value,
        short_ru=t.short_ru,
    )


@router.get("", response_model=list[GlossaryTermShort])
async def list_terms(
    category: str | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=64),
    _tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(GlossaryTerm).order_by(GlossaryTerm.title_ru)
    if category:
        try:
            cat_enum = GlossaryCategory(category)
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid category")
        stmt = stmt.where(GlossaryTerm.category == cat_enum)
    if q:
        pattern = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                GlossaryTerm.title_ru.ilike(pattern),
                GlossaryTerm.short_ru.ilike(pattern),
                GlossaryTerm.slug.ilike(pattern),
            )
        )
    result = await db.execute(stmt)
    return [_to_short(t) for t in result.scalars().all()]


@router.get("/{slug}", response_model=GlossaryTermFull)
async def get_term(
    slug: str,
    _tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(GlossaryTerm).where(GlossaryTerm.slug == slug))
    term = result.scalar_one_or_none()
    if term is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Term not found")

    related: list[GlossaryTermShort] = []
    if term.related_slugs:
        rel_result = await db.execute(
            select(GlossaryTerm).where(GlossaryTerm.slug.in_(term.related_slugs))
        )
        related = [_to_short(t) for t in rel_result.scalars().all()]

    return GlossaryTermFull(
        slug=term.slug,
        title_ru=term.title_ru,
        category=term.category.value,
        short_ru=term.short_ru,
        full_ru=term.full_ru,
        related=related,
    )
