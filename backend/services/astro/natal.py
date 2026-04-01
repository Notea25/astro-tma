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
from kerykeion import NatalAspects

from core.logging import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class PlanetPosition:
    name: str
    sign: str
    sign_ru: str
    degree: float          # absolute degree 0–360
    sign_degree: float     # degree within sign 0–30
    house: int             # 1–12
    retrograde: bool
    speed: float           # degrees/day


@dataclass(frozen=True)
class AspectData:
    p1: str         # planet 1 name
    p2: str         # planet 2 name
    aspect: str     # "conjunction", "trine", "square", "opposition", "sextile"
    orb: float      # degrees of orb
    applying: bool  # applying vs separating


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
    houses: list[dict[str, Any]]   # [{number: 1, sign: "aries", degree: 15.5}, ...]
    aspects: list[AspectData]
    raw: dict[str, Any]            # full kerykeion dump for future use


# Russian sign names mapping
_SIGN_RU: dict[str, str] = {
    "Aries": "Овен", "Taurus": "Телец", "Gemini": "Близнецы",
    "Cancer": "Рак", "Leo": "Лев", "Virgo": "Дева",
    "Libra": "Весы", "Scorpio": "Скорпион", "Sagittarius": "Стрелец",
    "Capricorn": "Козерог", "Aquarius": "Водолей", "Pisces": "Рыбы",
}

_PLANET_ATTRS = [
    "sun", "moon", "mercury", "venus", "mars",
    "jupiter", "saturn", "uranus", "neptune", "pluto",
]

# Kerykeion v5 returns house as string; map to int 1–12
_HOUSE_STR_TO_INT: dict[str, int] = {
    "First_House": 1, "Second_House": 2, "Third_House": 3,
    "Fourth_House": 4, "Fifth_House": 5, "Sixth_House": 6,
    "Seventh_House": 7, "Eighth_House": 8, "Ninth_House": 9,
    "Tenth_House": 10, "Eleventh_House": 11, "Twelfth_House": 12,
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
        sign = p.sign or "Unknown"
        planets[attr] = PlanetPosition(
            name=attr,
            sign=sign,
            sign_ru=_SIGN_RU.get(sign, sign),
            degree=round(p.abs_pos or 0.0, 4),
            sign_degree=round(p.position or 0.0, 4),
            house=_parse_house(p),
            retrograde=bool(p.retrograde),
            speed=round(p.speed or 0.0, 4),
        )

    # Houses
    houses = [
        {
            "number": i + 1,
            "sign": h.sign or "Unknown",
            "sign_ru": _SIGN_RU.get(h.sign or "", h.sign or ""),
            "degree": round(h.abs_pos or 0.0, 4),
        }
        for i, h in enumerate(subject.houses_list)
    ]

    # Aspects
    natal_aspects = NatalAspects(subject)
    aspects: list[AspectData] = []
    for a in natal_aspects.all_aspects:
        aspects.append(AspectData(
            p1=a.p1_name,
            p2=a.p2_name,
            aspect=a.aspect_name.lower(),
            orb=round(a.orbit, 2),
            applying=bool(getattr(a, "applying", False)),
        ))

    # Ascendant / MC — attribute names differ between kerykeion versions
    asc = getattr(subject, "ascendant", None) or getattr(subject, "first_house", None)
    mc = getattr(subject, "medium_coeli", None) or getattr(subject, "tenth_house", None)

    chart = NatalChartData(
        **planets,
        ascendant_sign=asc.sign if asc else None,
        mc_sign=mc.sign if mc else None,
        houses=houses,
        aspects=aspects,
        raw=subject.model_dump(),
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
            "sign": p.sign, "sign_ru": p.sign_ru,
            "degree": p.degree, "sign_degree": p.sign_degree,
            "house": p.house, "retrograde": p.retrograde, "speed": p.speed,
        }

    return {
        "planets": {attr: planet_dict(getattr(chart, attr)) for attr in _PLANET_ATTRS},
        "ascendant_sign": chart.ascendant_sign,
        "mc_sign": chart.mc_sign,
        "houses": chart.houses,
        "aspects": [
            {"p1": a.p1, "p2": a.p2, "aspect": a.aspect,
             "orb": a.orb, "applying": a.applying}
            for a in chart.aspects
        ],
    }
