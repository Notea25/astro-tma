#!/usr/bin/env python3
"""
Seed natal chart interpretations: planets in signs, planets in houses, aspects.
Parses natal_interpretations.md and inserts ~290 records into the interpretations table.

Run: docker compose exec backend python scripts/seed_natal_interpretations.py
"""
import asyncio
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from sqlalchemy import delete
from db.database import AsyncSessionLocal
from db.models import Interpretation


# ── Mappings ─────────────────────────────────────────────────────────────────

PLANET_MAP = {
    # Nominative case (for first planet / planet-in-sign / planet-in-house)
    "Солнце": "sun",
    "Луна": "moon",
    "Меркурий": "mercury",
    "Венера": "venus",
    "Марс": "mars",
    "Юпитер": "jupiter",
    "Сатурн": "saturn",
    "Уран": "uranus",
    "Нептун": "neptune",
    "Плутон": "pluto",
    # Instrumental case (for second planet in aspect headers: "с Луной")
    "Луной": "moon",
    "Меркурием": "mercury",
    "Венерой": "venus",
    "Марсом": "mars",
    "Юпитером": "jupiter",
    "Сатурном": "saturn",
    "Ураном": "uranus",
    "Нептуном": "neptune",
    "Плутоном": "pluto",
    "Солнцем": "sun",
}

SIGN_MAP = {
    "Овне": "aries",
    "Овен": "aries",
    "Тельце": "taurus",
    "Телец": "taurus",
    "Близнецах": "gemini",
    "Близнецы": "gemini",
    "Раке": "cancer",
    "Рак": "cancer",
    "Льве": "leo",
    "Лев": "leo",
    "Деве": "virgo",
    "Дева": "virgo",
    "Весах": "libra",
    "Весы": "libra",
    "Скорпионе": "scorpio",
    "Скорпион": "scorpio",
    "Стрельце": "sagittarius",
    "Стрелец": "sagittarius",
    "Козероге": "capricorn",
    "Козерог": "capricorn",
    "Водолее": "aquarius",
    "Водолей": "aquarius",
    "Рыбах": "pisces",
    "Рыбы": "pisces",
}

ASPECT_MAP = {
    "соединении": "conjunction",
    "оппозиции": "opposition",
    "квадрате": "square",
    "трине": "trine",
    "секстиле": "sextile",
}

# Regex for house number: "в 1-м доме", "во 2-м доме"
HOUSE_RE = re.compile(r"в[о]?\s+(\d{1,2})-м\s+доме")

# Regex for planet in sign: "Солнце в Овне" (possibly with extra like "(обитель)")
PLANET_SIGN_RE = re.compile(
    r"^([\w]+)\s+в[о]?\s+([\w]+?)(?:\s*\(.*\))?$"
)

# Regex for planet in house: "Солнце в 1-м доме" (possibly with extra like "(естественный дом)")
PLANET_HOUSE_RE = re.compile(
    r"^([\w]+)\s+в[о]?\s+(\d{1,2})-м\s+доме(?:\s*\(.*\))?$"
)

# Regex for aspect: "Солнце в соединении с Луной"
ASPECT_RE = re.compile(
    r"^([\w]+)\s+в\s+([\w]+)\s+с\s+([\w]+)$"
)


def parse_markdown(filepath: str) -> list[dict]:
    """Parse the natal interpretations markdown file into a list of records."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    records = []
    # Split into sections by ### headers
    sections = re.split(r"^### ", content, flags=re.MULTILINE)

    for section in sections[1:]:  # skip everything before first ###
        lines = section.strip().split("\n", 1)
        if len(lines) < 2:
            continue

        title = lines[0].strip()
        body = lines[1].strip()

        # Extract only the first paragraph (stop at ---, ##, or blank line + ##)
        # The actual interpretation text is always the first paragraph after the title.
        text_lines = []
        for line in body.split("\n"):
            stripped = line.strip()
            if stripped.startswith("---") or stripped.startswith("##") or stripped.startswith("# "):
                break
            if stripped == "" and text_lines:
                break
            if stripped:
                text_lines.append(stripped)

        text = " ".join(text_lines).strip()
        if not text:
            continue

        record = _parse_title(title, text)
        if record:
            records.append(record)

    return records


def _parse_title(title: str, text: str) -> dict | None:
    """Parse a ### title into a structured record."""

    # Try aspect first (most specific pattern): "Солнце в соединении с Луной"
    m = ASPECT_RE.match(title)
    if m:
        planet1_ru, aspect_ru, planet2_ru = m.groups()
        planet1 = PLANET_MAP.get(planet1_ru)
        aspect = ASPECT_MAP.get(aspect_ru)
        planet2 = PLANET_MAP.get(planet2_ru)
        if planet1 and aspect and planet2:
            return {
                "planet": planet1,
                "sign": planet2,  # second planet stored in sign column
                "house": None,
                "aspect": aspect,
                "text_ru": text,
            }
        return None

    # Try planet in house: "Солнце в 1-м доме"
    m = PLANET_HOUSE_RE.match(title)
    if m:
        planet_ru, house_num = m.groups()
        planet = PLANET_MAP.get(planet_ru)
        if planet:
            return {
                "planet": planet,
                "sign": None,
                "house": int(house_num),
                "aspect": None,
                "text_ru": text,
            }
        return None

    # Try planet in sign: "Солнце в Овне"
    m = PLANET_SIGN_RE.match(title)
    if m:
        planet_ru, sign_ru = m.groups()
        planet = PLANET_MAP.get(planet_ru)
        sign = SIGN_MAP.get(sign_ru)
        if planet and sign:
            return {
                "planet": planet,
                "sign": sign,
                "house": None,
                "aspect": None,
                "text_ru": text,
            }
        return None

    return None


async def seed():
    # Resolve path to the markdown file
    # When running inside docker, the file should be copied to a known location.
    # For local dev, use the desktop path or pass via env var.
    md_path = os.environ.get(
        "NATAL_MD_PATH",
        os.path.join(os.path.dirname(__file__), "natal_interpretations.md"),
    )

    if not os.path.exists(md_path):
        print(f"File not found: {md_path}")
        print("Set NATAL_MD_PATH env var or place the file next to this script.")
        sys.exit(1)

    records = parse_markdown(md_path)
    print(f"Parsed {len(records)} interpretations from markdown")

    # Count by type
    signs = sum(1 for r in records if r["sign"] and not r["aspect"])
    houses = sum(1 for r in records if r["house"] is not None)
    aspects = sum(1 for r in records if r["aspect"])
    print(f"  Planets in signs:  {signs}")
    print(f"  Planets in houses: {houses}")
    print(f"  Aspects:           {aspects}")

    async with AsyncSessionLocal() as session:
        # Clear existing interpretations
        await session.execute(delete(Interpretation))

        for r in records:
            session.add(Interpretation(
                planet=r["planet"],
                sign=r["sign"],
                house=r["house"],
                aspect=r["aspect"],
                text_ru=r["text_ru"],
            ))

        await session.commit()
        print(f"\nSeeded {len(records)} natal interpretations into DB")


if __name__ == "__main__":
    asyncio.run(seed())
