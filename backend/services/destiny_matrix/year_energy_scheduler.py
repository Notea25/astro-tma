"""Hourly job: invalidate the year_energy section on a user's birthday.

The V3 reading's `year_energy` section is cached forever in
`destiny_interpretations_v3` like the other 14 sections — but unlike
them, its underlying arcana value SHIFTS once a year on the user's
birthday (see ``services.destiny_matrix.extended.calculate_year_energy``).
This job catches the local-timezone rollover into the new
birth-year and drops the cached row so the next ``/reading`` call
regenerates it for the new arcana.

We run hourly (not daily) because each hour catches a different group
of timezones rolling past midnight on their birthday. Doing it once a
day would miss the precise BD boundary for ~22h of users.

Idempotent: deleting a row twice is a no-op. If we miss a beat (job
skipped, crashed), the stale row simply lingers until the user opens
the app and triggers ``/regenerate``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select

from core.logging import get_logger
from db.database import AsyncSessionLocal
from db.models import DestinyInterpretationV3, User

log = get_logger(__name__)


async def invalidate_year_energy_on_birthday() -> None:
    """Drop the cached `year_energy` section for users whose local
    calendar just rolled into their BD."""
    now_utc = datetime.now(UTC)
    invalidated = 0
    checked = 0

    async with AsyncSessionLocal() as db:
        users = (
            await db.execute(select(User).where(User.birth_date.is_not(None)))
        ).scalars()

        for user in users:
            checked += 1
            tz_name = user.birth_tz or "UTC"
            try:
                local_now = now_utc.astimezone(ZoneInfo(tz_name))
            except Exception:  # noqa: BLE001
                local_now = now_utc

            # User.birth_date may be Date or DateTime depending on the column —
            # normalise to `date` before comparing or `.replace()` keeps the
            # datetime type and we'd compare datetime > date below.
            bd_date = user.birth_date
            if isinstance(bd_date, datetime):
                bd_date = bd_date.date()
            # Feb 29 → use Feb 28 on non-leap years so the rollover still
            # fires once a year. Trying to call .replace(year=…) would
            # raise ValueError otherwise.
            try:
                bd_this_year = bd_date.replace(year=local_now.year)
            except ValueError:
                bd_this_year = bd_date.replace(year=local_now.year, day=28)
            today_local = local_now.date()
            yesterday_local = today_local - timedelta(days=1)

            # Rollover hour: today is on/after this year's BD AND yesterday
            # wasn't. That's exactly the one-day window after the BD
            # boundary across all hour-granularity timezones.
            if not (today_local >= bd_this_year > yesterday_local):
                continue

            result = await db.execute(
                delete(DestinyInterpretationV3).where(
                    DestinyInterpretationV3.user_id == user.id,
                    DestinyInterpretationV3.section == "year_energy",
                )
            )
            if result.rowcount:
                invalidated += 1
                log.info(
                    "destiny_v3.year_energy.invalidated_user",
                    user_id=user.id, tz=tz_name,
                )

        await db.commit()
        log.info(
            "destiny_v3.year_energy.invalidated_run",
            checked=checked, invalidated=invalidated,
        )
