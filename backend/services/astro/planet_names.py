"""Canonical Russian translations and glyphs for planets and chart points.

Used everywhere we render astrological data in the UI / PDF / LLM prompts.
Centralised so that adding a new chart point (e.g. Chiron, Lilith variants,
lunar nodes) only needs to be done once.
"""

# Chart point key (kerykeion's `.lower()`) → Russian display name.
PLANET_RU: dict[str, str] = {
    # Classical planets + luminaries
    "sun": "Солнце",
    "moon": "Луна",
    "mercury": "Меркурий",
    "venus": "Венера",
    "mars": "Марс",
    "jupiter": "Юпитер",
    "saturn": "Сатурн",
    "uranus": "Уран",
    "neptune": "Нептун",
    "pluto": "Плутон",
    # Chart axes
    "ascendant": "Асцендент",
    "descendant": "Десцендент",
    "medium_coeli": "Середина неба",
    "imum_coeli": "Глубина неба",
    # Lunar nodes (kerykeion uses several variants)
    "mean_node": "Северный узел",
    "true_node": "Северный узел",
    "mean_lunar_node": "Северный узел",
    "true_lunar_node": "Северный узел",
    "mean_north_lunar_node": "Северный узел",
    "true_north_lunar_node": "Северный узел",
    "mean_south_node": "Южный узел",
    "true_south_node": "Южный узел",
    "mean_south_lunar_node": "Южный узел",
    "true_south_lunar_node": "Южный узел",
    # Lilith (Black Moon)
    "mean_lilith": "Лилит",
    "true_lilith": "Лилит",
    "black_moon_lilith": "Лилит",
    # Other points
    "chiron": "Хирон",
}

# Chart point key → unicode glyph. Falls back to "●" for unknown.
PLANET_GLYPH: dict[str, str] = {
    "sun": "☉",
    "moon": "☽",
    "mercury": "☿",
    "venus": "♀",
    "mars": "♂",
    "jupiter": "♃",
    "saturn": "♄",
    "uranus": "♅",
    "neptune": "♆",
    "pluto": "♇",
    "ascendant": "Asc",
    "descendant": "Dsc",
    "medium_coeli": "MC",
    "imum_coeli": "IC",
    "mean_node": "☊",
    "true_node": "☊",
    "mean_lunar_node": "☊",
    "true_lunar_node": "☊",
    "mean_north_lunar_node": "☊",
    "true_north_lunar_node": "☊",
    "mean_south_node": "☋",
    "true_south_node": "☋",
    "mean_south_lunar_node": "☋",
    "true_south_lunar_node": "☋",
    "mean_lilith": "⚸",
    "true_lilith": "⚸",
    "black_moon_lilith": "⚸",
    "chiron": "⚷",
}


def planet_ru(name: str) -> str:
    """Lookup with sensible fallback — returns the input unchanged if unknown."""
    return PLANET_RU.get(name.lower(), name)


def planet_glyph(name: str) -> str:
    return PLANET_GLYPH.get(name.lower(), "●")
