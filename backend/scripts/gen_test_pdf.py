"""Quick local script to generate a test natal PDF and save it to /tmp/test_natal.pdf.

Mirrors prod behaviour from api/routes/natal.py — tries HTML renderer first
(Playwright/Chromium), falls back to ReportLab on failure.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.natal_pdf import generate_natal_pdf
from services.natal_pdf_html import generate_natal_pdf_html

planets = {
    "sun": {
        "sign": "libra",
        "sign_ru": "Весы",
        "degree": 197.2,
        "sign_degree": 17.2,
        "house": 12,
        "retrograde": False,
    },
    "moon": {
        "sign": "pisces",
        "sign_ru": "Рыбы",
        "degree": 339.9,
        "sign_degree": 9.9,
        "house": 4,
        "retrograde": False,
    },
    "mercury": {
        "sign": "scorpio",
        "sign_ru": "Скорпион",
        "degree": 222.2,
        "sign_degree": 12.2,
        "house": 1,
        "retrograde": False,
    },
    "venus": {
        "sign": "scorpio",
        "sign_ru": "Скорпион",
        "degree": 229.0,
        "sign_degree": 19.0,
        "house": 1,
        "retrograde": False,
    },
    "mars": {
        "sign": "virgo",
        "sign_ru": "Дева",
        "degree": 164.6,
        "sign_degree": 14.6,
        "house": 10,
        "retrograde": False,
    },
    "jupiter": {
        "sign": "gemini",
        "sign_ru": "Близнецы",
        "degree": 71.0,
        "sign_degree": 11.0,
        "house": 8,
        "retrograde": True,
    },
    "saturn": {
        "sign": "gemini",
        "sign_ru": "Близнецы",
        "degree": 60.3,
        "sign_degree": 0.3,
        "house": 8,
        "retrograde": True,
    },
    "uranus": {
        "sign": "aquarius",
        "sign_ru": "Водолей",
        "degree": 317.0,
        "sign_degree": 17.0,
        "house": 3,
        "retrograde": True,
    },
    "neptune": {
        "sign": "aquarius",
        "sign_ru": "Водолей",
        "degree": 303.8,
        "sign_degree": 3.8,
        "house": 3,
        "retrograde": True,
    },
    "pluto": {
        "sign": "sagittarius",
        "sign_ru": "Стрелец",
        "degree": 250.8,
        "sign_degree": 10.8,
        "house": 2,
        "retrograde": False,
    },
}

houses = [
    {"number": 1, "sign": "scorpio", "sign_ru": "Скорпион", "degree": 210.6},
    {"number": 2, "sign": "scorpio", "sign_ru": "Скорпион", "degree": 236.7},
    {"number": 3, "sign": "capricorn", "sign_ru": "Козерог", "degree": 273.0},
    {"number": 4, "sign": "aquarius", "sign_ru": "Водолей", "degree": 317.0},
    {"number": 5, "sign": "pisces", "sign_ru": "Рыбы", "degree": 350.8},
    {"number": 6, "sign": "aries", "sign_ru": "Овен", "degree": 14.1},
    {"number": 7, "sign": "taurus", "sign_ru": "Телец", "degree": 30.6},
    {"number": 8, "sign": "taurus", "sign_ru": "Телец", "degree": 56.7},
    {"number": 9, "sign": "cancer", "sign_ru": "Рак", "degree": 93.0},
    {"number": 10, "sign": "leo", "sign_ru": "Лев", "degree": 137.0},
    {"number": 11, "sign": "virgo", "sign_ru": "Дева", "degree": 170.8},
    {"number": 12, "sign": "libra", "sign_ru": "Весы", "degree": 194.1},
]

aspects = [
    {"p1": "sun", "p2": "jupiter", "aspect": "trine", "orb": 6.2},
    {"p1": "sun", "p2": "uranus", "aspect": "trine", "orb": 0.2},
    {"p1": "sun", "p2": "pluto", "aspect": "sextile", "orb": 6.4},
    {"p1": "moon", "p2": "mercury", "aspect": "trine", "orb": 2.2},
    {"p1": "moon", "p2": "jupiter", "aspect": "square", "orb": 1.1},
    {"p1": "moon", "p2": "mars", "aspect": "opposition", "orb": 4.6},
    {"p1": "moon", "p2": "pluto", "aspect": "square", "orb": 0.9},
    {"p1": "mercury", "p2": "venus", "aspect": "conjunction", "orb": 6.8},
    {"p1": "mercury", "p2": "mars", "aspect": "sextile", "orb": 2.4},
    {"p1": "mercury", "p2": "uranus", "aspect": "square", "orb": 4.8},
    {"p1": "venus", "p2": "mars", "aspect": "sextile", "orb": 4.5},
    {"p1": "venus", "p2": "uranus", "aspect": "square", "orb": 2.0},
    {"p1": "mars", "p2": "jupiter", "aspect": "square", "orb": 3.5},
    {"p1": "mars", "p2": "pluto", "aspect": "square", "orb": 3.8},
    {"p1": "jupiter", "p2": "uranus", "aspect": "trine", "orb": 6.0},
    {"p1": "jupiter", "p2": "neptune", "aspect": "trine", "orb": 7.2},
    {"p1": "jupiter", "p2": "pluto", "aspect": "opposition", "orb": 0.2},
    {"p1": "saturn", "p2": "neptune", "aspect": "trine", "orb": 3.5},
    {"p1": "uranus", "p2": "pluto", "aspect": "sextile", "orb": 6.2},
    {"p1": "neptune", "p2": "pluto", "aspect": "sextile", "orb": 7.0},
]

reading = """**Ядро личности**
Внутри вас живёт уравновешенный и справедливый человек — это ваше Солнце в Весах. Вы от природы склонны видеть разные стороны ситуации, взвешивать аргументы, искать компромисс. Но это внутреннее «я» находится в 12-м доме — месте, где мы часто скрываем самые личные убеждения. Луна в Рыбах добавляет совсем другое измерение: глубокую чувствительность и способность без слов понять эмоциональное состояние другого человека.

**Ум и общение**
Меркурий в Скорпионе в 1-м доме — это острый, проницательный ум. Вы говорите немного, но каждое слово взвешено. Вам нравится копать глубже, доходить до сути, вы замечаете то, что другие упускают.

**Любовь и ценности**
Венера в Скорпионе в 1-м доме — вы любите глубоко, полностью, с огромной преданностью и требованием такой же от партнёра. Секс и эмоциональное слияние для вас неразделимы.

**Энергия и воля**
Марс в Деве в 10-м доме — вы действуете расчётливо и систематично. Это не импульсивный боец, это стратег. В карьере это выглядит как последовательное продвижение.

**Ключевые аспекты**
Солнце в тайном трине с Ураном (орб 0.2° — точный аспект) — редкий подарок. Уран планета революции, отличия, свободы. Трин означает, что вам легче отойти от шаблонов и быть собой."""

out = "/tmp/test_natal.pdf"
kwargs = dict(
    user_name="Andrey",
    birth_date="2000-10-10",
    birth_time="10:00",
    birth_city="Санкт-Петербург, Россия",
    sun_sign="libra",
    moon_sign="pisces",
    asc_sign="scorpio",
    planets=planets,
    houses=houses,
    aspects=aspects,
    reading=reading,
    descriptions=None,
)


async def main():
    try:
        pdf = await generate_natal_pdf_html(**kwargs)
        renderer = "HTML (Playwright)"
    except Exception as e:
        print(f"HTML renderer failed ({e}), falling back to ReportLab")
        pdf = generate_natal_pdf(**kwargs)
        renderer = "ReportLab"
    with open(out, "wb") as f:
        f.write(pdf)
    print(f"PDF saved to {out} ({len(pdf)} bytes) via {renderer}")


asyncio.run(main())
