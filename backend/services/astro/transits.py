"""
Daily transit calculation — current sky vs natal chart.
Used to personalise horoscopes beyond generic sun-sign text.
"""

from datetime import datetime, timezone
from typing import Any

from kerykeion import AstrologicalSubjectFactory
from kerykeion.aspects.synastry_aspects import SynastryAspects

from core.logging import get_logger
from services.astro.natal import NatalChartData, _PLANET_ATTRS

log = get_logger(__name__)

# Tight orbs for transits (stricter than natal)
TRANSIT_ORBS: dict[str, float] = {
    "conjunction": 3.0,
    "opposition": 3.0,
    "square": 2.5,
    "trine": 2.5,
    "sextile": 2.0,
}

# Weight by significance (used to sort which transits matter most)
PLANET_WEIGHT: dict[str, int] = {
    "sun": 10, "moon": 9, "mercury": 6, "venus": 7, "mars": 8,
    "jupiter": 5, "saturn": 7, "uranus": 3, "neptune": 2, "pluto": 2,
}

ASPECT_WEIGHT: dict[str, int] = {
    "conjunction": 10, "opposition": 8, "square": 7,
    "trine": 6, "sextile": 4,
}


def get_current_sky(dt: datetime | None = None) -> dict[str, Any]:
    """Return current planetary positions as a plain dict."""
    dt = dt or datetime.now(timezone.utc)
    subject = AstrologicalSubjectFactory.from_birth_data(
        name="_transit",
        year=dt.year, month=dt.month, day=dt.day,
        hour=dt.hour, minute=dt.minute,
        lat=0.0, lng=0.0, tz_str="UTC",
        online=False,
    )
    return {
        attr: {
            "sign": getattr(subject, attr).sign,
            "degree": round(getattr(subject, attr).abs_pos, 4),
            "retrograde": bool(getattr(subject, attr).retrograde),
        }
        for attr in _PLANET_ATTRS
    }


def calculate_transits(natal: NatalChartData, dt: datetime | None = None) -> list[dict[str, Any]]:
    """
    Find significant transit aspects to natal chart.
    Returns list sorted by significance (highest-weight first).
    """
    dt = dt or datetime.now(timezone.utc)

    natal_subject = AstrologicalSubjectFactory.from_birth_data(
        name="_natal",
        year=2000, month=1, day=1,  # placeholder — we override planets below
        hour=12, minute=0,
        lat=0.0, lng=0.0, tz_str="UTC",
        online=False,
    )
    transit_subject = AstrologicalSubjectFactory.from_birth_data(
        name="_current",
        year=dt.year, month=dt.month, day=dt.day,
        hour=dt.hour, minute=dt.minute,
        lat=0.0, lng=0.0, tz_str="UTC",
        online=False,
    )

    synastry = SynastryAspects(natal_subject, transit_subject)
    results: list[dict[str, Any]] = []

    for aspect in synastry.all_aspects:
        aspect_name = aspect.aspect_name.lower()
        if aspect_name not in TRANSIT_ORBS:
            continue
        if abs(aspect.orbit) > TRANSIT_ORBS[aspect_name]:
            continue

        weight = (
            PLANET_WEIGHT.get(aspect.p1_name.lower(), 1)
            + ASPECT_WEIGHT.get(aspect_name, 1)
        )
        results.append({
            "transit_planet": aspect.p2_name,
            "natal_planet": aspect.p1_name,
            "aspect": aspect_name,
            "orb": round(aspect.orbit, 2),
            "weight": weight,
        })

    results.sort(key=lambda x: x["weight"], reverse=True)
    log.debug("transits.calculated", count=len(results), date=dt.date().isoformat())
    return results[:10]  # top 10 most significant


def build_energy_scores(transits: list[dict[str, Any]], base_sign: str) -> dict[str, int]:
    """
    Derive love / career / health / luck scores from active transits.
    Returns values 0–100. Used for the progress bars in the UI.
    """
    base = 55  # neutral baseline

    # Sign-based modifiers (static component)
    sign_mod: dict[str, dict[str, int]] = {
        "aries":       {"love": -2, "career": 5, "health": 5, "luck": 3},
        "taurus":      {"love": 5,  "career": 2, "health": 3, "luck": 2},
        "gemini":      {"love": 2,  "career": 5, "health": -2,"luck": 3},
        "cancer":      {"love": 8,  "career": -2,"health": 3, "luck": 0},
        "leo":         {"love": 5,  "career": 8, "health": 3, "luck": 5},
        "virgo":       {"love": -2, "career": 8, "health": 5, "luck": 2},
        "libra":       {"love": 8,  "career": 2, "health": 0, "luck": 5},
        "scorpio":     {"love": 5,  "career": 3, "health": -3,"luck": 2},
        "sagittarius": {"love": 3,  "career": 3, "health": 5, "luck": 8},
        "capricorn":   {"love": -3, "career": 10,"health": 2, "luck": 3},
        "aquarius":    {"love": 2,  "career": 5, "health": 0, "luck": 5},
        "pisces":      {"love": 5,  "career": -2,"health": 2, "luck": 3},
    }

    mods = sign_mod.get(base_sign.lower(), {})
    scores = {
        "love":   base + mods.get("love", 0),
        "career": base + mods.get("career", 0),
        "health": base + mods.get("health", 0),
        "luck":   base + mods.get("luck", 0),
    }

    # Transit-based adjustments
    _LOVE_PLANETS = {"venus", "moon"}
    _CAREER_PLANETS = {"saturn", "jupiter", "mars", "sun"}
    _HEALTH_PLANETS = {"mars", "sun", "moon"}
    _LUCK_PLANETS = {"jupiter", "sun"}

    _POSITIVE_ASPECTS = {"trine", "sextile", "conjunction"}
    _NEGATIVE_ASPECTS = {"square", "opposition"}

    for t in transits:
        tp = t["transit_planet"].lower()
        aspect = t["aspect"]
        delta = 5 if aspect in _POSITIVE_ASPECTS else -5
        if tp in _LOVE_PLANETS:    scores["love"]   += delta
        if tp in _CAREER_PLANETS:  scores["career"] += delta
        if tp in _HEALTH_PLANETS:  scores["health"] += delta
        if tp in _LUCK_PLANETS:    scores["luck"]   += delta

    # Clamp 20–95
    return {k: max(20, min(95, v)) for k, v in scores.items()}
