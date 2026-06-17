"""Shared period helpers for user-facing daily/weekly limits."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

APP_TZ = ZoneInfo("Europe/Minsk")

DAILY = "daily"
WEEKLY = "weekly"

_WEEKLY_TAROT_SPREADS = {"celtic_cross", "week"}


def now_utc() -> datetime:
    return datetime.now(UTC)


def period_type_for_tarot(spread_type: str) -> str:
    return WEEKLY if spread_type in _WEEKLY_TAROT_SPREADS else DAILY


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def period_start(dt: datetime, period_type: str) -> datetime:
    """Local-time start of the period containing `dt`.

    Daily   → 00:00 of the same local day.
    Weekly  → 00:00 of the local Monday of that ISO week. A spread drawn
              on Wednesday and one drawn on Sunday share the same period
              and reset together on the following Monday 00:00 local.
    """
    local = _ensure_aware(dt).astimezone(APP_TZ)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    if period_type == WEEKLY:
        # weekday(): Mon=0, Sun=6. Roll back to Monday 00:00 local.
        start -= timedelta(days=start.weekday())
    return start.astimezone(UTC)


def period_end(dt: datetime, period_type: str) -> datetime:
    days = 7 if period_type == WEEKLY else 1
    return period_start(dt, period_type) + timedelta(days=days)


def next_reset_at(dt: datetime, period_type: str) -> datetime:
    return period_end(dt, period_type)


def is_active_period(created_at: datetime, period_type: str, *, now: datetime | None = None) -> bool:
    current = now or now_utc()
    return _ensure_aware(current) < next_reset_at(created_at, period_type)
