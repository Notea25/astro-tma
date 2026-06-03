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

log = get_logger(__name__)

_MODEL = "claude-haiku-4-5-20251001"

from services.astro.planet_names import PLANET_RU as _PLANET_RU  # noqa: E402

# Iteration order for the per-planet description loop — only the 10 classical
# points; chart axes / nodes / Lilith come through aspects but aren't seeded
# as standalone descriptions.
_PLANET_ORDER = [
    "sun", "moon", "mercury", "venus", "mars",
    "jupiter", "saturn", "uranus", "neptune", "pluto",
]

_ASPECT_RU: dict[str, str] = {
    "conjunction": "соединение",
    "sextile": "секстиль",
    "square": "квадрат",
    "trine": "трин",
    "opposition": "оппозиция",
    "quincunx": "квинконс",
}


_MIN_FULL_WORDS = {
    "planets": 150,
    "houses": 110,
    "aspects": 150,
}


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


def _chart_context(
    planets: dict[str, dict[str, Any]],
    houses: list[dict[str, Any]],
    aspects: list[dict[str, Any]],
) -> str:
    """Compact full-chart context included in every batch prompt. The batch
    still asks for only 1-2 outputs, but the model can see the whole chart
    and avoid generic copy detached from the real layout."""
    planet_rows = [
        _planet_row(key, planets[key])
        for key in _PLANET_ORDER
        if planets.get(key)
    ]
    house_rows = [
        _house_row(h)
        for h in houses
        if h.get("number")
    ]
    aspect_rows = [
        _aspect_row(a)
        for a in aspects
        if (a.get("p1") or "").lower() in _PLANET_RU
        and (a.get("p2") or "").lower() in _PLANET_RU
        and (a.get("aspect") or "").lower() in _ASPECT_RU
    ]
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
        "Все аспекты:\n"
        f"{chr(10).join(aspect_rows) if aspect_rows else '- нет основных аспектов'}"
    )


def _quality_rules(section: str) -> str:
    min_words = _MIN_FULL_WORDS[section]
    return f"""КРИТИЧЕСКИЕ ПРАВИЛА КАЧЕСТВА:
- "full" должен быть полноценным PDF-текстом минимум {min_words} слов и заметно длиннее "short"; не делай из short просто расширенную версию.
- Каждый "full" обязан учитывать реальный контекст карты выше: дом, знак, орб, ретроградность и соседние акценты карты, где это применимо.
- Не используй одинаковый каркас абзацев для разных элементов. Меняй порядок тем, примеры, лексику и финальный вывод.
- Последнее предложение каждого "full" должно быть уникальным; запрещены повторяющиеся финалы вроде «это поможет проживать аспект мягче», «важно найти баланс», «это ваш ресурс», «стоит действовать осознанно».
- Если два элемента похожи, всё равно объясни, чем именно они отличаются в этой карте."""


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
{chart_context}

Положения планет ({count} штук):
{chr(10).join(rows)}

Для КАЖДОЙ из перечисленных планет напиши:
- "short" — компактное описание (2 предложения, ~35-55 слов): что эта планета в данном знаке означает для человека — характер, проявления в жизни, на что обратить внимание; дом упомяни только одним прикладным штрихом.
- "full" — масштабное полноценное описание (4-6 абзацев, ~300-420 слов): центр разбора — связка планета + знак. Раскрой характер, мотивацию, сильные стороны, уязвимости, отношения, работу/дела, привычки, бытовые проявления, повторяющиеся жизненные сценарии и практический совет. Дом используй только ближе к концу как персональное уточнение, не делай его главной темой.

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
    for h in houses:
        num = h.get("number")
        if not num:
            continue
        rows.append(_house_row(h))

    count = len(rows)
    return f"""Ты — опытный астролог, пишешь персональные интерпретации натальной карты на русском языке.

{_gender_directive(gender)}Куспиды домов ({count} штук):
{chart_context}

{chr(10).join(rows)}

Для КАЖДОГО дома напиши:
- "short" — компактное описание (2 предложения, ~35-55 слов): какую сферу жизни описывает этот дом, как знак на куспиде окрашивает её, ключевые проявления.
- "full" — масштабное полноценное описание (4-5 абзацев, ~230-320 слов): тема дома, стиль знака на куспиде, типичные жизненные сценарии, как это видно в характере и поведении, отношения, работа/дела или быт этой сферы, сильная сторона, точка внимания и практический ориентир.

{_quality_rules("houses")}

Пиши тепло, конкретно, от второго лица («вы»). Не копируй чужие тексты. Избегай общих фраз без жизненного проявления. У каждого дома должны отличаться ритм, примеры и последнее предложение: не закрывай тексты одинаковым советом, выводом или фразой про «осознанность». Финал каждого дома должен звучать как отдельный персональный ориентир именно для этой сферы жизни. Используй правильные склонения: «знак на куспиде — Овен», но «дом в Овне». Без markdown, без заголовков, без списков. Только обычные предложения.

Вызови инструмент submit_house_descriptions РОВНО ОДИН РАЗ. В одном вызове укажи КАЖДЫЙ из {count} домов как отдельный ключ верхнего уровня в виде строки с номером ("1", "2", …, "{count}"); значение каждого ключа — это объект с двумя полями short и full. Не пропускай ни один дом."""


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
{chart_context}

{chr(10).join(rows)}

Для КАЖДОГО аспекта напиши:
- "short" — компактное описание (2 предложения, ~35-55 слов): как эти две планеты взаимодействуют, что человеку даёт или с чем приходится работать.
- "full" — масштабное полноценное описание (4-6 абзацев, ~300-420 слов): как именно взаимодействуют две планеты, гармония это или напряжение, какие темы жизни затронуты, как проявляется в характере, отношениях/делах, привычных реакциях и повторяющихся ситуациях, что является сильной стороной, где зона роста и какой практический способ проживать аспект мягче. Добавь 1-2 жизненных примера: разговор, выбор, рабочую ситуацию, близость, конфликт или привычную реакцию.

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

    async with llm_semaphore:
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

    async with llm_semaphore:
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
- Без банальностей вроде «вы — творческая натура».
- Каждый текст должен иметь свой ритм, свои примеры и уникальное последнее предложение; не используй одинаковые финальные формулы в соседних описаниях.
- Не копируй чужие тексты; используй только общую структуру глубокого астрологического разбора.
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

Планета: {_PLANET_RU.get(key, key)} в {sign_prep}; форма «в знаке {sign_gen}»; именительный: {sign_nom}; {house}-й дом{retro}.
Важно: центр разбора — связка планета + знак. Дом используй только как короткое персональное уточнение ближе к концу, не смешивай весь текст с темой дома.

Вызови инструмент submit_entry с двумя полями:
- "short" (2 предложения, ~35-55 слов): что эта планета в данном знаке значит для человека — как проявляется в характере и в жизни, на что обратить внимание; дом упомяни только одним прикладным штрихом.
- "full" (4-6 абзацев, ~300-420 слов): подробный справочный текст как в классическом описании «планета в знаке»: характер, мотивации, сильные стороны, уязвимости, отношения, работа/дела, привычки, бытовые проявления, повторяющиеся жизненные сценарии и практический совет. Дом добавь только ближе к концу как персональный акцент.

{_STYLE_BRIEF}"""


def _house_one_prompt(num: int, sign_name: str) -> str:
    sign_nom = sign_ru(sign_name)
    sign_prep = sign_ru(sign_name, "prep")
    return f"""Ты пишешь персональный разбор натальной карты для популярного приложения. Читатель — обычный человек, не астролог.

Дом: {num}-й, знак на куспиде — {sign_nom}; форма «дом в {sign_prep}».

Вызови инструмент submit_entry с двумя полями:
- "short" (2 предложения, ~35-55 слов): какую сферу жизни описывает этот дом, как знак на куспиде её окрашивает, ключевые проявления.
- "full" (4-5 абзацев, ~230-320 слов): тема дома подробнее, стиль знака на куспиде, типичные жизненные сценарии, как это видно в характере и поведении, отношения, работа/дела или быт этой сферы, сильная сторона, точка внимания и практический ориентир.

{_STYLE_BRIEF}"""


def _aspect_one_prompt(p1: str, p2: str, atype: str) -> str:
    return f"""Ты пишешь персональный разбор натальной карты для популярного приложения. Читатель — обычный человек, не астролог.

Аспект: {_PLANET_RU.get(p1, p1)} — {_ASPECT_RU.get(atype, atype)} — {_PLANET_RU.get(p2, p2)}.

Вызови инструмент submit_entry с двумя полями:
- "short" (2 предложения, ~35-55 слов): как эти две темы взаимодействуют — что даёт человеку или с чем приходится работать.
- "full" (4-6 абзацев, ~300-420 слов): как именно сочетаются эти две темы, гармония это или трение, какие сферы жизни затронуты, как проявляется в характере, отношениях/делах, привычных реакциях и повторяющихся ситуациях, сильные стороны, зоны роста и практический способ проживать аспект мягче. Добавь 1-2 бытовых примера проявления аспекта.

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
- "full": напиши заново как полноценный PDF-разбор минимум {_MIN_FULL_WORDS[section]} слов. Он должен быть явно длиннее short, учитывать реальный контекст карты, иметь свои примеры и уникальное последнее предложение.

{_quality_rules(section)}

Без markdown, списков и заголовков."""


async def _one_entry(
    client: Any,
    prompt: str,
    sem: asyncio.Semaphore,
    max_tokens: int = 3000,
) -> dict[str, str]:
    """Single LLM call → dict with {short, full}. Semaphore-limited and
    auto-retries once on a 429 rate-limit response. Returns empty strings
    on permanent failure."""
    for attempt in range(2):
        async with sem:
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
                        "short": str(result.get("short", "")),
                        "full": str(result.get("full", "")),
                    }
                return {"short": "", "full": ""}
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                is_rate_limit = "429" in msg or "rate_limit" in msg.lower()
                if is_rate_limit and attempt == 0:
                    log.info("natal_descriptions.rate_limit_retry")
                    await asyncio.sleep(20)
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
    sem: asyncio.Semaphore,
) -> dict[str, dict[str, str]]:
    """Single batched LLM call → flat {key → {short, full}} dict. Retries
    once on 429. Returns empty dict on permanent failure."""
    schema = {
        "type": "object",
        "properties": {k: _entry_schema() for k in keys},
        "required": keys,
    }
    for attempt in range(2):
        async with sem:
            try:
                result = await _call_tool(
                    client, prompt, tool_name, schema, max_tokens,
                )
                if not isinstance(result, dict):
                    return {}
                out: dict[str, dict[str, str]] = {}
                for k, v in result.items():
                    if isinstance(v, dict):
                        out[str(k)] = {
                            "short": str(v.get("short", "")),
                            "full": str(v.get("full", "")),
                        }
                return out
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                is_rate_limit = "429" in msg or "rate_limit" in msg.lower()
                if is_rate_limit and attempt == 0:
                    log.info("natal_descriptions.batch_rate_limit_retry")
                    await asyncio.sleep(20)
                    continue
                log.warning(
                    "natal_descriptions.batch_failed",
                    tool=tool_name, keys=keys, error=msg[:200],
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


def _normalise_sentence(text: str) -> str:
    text = _last_sentence(text).lower().replace("ё", "е")
    text = re.sub(r"[^\wа-яА-Я]+", " ", text, flags=re.IGNORECASE)
    return " ".join(text.split())


def _entry_needs_repair(entry: dict[str, str], section: str) -> bool:
    short = str(entry.get("short") or "").strip()
    full = str(entry.get("full") or "").strip()
    if _word_count(full) < _MIN_FULL_WORDS[section]:
        return True
    if short and _word_count(full) < max(_word_count(short) * 3, _MIN_FULL_WORDS[section]):
        return True
    return False


def _quality_repair_keys(entries: dict[str, dict[str, str]], section: str) -> set[str]:
    repair: set[str] = {
        key for key, entry in entries.items() if _entry_needs_repair(entry, section)
    }
    endings: dict[str, str] = {}
    for key, entry in entries.items():
        ending = _normalise_sentence(str(entry.get("full") or ""))
        if len(ending.split()) < 4:
            continue
        if ending in endings:
            repair.add(key)
            repair.add(endings[ending])
        else:
            endings[ending] = key
    return repair


async def _repair_entries(
    client: Any,
    entries: dict[str, dict[str, str]],
    labels: dict[str, str],
    section: str,
    chart_context: str,
    sem: asyncio.Semaphore,
) -> dict[str, dict[str, str]]:
    repair_keys = _quality_repair_keys(entries, section)
    if not repair_keys:
        return entries
    tasks = {
        key: _one_entry(
            client,
            _repair_prompt(
                section=section,
                label=labels.get(key, key),
                current=entries.get(key, {}),
                chart_context=chart_context,
            ),
            sem,
            max_tokens=3600,
        )
        for key in repair_keys
    }
    repaired = await asyncio.gather(*tasks.values(), return_exceptions=False)
    out = dict(entries)
    for key, entry in zip(tasks.keys(), repaired):
        if entry.get("short") or entry.get("full"):
            out[key] = entry
    return out


# Per-chunk cap of items in a single LLM call. Longer PDF copy needs smaller
# batches so the tool-call payload keeps schema adherence and avoids truncation.
_BATCH_SIZE = 2
_BATCH_MAX_TOKENS = 5600


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
    # Anthropic free-tier rate limit is 50 RPM with low concurrent-conn cap.
    # 3 in flight is plenty for 6-7 batched calls and keeps us under both.
    sem = asyncio.Semaphore(3)
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
                client, prompt, "submit_planet_descriptions",
                keys, _BATCH_MAX_TOKENS, sem,
            )
        )

    # ── Houses ──────────────────────────────────────────────────────────
    house_items: list[dict[str, Any]] = []
    for h in houses:
        num = h.get("number")
        if not num:
            continue
        house_items.append({
            "number": int(num),
            "sign_ru": _normalise_sign(h.get("sign_ru") or h.get("sign")),
        })
    house_chunks = _chunked(house_items, _BATCH_SIZE)
    house_tasks = []
    for chunk in house_chunks:
        prompt = _build_houses_prompt(chunk, gender, chart_context=chart_context)
        keys = [str(h["number"]) for h in chunk]
        house_tasks.append(
            _call_tool_chunk(
                client, prompt, "submit_house_descriptions",
                keys, _BATCH_MAX_TOKENS, sem,
            )
        )

    # ── Aspects ─────────────────────────────────────────────────────────
    aspect_items: list[dict[str, Any]] = []
    aspect_ids_lookup: dict[str, tuple[str, str, str]] = {}
    for a in aspects:
        p1 = (a.get("p1") or "").lower()
        p2 = (a.get("p2") or "").lower()
        atype = (a.get("aspect") or "").lower()
        if not (
            p1 and p2 and atype
            and p1 in _PLANET_RU and p2 in _PLANET_RU
            and atype in _ASPECT_RU
        ):
            continue
        aid = f"{p1}_{p2}_{atype}"
        aspect_items.append({
            "p1": p1, "p2": p2, "aspect": atype, "orb": a.get("orb", 0),
        })
        aspect_ids_lookup[aid] = (p1, p2, atype)
    aspect_chunks = _chunked(aspect_items, _BATCH_SIZE)
    aspect_tasks = []
    for chunk in aspect_chunks:
        prompt, chunk_ids = _build_aspects_prompt(chunk, gender, chart_context=chart_context)
        if not chunk_ids:
            continue
        aspect_tasks.append(
            _call_tool_chunk(
                client, prompt, "submit_aspect_descriptions",
                chunk_ids, _BATCH_MAX_TOKENS, sem,
            )
        )

    # Fire everything in parallel — semaphore caps actual concurrency.
    all_results = await asyncio.gather(
        *planet_tasks, *house_tasks, *aspect_tasks, return_exceptions=False,
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
            f"{_PLANET_RU.get(p1, p1)} — {_ASPECT_RU.get(atype, atype)} — "
            f"{_PLANET_RU.get(p2, p2)}"
        )

    planet_out = await _repair_entries(
        client, planet_out, planet_labels, "planets", chart_context, sem,
    )
    house_out = await _repair_entries(
        client, house_out, house_labels, "houses", chart_context, sem,
    )
    aspect_out = await _repair_entries(
        client, aspect_out, aspect_labels, "aspects", chart_context, sem,
    )

    out: dict[str, Any] = {"planets": planet_out, "houses": house_out, "aspects": []}
    for aid, entry in aspect_out.items():
        triple = aspect_ids_lookup.get(aid)
        if not triple:
            continue
        p1, p2, atype = triple
        out["aspects"].append({"p1": p1, "p2": p2, "type": atype, **entry})

    log.info(
        "natal_descriptions.done",
        planets=len(out["planets"]),
        houses=len(out["houses"]),
        aspects=len(out["aspects"]),
        batches=len(planet_tasks) + len(house_tasks) + len(aspect_tasks),
    )
    return out
