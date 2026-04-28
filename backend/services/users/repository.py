"""
User repository — all DB queries for the User domain.
Services call this; routes call services. Routes never touch DB directly.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.logging import get_logger
from db.models import (
    NatalChart,
    User,
    ZodiacSign,
)

log = get_logger(__name__)


async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(
        select(User)
        .options(selectinload(User.natal_chart), selectinload(User.subscriptions))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_or_create(
    db: AsyncSession,
    tg_user_id: int,
    first_name: str,
    username: str | None = None,
    last_name: str | None = None,
    language_code: str = "ru",
    is_premium: bool = False,
) -> tuple[User, bool]:
    """
    Upsert user from Telegram initData.
    Returns (user, created) tuple.
    """
    user = await get_by_id(db, tg_user_id)
    if user:
        # Sync mutable Telegram fields
        user.tg_first_name = first_name
        user.tg_username = username
        user.tg_last_name = last_name
        user.tg_is_premium = is_premium
        return user, False

    user = User(
        id=tg_user_id,
        tg_first_name=first_name,
        tg_username=username,
        tg_last_name=last_name,
        tg_language_code=language_code,
        tg_is_premium=is_premium,
    )
    db.add(user)
    await db.flush()
    log.info("user.created", user_id=tg_user_id, name=first_name)
    return user, True


async def update_birth_data(
    db: AsyncSession,
    user: User,
    birth_date: datetime,
    birth_time_known: bool,
    birth_city: str,
    lat: float,
    lng: float,
    tz_str: str,
    sun_sign: ZodiacSign,
) -> User:
    user.birth_date = birth_date
    user.birth_time_known = birth_time_known
    user.birth_city = birth_city
    user.birth_lat = lat
    user.birth_lng = lng
    user.birth_tz = tz_str
    user.sun_sign = sun_sign
    await db.flush()
    log.info("user.birth_updated", user_id=user.id, sign=sun_sign)
    return user


async def save_natal_chart(
    db: AsyncSession,
    user_id: int,
    sun_sign: str,
    moon_sign: str,
    ascendant_sign: str | None,
    chart_data: dict,
) -> NatalChart:
    result = await db.execute(
        select(NatalChart).where(NatalChart.user_id == user_id)
    )
    chart = result.scalar_one_or_none()

    if chart:
        chart.sun_sign = sun_sign
        chart.moon_sign = moon_sign
        chart.ascendant_sign = ascendant_sign
        chart.chart_data = chart_data
    else:
        chart = NatalChart(
            user_id=user_id,
            sun_sign=sun_sign,
            moon_sign=moon_sign,
            ascendant_sign=ascendant_sign,
            chart_data=chart_data,
        )
        db.add(chart)

    await db.flush()
    return chart


async def is_premium(db: AsyncSession, user_id: int) -> bool:
    """
    Check if user has active premium subscription.
    # TEST MODE: always returns True — revert before production
    """
    return True  # TEST MODE


async def has_purchased(db: AsyncSession, user_id: int, product_id: str) -> bool:
    """Check one-time purchase (e.g. natal_full, synastry).
    # TEST MODE: always returns True — revert before production
    """
    return True  # TEST MODE
