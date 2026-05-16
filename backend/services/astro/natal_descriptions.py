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

    return f"""Ты — опытный астролог, пишешь персональные интерпретации натальной карты на русском языке.

Положения планет:
{chr(10).join(rows)}

Для КАЖДОЙ из перечисленных планет напиши:
- "short" — содержательное описание (4-5 предложений, ~80-120 слов): что эта планета в данном знаке и доме означает для человека — характер, проявления в жизни, на что обратить внимание.
- "full" — полное описание (6-9 предложений, ~150-220 слов) в стиле классических астрологических справочников: характер, мотивации, сильные стороны, потенциальные сложности; разверни тему дома — на какую сферу жизни это влияет, как именно проявляется.

Пиши тепло, конкретно, от второго лица («вы»). Без markdown, без заголовков, без списков. Только обычные предложения.

ВАЖНО: внутри значений "short" и "full" не используй переносы строк (\n) и табуляции — пиши весь абзац одной логической строкой через обычные пробелы. Это критически важно для разбора JSON.

Верни СТРОГО JSON-объект без всяких комментариев, без блоков кода:
{{
  "sun":     {{"short": "...", "full": "..."}},
  "moon":    {{"short": "...", "full": "..."}},
  "mercury": {{"short": "...", "full": "..."}},
  "venus":   {{"short": "...", "full": "..."}},
  "mars":    {{"short": "...", "full": "..."}},
  "jupiter": {{"short": "...", "full": "..."}},
  "saturn":  {{"short": "...", "full": "..."}},
  "uranus":  {{"short": "...", "full": "..."}},
  "neptune": {{"short": "...", "full": "..."}},
  "pluto":   {{"short": "...", "full": "..."}}
}}

Включай в JSON только те планеты, что были перечислены выше."""


def _build_houses_prompt(houses: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for h in houses:
        num = h.get("number")
        if not num:
            continue
        sign_ru = _normalise_sign(h.get("sign_ru") or h.get("sign"))
        rows.append(f"- Дом {num}: знак на куспиде — {sign_ru}")

    return f"""Ты — опытный астролог, пишешь персональные интерпретации натальной карты на русском языке.

Куспиды домов:
{chr(10).join(rows)}

Для КАЖДОГО дома напиши:
- "short" — содержательное описание (4-5 предложений, ~80-120 слов): какую сферу жизни описывает этот дом, как знак на куспиде окрашивает её, ключевые проявления.
- "full" — полное описание (6-9 предложений, ~150-220 слов): тема дома, что говорит знак на куспиде о вашем подходе к этой сфере, проявления в характере и жизненных ситуациях, сильные стороны, на что обратить внимание.

Пиши тепло, конкретно, от второго лица («вы»). Без markdown, без заголовков, без списков. Только обычные предложения.

ВАЖНО: внутри значений "short" и "full" не используй переносы строк (\n) и табуляции — пиши весь абзац одной логической строкой через обычные пробелы. Это критически важно для разбора JSON.

Верни СТРОГО JSON-объект без всяких комментариев и блоков кода. Ключи — номера домов как строки:
{{
  "1": {{"short": "...", "full": "..."}},
  "2": {{"short": "...", "full": "..."}},
  ...
  "12": {{"short": "...", "full": "..."}}
}}

Включай только те дома, которые перечислены выше."""


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

    return f"""Ты — опытный астролог, пишешь персональные интерпретации натальной карты на русском языке.

Аспекты между планетами:
{chr(10).join(rows)}

Для КАЖДОГО аспекта напиши:
- "short" — содержательное описание (4-5 предложений, ~80-120 слов): как эти две планеты взаимодействуют, что человеку даёт или с чем приходится работать.
- "full" — полное описание (6-9 предложений, ~150-220 слов): как именно эти две планеты взаимодействуют, гармония это или напряжение, какие сферы жизни затронуты, как проявляется в характере и ситуациях, сильные стороны и зоны роста.

Пиши тепло, конкретно, от второго лица («вы»). Без markdown, без заголовков, без списков. Только обычные предложения.

ВАЖНО: внутри значений "short" и "full" не используй переносы строк (\n) и табуляции — пиши весь абзац одной логической строкой через обычные пробелы. Это критически важно для разбора JSON.

Верни СТРОГО JSON-массив без комментариев и блоков кода. Идентификатор каждого аспекта — строка вида "<планета1>_<планета2>_<аспект>" (как в списке выше):
[
  {{"id": "sun_moon_trine", "short": "...", "full": "..."}},
  ...
]

Включай ровно те аспекты, что перечислены выше."""


# ── LLM call ──────────────────────────────────────────────────────────────────

async def _call_llm(client: Any, prompt: str, max_tokens: int) -> str:
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

    Returns a dict shaped like:
        {
            "planets": {"sun": {"short": "...", "full": "..."}, ...},
            "houses":  {"1":   {"short": "...", "full": "..."}, ...},
            "aspects": [{"p1": "sun", "p2": "moon", "type": "trine",
                         "short": "...", "full": "..."}, ...],
        }

    Raises on transport / parsing errors — caller decides on fallback.
    """
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=api_key)

    planets_prompt = _build_planets_prompt(planets)
    houses_prompt = _build_houses_prompt(houses)
    aspects_prompt = _build_aspects_prompt(aspects)

    tasks: list[Any] = [
        _call_llm(client, planets_prompt, 4096),
        _call_llm(client, houses_prompt, 4096),
    ]
    if aspects_prompt:
        tasks.append(_call_llm(client, aspects_prompt, 6144))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    planets_raw = results[0]
    houses_raw = results[1]
    aspects_raw = results[2] if len(results) > 2 else None

    out: dict[str, Any] = {"planets": {}, "houses": {}, "aspects": []}

    if isinstance(planets_raw, str):
        try:
            parsed = _safe_load_json(planets_raw)
            if isinstance(parsed, dict):
                out["planets"] = {
                    k: {"short": str(v.get("short", "")), "full": str(v.get("full", ""))}
                    for k, v in parsed.items()
                    if isinstance(v, dict)
                }
        except Exception as e:
            log.error(
                "natal_descriptions.planets_parse_failed",
                error=str(e),
                sample=planets_raw[:300],
                length=len(planets_raw),
            )
    elif isinstance(planets_raw, BaseException):
        log.error("natal_descriptions.planets_call_failed", error=str(planets_raw))

    if isinstance(houses_raw, str):
        try:
            parsed = _safe_load_json(houses_raw)
            if isinstance(parsed, dict):
                out["houses"] = {
                    str(k): {"short": str(v.get("short", "")), "full": str(v.get("full", ""))}
                    for k, v in parsed.items()
                    if isinstance(v, dict)
                }
        except Exception as e:
            log.error(
                "natal_descriptions.houses_parse_failed",
                error=str(e),
                sample=houses_raw[:300],
                length=len(houses_raw),
            )
    elif isinstance(houses_raw, BaseException):
        log.error("natal_descriptions.houses_call_failed", error=str(houses_raw))

    if isinstance(aspects_raw, str):
        try:
            parsed = _safe_load_json(aspects_raw)
            if isinstance(parsed, list):
                items: list[dict[str, str]] = []
                for entry in parsed:
                    if not isinstance(entry, dict):
                        continue
                    raw_id = str(entry.get("id", ""))
                    parts = raw_id.split("_")
                    if len(parts) != 3:
                        continue
                    p1, p2, atype = parts
                    items.append({
                        "p1": p1,
                        "p2": p2,
                        "type": atype,
                        "short": str(entry.get("short", "")),
                        "full": str(entry.get("full", "")),
                    })
                out["aspects"] = items
        except Exception as e:
            log.error("natal_descriptions.aspects_parse_failed", error=str(e))
    elif isinstance(aspects_raw, BaseException):
        log.error("natal_descriptions.aspects_call_failed", error=str(aspects_raw))

    log.info(
        "natal_descriptions.done",
        planets=len(out["planets"]),
        houses=len(out["houses"]),
        aspects=len(out["aspects"]),
    )
    return out
