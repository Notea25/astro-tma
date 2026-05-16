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
    category: str    # "personality" | "emotion" | "communication" | "love" | "career" | "house" | "aspect"
    text: str
    weight: int      # higher = more important, shown first


# Per-planet config for natal slide generation.
# weight  — sort priority (higher = first slide)
# category — UI label group on the frontend (CATEGORY_RU)
_PLANET_NATAL_CONFIG: dict[str, tuple[str, int]] = {
    "sun":       ("personality",   10),
    "moon":      ("emotion",        9),
    "ascendant": ("personality",    8),
    "mercury":   ("communication",  7),
    "venus":     ("love",           7),
    "mars":      ("career",         6),
    "jupiter":   ("growth",         5),
    "saturn":    ("discipline",     5),
}


async def get_natal_interpretation(
    db: AsyncSession,
    sun_sign: str,
    moon_sign: str,
    asc_sign: str | None,
    planet_signs: dict[str, str],            # {"mercury": "scorpio", ...}
    planet_houses: dict[str, int] | None = None,   # {"sun": 5, ...}
    aspects: list[dict[str, Any]] | None = None,   # [{p1, p2, aspect, orb}, ...]
) -> list[InterpretationBlock]:
    """
    Fetch natal interpretations for the user's chart.

    Three layers of content, all returned as InterpretationBlock objects:
      1. planet × sign  — "Sun in Aries means..." (8 placements when full)
      2. planet × house — "Sun in 10th house means..." (up to 8)
      3. aspect rows    — "Sun trine Moon means..." (top 4 by orb)

    Returns blocks sorted by weight (most significant first).
    """
    blocks: list[InterpretationBlock] = []

    # ── Layer 1: planet × sign ────────────────────────────────────────────
    sign_queries: list[tuple[str, str, str, int]] = [
        ("sun",  sun_sign,  "personality", 10),
        ("moon", moon_sign, "emotion",      9),
    ]
    if asc_sign:
        sign_queries.append(("ascendant", asc_sign, "personality", 8))

    for planet, sign in (planet_signs or {}).items():
        if planet not in _PLANET_NATAL_CONFIG or planet in ("sun", "moon", "ascendant"):
            continue
        category, weight = _PLANET_NATAL_CONFIG[planet]
        sign_queries.append((planet, sign, category, weight))

    for planet, sign, category, weight in sign_queries:
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
            log.debug("interpreter.no_sign_text", planet=planet, sign=sign)

    # ── Layer 2: planet × house ───────────────────────────────────────────
    # House placements add colour ("Sun in 10th house" — public success).
    # Slightly lower weight than the same planet's sign block.
    for planet, house in (planet_houses or {}).items():
        if planet not in _PLANET_NATAL_CONFIG or not house:
            continue
        result = await db.execute(
            select(Interpretation).where(
                and_(
                    Interpretation.planet == planet,
                    Interpretation.house == int(house),
                    Interpretation.sign.is_(None),
                    Interpretation.aspect.is_(None),
                )
            ).limit(1)
        )
        interp = result.scalar_one_or_none()
        if interp:
            _, base_weight = _PLANET_NATAL_CONFIG[planet]
            blocks.append(InterpretationBlock(
                planet=planet,
                category="house",
                text=interp.text_ru,
                weight=base_weight - 2,
            ))

    # ── Layer 3: aspects (top 4 by tightest orb) ──────────────────────────
    # Aspects are bidirectional — DB may store the pair in either order.
    if aspects:
        ranked = sorted(
            (a for a in aspects if a.get("p1") and a.get("p2") and a.get("aspect")),
            key=lambda a: a.get("orb", 99),
        )[:4]
        for a in ranked:
            p1 = str(a["p1"]).lower()
            p2 = str(a["p2"]).lower()
            atype = str(a["aspect"]).lower()
            result = await db.execute(
                select(Interpretation).where(
                    and_(
                        Interpretation.aspect == atype,
                        Interpretation.sign.is_(None),
                        Interpretation.house.is_(None),
                        Interpretation.planet.in_([p1, p2, f"{p1}_{p2}", f"{p2}_{p1}"]),
                    )
                ).limit(1)
            )
            interp = result.scalar_one_or_none()
            if interp:
                blocks.append(InterpretationBlock(
                    planet=f"{p1}_{p2}",
                    category="aspect",
                    text=interp.text_ru,
                    weight=4,
                ))

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
