"""
LLM-generated personalised descriptions for natal planets, houses and aspects.

Produces both a short blurb (shown in the in-app popup) and a compact full
paragraph (rendered in the downloadable PDF).
Result is cached by the caller — this module only calls the API.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from core.logging import get_logger
from services.astro.sign_cases import sign_ru
from services.llm_utils import first_text_block
from services.quality_validator import (
    Severity,
    TextValidator,
    ValidationContext,
    sanitize_ru_text,
)

log = get_logger(__name__)

# Section name (planets/houses/aspects) → validator section_kind.
_SECTION_KIND = {
    "planets": "planet_in_sign",
    "houses": "house",
    "aspects": "aspect",
}

# Validator reused across entries; spellchecker off (astro terms ⇒ false positives).
_VALIDATOR = TextValidator(use_spellchecker=False)

_MODEL = "claude-haiku-4-5-20251001"

from services.astro.planet_names import PLANET_RU as _PLANET_RU  # noqa: E402

# Iteration order for the per-planet description loop — only the 10 classical
# points; chart axes / nodes / Lilith come through aspects but aren't seeded
# as standalone descriptions.
_PLANET_ORDER = [
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
]

_ASPECT_RU: dict[str, str] = {
    "conjunction": "соединение",
    "sextile": "секстиль",
    "square": "квадрат",
    "trine": "трин",
    "opposition": "оппозиция",
    "quincunx": "квинконс",
}


# Free-tier Anthropic keys cap output at ~10k tokens/min. Output tokens are the
# bottleneck (the bucket throttles them), so these targets are kept tight —
# halved from the earlier values to roughly halve generation time on any tier.
# Upper hints, not floors — the prompt tells the model "shorter is better".
# Согласовано с верхними ориентирами промптов (planets ~80-100, houses
# ~110-150, aspects ~130-170). thin-floor = target * _THIN_RATIO даёт
# 72 / 96 / 112 — ниже того, что промпт реально просит, поэтому штатный
# текст не уходит в repair, но Венера-60 / дома-65 / аспекты-80 ловятся.
_MIN_FULL_WORDS = {
    "planets": 90,
    "houses": 120,
    "aspects": 140,
}

_FORBIDDEN_COPY_MARKERS = (
    "подробнее",
    "читать далее",
    "источник",
    "geocult",
    "геокульт",
)

_REFERENCE_STYLE_BLUEPRINT = """КАК ПИСАТЬ — КОНКРЕТНО, БЕЗ ВОДЫ:
- Каждое предложение несёт факт или наблюдение о ЭТОМ человеке. Если предложение можно вставить в любой другой разбор — выкинь его.
- Запрещены пустые обороты и общие места: «это про баланс», «важно прислушиваться к себе», «энергия знака», «вселенная даёт», «потенциал для роста», «гармония и осознанность», «работа над собой». Вместо абстракции — конкретное проявление в поведении, словах, выборе, реакции.
- Структура каждого "full": (1) что эта конфигурация реально делает с характером/поведением — в 1-2 фразах, сразу по сути; (2) как это видно в жизни — конкретный пример (разговор, работа, деньги, отношения, привычка); (3) сильная сторона и где это мешает — называй прямо; (4) один практический ориентир, привязанный именно к этой паре.
- Ноль вступлений и подводок («давайте разберём», «стоит отметить»). Начинай сразу с сути.
- Не повторяй одно и то же разными словами. Один смысл — один раз.
- Запрещены маркеры копипаста: «Подробнее», «Читать далее», «Источник», «Geocult», рекламные переходы."""


def _normalise_sign(sign: str | None) -> str:
    return sign_ru(sign)


def _strip_code_fence(text: str) -> str:
    """Strip any leading/trailing ```/```json fence the model emits.
    Handles both balanced (both fences present) and unbalanced output."""
    text = text.strip()
    # Leading fence
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    # Trailing fence
    text = re.sub(r"\n?\s*```\s*$", "", text)
    return text.strip()


def _escape_unescaped_newlines_in_strings(raw: str) -> str:
    """Walk the JSON char-by-char and replace bare \\n inside string values
    with \\\\n. Handles the most common LLM mistake — emitting multi-line
    Russian text inside a JSON string without escaping the newlines."""
    out: list[str] = []
    in_string = False
    escape_next = False
    for ch in raw:
        if escape_next:
            out.append(ch)
            escape_next = False
            continue
        if ch == "\\":
            out.append(ch)
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            out.append(ch)
            continue
        if in_string and ch == "\n":
            out.append("\\n")
            continue
        if in_string and ch == "\r":
            out.append("\\r")
            continue
        if in_string and ch == "\t":
            out.append("\\t")
            continue
        out.append(ch)
    return "".join(out)


def _safe_load_json(raw: str) -> Any:
    cleaned = _strip_code_fence(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Try escaping bare newlines inside strings — the most common LLM failure.
    try:
        return json.loads(_escape_unescaped_newlines_in_strings(cleaned))
    except json.JSONDecodeError:
        pass
    # Fall back to extracting the first JSON object/array embedded in prose
    match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
    if not match:
        raise json.JSONDecodeError("no json-like content found", cleaned, 0)
    inner = match.group(1)
    try:
        return json.loads(inner)
    except json.JSONDecodeError:
        return json.loads(_escape_unescaped_newlines_in_strings(inner))


# ── Prompts ───────────────────────────────────────────────────────────────────


def _gender_directive(gender: str | None) -> str:
    """One-liner injected into every batch prompt. The «вы»-форма is mostly
    gender-neutral in Russian, so the directive only needs to anchor
    adjectives, past-tense verbs and participles — the few places that
    actually differ."""
    if gender == "male":
        return (
            "Пол читателя: МУЖЧИНА. Все прилагательные, причастия, "
            "глаголы прошедшего времени — в МУЖСКОМ роде (например, "
            "«вы сделали», «вы внимательный», «настоящий»).\n\n"
        )
    if gender == "female":
        return (
            "Пол читателя: ЖЕНЩИНА. Все прилагательные, причастия, "
            "глаголы прошедшего времени — в ЖЕНСКОМ роде (например, "
            "«вы сделали» с женскими формами далее, «вы внимательная», "
            "«настоящая»).\n\n"
        )
    return ""


def _planet_row(key: str, planet: dict[str, Any]) -> str:
    sign_nom = sign_ru(planet.get("sign_ru") or planet.get("sign"))
    sign_prep = sign_ru(planet.get("sign_ru") or planet.get("sign"), "prep")
    sign_gen = sign_ru(planet.get("sign_ru") or planet.get("sign"), "gen")
    house = planet.get("house", "?")
    degree = planet.get("sign_degree", planet.get("degree", "?"))
    retro = " (ретроградный)" if planet.get("retrograde") else ""
    return (
        f"- {key}: {_PLANET_RU.get(key, key)} в {sign_prep} / в знаке {sign_gen}; "
        f"именительный: {sign_nom}; {house}-й дом; градус {degree}{retro}"
    )


def _house_row(house: dict[str, Any]) -> str:
    num = house.get("number")
    sign_nom = sign_ru(house.get("sign_ru") or house.get("sign"))
    sign_prep = sign_ru(house.get("sign_ru") or house.get("sign"), "prep")
    degree = house.get("degree", "?")
    return f"- Дом {num}: знак на куспиде — {sign_nom}; дом в {sign_prep}; градус {degree}"


def _aspect_row(aspect: dict[str, Any]) -> str:
    p1 = (aspect.get("p1") or "").lower()
    p2 = (aspect.get("p2") or "").lower()
    atype = (aspect.get("aspect") or "").lower()
    orb = aspect.get("orb", 0)
    return (
        f"- {p1}_{p2}_{atype}: {_PLANET_RU.get(p1, p1)} — "
        f"{_ASPECT_RU.get(atype, atype)} — {_PLANET_RU.get(p2, p2)} "
        f"(орб {float(orb):.1f}°)"
    )


def _planet_aspect_context(aspects: list[dict[str, Any]]) -> list[str]:
    related: dict[str, list[str]] = {key: [] for key in _PLANET_ORDER}
    for aspect in aspects:
        p1 = (aspect.get("p1") or "").lower()
        p2 = (aspect.get("p2") or "").lower()
        atype = (aspect.get("aspect") or "").lower()
        if p1 not in _PLANET_RU or p2 not in _PLANET_RU or atype not in _ASPECT_RU:
            continue
        orb = aspect.get("orb", 0)
        text = (
            f"{_PLANET_RU.get(p1, p1)} — {_ASPECT_RU.get(atype, atype)} — "
            f"{_PLANET_RU.get(p2, p2)} (орб {float(orb):.1f}°)"
        )
        if p1 in related:
            related[p1].append(text)
        if p2 in related:
            related[p2].append(text)
    return [
        f"- {_PLANET_RU.get(key, key)}: {', '.join(items)}"
        for key, items in related.items()
        if items
    ]


def _house_planet_context(
    planets: dict[str, dict[str, Any]],
    houses: list[dict[str, Any]],
) -> list[str]:
    house_nums = [int(h.get("number") or 0) for h in houses if h.get("number")]
    by_house: dict[int, list[str]] = {num: [] for num in house_nums}
    for key, planet in planets.items():
        try:
            house = int(planet.get("house") or 0)
        except (TypeError, ValueError):
            continue
        if house in by_house:
            sign = sign_ru(planet.get("sign_ru") or planet.get("sign"), "prep")
            by_house[house].append(f"{_PLANET_RU.get(key, key)} в {sign}")
    return [
        f"- Дом {num}: {', '.join(items) if items else 'нет планет из основного набора'}"
        for num, items in by_house.items()
    ]


def _chart_context(
    planets: dict[str, dict[str, Any]],
    houses: list[dict[str, Any]],
    aspects: list[dict[str, Any]],
) -> str:
    """Compact full-chart context included in every batch prompt. The batch
    still asks for only 1-2 outputs, but the model can see the whole chart
    and avoid generic copy detached from the real layout."""
    planet_rows = [_planet_row(key, planets[key]) for key in _PLANET_ORDER if planets.get(key)]
    house_rows = [_house_row(h) for h in houses if h.get("number")]
    aspect_rows = [
        _aspect_row(a)
        for a in aspects
        if (a.get("p1") or "").lower() in _PLANET_RU
        and (a.get("p2") or "").lower() in _PLANET_RU
        and (a.get("aspect") or "").lower() in _ASPECT_RU
    ]
    related_aspect_rows = _planet_aspect_context(aspects)
    house_planet_rows = _house_planet_context(planets, houses)
    big_three = []
    if sun := planets.get("sun"):
        big_three.append(f"Солнце: {sign_ru(sun.get('sign_ru') or sun.get('sign'), 'prep')}")
    if moon := planets.get("moon"):
        big_three.append(f"Луна: {sign_ru(moon.get('sign_ru') or moon.get('sign'), 'prep')}")
    asc = next((h for h in houses if int(h.get("number") or 0) == 1), None)
    if asc:
        big_three.append(f"Асцендент: {sign_ru(asc.get('sign_ru') or asc.get('sign'), 'prep')}")
    return (
        "Контекст всей натальной карты, который обязательно учитывай при каждом описании:\n"
        f"Ключевые точки: {', '.join(big_three) if big_three else 'не указаны'}.\n"
        "Все планеты:\n"
        f"{chr(10).join(planet_rows) if planet_rows else '- нет данных'}\n"
        "Все дома:\n"
        f"{chr(10).join(house_rows) if house_rows else '- нет данных'}\n"
        "Планеты в домах:\n"
        f"{chr(10).join(house_planet_rows) if house_planet_rows else '- нет данных'}\n"
        "Все аспекты:\n"
        f"{chr(10).join(aspect_rows) if aspect_rows else '- нет основных аспектов'}\n"
        "Связанные аспекты по планетам:\n"
        f"{chr(10).join(related_aspect_rows) if related_aspect_rows else '- нет связанных аспектов'}"
    )


def _quality_rules(section: str) -> str:
    min_words = _MIN_FULL_WORDS[section]
    return f"""КРИТИЧЕСКИЕ ПРАВИЛА КАЧЕСТВА:
- "full" — около {min_words} слов как ВЕРХНИЙ ориентир. Лучше короче и по делу, чем добивать объём водой. Каждое предложение — факт о человеке, а не общая фраза.
- Запрещены абстрактные наполнители без конкретики: «баланс», «гармония», «осознанность», «энергия», «потенциал», «работа над собой», «прислушиваться к себе», «вселенная». Каждое такое слово заменяй конкретным проявлением (что человек делает, говорит, выбирает, чувствует в реальной ситуации).
- "full" заметно длиннее "short" и не пересказывает его; "short" — это выжимка, "full" — разбор с примерами.
- Учитывай реальный контекст карты выше: дом, знак, орб, ретроградность, соседние акценты — называй их конкретно, а не «по ситуации».
- Не используй одинаковый каркас абзацев для разных элементов. Меняй порядок тем, первые предложения, примеры, лексику и финал.
- Первое и последнее предложение каждого "full" уникальны; запрещены шаблонные финалы «это поможет проживать аспект мягче», «важно найти баланс», «это ваш ресурс», «стоит действовать осознанно».
- Никаких вступлений-подводок («давайте разберём», «стоит отметить») — сразу суть.
- Запрещены маркеры копипаста: «Подробнее», «Читать далее», «Источник», «Geocult», рекламные переходы.
- ВЫСШИЕ ПЛАНЕТЫ (Уран, Нептун, Плутон) трактуй ИНДИВИДУАЛЬНО — через дом и аспекты этой карты, а не через год/поколение рождения. Запрещены фразы «поколение 1996–2003», «цифровое поколение» и любые «поколенческие» ярлыки: они одинаковы для миллионов и не говорят о человеке. Покажи, в какой сфере (дом) и через какие связки (аспекты) эта планета работает лично у него.
- ЯЗЫК: только русский, 100% кириллица. Запрещены любые иероглифы, латинские буквы внутри русских слов и любой иной алфавит. Имена планет/знаков пиши кириллицей целиком («Козерог», не «Козеrog»). Исключение — общепринятые аббревиатуры осей (MC, IC, Asc).
- ЛИЦО: обращение строго на «вы» во множественном числе — «вы можете», «вы чувствуете», «вы стремитесь». Запрещены формы «вы можешь», «вы можем», «ты».
- ПАДЕЖИ: следи за управлением. После «направлено на», «нацелено на», «ориентировано на» ставь винительный падеж и склоняй слова («направлено на карьеру и статус», не «направлено на карьера, статус»). Не вставляй списки ключевых слов в именительном падеже после предлога — перестрой фразу («работает в сфере карьеры», «отвечает за деньги и ресурсы»).
- Если два элемента похожи, объясни конкретную разницу именно в этой карте."""


def _build_planets_prompt(
    planets: dict[str, dict[str, Any]],
    gender: str | None = None,
    *,
    chart_context: str = "",
) -> str:
    rows: list[str] = []
    for key in _PLANET_ORDER:
        p = planets.get(key)
        if not p:
            continue
        rows.append(_planet_row(key, p))

    count = len(rows)
    return f"""Ты — опытный астролог, пишешь персональные интерпретации натальной карты на русском языке.

{_gender_directive(gender)}Раздел PDF: «Планеты в знаках».
{_REFERENCE_STYLE_BLUEPRINT}

{chart_context}

Положения планет ({count} штук):
{chr(10).join(rows)}

Для КАЖДОЙ из перечисленных планет напиши:
- "short" — компактное описание (2 предложения, ~35-55 слов): что эта планета в данном знаке означает для человека — характер, проявления в жизни, на что обратить внимание; дом упомяни только одним прикладным штрихом.
- "full" — полноценное описание (1-2 абзаца, ~80-100 слов): центр разбора — связка планета + знак. Объясни роль планеты как архетип и жизненную функцию, положение планеты в знаке, характер, мотивацию, сильные стороны и уязвимости, проявления в отношениях и работе/делах, практический совет. Дом, ретроградность и связанные аспекты используй как персональные уточнения, не делай их случайной припиской. Пиши плотно, без воды и повторов — лучше короче и по делу.

{_quality_rules("planets")}

Пиши тепло, конкретно, от второго лица («вы»). Не копируй чужие тексты. Избегай общих фраз вроде «вы творческий человек» без объяснения, как это видно в жизни. У каждой планеты должна быть своя композиция текста и свой финальный акцент: не заканчивай несколько описаний одинаковыми формулами вроде «важно учиться…», «полезно…», «это ваш ресурс». Последнее предложение должно быть уникальным и привязанным именно к этой планете, знаку и дому. Используй правильные склонения: «Солнце в Скорпионе», но «в знаке Скорпиона». Без рекламы, markdown, заголовков и списков. Только обычные предложения и абзацы внутри строк.

Вызови инструмент submit_planet_descriptions РОВНО ОДИН РАЗ. В одном вызове укажи КАЖДУЮ из {count} планет как отдельный ключ верхнего уровня (например, "sun", "moon", "mercury", … "pluto"); значение каждого ключа — это объект с двумя полями short и full. Не пропускай ни одну планету."""


def _build_houses_prompt(
    houses: list[dict[str, Any]],
    gender: str | None = None,
    *,
    chart_context: str = "",
) -> str:
    rows: list[str] = []
    house_nums: list[str] = []
    for h in houses:
        num = h.get("number")
        if not num:
            continue
        rows.append(_house_row(h))
        house_nums.append(str(int(num)))

    count = len(rows)
    keys_hint = ", ".join(f'"{n}"' for n in house_nums)
    return f"""Ты — опытный астролог, пишешь персональные интерпретации натальной карты на русском языке.

{_gender_directive(gender)}Куспиды домов ({count} штук):
{_REFERENCE_STYLE_BLUEPRINT}

{chart_context}

{chr(10).join(rows)}

Для КАЖДОГО дома напиши:
- "short" — компактное описание (2 предложения, ~35-55 слов): какую сферу жизни описывает этот дом, как знак на куспиде окрашивает её, ключевые проявления.
- "full" — полноценное описание (1-2 абзаца, ~110-150 слов): тема дома, стиль знака на куспиде, типичные жизненные сценарии, как это видно в характере и поведении, отношения или работа/дела этой сферы, сильная сторона, риск и практический ориентир. Пиши плотно, без воды — лучше короче и по делу.

{_quality_rules("houses")}

Пиши тепло, конкретно, от второго лица («вы»). Не копируй чужие тексты. Избегай общих фраз без жизненного проявления. У каждого дома должны отличаться ритм, примеры и последнее предложение: не закрывай тексты одинаковым советом, выводом или фразой про «осознанность». Финал каждого дома должен звучать как отдельный персональный ориентир именно для этой сферы жизни. Используй правильные склонения: «знак на куспиде — Овен», но «дом в Овне». Без markdown, без заголовков, без списков. Только обычные предложения.

Вызови инструмент submit_house_descriptions РОВНО ОДИН РАЗ. В одном вызове укажи КАЖДЫЙ из {count} домов как отдельный ключ верхнего уровня в виде строки с номером дома. Используй ИМЕННО эти номера, не перенумеровывай: {keys_hint}. Значение каждого ключа — это объект с двумя полями short и full. Не пропускай ни один дом."""


def _build_aspects_prompt(
    aspects: list[dict[str, Any]],
    gender: str | None = None,
    *,
    chart_context: str = "",
) -> tuple[str, list[str]]:
    """Returns (prompt, list_of_aspect_ids). Empty prompt + empty list if
    nothing was usable."""
    rows: list[str] = []
    aspect_keys: list[tuple[str, str, str]] = []
    for a in aspects:
        p1 = (a.get("p1") or "").lower()
        p2 = (a.get("p2") or "").lower()
        atype = (a.get("aspect") or "").lower()
        if not p1 or not p2 or not atype:
            continue
        if p1 not in _PLANET_RU or p2 not in _PLANET_RU:
            continue
        if atype not in _ASPECT_RU:
            continue
        rows.append(_aspect_row(a))
        aspect_keys.append((p1, p2, atype))

    if not rows:
        return "", []

    aspect_ids = [f"{p1}_{p2}_{atype}" for p1, p2, atype in aspect_keys]
    count = len(rows)
    prompt = f"""Ты — опытный астролог, пишешь персональные интерпретации натальной карты на русском языке.

{_gender_directive(gender)}Аспекты между планетами ({count} штук):
{_REFERENCE_STYLE_BLUEPRINT}

{chart_context}

{chr(10).join(rows)}

Для КАЖДОГО аспекта напиши:
- "short" — компактное описание (2 предложения, ~35-55 слов): как эти две планеты взаимодействуют, что человеку даёт или с чем приходится работать.
- "full" — полноценное описание (1-2 абзаца, ~130-170 слов): как именно взаимодействуют две планеты, гармония это или напряжение, какие темы жизни затронуты, как проявляется в характере, отношениях и делах, сильная сторона, зона роста и практический способ проживать аспект мягче. Добавь 1 жизненный пример. Пиши плотно, без воды — лучше короче и по делу.

{_quality_rules("aspects")}

Пиши тепло, конкретно, от второго лица («вы»). Не копируй чужие тексты. Не ограничивайся фразой «планеты взаимодействуют»: объясни механизм и жизненный пример. Не заканчивай аспекты одинаковыми фразами про «баланс», «зону роста» или «проживать мягче»; последний абзац должен быть разным для каждого аспекта и опираться на конкретную пару планет. Без markdown, без заголовков, без списков. Только обычные предложения.

Вызови инструмент submit_aspect_descriptions РОВНО ОДИН РАЗ. В одном вызове укажи КАЖДЫЙ из {count} аспектов как отдельный ключ верхнего уровня в формате "<планета1>_<планета2>_<аспект>" (например, "{aspect_ids[0]}"); значение каждого ключа — это объект с двумя полями short и full. Не пропускай ни один аспект."""
    return prompt, aspect_ids


# ── LLM call ──────────────────────────────────────────────────────────────────


def _entry_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "short": {"type": "string"},
            "full": {"type": "string"},
        },
        "required": ["short", "full"],
    }


def _planets_tool_schema(planets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Force the model to return entries only for the planets we actually
    have. Each value is an object with required `short`+`full` strings."""
    keys = [k for k in _PLANET_ORDER if k in planets]
    if not keys:
        keys = list(planets.keys())
    return {
        "type": "object",
        "properties": {k: _entry_schema() for k in keys},
        "required": keys,
    }


def _houses_tool_schema(houses: list[dict[str, Any]]) -> dict[str, Any]:
    nums = [str(h.get("number")) for h in houses if h.get("number")]
    return {
        "type": "object",
        "properties": {n: _entry_schema() for n in nums},
        "required": nums,
    }


def _aspects_tool_schema(aspect_ids: list[str]) -> dict[str, Any]:
    """Flat object keyed by aspect_id (e.g. "sun_moon_trine"). Matches the
    structure planets/houses already use, which the model handles better
    than nested arrays."""
    return {
        "type": "object",
        "properties": {aid: _entry_schema() for aid in aspect_ids},
        "required": aspect_ids,
    }


async def _call_tool(
    client: Any,
    prompt: str,
    tool_name: str,
    input_schema: dict[str, Any],
    max_tokens: int,
) -> dict[str, Any] | None:
    """Invoke the model with a forced tool call — the response's tool_use
    block carries an already-parsed dict matching `input_schema`. No JSON
    string handling needed on our side."""
    from services.llm_pool import llm_semaphore
    from services.rate_limiter import AnthropicLimiter

    async with llm_semaphore, AnthropicLimiter(max_tokens):
        message = await client.messages.create(
            model=_MODEL,
            max_tokens=max_tokens,
            tools=[
                {
                    "name": tool_name,
                    "description": "Submit the requested descriptions.",
                    "input_schema": input_schema,
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
            messages=[{"role": "user", "content": prompt}],
        )
    for block in message.content:
        if getattr(block, "type", None) == "tool_use":
            return getattr(block, "input", None)
    return None


async def _call_llm(client: Any, prompt: str, max_tokens: int) -> str:
    """Legacy plain-text call — kept for any future free-form prompt."""
    from services.llm_pool import llm_semaphore
    from services.rate_limiter import AnthropicLimiter

    async with llm_semaphore, AnthropicLimiter(max_tokens):
        message = await client.messages.create(
            model=_MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
    return first_text_block(message.content)


def _single_entry_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "short": {"type": "string"},
            "full": {"type": "string"},
        },
        "required": ["short", "full"],
    }


_STYLE_BRIEF = """КАК ПИСАТЬ:
- Живой разговорный язык, как будто рассказываешь хорошему знакомому про него самого.
- Конкретные образы из жизни: работа, отношения, привычки, разговоры, реакции.
- Без астрологического жаргона: ни «энергии», ни «вселенная», ни «архетипы», ни «эманации», ни «работа со страхами».
- Без банальностей вроде «вы — творческая натура»: вместо ярлыка — как именно это видно (что делает, как реагирует, что выбирает).
- Каждое предложение несёт факт/наблюдение об этом человеке. Предложение, которое подошло бы любому, — выкинь.
- Каждый текст имеет свой ритм, свои примеры, уникальное первое и последнее предложение; не повторяй стартовые/финальные формулы в соседних описаниях.
- Full — конкретный разбор с примерами и одним практическим ориентиром, а не короткий вывод и не вода ради длины. Лучше короче и по делу.
- Не копируй чужие тексты; используй только общую структуру глубокого астрологического разбора.
- Не используй маркеры копипаста: «Подробнее», «Читать далее», «Источник», «Geocult».
- Следи за склонениями знаков: «в Скорпионе», но «в знаке Скорпиона».
- Обращайся на «вы», но по-человечески, не официально.
- Без markdown, без списков, без заголовков."""


def _planet_one_prompt(key: str, planet: dict[str, Any]) -> str:
    sign_nom = sign_ru(planet.get("sign_ru") or planet.get("sign"))
    sign_prep = sign_ru(planet.get("sign_ru") or planet.get("sign"), "prep")
    sign_gen = sign_ru(planet.get("sign_ru") or planet.get("sign"), "gen")
    house = planet.get("house", "?")
    retro = " (ретроградный)" if planet.get("retrograde") else ""
    return f"""Ты пишешь раздел PDF «Планеты в знаках» для популярного приложения с натальными картами. Читатель — обычный человек, не астролог.

{_REFERENCE_STYLE_BLUEPRINT}

Планета: {_PLANET_RU.get(key, key)} в {sign_prep}; форма «в знаке {sign_gen}»; именительный: {sign_nom}; {house}-й дом{retro}.
Важно: центр разбора — связка планета + знак. Дом используй только как короткое персональное уточнение ближе к концу, не смешивай весь текст с темой дома.

Вызови инструмент submit_entry с двумя полями:
- "short" (2 предложения, ~35-55 слов): что эта планета в данном знаке значит для человека — как проявляется в характере и в жизни, на что обратить внимание; дом упомяни только одним прикладным штрихом.
- "full" (1-2 абзаца, ~80-100 слов): справочный текст «планета в знаке»: роль планеты как архетип и жизненная функция, характер, мотивации, сильные стороны и уязвимости, проявления в отношениях и работе/делах, практический совет. Дом добавь только ближе к концу как персональный акцент. Плотно, без воды — лучше короче и по делу.

{_STYLE_BRIEF}"""


def _house_one_prompt(num: int, sign_name: str) -> str:
    sign_nom = sign_ru(sign_name)
    sign_prep = sign_ru(sign_name, "prep")
    return f"""Ты пишешь персональный разбор натальной карты для популярного приложения. Читатель — обычный человек, не астролог.

{_REFERENCE_STYLE_BLUEPRINT}

Дом: {num}-й, знак на куспиде — {sign_nom}; форма «дом в {sign_prep}».

Вызови инструмент submit_entry с двумя полями:
- "short" (2 предложения, ~35-55 слов): какую сферу жизни описывает этот дом, как знак на куспиде её окрашивает, ключевые проявления.
- "full" (1-2 абзаца, ~110-150 слов): тема дома, стиль знака на куспиде, типичные жизненные сценарии, как это видно в характере и поведении, отношения или работа/дела этой сферы, сильная сторона, риск и практический ориентир. Плотно, без воды — лучше короче и по делу.

{_STYLE_BRIEF}"""


def _aspect_one_prompt(p1: str, p2: str, atype: str) -> str:
    return f"""Ты пишешь персональный разбор натальной карты для популярного приложения. Читатель — обычный человек, не астролог.

{_REFERENCE_STYLE_BLUEPRINT}

Аспект: {_PLANET_RU.get(p1, p1)} — {_ASPECT_RU.get(atype, atype)} — {_PLANET_RU.get(p2, p2)}.

Вызови инструмент submit_entry с двумя полями:
- "short" (2 предложения, ~35-55 слов): как эти две темы взаимодействуют — что даёт человеку или с чем приходится работать.
- "full" (1-2 абзаца, ~130-170 слов): как именно сочетаются эти две темы, гармония это или трение, какие сферы жизни затронуты, как проявляется в характере, отношениях и делах, сильная сторона, зона роста и практический способ проживать аспект мягче. Добавь 1 бытовой пример. Плотно, без воды — лучше короче и по делу.

{_STYLE_BRIEF}"""


def _repair_prompt(
    *,
    section: str,
    label: str,
    current: dict[str, str],
    chart_context: str,
) -> str:
    short = str(current.get("short") or "").strip()
    full = str(current.get("full") or "").strip()
    return f"""Ты исправляешь некачественный текст для натальной карты. Предыдущая версия была слишком короткой, шаблонной или заканчивалась так же, как другие описания.

Элемент: {label}
Раздел: {section}

{chart_context}

Текущий short:
{short}

Текущий full, который нужно переписать полностью:
{full}

Вызови инструмент submit_entry с двумя полями:
- "short": оставь компактным, 2 предложения, без воды.
- "full": напиши заново как плотный PDF-разбор около {_MIN_FULL_WORDS[section]} слов (ориентир объёма, без воды). Явно длиннее short, учитывает реальный контекст карты, имеет свои примеры, уникальное первое и последнее предложение.

{_REFERENCE_STYLE_BLUEPRINT}

{_quality_rules(section)}

Без markdown, списков и заголовков."""


# Rate-limit handling for the descriptions batch. The key may be on a low
# RPM tier, and ~15 batched calls fire near-simultaneously — so a single
# 20s retry is not enough. Retry several times with exponential backoff.
_RATE_LIMIT_MAX_ATTEMPTS = 5
_RATE_LIMIT_BASE_DELAY = 15.0

# Сколько проходов регенерации делать для плохих текстов (планеты/дома/аспекты).
# 2 = основной generate + до 2 repair-итераций. Шаблонные fallback так почти
# никогда не доходят до финального PDF, но цикл ограничен — без риска таймаута.
_MAX_REPAIR_CYCLES = 2


def _is_rate_limit_error(msg: str) -> bool:
    low = msg.lower()
    return "429" in msg or "rate_limit" in low or "overloaded" in low or "529" in msg


def _rate_limit_delay(attempt: int) -> float:
    # 15s, 30s, 60s, 120s — capped. attempt is 0-based.
    return min(_RATE_LIMIT_BASE_DELAY * (2**attempt), 120.0)


async def _one_entry(
    client: Any,
    prompt: str,
    max_tokens: int = 3000,
) -> dict[str, str]:
    """Single LLM call → dict with {short, full}. Concurrency is governed by
    the global ``llm_semaphore`` + distributed token bucket inside ``_call_tool``.
    Retries with exponential backoff on a 429 rate-limit response. Returns
    empty strings on permanent failure."""
    for attempt in range(_RATE_LIMIT_MAX_ATTEMPTS):
        try:
            result = await _call_tool(
                client,
                prompt,
                "submit_entry",
                _single_entry_schema(),
                max_tokens,
            )
            if isinstance(result, dict):
                return {
                    "short": sanitize_ru_text(str(result.get("short", ""))),
                    "full": sanitize_ru_text(str(result.get("full", ""))),
                }
            return {"short": "", "full": ""}
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if _is_rate_limit_error(msg) and attempt < _RATE_LIMIT_MAX_ATTEMPTS - 1:
                delay = _rate_limit_delay(attempt)
                log.info("natal_descriptions.rate_limit_retry", attempt=attempt + 1, delay=delay)
                await asyncio.sleep(delay)
                continue
            log.warning("natal_descriptions.entry_failed", error=msg[:200])
            return {"short": "", "full": ""}
    return {"short": "", "full": ""}


def _chunked(items: list[Any], n: int) -> list[list[Any]]:
    """Split a list into fixed-size chunks (last chunk may be shorter)."""
    return [items[i : i + n] for i in range(0, len(items), n)]


async def _call_tool_chunk(
    client: Any,
    prompt: str,
    tool_name: str,
    keys: list[str],
    max_tokens: int,
) -> dict[str, dict[str, str]]:
    """Single batched LLM call → flat {key → {short, full}} dict. Concurrency
    is governed by the global ``llm_semaphore`` + distributed token bucket
    inside ``_call_tool``. Retries with exponential backoff on 429. Returns
    empty dict on permanent failure."""
    schema = {
        "type": "object",
        "properties": {k: _entry_schema() for k in keys},
        "required": keys,
    }
    for attempt in range(_RATE_LIMIT_MAX_ATTEMPTS):
        try:
            result = await _call_tool(
                client,
                prompt,
                tool_name,
                schema,
                max_tokens,
            )
            if not isinstance(result, dict):
                return {}
            out: dict[str, dict[str, str]] = {}
            for k, v in result.items():
                if isinstance(v, dict):
                    out[str(k)] = {
                        "short": sanitize_ru_text(str(v.get("short", ""))),
                        "full": sanitize_ru_text(str(v.get("full", ""))),
                    }
            return out
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if _is_rate_limit_error(msg) and attempt < _RATE_LIMIT_MAX_ATTEMPTS - 1:
                delay = _rate_limit_delay(attempt)
                log.info(
                    "natal_descriptions.batch_rate_limit_retry",
                    tool=tool_name,
                    attempt=attempt + 1,
                    delay=delay,
                )
                await asyncio.sleep(delay)
                continue
            log.warning(
                "natal_descriptions.batch_failed",
                tool=tool_name,
                keys=keys,
                error=msg[:200],
            )
            return {}
    return {}


def _word_count(text: str) -> int:
    return len(str(text or "").split())


def _last_sentence(text: str) -> str:
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        return ""
    sentences = re.split(r"(?<=[.!?…])\s+", cleaned)
    return sentences[-1].strip() if sentences else cleaned


def _first_sentence(text: str) -> str:
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        return ""
    sentences = re.split(r"(?<=[.!?…])\s+", cleaned)
    return sentences[0].strip() if sentences else cleaned


def _normalise_text(text: str) -> str:
    text = str(text or "").lower().replace("ё", "е")
    text = re.sub(r"[^\wа-яА-Я]+", " ", text, flags=re.IGNORECASE)
    return " ".join(text.split())


def _normalise_sentence(text: str) -> str:
    return _normalise_text(_last_sentence(text))


def _normalise_first_sentence(text: str) -> str:
    return _normalise_text(_first_sentence(text))


def _has_forbidden_copy_marker(text: str) -> bool:
    normalised = _normalise_text(text)
    return any(marker in normalised for marker in _FORBIDDEN_COPY_MARKERS)


def _full_too_close_to_short(short: str, full: str) -> bool:
    short_norm = _normalise_text(short)
    full_norm = _normalise_text(full)
    if len(short_norm.split()) < 5 or not full_norm:
        return False
    if full_norm.startswith(short_norm) or short_norm in full_norm:
        return True
    short_words = set(short_norm.split())
    full_words = set(full_norm.split())
    if not short_words:
        return False
    overlap = len(short_words & full_words) / len(short_words)
    return overlap > 0.9 and _word_count(full) < max(
        _word_count(short) * 4, _MIN_FULL_WORDS["houses"]
    )


def _validate_full(full: str, section: str, subject: str = "") -> list:
    """Прогон валидатора по тексту секции (planets/houses/aspects).

    target_words = целевой объём секции, чтобы thin-порог валидатора был
    согласован с промптом генератора (а не зашит константой).
    """
    ctx = ValidationContext(
        section_kind=_SECTION_KIND.get(section, "planet_in_sign"),
        subject=subject,
        target_words=_MIN_FULL_WORDS.get(section),
    )
    return _VALIDATOR.validate(full, ctx)


def _entry_needs_repair(entry: dict[str, str], section: str) -> bool:
    full = str(entry.get("full") or "").strip()
    if not full:
        return True
    if _has_forbidden_copy_marker(full):
        return True
    issues = _validate_full(full, section)
    # CRITICAL (короткий/обрыв) — всегда регенерим. Шаблонные/поколенческие
    # болванки тоже отправляем на регенерацию, чтобы не было «расслоения качества».
    if any(i.severity == Severity.CRITICAL for i in issues):
        return True
    bad_codes = {
        "TEMPLATE_PHRASE",
        "GENERATIONAL_IN_INDIVIDUAL",
        "TOO_SHORT_THIN",
        "CASE_AFTER_PREP",
        "FALSE_ASC_ATTRIBUTION",
        "GENDER_NUMBER_MISMATCH",
        "PERSON_MISMATCH",
        "LATIN_IN_RUSSIAN",
        "SIGN_PLANET_REVERSED",
        "TYPO",
    }
    if any(i.code in bad_codes for i in issues):
        return True
    return False


def _quality_repair_keys(entries: dict[str, dict[str, str]], section: str) -> set[str]:
    return {key for key, entry in entries.items() if _entry_needs_repair(entry, section)}


async def _repair_entries(
    client: Any,
    entries: dict[str, dict[str, str]],
    labels: dict[str, str],
    section: str,
    chart_context: str,
) -> dict[str, dict[str, str]]:
    """Регенерируем плохие тексты до годного — цикл из _MAX_REPAIR_CYCLES
    проходов. Раньше был один проход: если repair снова вернул шаблонный/
    короткий текст, он оставался в PDF. Теперь повторяем, пока текст не пройдёт
    валидацию (или не кончатся попытки) — шаблонные fallback так почти никогда
    не доходят до финального PDF. Новый текст принимаем только если он лучше
    (стал годным) или старый был пуст — чтобы не заменить нормальный на худший."""
    out = dict(entries)
    for cycle in range(_MAX_REPAIR_CYCLES):
        repair_keys = _quality_repair_keys(out, section)
        if not repair_keys:
            break
        log.info(
            "natal_descriptions.repair_cycle",
            section=section,
            cycle=cycle + 1,
            remaining=len(repair_keys),
        )
        tasks = {
            key: _one_entry(
                client,
                _repair_prompt(
                    section=section,
                    label=labels.get(key, key),
                    current=out.get(key, {}),
                    chart_context=chart_context,
                ),
                max_tokens=2000,
            )
            for key in repair_keys
        }
        repaired = await asyncio.gather(*tasks.values(), return_exceptions=False)
        for key, entry in zip(tasks.keys(), repaired):
            if not (entry.get("short") or entry.get("full")):
                continue
            old_bad = _entry_needs_repair(out.get(key, {}), section)
            new_bad = _entry_needs_repair(entry, section)
            # Принимаем, если новый годный, либо если старый был пуст/плохой и
            # новый не хуже (не пустой) — деградацию годного текста не допускаем.
            if not new_bad or old_bad:
                out[key] = entry
    return out


# Per-chunk cap of items in a single LLM call. The PDF copy is now compact, so a
# 4-item tool payload stays small while cutting request count sharply.
_BATCH_SIZE = 4
_BATCH_MAX_TOKENS = 1800

# Детерминированный порог «полный текст vs можно скрыть» для аспектов. Аспект с
# узким орбом ИЛИ с участием персональной планеты — важный, его НЕ скрываем даже
# если LLM-текст слабоват (лучше показать репейром, чем потерять важный аспект).
# Широкий орб между «дальними» планетами — допустимо скрыть, если текст-заглушка.
_FULL_ASPECT_ORB = 3.0
_PERSONAL_PLANETS = frozenset({"sun", "moon", "mercury", "venus", "mars"})


def _aspect_wants_full(p1: str, p2: str, orb: float) -> bool:
    """Единое правило важности аспекта на весь документ: тесный орб или
    участие персональной планеты → аспект важный (не скрываем по качеству)."""
    if orb <= _FULL_ASPECT_ORB:
        return True
    return p1 in _PERSONAL_PLANETS or p2 in _PERSONAL_PLANETS


def _aspect_quality_fallback(p1: str, p2: str, atype: str, orb: float) -> str:
    p1_ru = _PLANET_RU.get(p1, p1)
    p2_ru = _PLANET_RU.get(p2, p2)
    aspect_ru = _ASPECT_RU.get(atype, atype)
    dynamic = {
        "conjunction": (
            f"{p1_ru} и {p2_ru} работают как один спаянный импульс: человеку трудно отделить "
            "одно желание от другого, поэтому реакция выходит цельной и заметной."
        ),
        "trine": (
            f"{p1_ru} и {p2_ru} поддерживают друг друга естественно: сильная сторона включается "
            "без долгой подготовки и часто кажется самому человеку чем-то само собой разумеющимся."
        ),
        "sextile": (
            f"{p1_ru} и {p2_ru} дают возможность, которая раскрывается через действие: талант есть, "
            "но ему нужен конкретный повод, задача или разговор."
        ),
        "square": (
            f"{p1_ru} и {p2_ru} создают внутреннее трение: одна часть характера требует своего, "
            "другая мешает ей действовать привычным способом."
        ),
        "opposition": (
            f"{p1_ru} и {p2_ru} стоят на разных полюсах: человека может качать между двумя "
            "потребностями, пока он не научится удерживать обе."
        ),
        "quincunx": (
            f"{p1_ru} и {p2_ru} требуют ручной настройки: темы плохо стыкуются автоматически, "
            "поэтому важны наблюдение за собой и своевременная корректировка привычек."
        ),
    }.get(
        atype,
        f"{p1_ru} и {p2_ru} образуют важную связь, которую лучше читать через реальные реакции и выборы.",
    )
    # Орб-строку варьируем по типу аспекта, чтобы у нескольких аспектов она не
    # была дословно одинаковой (P1-3).
    if orb <= _FULL_ASPECT_ORB:
        orb_tail = {
            "conjunction": "слияние ощущается почти постоянно, в первой же реакции.",
            "trine": "ресурс включается сам собой и легко остаётся незамеченным.",
            "sextile": "возможность срабатывает, стоит сделать шаг.",
            "square": "трение видно в повторяющихся решениях и интонациях.",
            "opposition": "качели между полюсами включаются в каждом значимом выборе.",
            "quincunx": "рассогласование заметно в мелких сбоях, требующих подстройки.",
        }.get(atype, "он проявляется в повторяющихся решениях и реакциях.")
        orb_line = f"Орб {orb:.1f}° делает аспект заметным и личным: {orb_tail}"
    else:
        orb_tail = {
            "conjunction": "слитность выходит наружу в поворотные моменты.",
            "trine": "талант раскрывается в крупных ситуациях, а не в рутине.",
            "sextile": "возможность открывается эпизодически, под конкретную задачу.",
            "square": "напряжение копится и прорывается в ключевых решениях.",
            "opposition": "полярность обостряется в моменты важного выбора.",
            "quincunx": "несостыковка всплывает в нестандартных обстоятельствах.",
        }.get(atype, "аспект включается в заметных, поворотных ситуациях.")
        orb_line = f"Орб {orb:.1f}° шире, поэтому {orb_tail}"
    return (
        f"{p1_ru} — {aspect_ru} — {p2_ru}. {dynamic} {orb_line} "
        "В жизни это заметно, когда приходится одновременно хотеть результата и учитывать вторую внутреннюю потребность: "
        "например, в разговоре, договорённости, рабочем решении или близких отношениях. "
        "Сильная сторона аспекта — он не даёт жить на автопилоте и заставляет точнее понимать собственный мотив. "
        "Риск — реагировать слишком резко или, наоборот, откладывать выбор, пока напряжение не накопится. "
        "Практический ориентир простой: сначала назвать обе темы вслух, затем выбрать действие, которое учитывает каждую из них хотя бы частично."
    )


async def generate_natal_descriptions(
    planets: dict[str, dict[str, Any]],
    houses: list[dict[str, Any]],
    aspects: list[dict[str, Any]],
    api_key: str,
    gender: str | None = None,
) -> dict[str, Any]:
    """Batched LLM generation: each tool call covers up to 2 items at once.
    The smaller batch size keeps long PDF descriptions from being truncated
    inside a tool-call payload. Cached forever per chart so the cost is paid once.

    ``gender`` is propagated into every batch prompt so adjectives/past-
    tense verbs match the reader. Caller should also write ``gender`` into
    the cached payload so a profile change triggers a regen."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=api_key)
    # Concurrency and the Anthropic per-minute output-token limit are now
    # governed globally: llm_semaphore (in-process conn cap) + the distributed
    # token bucket, both inside _call_tool. Backoff in _call_tool_chunk still
    # absorbs residual 429/529 spikes.
    chart_context = _chart_context(planets, houses, aspects)

    # ── Planets ─────────────────────────────────────────────────────────
    planet_items = [(k, p) for k in _PLANET_ORDER if (p := planets.get(k))]
    planet_chunks = _chunked(planet_items, _BATCH_SIZE)
    planet_tasks = []
    for chunk in planet_chunks:
        chunk_dict = dict(chunk)
        prompt = _build_planets_prompt(chunk_dict, gender, chart_context=chart_context)
        keys = [k for k, _ in chunk]
        planet_tasks.append(
            _call_tool_chunk(
                client,
                prompt,
                "submit_planet_descriptions",
                keys,
                _BATCH_MAX_TOKENS,
            )
        )

    # ── Houses ──────────────────────────────────────────────────────────
    house_items: list[dict[str, Any]] = []
    for h in houses:
        num = h.get("number")
        if not num:
            continue
        house_items.append(
            {
                "number": int(num),
                "sign_ru": _normalise_sign(h.get("sign_ru") or h.get("sign")),
            }
        )
    house_chunks = _chunked(house_items, _BATCH_SIZE)
    house_tasks = []
    for chunk in house_chunks:
        prompt = _build_houses_prompt(chunk, gender, chart_context=chart_context)
        keys = [str(h["number"]) for h in chunk]
        house_tasks.append(
            _call_tool_chunk(
                client,
                prompt,
                "submit_house_descriptions",
                keys,
                _BATCH_MAX_TOKENS,
            )
        )

    # ── Aspects ─────────────────────────────────────────────────────────
    aspect_items: list[dict[str, Any]] = []
    aspect_ids_lookup: dict[str, tuple[str, str, str]] = {}
    aspect_orb_lookup: dict[str, float] = {}
    for a in aspects:
        p1 = (a.get("p1") or "").lower()
        p2 = (a.get("p2") or "").lower()
        atype = (a.get("aspect") or "").lower()
        if not (
            p1 and p2 and atype and p1 in _PLANET_RU and p2 in _PLANET_RU and atype in _ASPECT_RU
        ):
            continue
        aid = f"{p1}_{p2}_{atype}"
        try:
            orb = float(a.get("orb") or 0)
        except (TypeError, ValueError):
            orb = 0.0
        aspect_items.append(
            {
                "p1": p1,
                "p2": p2,
                "aspect": atype,
                "orb": orb,
            }
        )
        aspect_ids_lookup[aid] = (p1, p2, atype)
        aspect_orb_lookup[aid] = orb
    aspect_chunks = _chunked(aspect_items, _BATCH_SIZE)
    aspect_tasks = []
    for chunk in aspect_chunks:
        prompt, chunk_ids = _build_aspects_prompt(chunk, gender, chart_context=chart_context)
        if not chunk_ids:
            continue
        aspect_tasks.append(
            _call_tool_chunk(
                client,
                prompt,
                "submit_aspect_descriptions",
                chunk_ids,
                _BATCH_MAX_TOKENS,
            )
        )

    # Fire everything in parallel — llm_semaphore + token bucket cap concurrency.
    all_results = await asyncio.gather(
        *planet_tasks,
        *house_tasks,
        *aspect_tasks,
        return_exceptions=False,
    )

    p_n = len(planet_tasks)
    h_n = len(house_tasks)
    planet_results = all_results[:p_n]
    house_results = all_results[p_n : p_n + h_n]
    aspect_results = all_results[p_n + h_n :]

    planet_out: dict[str, dict[str, str]] = {}
    house_out: dict[str, dict[str, str]] = {}
    aspect_out: dict[str, dict[str, str]] = {}

    for chunk_dict in planet_results:
        for key, entry in chunk_dict.items():
            if entry.get("short") or entry.get("full"):
                planet_out[key] = entry

    for chunk_dict in house_results:
        for key, entry in chunk_dict.items():
            if entry.get("short") or entry.get("full"):
                if key in house_out:
                    log.warning("natal_descriptions.house_key_collision", key=key)
                house_out[key] = entry

    for chunk_dict in aspect_results:
        for aid, entry in chunk_dict.items():
            triple = aspect_ids_lookup.get(aid)
            if not triple:
                continue
            if entry.get("short") or entry.get("full"):
                aspect_out[aid] = entry

    planet_labels = {
        key: f"{_PLANET_RU.get(key, key)} в {sign_ru((planets.get(key) or {}).get('sign_ru') or (planets.get(key) or {}).get('sign'), 'prep')}"
        for key in planet_out
    }
    house_labels = {
        key: f"{key}-й дом в {sign_ru(next((h.get('sign_ru') or h.get('sign') for h in house_items if str(h.get('number')) == key), ''), 'prep')}"
        for key in house_out
    }
    aspect_labels = {}
    for aid in aspect_out:
        p1, p2, atype = aspect_ids_lookup.get(aid, ("", "", ""))
        aspect_labels[aid] = (
            f"{_PLANET_RU.get(p1, p1)} — {_ASPECT_RU.get(atype, atype)} — {_PLANET_RU.get(p2, p2)}"
        )

    planet_out = await _repair_entries(
        client,
        planet_out,
        planet_labels,
        "planets",
        chart_context,
    )
    house_out = await _repair_entries(
        client,
        house_out,
        house_labels,
        "houses",
        chart_context,
    )
    aspect_out = await _repair_entries(
        client,
        aspect_out,
        aspect_labels,
        "aspects",
        chart_context,
    )

    out: dict[str, Any] = {"planets": planet_out, "houses": house_out, "aspects": []}
    hidden_aspects = 0
    seen_full: set[str] = set()  # дедуп дословных дублей аспектов
    for aid, entry in aspect_out.items():
        triple = aspect_ids_lookup.get(aid)
        if not triple:
            continue
        p1, p2, atype = triple
        aspect: dict[str, Any] = {"p1": p1, "p2": p2, "type": atype, **entry}
        full = str(entry.get("full") or "").strip()
        issues = _validate_full(full, "aspects", subject=aspect_labels.get(aid, aid))
        hide_codes = {
            "TEMPLATE_PHRASE",
            "TOO_SHORT_THIN",
            "CASE_AFTER_PREP",
            "FALSE_ASC_ATTRIBUTION",
            "GENDER_NUMBER_MISMATCH",
            "PERSON_MISMATCH",
            "LATIN_IN_RUSSIAN",
            "SIGN_PLANET_REVERSED",
            "TYPO",
        }
        bad = any(i.severity == Severity.CRITICAL for i in issues) or any(
            i.code in hide_codes for i in issues
        )
        # Детерминированный порог: важный аспект (тесный орб / персональная планета)
        # НЕ скрываем по качеству — он несёт смысл карты; рендер подставит заглушку.
        # Скрываем только неважный аспект-болванку (широкий орб между дальними).
        orb = aspect_orb_lookup.get(aid, 0.0)
        important = _aspect_wants_full(p1, p2, orb)
        # После цикла repair шаблон не используем: плохой аспект скрываем.
        # Шаблон _aspect_quality_fallback остаётся ТОЛЬКО как авария для важного
        # аспекта, чей текст вообще пуст (LLM лёг/таймаут) — иначе важная связка
        # с персональной планетой молча пропала бы из платного отчёта.
        if bad:
            text_empty = not full
            if important and text_empty:
                aspect["full"] = _aspect_quality_fallback(p1, p2, atype, orb)
                aspect["short"] = str(aspect.get("short") or "").strip() or (
                    f"{_PLANET_RU.get(p1, p1)} и {_PLANET_RU.get(p2, p2)} образуют важный аспект с орбом {orb:.1f}°."
                )
                full = str(aspect.get("full") or "").strip()
            else:
                aspect["hide"] = True
                hidden_aspects += 1
        # Дедуп: дословный дубль full-текста между аспектами → скрыть второй.
        norm = " ".join(full.split()).lower()
        if norm and norm in seen_full and not aspect.get("hide"):
            log.warning("natal_descriptions.aspect_dup_full", aid=aid)
            aspect["hide"] = True
            hidden_aspects += 1
        if norm:
            seen_full.add(norm)
        out["aspects"].append(aspect)

    log.info(
        "natal_descriptions.done",
        planets=len(out["planets"]),
        houses=len(out["houses"]),
        aspects=len(out["aspects"]),
        hidden_aspects=hidden_aspects,
        batches=len(planet_tasks) + len(house_tasks) + len(aspect_tasks),
    )
    return out
