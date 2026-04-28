"""
Horoscope text interpreter.

Responsibility: given a NatalChartData + list of active transits,
assemble a human-readable horoscope text in Russian.

Architecture:
  1. Query DB for matching interpretation texts
  2. If personalised (has natal) → merge natal + transit interpretations
  3. If generic (sign only)     → return sign-of-day text
  4. Assemble into a coherent paragraph (not just list of facts)

This module is the CONTENT layer — it doesn't do astronomical calculations.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from db.models import Interpretation

log = get_logger(__name__)


@dataclass
class InterpretationBlock:
    """A single interpreted piece of the horoscope."""
    planet: str
    category: str    # "personality" | "emotion" | "communication" | "love" | "career"
    text: str
    weight: int      # higher = more important, shown first


async def get_natal_interpretation(
    db: AsyncSession,
    sun_sign: str,
    moon_sign: str,
    asc_sign: str | None,
    planet_signs: dict[str, str],  # {"mercury": "scorpio", ...}
) -> list[InterpretationBlock]:
    """
    Fetch natal interpretations for the core placements.
    Returns blocks sorted by weight (most significant first).
    """
    # Build queries for the most important placements
    queries = [
        ("sun",     sun_sign,  None, None, "personality", 10),
        ("moon",    moon_sign, None, None, "emotion",     9),
    ]
    if asc_sign:
        queries.append(("ascendant", asc_sign, None, None, "personality", 8))

    for planet, sign in planet_signs.items():
        if planet in ("mercury", "venus", "mars"):
            weight = {"mercury": 7, "venus": 7, "mars": 6}[planet]
            category = {"mercury": "communication", "venus": "love", "mars": "career"}[planet]
            queries.append((planet, sign, None, None, category, weight))

    blocks: list[InterpretationBlock] = []

    for planet, sign, house, aspect, category, weight in queries:
        result = await db.execute(
            select(Interpretation).where(
                and_(
                    Interpretation.planet == planet,
                    Interpretation.sign == sign.lower(),
                    Interpretation.house.is_(None),
                    Interpretation.aspect.is_(None),
                )
            ).limit(1)
        )
        interp = result.scalar_one_or_none()
        if interp:
            blocks.append(InterpretationBlock(
                planet=planet,
                category=category,
                text=interp.text_ru,
                weight=weight,
            ))
        else:
            log.debug("interpreter.no_text", planet=planet, sign=sign)

    blocks.sort(key=lambda b: b.weight, reverse=True)
    return blocks


async def build_daily_text(
    db: AsyncSession,
    sign: str,
    transits: list[dict[str, Any]],
    natal_blocks: list[InterpretationBlock] | None = None,
) -> str:
    """
    Assemble the final horoscope text.

    Logic:
    - Start with the strongest natal placement (or generic sign text)
    - Weave in the top 2–3 active transits
    - End with a forward-looking sentence
    """
    # ── Generic fallback texts per sign ────────────────────────────────────────
    SIGN_BASE: dict[str, str] = {
        "aries":       "Марс придаёт вам мощный заряд энергии и инициативы.",
        "taurus":      "Венера создаёт стабильный фон для финансов и отношений.",
        "gemini":      "Меркурий обостряет интеллект и коммуникабельность.",
        "cancer":      "Луна усиливает интуицию и эмоциональную глубину.",
        "leo":         "Солнце освещает ваш путь к самовыражению и успеху.",
        "virgo":       "Меркурий помогает увидеть важные детали, которые упускают другие.",
        "libra":       "Венера гармонизирует отношения и создаёт атмосферу красоты.",
        "scorpio":     "Плутон открывает скрытые пласты реальности — доверяйте интуиции.",
        "sagittarius": "Юпитер расширяет горизонты и привлекает удачу к смелым.",
        "capricorn":   "Сатурн вознаграждает дисциплину и последовательность.",
        "aquarius":    "Уран приносит неожиданные озарения и нестандартные решения.",
        "pisces":      "Нептун усиливает творческое воображение и духовную чуткость.",
    }

    # ── Transit phrases ─────────────────────────────────────────────────────────
    TRANSIT_PHRASES: dict[str, dict[str, str]] = {
        "conjunction": {
            "jupiter": "Юпитер в соединении открывает двери удачи — не упустите момент.",
            "venus":   "Венера в соединении сулит тёплые встречи и приятные сюрпризы.",
            "saturn":  "Сатурн в соединении призывает к серьёзному взгляду на обязательства.",
            "mars":    "Марс в соединении заряжает решимостью — самое время действовать.",
            "moon":    "Луна в соединении обостряет чувства — прислушайтесь к себе.",
            "sun":     "Солнце в соединении освещает путь к вашим истинным целям.",
        },
        "trine": {
            "jupiter": "Трин Юпитера приносит лёгкость и благоприятные стечения обстоятельств.",
            "venus":   "Трин Венеры создаёт гармоничный фон для личных отношений.",
            "saturn":  "Трин Сатурна помогает выстроить прочную основу для долгосрочных планов.",
            "mars":    "Трин Марса даёт ровную и мощную энергию на весь день.",
            "moon":    "Трин Луны — ваши эмоции и разум сегодня работают в унисон.",
            "sun":     "Трин Солнца — прекрасный день для творческих и личных инициатив.",
        },
        "square": {
            "saturn":  "Квадрат Сатурна создаёт трение, которое в итоге ведёт к росту.",
            "mars":    "Квадрат Марса требует сознательно управлять импульсами и раздражением.",
            "jupiter": "Квадрат Юпитера предупреждает: не переоценивайте силы.",
            "moon":    "Квадрат Луны — сегодня важно не принимать решений на эмоциях.",
        },
        "opposition": {
            "saturn":  "Оппозиция Сатурна указывает на необходимость найти баланс между долгом и желаниями.",
            "mars":    "Оппозиция Марса — сохраняйте дипломатичность в потенциальных конфликтах.",
            "venus":   "Оппозиция Венеры может обострить отношения — будьте мягче.",
        },
    }

    # Build base sentence
    base = SIGN_BASE.get(sign.lower(), "Звёзды благоволят вашим начинаниям.")

    # Add natal block if available
    natal_sentence = ""
    if natal_blocks:
        top = natal_blocks[0]
        # Use first 100 chars of the block as a teaser
        snippet = top.text[:120].rstrip()
        if len(top.text) > 120:
            snippet += "..."
        natal_sentence = f" {snippet}"

    # Weave in top transits
    transit_sentences: list[str] = []
    seen_planets: set[str] = set()
    for t in transits[:3]:
        tp = t["transit_planet"].lower()
        aspect = t["aspect"].lower()
        if tp in seen_planets:
            continue
        seen_planets.add(tp)
        phrase = TRANSIT_PHRASES.get(aspect, {}).get(tp, "")
        if phrase:
            transit_sentences.append(phrase)

    # Forward-looking closer
    CLOSERS = [
        "Вечер подходит для размышлений и планирования.",
        "Не упустите возможности, которые появятся во второй половине дня.",
        "Доверяйте внутреннему голосу — он сегодня особенно точен.",
        "Небольшой отдых зарядит вас энергией для новых свершений.",
    ]
    import hashlib
    from datetime import date
    day_hash = int(hashlib.md5(f"{sign}{date.today()}".encode()).hexdigest(), 16)
    closer = CLOSERS[day_hash % len(CLOSERS)]

    # Assemble
    parts = [base + natal_sentence]
    parts.extend(transit_sentences)
    parts.append(closer)

    return " ".join(parts)
