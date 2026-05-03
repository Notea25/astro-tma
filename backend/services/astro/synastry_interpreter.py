"""LLM-backed text interpretations for synastry aspects.

Two functions:
- get_or_generate_aspect_texts: per-aspect text for a list of aspects, cached
  in the synastry_interpretations table (key = sorted (p1, p2, aspect)).
- generate_pair_summary: short narrative summary for a specific pair —
  caller is responsible for caching by pair (we store it in
  SynastryRequest.result_json).

Both functions return Russian text. They never raise on LLM failure — the
caller gets either real text or a generic fallback.
"""

import json
from typing import Any

from sqlalchemy import and_, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from db.models import SynastryInterpretation
from services.llm_utils import first_text_block

log = get_logger(__name__)

_PLANET_RU: dict[str, str] = {
    "sun": "Солнце", "moon": "Луна", "mercury": "Меркурий",
    "venus": "Венера", "mars": "Марс", "jupiter": "Юпитер",
    "saturn": "Сатурн", "uranus": "Уран", "neptune": "Нептун",
    "pluto": "Плутон", "chiron": "Хирон", "true_node": "Северный узел",
    "mean_node": "Северный узел", "lilith": "Лилит",
}

_ASPECT_RU: dict[str, str] = {
    "conjunction": "соединение", "trine": "трин",
    "square": "квадрат", "opposition": "оппозиция", "sextile": "секстиль",
}

_ASPECT_FALLBACK: dict[str, str] = {
    "conjunction": "Соединение усиливает обе планеты, действуя как единое целое.",
    "trine": "Трин даёт лёгкое и гармоничное взаимодействие энергий.",
    "sextile": "Секстиль создаёт возможности при небольшом усилии с обеих сторон.",
    "square": "Квадрат вносит напряжение, требующее осознанной работы.",
    "opposition": "Оппозиция показывает противоположности, которые нужно балансировать.",
}


def _normalize_key(p1: str, p2: str) -> tuple[str, str]:
    """Return (lower_p1, lower_p2) sorted alphabetically."""
    a, b = p1.lower(), p2.lower()
    return (a, b) if a <= b else (b, a)


async def _llm_batch(missing: list[tuple[str, str, str]], api_key: str) -> dict[tuple[str, str, str], str]:
    """Generate text for every (p1, p2, aspect) triple in one LLM call.
    Returns {triple: text_ru}. On any error returns {} — caller falls back."""
    if not missing:
        return {}

    import anthropic

    items = []
    for i, (p1, p2, aspect) in enumerate(missing):
        items.append(
            f"{i + 1}. {_PLANET_RU.get(p1, p1)} — {_ASPECT_RU.get(aspect, aspect)} — "
            f"{_PLANET_RU.get(p2, p2)}"
        )

    prompt = f"""Ты — практикующий астролог. Для каждого аспекта между планетами двух людей в их синастрии напиши короткую (80-130 слов) интерпретацию на русском языке.

Аспекты:
{chr(10).join(items)}

Стиль: тёплый, конкретный, психологический. Не астрологический жаргон. Описывай динамику между двумя людьми («один из вас», «другой», «вы вместе»). Не используй имена.

Верни ТОЛЬКО JSON-массив строк в порядке списка, без дополнительного текста, без markdown-обёртки. Пример: ["текст1", "текст2", ...]"""

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = first_text_block(message.content).strip()
        # Strip code fences if model adds them
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw
            if raw.endswith("```"):
                raw = raw.rsplit("```", 1)[0]
            raw = raw.strip()
        texts = json.loads(raw)
        if not isinstance(texts, list) or len(texts) != len(missing):
            log.warning("synastry_interp.llm_shape_mismatch", expected=len(missing), got=len(texts) if isinstance(texts, list) else "non-list")
            return {}
        return {triple: str(text).strip() for triple, text in zip(missing, texts) if text}
    except Exception as e:  # noqa: BLE001 — we want broad catch; caller handles empty dict
        log.error("synastry_interp.llm_failed", error=str(e), count=len(missing))
        return {}


async def get_or_generate_aspect_texts(
    db: AsyncSession,
    aspects: list[dict[str, Any]],
    api_key: str | None,
) -> dict[tuple[str, str, str], str]:
    """For each aspect in `aspects`, return a triple-keyed dict of Russian text.
    Uses synastry_interpretations as a cache, falls back to LLM, then to a
    generic phrase if LLM is unavailable or fails. Aspects without a known
    aspect type are skipped silently."""
    if not aspects:
        return {}

    # Normalize and dedupe
    triples: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for a in aspects:
        p1, p2 = _normalize_key(a["p1_name"], a["p2_name"])
        triple = (p1, p2, a["aspect"])
        if triple not in seen:
            seen.add(triple)
            triples.append(triple)

    # DB lookup
    result = await db.execute(
        select(
            SynastryInterpretation.p1,
            SynastryInterpretation.p2,
            SynastryInterpretation.aspect,
            SynastryInterpretation.text_ru,
        ).where(
            tuple_(
                SynastryInterpretation.p1,
                SynastryInterpretation.p2,
                SynastryInterpretation.aspect,
            ).in_(triples)
        )
    )
    cached: dict[tuple[str, str, str], str] = {
        (row.p1, row.p2, row.aspect): row.text_ru for row in result
    }

    missing = [t for t in triples if t not in cached]

    # LLM fill (batched)
    if missing and api_key:
        generated = await _llm_batch(missing, api_key)
        for triple, text in generated.items():
            db.add(
                SynastryInterpretation(
                    p1=triple[0],
                    p2=triple[1],
                    aspect=triple[2],
                    text_ru=text,
                )
            )
            cached[triple] = text
        if generated:
            await db.flush()

    # Static fallback for whatever is still missing
    for triple in triples:
        if triple not in cached:
            cached[triple] = _ASPECT_FALLBACK.get(triple[2], "")

    return cached


async def generate_pair_summary(
    initiator_name: str | None,
    partner_name: str | None,
    aspects: list[dict[str, Any]],
    scores: dict[str, int],
    api_key: str | None,
) -> str | None:
    """One LLM call producing a short Russian portrait of the relationship.
    Returns None on failure or missing API key — caller can hide the block."""
    if not api_key or not aspects:
        return None

    import anthropic

    aspect_lines = []
    for a in aspects[:10]:
        p1 = _PLANET_RU.get(a["p1_name"].lower(), a["p1_name"])
        p2 = _PLANET_RU.get(a["p2_name"].lower(), a["p2_name"])
        asp = _ASPECT_RU.get(a["aspect"], a["aspect"])
        aspect_lines.append(f"- {p1} {asp} {p2} (орб {a['orb']:.1f}°)")

    score_line = (
        f"Любовь {scores.get('love', 0)}, общение {scores.get('communication', 0)}, "
        f"доверие {scores.get('trust', 0)}, страсть {scores.get('passion', 0)}, "
        f"общая совместимость {scores.get('overall', 0)}."
    )

    name_a = initiator_name or "первый партнёр"
    name_b = partner_name or "второй партнёр"

    prompt = f"""Ты — практикующий астролог. Напиши короткий портрет отношений ({name_a} и {name_b}) на русском языке (180-260 слов).

Ключевые аспекты синастрии:
{chr(10).join(aspect_lines)}

Баллы по сферам (от 15 до 95):
{score_line}

Структура:
1. Главная тема союза — 1-2 предложения
2. Сильные стороны и где паре легко — 2-3 предложения
3. Зоны напряжения и над чем поработать — 2-3 предложения
4. Вектор развития — 1-2 предложения

Стиль: тёплый, конкретный. Используй имена партнёров. Избегай клише, не используй слово «синастрия». Без markdown."""

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}],
        )
        text = first_text_block(message.content).strip()
        log.info("synastry_summary.done", chars=len(text))
        return text
    except Exception as e:  # noqa: BLE001
        log.error("synastry_summary.failed", error=str(e))
        return None
