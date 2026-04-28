"""
Astro event detection — scans ephemeris for noteworthy events in a date range.
Produces seed data for the news generator.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from kerykeion import AstrologicalSubjectFactory

from core.logging import get_logger
from db.models import NewsCategory
from services.astro.natal import _PLANET_ATTRS

log = get_logger(__name__)

_SIGN_ABBR_TO_FULL = {
    "Ari": "Aries", "Tau": "Taurus", "Gem": "Gemini", "Can": "Cancer",
    "Leo": "Leo", "Vir": "Virgo", "Lib": "Libra", "Sco": "Scorpio",
    "Sag": "Sagittarius", "Cap": "Capricorn", "Aqu": "Aquarius", "Pis": "Pisces",
}

_SIGN_RU = {
    "Aries": "Овен", "Taurus": "Телец", "Gemini": "Близнецы",
    "Cancer": "Рак", "Leo": "Лев", "Virgo": "Дева",
    "Libra": "Весы", "Scorpio": "Скорпион", "Sagittarius": "Стрелец",
    "Capricorn": "Козерог", "Aquarius": "Водолей", "Pisces": "Рыбы",
}

_PLANET_RU = {
    "sun": "Солнце", "moon": "Луна", "mercury": "Меркурий", "venus": "Венера",
    "mars": "Марс", "jupiter": "Юпитер", "saturn": "Сатурн",
    "uranus": "Уран", "neptune": "Нептун", "pluto": "Плутон",
}


def _sky_snapshot(dt: datetime) -> dict[str, dict[str, Any]]:
    subject = AstrologicalSubjectFactory.from_birth_data(
        name="_sky",
        year=dt.year, month=dt.month, day=dt.day,
        hour=dt.hour, minute=dt.minute,
        lat=0.0, lng=0.0, tz_str="UTC",
        online=False,
    )
    snap = {}
    for attr in _PLANET_ATTRS:
        p = getattr(subject, attr)
        sign = p.sign
        sign_full = _SIGN_ABBR_TO_FULL.get(sign, sign) if sign else "Unknown"
        snap[attr] = {
            "sign": sign_full,
            "sign_ru": _SIGN_RU.get(sign_full, sign_full),
            "degree": round(p.abs_pos or 0.0, 4),
            "retrograde": bool(p.retrograde),
        }
    return snap


def detect_events(start: datetime, days: int = 2) -> list[dict[str, Any]]:
    """
    Detect notable events in [start, start+days).
    Returns list of dicts with keys: date, category, priority, title_ru, source_data.
    Currently detects: sign ingress (planet moves to new sign), retrograde change.
    """
    events: list[dict[str, Any]] = []
    if days < 1:
        return events

    # Sample 1 snapshot per day at noon UTC
    snapshots: list[tuple[datetime, dict]] = []
    for i in range(days + 1):
        d = start + timedelta(days=i)
        d = d.replace(hour=12, minute=0, second=0, microsecond=0, tzinfo=UTC)
        snapshots.append((d, _sky_snapshot(d)))

    for idx in range(1, len(snapshots)):
        prev_dt, prev_snap = snapshots[idx - 1]
        curr_dt, curr_snap = snapshots[idx]

        for planet in _PLANET_ATTRS:
            prev = prev_snap[planet]
            curr = curr_snap[planet]

            # Ingress: sign changed
            if prev["sign"] != curr["sign"]:
                ru_planet = _PLANET_RU.get(planet, planet)
                events.append({
                    "date": curr_dt,
                    "category": NewsCategory.INGRESS,
                    "priority": 8 if planet in {"sun", "venus", "mars", "jupiter"} else 5,
                    "title_ru": f"{ru_planet} переходит в {curr['sign_ru']}",
                    "source_data": {
                        "planet": planet,
                        "from_sign": prev["sign"],
                        "to_sign": curr["sign"],
                        "to_sign_ru": curr["sign_ru"],
                    },
                })

            # Retrograde change
            if prev["retrograde"] != curr["retrograde"]:
                ru_planet = _PLANET_RU.get(planet, planet)
                if curr["retrograde"]:
                    title = f"{ru_planet} становится ретроградным"
                    priority = 9 if planet in {"mercury", "venus", "mars"} else 6
                else:
                    title = f"{ru_planet} возобновляет прямое движение"
                    priority = 7 if planet in {"mercury", "venus", "mars"} else 5
                events.append({
                    "date": curr_dt,
                    "category": NewsCategory.EVENT,
                    "priority": priority,
                    "title_ru": title,
                    "source_data": {
                        "planet": planet,
                        "retrograde": curr["retrograde"],
                    },
                })

    log.info("news.events_detected", count=len(events), days=days)
    return events
