"""
LLM-generated personalised descriptions for natal planets, houses and aspects.

Produces both a short blurb (2-3 sentences, shown in the in-app popup)
and a full paragraph (4-6 sentences, rendered in the downloadable PDF).
Result is cached by the caller — this module only calls the API.
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from core.logging import get_logger
from services.llm_utils import first_text_block

log = get_logger(__name__)

_MODEL = "claude-haiku-4-5-20251001"

_PLANET_RU: dict[str, str] = {
    "sun": "Солнце", "moon": "Луна", "mercury": "Меркурий",
    "venus": "Венера", "mars": "Марс", "jupiter": "Юпитер",
    "saturn": "Сатурн", "uranus": "Уран", "neptune": "Нептун",
    "pluto": "Плутон",
}

_PLANET_ORDER = list(_PLANET_RU.keys())

_ASPECT_RU: dict[str, str] = {
    "conjunction": "соединение",
    "sextile": "секстиль",
    "square": "квадрат",
    "trine": "трин",
    "opposition": "оппозиция",
    "quincunx": "квинконс",
}

_SIGN_RU: dict[str, str] = {
    "aries": "Овен", "taurus": "Телец", "gemini": "Близнецы", "cancer": "Рак",
    "leo": "Лев", "virgo": "Дева", "libra": "Весы", "scorpio": "Скорпион",
    "sagittarius": "Стрелец", "capricorn": "Козерог",
    "aquarius": "Водолей", "pisces": "Рыбы",
}


def _normalise_sign(sign: str | None) -> str:
    if not sign:
        return ""
    key = sign.strip().lower()
    return _SIGN_RU.get(key, sign)


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

def _build_planets_prompt(planets: dict[str, dict[str, Any]]) -> str:
    rows: list[str] = []
    for key in _PLANET_ORDER:
        p = planets.get(key)
        if not p:
            continue
        sign_ru = _normalise_sign(p.get("sign_ru") or p.get("sign"))
        house = p.get("house", "?")
        retro = " (ретроградный)" if p.get("retrograde") else ""
        rows.append(
            f"- {key}: {_PLANET_RU[key]} в знаке {sign_ru}, {house}-й дом{retro}"
        )

    count = len(rows)
    return f"""Ты — опытный астролог, пишешь персональные интерпретации натальной карты на русском языке.

Положения планет ({count} штук):
{chr(10).join(rows)}

Для КАЖДОЙ из перечисленных планет напиши:
- "short" — содержательное описание (4-5 предложений, ~80-120 слов): что эта планета в данном знаке и доме означает для человека — характер, проявления в жизни, на что обратить внимание.
- "full" — полное описание (6-9 предложений, ~150-220 слов) в стиле классических астрологических справочников: характер, мотивации, сильные стороны, потенциальные сложности; разверни тему дома — на какую сферу жизни это влияет, как именно проявляется.

Пиши тепло, конкретно, от второго лица («вы»). Без markdown, без заголовков, без списков. Только обычные предложения.

Вызови инструмент submit_planet_descriptions РОВНО ОДИН РАЗ. В одном вызове укажи КАЖДУЮ из {count} планет как отдельный ключ верхнего уровня (например, "sun", "moon", "mercury", … "pluto"); значение каждого ключа — это объект с двумя полями short и full. Не пропускай ни одну планету."""


def _build_houses_prompt(houses: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for h in houses:
        num = h.get("number")
        if not num:
            continue
        sign_ru = _normalise_sign(h.get("sign_ru") or h.get("sign"))
        rows.append(f"- Дом {num}: знак на куспиде — {sign_ru}")

    count = len(rows)
    return f"""Ты — опытный астролог, пишешь персональные интерпретации натальной карты на русском языке.

Куспиды домов ({count} штук):
{chr(10).join(rows)}

Для КАЖДОГО дома напиши:
- "short" — содержательное описание (4-5 предложений, ~80-120 слов): какую сферу жизни описывает этот дом, как знак на куспиде окрашивает её, ключевые проявления.
- "full" — полное описание (6-9 предложений, ~150-220 слов): тема дома, что говорит знак на куспиде о вашем подходе к этой сфере, проявления в характере и жизненных ситуациях, сильные стороны, на что обратить внимание.

Пиши тепло, конкретно, от второго лица («вы»). Без markdown, без заголовков, без списков. Только обычные предложения.

Вызови инструмент submit_house_descriptions РОВНО ОДИН РАЗ. В одном вызове укажи КАЖДЫЙ из {count} домов как отдельный ключ верхнего уровня в виде строки с номером ("1", "2", …, "{count}"); значение каждого ключа — это объект с двумя полями short и full. Не пропускай ни один дом."""


def _build_aspects_prompt(aspects: list[dict[str, Any]]) -> tuple[str, list[str]]:
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
        orb = a.get("orb", 0)
        rows.append(
            f"- {p1}_{p2}_{atype}: {_PLANET_RU[p1]} — {_ASPECT_RU[atype]} — "
            f"{_PLANET_RU[p2]} (орб {float(orb):.1f}°)"
        )
        aspect_keys.append((p1, p2, atype))

    if not rows:
        return "", []

    aspect_ids = [f"{p1}_{p2}_{atype}" for p1, p2, atype in aspect_keys]
    count = len(rows)
    prompt = f"""Ты — опытный астролог, пишешь персональные интерпретации натальной карты на русском языке.

Аспекты между планетами ({count} штук):
{chr(10).join(rows)}

Для КАЖДОГО аспекта напиши:
- "short" — содержательное описание (4-5 предложений, ~80-120 слов): как эти две планеты взаимодействуют, что человеку даёт или с чем приходится работать.
- "full" — полное описание (6-9 предложений, ~150-220 слов): как именно эти две планеты взаимодействуют, гармония это или напряжение, какие сферы жизни затронуты, как проявляется в характере и ситуациях, сильные стороны и зоны роста.

Пиши тепло, конкретно, от второго лица («вы»). Без markdown, без заголовков, без списков. Только обычные предложения.

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


def _planet_one_prompt(key: str, planet: dict[str, Any]) -> str:
    sign_ru = _normalise_sign(planet.get("sign_ru") or planet.get("sign"))
    house = planet.get("house", "?")
    retro = " (ретроградный)" if planet.get("retrograde") else ""
    return f"""Ты — астролог. Напиши персональную интерпретацию положения планеты в натальной карте на русском языке.

Планета: {_PLANET_RU.get(key, key)} в знаке {sign_ru}, {house}-й дом{retro}.

Вызови инструмент submit_entry с двумя полями:
- "short" (4-5 предложений, ~80-120 слов): что эта планета в данном знаке и доме означает — характер, проявления в жизни, на что обратить внимание.
- "full" (6-9 предложений, ~150-220 слов): характер, мотивации, сильные стороны, потенциальные сложности; разверни тему дома — на какую сферу жизни это влияет.

Пиши тепло, от второго лица («вы»). Без markdown, без списков."""


def _house_one_prompt(num: int, sign_ru: str) -> str:
    return f"""Ты — астролог. Напиши персональную интерпретацию положения дома натальной карты на русском языке.

Дом: {num}-й, знак на куспиде — {sign_ru}.

Вызови инструмент submit_entry с двумя полями:
- "short" (4-5 предложений, ~80-120 слов): какую сферу жизни описывает этот дом, как знак на куспиде окрашивает её, ключевые проявления.
- "full" (6-9 предложений, ~150-220 слов): тема дома, что говорит знак о подходе к этой сфере, проявления в характере, сильные стороны, на что обратить внимание.

Пиши тепло, от второго лица («вы»). Без markdown, без списков."""


def _aspect_one_prompt(p1: str, p2: str, atype: str) -> str:
    return f"""Ты — астролог. Напиши персональную интерпретацию аспекта между двумя планетами в натальной карте на русском языке.

Аспект: {_PLANET_RU.get(p1, p1)} — {_ASPECT_RU.get(atype, atype)} — {_PLANET_RU.get(p2, p2)}.

Вызови инструмент submit_entry с двумя полями:
- "short" (4-5 предложений, ~80-120 слов): как эти две планеты взаимодействуют в этом аспекте, что человеку даёт или с чем приходится работать.
- "full" (6-9 предложений, ~150-220 слов): как именно эти планеты сочетаются, гармония это или напряжение, какие сферы жизни затронуты, как проявляется в характере, сильные стороны и зоны роста.

Пиши тепло, от второго лица («вы»). Без markdown, без списков."""


async def _one_entry(
    client: Any,
    prompt: str,
    sem: asyncio.Semaphore,
    max_tokens: int = 2048,
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


async def generate_natal_descriptions(
    planets: dict[str, dict[str, Any]],
    houses: list[dict[str, Any]],
    aspects: list[dict[str, Any]],
    api_key: str,
) -> dict[str, Any]:
    """Per-item LLM generation — one tool call per planet/house/aspect, all
    fired in parallel. Reliable (Haiku follows a small schema correctly),
    cached forever per chart so the cost is paid once. Total ~30 calls for
    a typical chart, ~30s in wall time when run in parallel."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=api_key)
    # Anthropic free-tier rate limit is 50 RPM with low concurrent-conn cap.
    # 5 in flight keeps us comfortably under both.
    sem = asyncio.Semaphore(5)

    planet_items = [(k, p) for k in _PLANET_ORDER if (p := planets.get(k))]
    planet_tasks = [_one_entry(client, _planet_one_prompt(k, p), sem) for k, p in planet_items]

    house_items: list[tuple[int, str]] = []
    for h in houses:
        num = h.get("number")
        if not num:
            continue
        sign_ru = _normalise_sign(h.get("sign_ru") or h.get("sign"))
        house_items.append((int(num), sign_ru))
    house_tasks = [_one_entry(client, _house_one_prompt(n, s), sem) for n, s in house_items]

    aspect_items: list[tuple[str, str, str]] = []
    for a in aspects:
        p1 = (a.get("p1") or "").lower()
        p2 = (a.get("p2") or "").lower()
        atype = (a.get("aspect") or "").lower()
        if (
            p1 and p2 and atype
            and p1 in _PLANET_RU and p2 in _PLANET_RU
            and atype in _ASPECT_RU
        ):
            aspect_items.append((p1, p2, atype))
    aspect_tasks = [_one_entry(client, _aspect_one_prompt(p1, p2, t), sem) for p1, p2, t in aspect_items]

    all_tasks = planet_tasks + house_tasks + aspect_tasks
    results = await asyncio.gather(*all_tasks, return_exceptions=False)

    p_count = len(planet_tasks)
    h_count = len(house_tasks)
    planet_results = results[:p_count]
    house_results = results[p_count : p_count + h_count]
    aspect_results = results[p_count + h_count :]

    out: dict[str, Any] = {"planets": {}, "houses": {}, "aspects": []}

    for (key, _), entry in zip(planet_items, planet_results):
        if entry.get("short") or entry.get("full"):
            out["planets"][key] = entry

    for (num, _), entry in zip(house_items, house_results):
        if entry.get("short") or entry.get("full"):
            out["houses"][str(num)] = entry

    for (p1, p2, atype), entry in zip(aspect_items, aspect_results):
        if entry.get("short") or entry.get("full"):
            out["aspects"].append(
                {"p1": p1, "p2": p2, "type": atype, **entry}
            )

    log.info(
        "natal_descriptions.done",
        planets=len(out["planets"]),
        houses=len(out["houses"]),
        aspects=len(out["aspects"]),
    )
    return out
