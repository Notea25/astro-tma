#!/usr/bin/env python3
"""Create/reset the development-only Astro QA comparison profile."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from core.cache import close_redis, get_redis, init_redis
from core.settings import settings
from db.database import AsyncSessionLocal
from db.models import (
    DestinyInterpretationV3,
    DestinyMatrixInterpretation,
    DestinyMatrixReading,
    Gender,
    NatalChart,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    SynastryRequest,
    TarotReading,
    User,
    YearEnergyInterpretation,
    ZodiacSign,
)
from services.astro.natal import calculate_natal, chart_to_json

QA_USER_ID = 777777777
QA_BIRTH = datetime(2000, 2, 20, 14, 30)


async def _clear_redis() -> None:
    try:
        await init_redis()
        redis = get_redis()
        keys: list[str] = []
        async for key in redis.scan_iter(match=f"*{QA_USER_ID}*"):
            keys.append(str(key))
        if keys:
            await redis.delete(*keys)
    except Exception as exc:  # Redis is optional for the DB seed itself.
        print(f"Redis cleanup skipped: {type(exc).__name__}")
    finally:
        await close_redis()


async def seed(*, reset: bool) -> None:
    if settings.APP_ENV == "production":
        raise RuntimeError("Refusing to seed Astro QA in production")

    chart = calculate_natal(
        name="Astro QA",
        birth_dt=QA_BIRTH,
        lat=55.7558,
        lng=37.6173,
        tz_str="Europe/Moscow",
        birth_time_known=True,
    )
    async with AsyncSessionLocal() as session:
        user = await session.get(User, QA_USER_ID)
        if user is None:
            user = User(
                id=QA_USER_ID,
                tg_first_name="Astro QA",
                tg_username="astro_qa_local",
                tg_last_name=None,
                tg_language_code="ru",
                tg_is_premium=False,
            )
            session.add(user)
            await session.flush()

        if reset:
            matrix_ids = select(DestinyMatrixReading.id).where(
                DestinyMatrixReading.user_id == QA_USER_ID
            )
            await session.execute(
                delete(DestinyMatrixInterpretation).where(
                    DestinyMatrixInterpretation.reading_id.in_(matrix_ids)
                )
            )
            await session.execute(delete(DestinyMatrixReading).where(DestinyMatrixReading.user_id == QA_USER_ID))
            await session.execute(delete(DestinyInterpretationV3).where(DestinyInterpretationV3.user_id == QA_USER_ID))
            await session.execute(delete(YearEnergyInterpretation).where(YearEnergyInterpretation.user_id == QA_USER_ID))
            await session.execute(delete(TarotReading).where(TarotReading.user_id == QA_USER_ID))
            await session.execute(
                delete(SynastryRequest).where(
                    SynastryRequest.initiator_user_id == QA_USER_ID
                )
            )
            await session.execute(delete(Subscription).where(Subscription.user_id == QA_USER_ID))

        user.tg_first_name = "Astro QA"
        user.gender = Gender.MALE
        user.birth_date = QA_BIRTH
        user.birth_time_known = True
        user.birth_city = "Москва, Россия"
        user.birth_lat = 55.7558
        user.birth_lng = 37.6173
        user.birth_tz = "Europe/Moscow"
        user.birth_country_code = "RU"
        user.sun_sign = ZodiacSign.PISCES

        natal = (
            await session.execute(select(NatalChart).where(NatalChart.user_id == QA_USER_ID))
        ).scalar_one_or_none()
        if natal is None:
            natal = NatalChart(user_id=QA_USER_ID)
            session.add(natal)
        natal.sun_sign = chart.sun.sign
        natal.moon_sign = chart.moon.sign
        natal.ascendant_sign = chart.ascendant_sign
        natal.chart_data = chart_to_json(chart)

        active = (
            await session.execute(
                select(Subscription).where(
                    Subscription.user_id == QA_USER_ID,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                )
            )
        ).scalar_one_or_none()
        if active is None:
            now = datetime.now(UTC)
            session.add(
                Subscription(
                    user_id=QA_USER_ID,
                    plan=SubscriptionPlan.PREMIUM_YEAR,
                    status=SubscriptionStatus.ACTIVE,
                    stars_paid=0,
                    starts_at=now,
                    expires_at=now + timedelta(days=3650),
                    is_trial=True,
                    trial_reason="comparison_qa",
                )
            )
        await session.commit()

    if reset:
        await _clear_redis()
    print("Astro QA ready: user_id=777777777, 20.02.2000 14:30 Europe/Moscow")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    asyncio.run(seed(reset=args.reset))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
