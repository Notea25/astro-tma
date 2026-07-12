"""
Natal chart calculation via Kerykeion / Swiss Ephemeris.

Responsibility: given birth data → return structured planet/house/aspect data.
No interpretation logic here — that lives in interpreter.py.
This module is PURE CALCULATION.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from kerykeion import AstrologicalSubjectFactory

from core.logging import get_logger
from services.astro.aspect_policy import (
    CLASSIC_PLANETS,
    natal_or_synastry_orb_limit,
)

log = get_logger(__name__)


@dataclass(frozen=True)
class PlanetPosition:
    name: str
    sign: str
    sign_ru: str
    degree: float  # absolute degree 0–360
    sign_degree: float  # degree within sign 0–30
    house: int | None  # 1–12; unknown without a reliable birth time
    retrograde: bool
    speed: float  # degrees/day


@dataclass(frozen=True)
class AspectData:
    p1: str  # planet 1 name
    p2: str  # planet 2 name
    aspect: str  # "conjunction", "trine", "square", "opposition", "sextile"
    orb: float  # degrees of orb
    applying: bool | None  # applying vs separating; None when not calculated


@dataclass(frozen=True)
class NatalChartData:
    sun: PlanetPosition
    moon: PlanetPosition
    mercury: PlanetPosition
    venus: PlanetPosition
    mars: PlanetPosition
    jupiter: PlanetPosition
    saturn: PlanetPosition
    uranus: PlanetPosition
    neptune: PlanetPosition
    pluto: PlanetPosition
    ascendant_sign: str | None
    mc_sign: str | None
    houses: list[dict[str, Any]]  # [{number: 1, sign: "aries", degree: 15.5}, ...]
    aspects: list[AspectData]
    raw: dict[str, Any]  # full kerykeion dump for future use
    # Лунные узлы (Раху/Кету). Держим отдельно от классических планет, чтобы не
    # попасть в расчёт аспектов и не отрисоваться как планета в круге. Ключи:
    # "true_north_lunar_node" / "true_south_lunar_node" → planet-dict (или None).
    nodes: dict[str, dict[str, Any]] | None = None


# Kerykeion v5 returns abbreviated sign names ("Ari", "Tau", …)
# Normalize to full name for consistency
_SIGN_ABBR_TO_FULL: dict[str, str] = {
    "Ari": "Aries",
    "Tau": "Taurus",
    "Gem": "Gemini",
    "Can": "Cancer",
    "Leo": "Leo",
    "Vir": "Virgo",
    "Lib": "Libra",
    "Sco": "Scorpio",
    "Sag": "Sagittarius",
    "Cap": "Capricorn",
    "Aqu": "Aquarius",
    "Pis": "Pisces",
}

# Russian sign names mapping (full names)
_SIGN_RU: dict[str, str] = {
    "Aries": "Овен",
    "Taurus": "Телец",
    "Gemini": "Близнецы",
    "Cancer": "Рак",
    "Leo": "Лев",
    "Virgo": "Дева",
    "Libra": "Весы",
    "Scorpio": "Скорпион",
    "Sagittarius": "Стрелец",
    "Capricorn": "Козерог",
    "Aquarius": "Водолей",
    "Pisces": "Рыбы",
}


def _normalize_sign(raw: str | None) -> str:
    """Convert kerykeion v5 abbreviated sign to full name."""
    if not raw:
        return "Unknown"
    return _SIGN_ABBR_TO_FULL.get(raw, raw)


_PLANET_ATTRS = list(CLASSIC_PLANETS)

_PLANET_DISPLAY_NAMES: dict[str, str] = {
    "sun": "Sun",
    "moon": "Moon",
    "mercury": "Mercury",
    "venus": "Venus",
    "mars": "Mars",
    "jupiter": "Jupiter",
    "saturn": "Saturn",
    "uranus": "Uranus",
    "neptune": "Neptune",
    "pluto": "Pluto",
}

_MAJOR_ASPECTS: tuple[tuple[str, float], ...] = (
    ("conjunction", 0.0),
    ("sextile", 60.0),
    ("square", 90.0),
    ("trine", 120.0),
    ("opposition", 180.0),
)

# Kerykeion v5 returns house as string; map to int 1–12
_HOUSE_STR_TO_INT: dict[str, int] = {
    "First_House": 1,
    "Second_House": 2,
    "Third_House": 3,
    "Fourth_House": 4,
    "Fifth_House": 5,
    "Sixth_House": 6,
    "Seventh_House": 7,
    "Eighth_House": 8,
    "Ninth_House": 9,
    "Tenth_House": 10,
    "Eleventh_House": 11,
    "Twelfth_House": 12,
}


def _parse_house(point) -> int:
    """Extract house number from a KerykeionPointModel (v5-compatible)."""
    # v5 uses .house (str like "First_House"), v4 used .house_name (int)
    for attr in ("house", "house_name"):
        val = getattr(point, attr, None)
        if val is None:
            continue
        if isinstance(val, int):
            return val
        if isinstance(val, str):
            return _HOUSE_STR_TO_INT.get(val, 1)
    return 1


def _angular_distance(left: float, right: float) -> float:
    distance = abs(left - right) % 360
    return min(distance, 360 - distance)


def _calculate_major_planet_aspects(
    planets: dict[str, PlanetPosition],
) -> list[AspectData]:
    """Calculate visible natal aspects in the same planet-only style as astro-online.

    Kerykeion's default list includes additional points like nodes and Lilith and
    uses different orb cutoffs. For the user-facing natal report we keep the
    classic 10 planets and the 5 major aspects with an 8-degree orb, matching
    the external reference site much more closely.
    """
    aspects: list[AspectData] = []

    for left_index, left_key in enumerate(_PLANET_ATTRS):
        left = planets[left_key]
        for right_key in _PLANET_ATTRS[left_index + 1 :]:
            right = planets[right_key]
            distance = _angular_distance(left.degree, right.degree)

            for aspect_name, target_angle in _MAJOR_ASPECTS:
                orb = abs(distance - target_angle)
                if orb <= natal_or_synastry_orb_limit(left_key, right_key):
                    aspects.append(
                        AspectData(
                            p1=_PLANET_DISPLAY_NAMES[left_key],
                            p2=_PLANET_DISPLAY_NAMES[right_key],
                            aspect=aspect_name,
                            orb=round(orb, 2),
                            applying=None,
                        )
                    )
                    break

    return aspects


_LUNAR_NODE_ATTRS = ("true_north_lunar_node", "true_south_lunar_node")


def _extract_lunar_nodes(
    subject, *, include_houses: bool = True
) -> dict[str, dict[str, Any]]:
    """Извлекает лунные узлы (Раху/Кету) из Kerykeion-субъекта.

    Возвращает dict {attr → planet-dict}. Узлы держим ОТДЕЛЬНО от _PLANET_ATTRS:
    они не должны попасть в расчёт аспектов или в круг как планеты. Если узел не
    рассчитан (None) — ключ пропускается."""
    nodes: dict[str, dict[str, Any]] = {}
    for attr in _LUNAR_NODE_ATTRS:
        p = getattr(subject, attr, None)
        if p is None or getattr(p, "sign", None) is None:
            continue
        sign = _normalize_sign(p.sign)
        nodes[attr] = {
            "name": attr,
            "sign": sign,
            "sign_ru": _SIGN_RU.get(sign, sign),
            "degree": round(getattr(p, "abs_pos", 0.0) or 0.0, 4),
            "sign_degree": round(getattr(p, "position", 0.0) or 0.0, 4),
            "house": _parse_house(p) if include_houses else None,
            "retrograde": bool(getattr(p, "retrograde", False)),
            "speed": round(getattr(p, "speed", 0.0) or 0.0, 4),
        }
    return nodes


def calculate_natal(
    name: str,
    birth_dt: datetime,
    lat: float,
    lng: float,
    tz_str: str,
    birth_time_known: bool = True,
) -> NatalChartData:
    """
    Core natal chart calculation.
    Thread-safe: creates a new Kerykeion subject each call (no shared state).
    Falls back to noon if birth time unknown.
    """
    hour = birth_dt.hour if birth_time_known else 12
    minute = birth_dt.minute if birth_time_known else 0

    log.debug(
        "natal.calculating",
        name=name,
        date=birth_dt.date().isoformat(),
        time_known=birth_time_known,
    )

    subject = AstrologicalSubjectFactory.from_birth_data(
        name=name,
        year=birth_dt.year,
        month=birth_dt.month,
        day=birth_dt.day,
        hour=hour,
        minute=minute,
        lat=lat,
        lng=lng,
        tz_str=tz_str,
        online=False,
        houses_system_identifier="P",  # Placidus — industry standard
    )

    planets: dict[str, PlanetPosition] = {}
    for attr in _PLANET_ATTRS:
        p = getattr(subject, attr)
        sign = _normalize_sign(p.sign)
        planets[attr] = PlanetPosition(
            name=attr,
            sign=sign,
            sign_ru=_SIGN_RU.get(sign, sign),
            degree=round(p.abs_pos or 0.0, 4),
            sign_degree=round(p.position or 0.0, 4),
            house=_parse_house(p) if birth_time_known else None,
            retrograde=bool(p.retrograde),
            speed=round(p.speed or 0.0, 4),
        )

    # Houses — v5 uses houses_names_list + individual attrs (first_house, etc.)
    houses: list[dict] = []
    house_name_list = getattr(subject, "houses_names_list", None)
    if birth_time_known and house_name_list:
        for i, house_name in enumerate(house_name_list):
            h = getattr(subject, house_name.lower(), None)
            if h:
                s = _normalize_sign(h.sign)
                houses.append(
                    {
                        "number": i + 1,
                        "sign": s,
                        "sign_ru": _SIGN_RU.get(s, s),
                        "degree": round(h.abs_pos or 0.0, 4),
                    }
                )

    aspects = _calculate_major_planet_aspects(planets)

    # Лунные узлы — отдельный канал (chart.nodes), НЕ в planets: не участвуют ни
    # в аспектах, ни в круге, ни в подсчёте стихий. Читаются только блоком
    # «Лунные узлы» в reading.
    nodes = _extract_lunar_nodes(subject, include_houses=birth_time_known)

    # Ascendant / MC — attribute names differ between kerykeion versions
    asc = getattr(subject, "ascendant", None) or getattr(subject, "first_house", None)
    mc = getattr(subject, "medium_coeli", None) or getattr(subject, "tenth_house", None)

    chart = NatalChartData(
        **planets,
        ascendant_sign=_normalize_sign(asc.sign) if birth_time_known and asc else None,
        mc_sign=_normalize_sign(mc.sign) if birth_time_known and mc else None,
        houses=houses,
        aspects=aspects,
        raw=subject.model_dump(),
        nodes=nodes or None,
    )

    log.info(
        "natal.calculated",
        sun=chart.sun.sign,
        moon=chart.moon.sign,
        asc=chart.ascendant_sign,
        aspects_count=len(aspects),
    )
    return chart


def chart_to_json(chart: NatalChartData) -> dict[str, Any]:
    """Serialise NatalChartData for DB storage (JSON column)."""

    def planet_dict(p: PlanetPosition) -> dict[str, Any]:
        return {
            "sign": p.sign,
            "sign_ru": p.sign_ru,
            "degree": p.degree,
            "sign_degree": p.sign_degree,
            "house": p.house,
            "retrograde": p.retrograde,
            "speed": p.speed,
        }

    planets_out = {attr: planet_dict(getattr(chart, attr)) for attr in _PLANET_ATTRS}

    return {
        "planets": planets_out,
        # Лунные узлы — ОТДЕЛЬНЫЙ канал, НЕ в planets. Иначе все потребители,
        # обходящие planets.values() (стихии в PDF, natal_hero, dominants),
        # ошибочно считали бы Раху/Кету планетами и ломали проценты стихий.
        # Узлы читает только блок «Лунные узлы» в generate_natal_reading.
        "nodes": chart.nodes or {},
        "ascendant_sign": chart.ascendant_sign,
        "mc_sign": chart.mc_sign,
        "houses": chart.houses,
        "aspects": [
            {"p1": a.p1, "p2": a.p2, "aspect": a.aspect, "orb": a.orb, "applying": a.applying}
            for a in chart.aspects
        ],
    }
