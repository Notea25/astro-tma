"""First-touch acquisition / ad attribution helpers."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from db.models import User

log = get_logger(__name__)

_SOURCE_RE = re.compile(r"^[a-z0-9_]{1,64}$")
_AD_PREFIXES = ("ad_", "utm_", "src_", "c_", "camp_")
_RESERVED_PREFIXES = ("syn_",)


def normalize_acquisition_source(raw: str | None) -> str | None:
    """Return a safe first-touch source string, or None if not attributable."""
    if not raw:
        return None
    s = raw.strip().lower()
    if s.startswith("/start"):
        parts = s.split(maxsplit=1)
        s = parts[1].strip() if len(parts) > 1 else ""
    s = s.replace("-", "_").replace(" ", "_")
    if not s or not _SOURCE_RE.match(s):
        return None
    if any(s.startswith(p) for p in _RESERVED_PREFIXES):
        return None
    if s.startswith("ref_"):
        return "ref"
    if any(s.startswith(p) for p in _AD_PREFIXES):
        return s
    if s in {"start", "app", "open", "menu"}:
        return None
    return s


def apply_acquisition_source(user: User, raw: str | None) -> bool:
    """Set acquisition_source once (first touch). Returns True if written."""
    if user.acquisition_source:
        return False
    source = normalize_acquisition_source(raw)
    if not source:
        return False
    user.acquisition_source = source
    user.acquisition_at = datetime.now(UTC)
    log.info("acquisition.set", user_id=user.id, source=source)
    return True


async def acquisition_breakdown(
    db: AsyncSession,
    *,
    days: int = 30,
) -> list[dict[str, Any]]:
    """Users / onboarded / active / paid grouped by acquisition_source."""
    window_start = datetime.now(UTC) - timedelta(days=days)

    rows = (
        await db.execute(
            text(
                """
                SELECT
                  COALESCE(u.acquisition_source, 'organic') AS source,
                  COUNT(DISTINCT u.id) AS users,
                  COUNT(DISTINCT u.id) FILTER (WHERE u.sun_sign IS NOT NULL) AS onboarded,
                  COUNT(DISTINCT u.id) FILTER (
                    WHERE u.last_seen_at IS NOT NULL
                      AND u.last_seen_at >= NOW() - INTERVAL '7 days'
                  ) AS active_7d,
                  COUNT(DISTINCT u.id) FILTER (
                    WHERE p.user_id IS NOT NULL
                  ) AS paid
                FROM users u
                LEFT JOIN purchases p
                  ON p.user_id = u.id AND p.status = 'completed'
                WHERE COALESCE(u.acquisition_at, u.created_at) >= :since
                GROUP BY 1
                ORDER BY users DESC
                LIMIT 50
                """
            ),
            {"since": window_start},
        )
    ).all()

    out: list[dict[str, Any]] = []
    for source, users, onboarded, active_7d, paid in rows:
        users_i = int(users or 0)
        onboarded_i = int(onboarded or 0)
        paid_i = int(paid or 0)
        out.append(
            {
                "source": source,
                "users": users_i,
                "onboarded": onboarded_i,
                "active_7d": int(active_7d or 0),
                "paid": paid_i,
                "onboard_pct": round(onboarded_i / users_i * 100, 1) if users_i else 0,
                "paid_pct": round(paid_i / users_i * 100, 1) if users_i else 0,
            }
        )
    return out
