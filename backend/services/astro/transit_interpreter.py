"""LLM-backed text interpretations for current transits.

Mirrors services/astro/synastry_interpreter but with a transit-framed
prompt ("right now planet X is making this aspect to your natal Y").
Cache lives in transit_interpretations (planet order matters here).
"""

import json
from typing import Any

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from db.models import TransitInterpretation
from services.llm_utils import first_text_block

log = get_logger(__name__)

_PLANET_RU: dict[str, str] = {
    "sun": "Солнце", "moon": "Луна", "mercury": "Меркурий",
    "venus": "Венера", "mars": "Марс", "jupiter": "Юпитер",
    "saturn": "Сатурн", "uranus": "Уран", "neptune": "Нептун",
    "pluto": "Плутон", "chiron": "Хирон",
    "ascendant": "Асцендент",
    "descendant": "Десцендент",
    "medium_coeli": "Середина неба",
    "imum_coeli": "Глубина неба",
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
    "mean_lilith": "Лилит",
    "true_lilith": "Лилит",
    "black_moon_lilith": "Лилит",
}

_ASPECT_RU: dict[str, str] = {
    "conjunction": "соединение", "trine": "трин",
    "square": "квадрат", "opposition": "оппозиция", "sextile": "секстиль",
}

# Last-resort copy when we have no LLM key and no cache row. Generic but
# casual — better than nothing while we wait for LLM to fill the gap.
_FALLBACK: dict[str, str] = {
    "conjunction": "Две темы сливаются в одну сильную волну — то, что раньше"
    " казалось разным, сегодня работает вместе.",
    "trine": "Сегодня всё складывается само — стоит сделать шаг, и поддержка"
    " найдётся.",
    "sextile": "Окно возможностей открыто, но само не зайдёт — нужен ваш ход.",
    "square": "Что-то трётся и мешает. Это не катастрофа — это место, где"
    " вы реально вырастете.",
    "opposition": "Внутри тянет в две стороны сразу. Не выбирайте крайность —"
    " попробуйте найти баланс.",
}


async def _llm_batch(
    missing: list[tuple[str, str, str]],
    api_key: str,
) -> dict[tuple[str, str, str], str]:
    """One LLM call producing N interpretations (transit-framed)."""
    if not missing:
        return {}

    import anthropic

    items = []
    for i, (tp, np, aspect) in enumerate(missing):
        items.append(
            f"{i + 1}. Транзитный {_PLANET_RU.get(tp, tp)} — "
            f"{_ASPECT_RU.get(aspect, aspect)} — натальный {_PLANET_RU.get(np, np)}"
        )

    prompt = f"""Ты пишешь короткие посты для популярного приложения с астрологией. Аудитория — обычные люди, не астрологи. Многие из них в первый раз сталкиваются с темой транзитов.

Транзиты:
{chr(10).join(items)}

Для каждого транзита напиши пост в 3-4 предложения (60-100 слов).

КАК ПИСАТЬ:
- Живой разговорный язык, как будто рассказываешь другу за кофе.
- Конкретные образы из обычной жизни: работа, отношения, деньги, разговоры, домашние дела.
- Один-два прямых совета: что попробовать сегодня, на что обратить внимание, чего лучше избежать.
- Обращайся на «вы», но без официоза.

ЧЕГО НЕ ДЕЛАТЬ:
- Никакого астрологического жаргона: ни «энергии», ни «вселенная подарит», ни «планеты учат», ни «эманации», ни «архетипы».
- Никаких заголовков, звёздочек, markdown, эмодзи.
- Не начинай с «Транзит...» или «Сегодня...». Начинай сразу с сути.
- Не повторяй название планет и аспекта в начале — пользователь и так его видит сверху.

ЧТО УЧИТЫВАТЬ:
- О чём «работает» транзитная планета: Венера — отношения, удовольствие, деньги, эстетика; Марс — действия, спор, спорт, желания; Меркурий — мысли, разговоры, переписки, мелкие дела; Луна — настроение и быт; Солнце — самоощущение, признание; Юпитер — рост, возможности, оптимизм; Сатурн — ответственность, границы, дисциплина; Уран — внезапное и свободное; Нептун — мечты, иллюзии, творчество; Плутон — глубокие изменения; Хирон — старые раны и их исцеление.
- Оси и точки карты: Асцендент — то, как вы выглядите для других и первое впечатление; Десцендент — близкие отношения и партнёры; Середина неба — карьера, публичный образ; Глубина неба — дом, семья, корни; Северный узел — направление роста; Южный узел — то, что пора отпустить; Лилит — теневая, неудобная сторона себя.
- Какая натальная тема активируется (та же логика для натальной планеты).
- Характер аспекта: трин/секстиль — поток и поддержка; квадрат/оппозиция — напряжение, выбор, трение; соединение — две темы сливаются в одну.

Верни ТОЛЬКО JSON-массив строк в порядке списка, без обёртки. Пример: ["текст1", "текст2", ...]"""

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = first_text_block(message.content).strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw
            if raw.endswith("```"):
                raw = raw.rsplit("```", 1)[0]
            raw = raw.strip()
        texts = json.loads(raw)
        if not isinstance(texts, list) or len(texts) != len(missing):
            log.warning(
                "transit_interp.llm_shape_mismatch",
                expected=len(missing),
                got=len(texts) if isinstance(texts, list) else "non-list",
            )
            return {}
        return {triple: str(text).strip() for triple, text in zip(missing, texts) if text}
    except Exception as e:  # noqa: BLE001
        log.error("transit_interp.llm_failed", error=str(e), count=len(missing))
        return {}


async def get_or_generate_transit_texts(
    db: AsyncSession,
    aspects: list[dict[str, Any]],
    api_key: str | None,
) -> dict[tuple[str, str, str], str]:
    """For each transit in `aspects`, return text indexed by
    (transit_planet, natal_planet, aspect). Cache → LLM → static fallback."""
    if not aspects:
        return {}

    triples: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for a in aspects:
        tp = (a.get("transit_planet") or "").lower()
        np = (a.get("natal_planet") or "").lower()
        ap = (a.get("aspect") or "").lower()
        if not tp or not np or not ap:
            continue
        triple = (tp, np, ap)
        if triple in seen:
            continue
        seen.add(triple)
        triples.append(triple)

    if not triples:
        return {}

    cached: dict[tuple[str, str, str], str] = {}
    result = await db.execute(
        select(
            TransitInterpretation.transit_planet,
            TransitInterpretation.natal_planet,
            TransitInterpretation.aspect,
            TransitInterpretation.text_ru,
        ).where(
            tuple_(
                TransitInterpretation.transit_planet,
                TransitInterpretation.natal_planet,
                TransitInterpretation.aspect,
            ).in_(triples)
        )
    )
    for row in result:
        cached[(row.transit_planet, row.natal_planet, row.aspect)] = row.text_ru

    missing = [t for t in triples if t not in cached]

    if missing and api_key:
        generated = await _llm_batch(missing, api_key)
        for triple, text in generated.items():
            db.add(
                TransitInterpretation(
                    transit_planet=triple[0],
                    natal_planet=triple[1],
                    aspect=triple[2],
                    text_ru=text,
                )
            )
            cached[triple] = text
        if generated:
            try:
                await db.flush()
            except Exception as e:  # noqa: BLE001
                log.warning("transit_interp.cache_collision", error=str(e))

    for triple in triples:
        cached.setdefault(triple, _FALLBACK.get(triple[2], ""))

    return cached
