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

Вызови инструмент submit_planet_descriptions РОВНО ОДИН РАЗ, передав в одном вызове short и full для ВСЕХ {count} планет. Это критически важно — не делай несколько вызовов и не пропускай ни одну планету."""


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

Вызови инструмент submit_house_descriptions РОВНО ОДИН РАЗ, передав в одном вызове short и full для ВСЕХ {count} домов. Ключи — номера домов как строки («1», «2», …, «{count}»). Не пропускай ни один дом."""


def _build_aspects_prompt(aspects: list[dict[str, Any]]) -> str:
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
        return ""

    count = len(rows)
    return f"""Ты — опытный астролог, пишешь персональные интерпретации натальной карты на русском языке.

Аспекты между планетами ({count} штук):
{chr(10).join(rows)}

Для КАЖДОГО аспекта напиши:
- "short" — содержательное описание (4-5 предложений, ~80-120 слов): как эти две планеты взаимодействуют, что человеку даёт или с чем приходится работать.
- "full" — полное описание (6-9 предложений, ~150-220 слов): как именно эти две планеты взаимодействуют, гармония это или напряжение, какие сферы жизни затронуты, как проявляется в характере и ситуациях, сильные стороны и зоны роста.

Пиши тепло, конкретно, от второго лица («вы»). Без markdown, без заголовков, без списков. Только обычные предложения.

Вызови инструмент submit_aspect_descriptions РОВНО ОДИН РАЗ. В поле items передай ВСЕ {count} аспектов из списка — каждый как объект с полями id, short, full. id формируется как "<планета1>_<планета2>_<аспект>", точно как в списке выше. Не пропускай ни один аспект."""


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


def _aspects_tool_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "short": {"type": "string"},
                        "full": {"type": "string"},
                    },
                    "required": ["id", "short", "full"],
                },
            }
        },
        "required": ["items"],
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


async def generate_natal_descriptions(
    planets: dict[str, dict[str, Any]],
    houses: list[dict[str, Any]],
    aspects: list[dict[str, Any]],
    api_key: str,
) -> dict[str, Any]:
    """
    Generate short+full descriptions for every planet, house and aspect.

    Uses Anthropic tool_use to force structured output — the model can't
    return free-form text, it has to call our "submit_*" tool with a dict
    that matches the declared schema. Eliminates the long-standing JSON
    parsing issues we used to recover from with regex.

    Returns a dict shaped like:
        {
            "planets": {"sun": {"short": "...", "full": "..."}, ...},
            "houses":  {"1":   {"short": "...", "full": "..."}, ...},
            "aspects": [{"p1": "sun", "p2": "moon", "type": "trine",
                         "short": "...", "full": "..."}, ...],
        }
    """
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=api_key)

    planets_prompt = _build_planets_prompt(planets)
    houses_prompt = _build_houses_prompt(houses)
    aspects_prompt = _build_aspects_prompt(aspects)

    # 10 planets × (short ~120w + full ~220w) ≈ 5–7k tokens output. Houses
    # similar. Aspects can grow with how many we feed in. Use 8192 — the
    # Claude Haiku 4.5 cap — so the model isn't truncated mid-tool-call.
    tasks: list[Any] = [
        _call_tool(
            client,
            planets_prompt,
            "submit_planet_descriptions",
            _planets_tool_schema(planets),
            8192,
        ),
        _call_tool(
            client,
            houses_prompt,
            "submit_house_descriptions",
            _houses_tool_schema(houses),
            8192,
        ),
    ]
    if aspects_prompt:
        tasks.append(
            _call_tool(
                client,
                aspects_prompt,
                "submit_aspect_descriptions",
                _aspects_tool_schema(),
                8192,
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    planets_input = results[0]
    houses_input = results[1]
    aspects_input = results[2] if len(results) > 2 else None

    out: dict[str, Any] = {"planets": {}, "houses": {}, "aspects": []}

    if isinstance(planets_input, dict):
        out["planets"] = {
            k: {"short": str(v.get("short", "")), "full": str(v.get("full", ""))}
            for k, v in planets_input.items()
            if isinstance(v, dict)
        }
        log.info(
            "natal_descriptions.planets_ok",
            received=list(planets_input.keys()),
            kept=list(out["planets"].keys()),
        )
    elif isinstance(planets_input, BaseException):
        log.error("natal_descriptions.planets_call_failed", error=str(planets_input))
    else:
        log.error(
            "natal_descriptions.planets_no_tool_use",
            value_type=type(planets_input).__name__,
        )

    if isinstance(houses_input, dict):
        out["houses"] = {
            str(k): {"short": str(v.get("short", "")), "full": str(v.get("full", ""))}
            for k, v in houses_input.items()
            if isinstance(v, dict)
        }
    elif isinstance(houses_input, BaseException):
        log.error("natal_descriptions.houses_call_failed", error=str(houses_input))
    else:
        log.error("natal_descriptions.houses_no_tool_use")

    log.info(
        "natal_descriptions.aspects_debug",
        had_prompt=bool(aspects_prompt),
        result_type=type(aspects_input).__name__,
        keys=list(aspects_input.keys()) if isinstance(aspects_input, dict) else None,
        items_count=len(aspects_input.get("items", [])) if isinstance(aspects_input, dict) else None,
    )
    if isinstance(aspects_input, dict):
        items_raw = aspects_input.get("items") or []
        items: list[dict[str, str]] = []
        for entry in items_raw:
            if not isinstance(entry, dict):
                continue
            raw_id = str(entry.get("id", ""))
            parts = raw_id.split("_")
            if len(parts) != 3:
                continue
            p1, p2, atype = parts
            items.append(
                {
                    "p1": p1,
                    "p2": p2,
                    "type": atype,
                    "short": str(entry.get("short", "")),
                    "full": str(entry.get("full", "")),
                }
            )
        out["aspects"] = items
    elif isinstance(aspects_input, BaseException):
        log.error("natal_descriptions.aspects_call_failed", error=str(aspects_input))

    log.info(
        "natal_descriptions.done",
        planets=len(out["planets"]),
        houses=len(out["houses"]),
        aspects=len(out["aspects"]),
    )
    return out
