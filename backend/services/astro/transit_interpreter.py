"""LLM-backed text interpretations for current transits.

Mirrors services/astro/synastry_interpreter but with a transit-framed
prompt ("right now planet X is making this aspect to your natal Y").
Cache lives in transit_interpretations (planet order matters here).
"""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from core.settings import settings
from db.database import AsyncSessionLocal
from db.models import TransitInterpretation
from services.content_version import CONTENT_VERSION
from services.llm_utils import first_text_block

log = get_logger(__name__)

from services.astro.planet_names import PLANET_RU as _PLANET_RU  # noqa: E402

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

    from services.llm_client import create_llm_client

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
- О чём «работает» транзитная планета: Венера — отношения, удовольствие, деньги, эстетика; Марс — действия, спор, спорт, желания; Меркурий — мысли, разговоры, переписки, мелкие дела; Луна — настроение и быт; Солнце — самоощущение, признание; Юпитер — рост, возможности, оптимизм; Сатурн — ответственность, границы, дисциплина; Уран — внезапное и свободное; Нептун — мечты, иллюзии, творчество; Плутон — глубокие изменения.
- Какая натальная тема активируется (та же логика для натальной планеты).
- Характер аспекта: трин/секстиль — поток и поддержка; квадрат/оппозиция — напряжение, выбор, трение; соединение — две темы сливаются в одну.

Верни ТОЛЬКО JSON-массив строк в порядке списка, без обёртки. Пример: ["текст1", "текст2", ...]"""

    from services.astro.fact_context import (
        AstroFactContext,
        safe_symbolic_fallback,
        validate_generated_text,
    )
    from services.llm_pool import llm_semaphore

    client = create_llm_client(api_key)

    async def _call(request_prompt: str) -> list[str] | None:
        async with llm_semaphore:
            message = await client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=4000,
                messages=[{"role": "user", "content": request_prompt}],
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
            return None
        return [str(text).strip() for text in texts]

    def _errors(texts: list[str]) -> list[str]:
        errors: list[str] = []
        for index, (triple, text) in enumerate(zip(missing, texts), start=1):
            context = AstroFactContext.from_chart(
                planets={},
                aspects=[{"p1": triple[0], "p2": triple[1], "aspect": triple[2]}],
                birth_time_known=False,
            )
            errors.extend(f"item {index}: {error}" for error in validate_generated_text(text, context))
        return errors

    try:
        texts = await _call(prompt)
        if texts is None:
            return {}
        errors = _errors(texts)
        if errors:
            texts = await _call(
                prompt + "\n\nИсправь отклонённый ответ:\n- " + "\n- ".join(errors)
            )
        if texts is None or _errors(texts):
            return {
                triple: safe_symbolic_fallback("Тема транзита")
                for triple in missing
            }
        return {triple: text for triple, text in zip(missing, texts) if text}
    except Exception as e:  # noqa: BLE001
        log.error("transit_interp.llm_failed", error=str(e), count=len(missing))
        return {}


def _extract_triples(
    aspects: list[dict[str, Any]],
) -> list[tuple[str, str, str]]:
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
    return triples


async def _lookup_cached(
    db: AsyncSession,
    triples: list[tuple[str, str, str]],
) -> dict[tuple[str, str, str], str]:
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
            TransitInterpretation.content_version == CONTENT_VERSION,
            tuple_(
                TransitInterpretation.transit_planet,
                TransitInterpretation.natal_planet,
                TransitInterpretation.aspect,
            ).in_(triples)
        )
    )
    for row in result:
        cached[(row.transit_planet, row.natal_planet, row.aspect)] = row.text_ru
    return cached


async def _background_generate(
    missing: list[tuple[str, str, str]],
    api_key: str,
    on_complete: Callable[[], Awaitable[None]] | None,
) -> None:
    """Fire-and-forget: generate LLM texts in a fresh DB session, then
    optionally invoke `on_complete` so the route layer can invalidate the
    Redis cache key it just populated with fallback text."""
    try:
        generated = await _llm_batch(missing, api_key)
        if generated:
            async with AsyncSessionLocal() as bg_db:
                for triple, text in generated.items():
                    bg_db.add(
                        TransitInterpretation(
                            transit_planet=triple[0],
                            natal_planet=triple[1],
                            aspect=triple[2],
                            text_ru=text,
                            content_version=CONTENT_VERSION,
                        )
                    )
                try:
                    await bg_db.commit()
                except Exception as e:  # noqa: BLE001
                    log.warning("transit_bg.cache_collision", error=str(e))
        if on_complete:
            try:
                await on_complete()
            except Exception as e:  # noqa: BLE001
                log.warning("transit_bg.on_complete_failed", error=str(e))
    except Exception as e:  # noqa: BLE001
        log.error("transit_bg.failed", error=str(e), count=len(missing))


async def get_or_generate_transit_texts(
    db: AsyncSession,
    aspects: list[dict[str, Any]],
    api_key: str | None,
    *,
    blocking: bool = True,
    on_background_complete: Callable[[], Awaitable[None]] | None = None,
) -> tuple[dict[tuple[str, str, str], str], int]:
    """For each transit, return (texts_by_triple, missing_count).

    With `blocking=True` (default), waits for the LLM call to populate any
    missing entries before returning — used internally for non-user-facing
    flows. With `blocking=False`, returns immediately with cache + fallback
    and schedules an asyncio background task to fill the gap. The optional
    `on_background_complete` lets the caller invalidate its Redis cache so
    the next request gets the freshly generated text.
    """
    if not aspects:
        return {}, 0

    triples = _extract_triples(aspects)
    if not triples:
        return {}, 0

    cached = await _lookup_cached(db, triples)
    missing = [t for t in triples if t not in cached]

    if missing and api_key:
        if blocking:
            generated = await _llm_batch(missing, api_key)
            for triple, text in generated.items():
                db.add(
                    TransitInterpretation(
                        transit_planet=triple[0],
                        natal_planet=triple[1],
                        aspect=triple[2],
                        text_ru=text,
                        content_version=CONTENT_VERSION,
                    )
                )
                cached[triple] = text
            if generated:
                try:
                    await db.flush()
                except Exception as e:  # noqa: BLE001
                    log.warning("transit_interp.cache_collision", error=str(e))
            missing = [t for t in triples if t not in cached]
        else:
            # Hand the LLM call to a background task. Use a copy so we
            # don't capture a mutable reference.
            asyncio.create_task(
                _background_generate(list(missing), api_key, on_background_complete)
            )

    for triple in triples:
        cached.setdefault(triple, _FALLBACK.get(triple[2], ""))

    return cached, len(missing)


# ── Deep-dive ("What does this mean for me") ─────────────────────────────────

# House → life-sphere topic. Mass-market friendly framing.
_HOUSE_TOPIC: dict[int, str] = {
    1: "Самоощущение и образ",
    2: "Деньги и ресурсы",
    3: "Общение и ближний круг",
    4: "Дом и семья",
    5: "Творчество и удовольствия",
    6: "Работа и здоровье",
    7: "Близкие отношения",
    8: "Глубокие изменения и общие ресурсы",
    9: "Рост, учёба, дальние горизонты",
    10: "Карьера и публичный образ",
    11: "Друзья и большие цели",
    12: "Внутренний мир и уединение",
}


# Hard aspects warrant a `risk_warning`. The model also adds it on
# conjunctions with the heavy/disruptive outer planets, since those can
# feel just as challenging as a square.
_HARD_PLANETS_ON_CONJUNCTION = {"mars", "saturn", "pluto", "uranus", "neptune"}


def _is_hard_aspect(aspect: str, tp: str, np: str) -> bool:
    a = aspect.lower()
    if a in ("square", "opposition"):
        return True
    if a == "conjunction" and (
        tp.lower() in _HARD_PLANETS_ON_CONJUNCTION
        or np.lower() in _HARD_PLANETS_ON_CONJUNCTION
    ):
        return True
    return False


async def _llm_advice(
    tp: str,
    np: str,
    aspect: str,
    text_blurb: str,
    api_key: str,
) -> dict[str, str | None]:
    """Generate the full deep-dive bundle for one transit triple:
    advice_do, advice_avoid, affirmation, ritual — and risk_warning
    only for hard aspects. One Sonnet/Haiku call → structured JSON.

    Returns a dict with the same keys as the DB columns; any None means
    «model didn't return it», so the UI block stays hidden.
    """
    from services.llm_client import create_llm_client

    tp_ru = _PLANET_RU.get(tp, tp)
    np_ru = _PLANET_RU.get(np, np)
    aspect_ru = _ASPECT_RU.get(aspect, aspect)
    needs_risk = _is_hard_aspect(aspect, tp, np)

    risk_clause = (
        "\n\n5) RISK_WARNING — 1 предложение, конкретный бытовой сценарий, "
        "где эта энергия может выйти из-под контроля сегодня (например: "
        "«Если попытаешься продавить решение силой — партнёр закроется на "
        "несколько дней»). Без катастрофизма, но конкретно."
        if needs_risk else ""
    )
    risk_json = ', "risk_warning": "Сценарий риска"' if needs_risk else ""

    prompt = f"""Транзит: {tp_ru} ({aspect_ru}) к натальной точке {np_ru}.
Уже написанный короткий разбор этого транзита:
"{text_blurb}"

Теперь напиши практическое руководство на сегодня. Пять блоков:

1) ЧТО СДЕЛАТЬ — 2-3 коротких конкретных совета. Каждый совет — одна фраза, начинается с глагола. Без эзотерики, без «вселенная», «энергии», «работа со страхами». Только конкретные действия из обычной жизни.

2) ЧЕГО ИЗБЕГАТЬ — 2-3 коротких предупреждения. Тоже конкретно, тоже одной фразой каждое.

3) AFFIRMATION — 1 фраза от первого лица («Я …»), которую читатель проговаривает вслух утром. 6-12 слов. Просто и тепло, без пафоса.

4) RITUAL — 1 микро-действие на сегодня, занимающее 1-5 минут (например: «Запиши 3 благодарности перед сном» или «Сделай паузу перед каждым ответом — 3 вдоха»). Конкретно.{risk_clause}

Тон: разговорный, как друг советует. Обращайся на «ты». Без markdown, без нумерации внутри блоков — разделяй советы в do/avoid переносом строки.

Верни ТОЛЬКО JSON следующего вида:
{{"do": "Совет 1\\nСовет 2", "avoid": "Предупреждение 1\\nПредупреждение 2", "affirmation": "Я …", "ritual": "Действие на 1-5 минут"{risk_json}}}"""

    from services.astro.fact_context import AstroFactContext, validate_generated_text
    from services.llm_pool import llm_semaphore

    client = create_llm_client(api_key)

    async def _call(request_prompt: str) -> dict[str, Any]:
        async with llm_semaphore:
            message = await client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=900,
                messages=[{"role": "user", "content": request_prompt}],
            )
        raw = first_text_block(message.content).strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw
            if raw.endswith("```"):
                raw = raw.rsplit("```", 1)[0]
            raw = raw.strip()
        parsed = json.loads(raw)
        return {
            "advice_do":    (str(parsed.get("do", "")).strip() or None),
            "advice_avoid": (str(parsed.get("avoid", "")).strip() or None),
            "affirmation":  (str(parsed.get("affirmation", "")).strip() or None),
            "ritual":       (str(parsed.get("ritual", "")).strip() or None),
            "risk_warning": (
                str(parsed.get("risk_warning", "")).strip() or None
            ) if needs_risk else None,
        }

    try:
        data = await _call(prompt)
        joined = " ".join(str(value or "") for value in data.values())
        fact_context = AstroFactContext.from_chart(
            planets={},
            aspects=[{"p1": tp, "p2": np, "aspect": aspect}],
            birth_time_known=False,
        )
        errors = validate_generated_text(joined, fact_context)
        if errors:
            data = await _call(
                prompt + "\n\nИсправь отклонённый ответ:\n- " + "\n- ".join(errors)
            )
            joined = " ".join(str(value or "") for value in data.values())
            if validate_generated_text(joined, fact_context):
                raise ValueError("transit advice failed fact validation twice")
        return data
    except Exception as e:  # noqa: BLE001
        log.error("transit_advice.llm_failed", tp=tp, np=np, aspect=aspect, error=str(e))
        return {
            "advice_do": None, "advice_avoid": None,
            "affirmation": None, "ritual": None, "risk_warning": None,
        }


async def get_transit_details(
    db: AsyncSession,
    transit_planet: str,
    natal_planet: str,
    aspect: str,
    natal_chart: dict[str, Any] | None,
    api_key: str | None,
) -> dict[str, Any]:
    """Look up (or generate) the deep-dive payload for a single transit.

    Returns dict with `text_ru`, `advice_do`, `advice_avoid`,
    `affected_house` (int | None) and `affected_house_topic` (str | None).
    """
    tp = transit_planet.lower()
    np = natal_planet.lower()
    ap = aspect.lower()

    result = await db.execute(
        select(TransitInterpretation).where(
            TransitInterpretation.transit_planet == tp,
            TransitInterpretation.natal_planet == np,
            TransitInterpretation.aspect == ap,
            TransitInterpretation.content_version == CONTENT_VERSION,
        )
    )
    row = result.scalar_one_or_none()
    text_ru = row.text_ru if row else _FALLBACK.get(ap, "")
    advice_do = row.advice_do if row else None
    advice_avoid = row.advice_avoid if row else None
    affirmation = row.affirmation if row else None
    ritual = row.ritual if row else None
    risk_warning = row.risk_warning if row else None

    # Trigger one LLM call if anything we want is missing. The model
    # is told whether to emit risk_warning based on aspect hardness.
    wants_risk = _is_hard_aspect(ap, tp, np)
    missing = (
        advice_do is None
        or advice_avoid is None
        or affirmation is None
        or ritual is None
        or (wants_risk and risk_warning is None)
    )
    if missing and api_key:
        extras = await _llm_advice(tp, np, ap, text_ru or "", api_key)
        advice_do = advice_do or extras["advice_do"]
        advice_avoid = advice_avoid or extras["advice_avoid"]
        affirmation = affirmation or extras["affirmation"]
        ritual = ritual or extras["ritual"]
        risk_warning = risk_warning or extras["risk_warning"]
        if any([
            extras["advice_do"], extras["advice_avoid"],
            extras["affirmation"], extras["ritual"], extras["risk_warning"],
        ]):
            if row:
                await db.execute(
                    update(TransitInterpretation)
                    .where(TransitInterpretation.id == row.id)
                    .values(
                        advice_do=advice_do, advice_avoid=advice_avoid,
                        affirmation=affirmation, ritual=ritual,
                        risk_warning=risk_warning,
                        content_version=CONTENT_VERSION,
                    )
                )
            else:
                db.add(
                    TransitInterpretation(
                        transit_planet=tp,
                        natal_planet=np,
                        aspect=ap,
                        text_ru=text_ru or _FALLBACK.get(ap, ""),
                        advice_do=advice_do,
                        advice_avoid=advice_avoid,
                        affirmation=affirmation,
                        ritual=ritual,
                        risk_warning=risk_warning,
                    )
                )
            try:
                await db.flush()
            except Exception as e:  # noqa: BLE001
                log.warning("transit_advice.cache_collision", error=str(e))

    affected_house: int | None = None
    affected_house_topic: str | None = None
    if natal_chart and isinstance(natal_chart, dict):
        planets = natal_chart.get("planets") or {}
        planet_data = planets.get(np) or planets.get(natal_planet)
        if isinstance(planet_data, dict):
            raw_house = planet_data.get("house")
            if isinstance(raw_house, (int, float)):
                affected_house = int(raw_house)
                affected_house_topic = _HOUSE_TOPIC.get(affected_house)

    return {
        "text_ru": text_ru,
        "advice_do": advice_do,
        "advice_avoid": advice_avoid,
        "affirmation": affirmation,
        "ritual": ritual,
        "risk_warning": risk_warning,
        "affected_house": affected_house,
        "affected_house_topic": affected_house_topic,
    }
