"""
Natal synastry — compatibility of two natal charts.
Uses Kerykeion SynastryAspects to find inter-chart aspects.
"""

from datetime import datetime
from typing import Any

from kerykeion import AstrologicalSubjectFactory, SynastryAspects

from core.logging import get_logger

log = get_logger(__name__)

SYNASTRY_ORBS: dict[str, float] = {
    "conjunction": 8.0,
    "opposition": 7.0,
    "trine": 6.0,
    "square": 6.0,
    "sextile": 4.0,
}

PLANET_WEIGHT: dict[str, int] = {
    "sun": 10, "moon": 10, "venus": 9, "mars": 8, "mercury": 7,
    "jupiter": 5, "saturn": 6, "uranus": 3, "neptune": 3, "pluto": 3,
}

ASPECT_WEIGHT: dict[str, int] = {
    "conjunction": 10, "trine": 9, "sextile": 7,
    "opposition": 6, "square": 6,
}

_LOVE_PLANETS = {"venus", "moon", "mars"}
_COMM_PLANETS = {"mercury", "sun"}
_TRUST_PLANETS = {"saturn", "sun", "moon"}
_PASSION_PLANETS = {"mars", "pluto", "venus"}

_POSITIVE = {"trine", "sextile", "conjunction"}


def _build_subject(
    name: str,
    birth_dt: datetime,
    lat: float,
    lng: float,
    tz_str: str,
    birth_time_known: bool = True,
):
    hour = birth_dt.hour if birth_time_known else 12
    minute = birth_dt.minute if birth_time_known else 0
    return AstrologicalSubjectFactory.from_birth_data(
        name=name,
        year=birth_dt.year, month=birth_dt.month, day=birth_dt.day,
        hour=hour, minute=minute,
        lat=lat, lng=lng, tz_str=tz_str,
        online=False,
    )


def _compute_scores(aspects: list[dict[str, Any]]) -> dict[str, int]:
    base = 50
    scores = {"love": base, "communication": base, "trust": base, "passion": base, "overall": base}

    for a in aspects[:20]:
        p1 = a["p1_name"].lower()
        p2 = a["p2_name"].lower()
        aspect = a["aspect"]
        delta = 3 if aspect in _POSITIVE else -2

        if p1 in _LOVE_PLANETS or p2 in _LOVE_PLANETS:
            scores["love"] += delta
        if p1 in _COMM_PLANETS or p2 in _COMM_PLANETS:
            scores["communication"] += delta
        if p1 in _TRUST_PLANETS or p2 in _TRUST_PLANETS:
            scores["trust"] += delta
        if p1 in _PASSION_PLANETS or p2 in _PASSION_PLANETS:
            scores["passion"] += delta
        scores["overall"] += delta // 2

    return {k: max(15, min(95, v)) for k, v in scores.items()}


def calculate_synastry(
    user_a: dict[str, Any],
    user_b: dict[str, Any],
) -> dict[str, Any]:
    """
    Args:
        user_a / user_b: dict with keys:
            name: str
            birth_dt: datetime
            lat: float
            lng: float
            tz_str: str
            birth_time_known: bool
    Returns: {aspects: [...top 12], scores: {love, communication, trust, passion, overall}, total_aspects: int}
    """
    sub_a = _build_subject(
        user_a.get("name", "A"),
        user_a["birth_dt"], user_a["lat"], user_a["lng"],
        user_a["tz_str"], user_a.get("birth_time_known", True),
    )
    sub_b = _build_subject(
        user_b.get("name", "B"),
        user_b["birth_dt"], user_b["lat"], user_b["lng"],
        user_b["tz_str"], user_b.get("birth_time_known", True),
    )

    synastry = SynastryAspects(sub_a, sub_b)

    aspects: list[dict[str, Any]] = []
    for a in synastry.all_aspects:
        aspect_raw = getattr(a, "aspect", None) or getattr(a, "aspect_name", "")
        if callable(aspect_raw):
            aspect_raw = aspect_raw()
        aspect_name = str(aspect_raw).lower()
        if aspect_name not in SYNASTRY_ORBS:
            continue
        if abs(a.orbit) > SYNASTRY_ORBS[aspect_name]:
            continue
        weight = (
            PLANET_WEIGHT.get(a.p1_name.lower(), 1)
            + PLANET_WEIGHT.get(a.p2_name.lower(), 1)
            + ASPECT_WEIGHT.get(aspect_name, 1)
        )
        aspects.append({
            "p1_name": a.p1_name,
            "p2_name": a.p2_name,
            "aspect": aspect_name,
            "orb": round(abs(a.orbit), 2),
            "weight": weight,
        })

    aspects.sort(key=lambda x: x["weight"], reverse=True)
    scores = _compute_scores(aspects)

    log.info("synastry.calculated", total=len(aspects), top_weight=aspects[0]["weight"] if aspects else 0)

    return {
        "aspects": aspects[:12],
        "scores": scores,
        "total_aspects": len(aspects),
    }
