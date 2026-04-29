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
    local = _ensure_aware(dt).astimezone(APP_TZ)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.astimezone(UTC)


def period_end(dt: datetime, period_type: str) -> datetime:
    days = 7 if period_type == WEEKLY else 1
    return period_start(dt, period_type) + timedelta(days=days)


def next_reset_at(dt: datetime, period_type: str) -> datetime:
    return period_end(dt, period_type)


def is_active_period(created_at: datetime, period_type: str, *, now: datetime | None = None) -> bool:
    current = now or now_utc()
    return _ensure_aware(current) < next_reset_at(created_at, period_type)
