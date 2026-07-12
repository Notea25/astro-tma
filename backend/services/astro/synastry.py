"""
Natal synastry — compatibility of two natal charts.
Uses Kerykeion SynastryAspects to find inter-chart aspects.
"""

from datetime import datetime
from typing import Any

from kerykeion import AstrologicalSubjectFactory, SynastryAspects

from core.logging import get_logger
from services.astro.aspect_policy import (
    is_classic_planet,
    natal_or_synastry_orb_limit,
)

log = get_logger(__name__)

SYNASTRY_ASPECTS = frozenset(
    {"conjunction", "opposition", "trine", "square", "sextile"}
)

PLANET_WEIGHT: dict[str, int] = {
    "sun": 10, "moon": 10, "venus": 9, "mars": 8, "mercury": 7,
    "jupiter": 5, "saturn": 6, "uranus": 3, "neptune": 3, "pluto": 3,
}

ASPECT_WEIGHT: dict[str, int] = {
    "conjunction": 10, "trine": 9, "sextile": 7,
    "opposition": 6, "square": 6,
}

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
    Returns: {aspects: [...top 12], total_aspects: int}
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
        if not (
            is_classic_planet(str(a.p1_name))
            and is_classic_planet(str(a.p2_name))
        ):
            continue
        if aspect_name not in SYNASTRY_ASPECTS:
            continue
        if abs(a.orbit) > natal_or_synastry_orb_limit(a.p1_name, a.p2_name):
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
    log.info("synastry.calculated", total=len(aspects), top_weight=aspects[0]["weight"] if aspects else 0)

    return {
        "aspects": aspects[:12],
        "total_aspects": len(aspects),
    }
