"""Astro news endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import get_tg_user
from api.schemas.news import NewsItem, NewsPreview
from db.database import get_db
from db.models import AstroNews, NewsCategory

router = APIRouter(prefix="/news", tags=["news"])


@router.get("", response_model=list[NewsPreview])
async def list_news(
    limit: int = Query(default=20, ge=1, le=100),
    category: str | None = Query(default=None),
    _tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(AstroNews)
        .where(AstroNews.published.is_(True))
        .order_by(desc(AstroNews.date), desc(AstroNews.priority))
        .limit(limit)
    )
    if category:
        try:
            cat_enum = NewsCategory(category)
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid category")
        stmt = stmt.where(AstroNews.category == cat_enum)

    result = await db.execute(stmt)
    return [
        NewsPreview(
            id=n.id,
            date=n.date,
            title_ru=n.title_ru,
            category=n.category.value,
            priority=n.priority,
            preview=(n.body_md[:160] + "…") if len(n.body_md) > 160 else n.body_md,
        )
        for n in result.scalars().all()
    ]


@router.get("/{news_id}", response_model=NewsItem)
async def get_news_item(
    news_id: int,
    _tg_user: dict = Depends(get_tg_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AstroNews).where(AstroNews.id == news_id))
    item = result.scalar_one_or_none()
    if item is None or not item.published:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "News not found")
    return NewsItem(
        id=item.id,
        date=item.date,
        title_ru=item.title_ru,
        body_md=item.body_md,
        category=item.category.value,
        priority=item.priority,
    )
