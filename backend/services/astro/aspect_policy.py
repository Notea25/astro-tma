"""Shared policy for user-facing astrological aspects."""

from __future__ import annotations

CLASSIC_PLANETS: tuple[str, ...] = (
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
)
CLASSIC_PLANET_SET = frozenset(CLASSIC_PLANETS)
LUMINARIES = frozenset({"sun", "moon"})


def normalize_point_name(name: str) -> str:
    """Normalize Kerykeion point names for allow-list comparisons."""
    return name.strip().lower().replace(" ", "_")


def is_classic_planet(name: str) -> bool:
    return normalize_point_name(name) in CLASSIC_PLANET_SET


def natal_or_synastry_orb_limit(left: str, right: str) -> float:
    """GeoCult-compatible orb: 8° for luminaries, 6° otherwise."""
    names = {normalize_point_name(left), normalize_point_name(right)}
    return 8.0 if names & LUMINARIES else 6.0
