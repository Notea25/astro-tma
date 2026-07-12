"""Canonical structured natal report generated in four parallel LLM batches.

Swiss Ephemeris data is the only source of astrology facts.  The model returns
``id + narrative`` pairs and never owns headings, signs, houses, degrees or
aspect labels.  The enriched payload produced here is durable and can be
rendered consistently by the API, PDF and Telegram delivery paths.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from core.logging import get_logger
from core.settings import settings
from services.astro.fact_context import AstroFactContext, validate_generated_text
from services.astro.planet_names import PLANET_RU
from services.astro.sign_cases import sign_ru
from services.content_version import CONTENT_VERSION
from services.llm_client import create_llm_client
from services.llm_pool import llm_semaphore
from services.quality_validator import sanitize_ru_text
from services.rate_limiter import LLMLimiter

log = get_logger(__name__)

NATAL_REPORT_SCHEMA_VERSION = 1
NATAL_REPORT_PROMPT_VERSION = 1

_PLANET_ORDER = (
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
)

_ASPECT_RU = {
    "conjunction": "соединение",
    "sextile": "секстиль",
    "square": "квадрат",
    "trine": "трин",
    "opposition": "оппозиция",
}

_ROMAN_HOUSES = {
    1: "I",
    2: "II",
    3: "III",
    4: "IV",
    5: "V",
    6: "VI",
    7: "VII",
    8: "VIII",
    9: "IX",
    10: "X",
    11: "XI",
    12: "XII",
}

_FACT_RE = re.compile(
    r"\b(?:солнц\w*|лун\w*|меркур\w*|венер\w*|марс\w*|юпитер\w*|"
    r"сатурн\w*|уран\w*|нептун\w*|плутон\w*|асцендент\w*|куспид\w*|"
    r"овн\w*|тельц\w*|близнец\w*|рак(?:а|е|ом)?|льв\w*|дев\w*|"
    r"вес(?:ы|ах|ов|ам|ами)|скорпион\w*|стрельц\w*|козерог\w*|водоле\w*|рыб\w*|"
    r"соединени\w*|секстил\w*|квадрат\w*|трин\w*|оппозиц\w*)\b|"
    r"\b(?:1[0-2]|[1-9])(?:-?[а-я]*)?\s+дом\w*|\d+(?:[.,]\d+)?\s*°",
    re.IGNORECASE,
)

_WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9-]+")
_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
_LETTER_RE = re.compile(r"[A-Za-zА-Яа-яЁё]")


class _NarrativeItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=96)
    narrative: str = Field(min_length=1)


class _NarrativeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[_NarrativeItem]


class ReportItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    heading: str
    fact_line: str = ""
    narrative: str
    fallback: bool = False


class NatalReportPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = NATAL_REPORT_SCHEMA_VERSION
    prompt_version: int = NATAL_REPORT_PROMPT_VERSION
    content_version: str = CONTENT_VERSION
    chart_mode: Literal["full", "date_only"]
    core: list[ReportItem]
    planets: list[ReportItem]
    houses: list[ReportItem]
    aspects: list[ReportItem]
    used_fallback: bool = False


@dataclass(frozen=True)
class GeneratedNatalReport:
    payload: dict[str, Any]
    text: str
    status: Literal["ready", "ready_with_fallback"]
    input_hash: str


@dataclass(frozen=True)
class _FactItem:
    id: str
    heading: str
    fact_line: str
    prompt_fact: str


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _planet_fact(key: str, data: dict[str, Any], *, include_house: bool) -> _FactItem:
    name = PLANET_RU.get(key, key)
    sign = sign_ru(data.get("sign_ru") or data.get("sign"))
    house = data.get("house") if include_house else None
    house_label = f", {_ROMAN_HOUSES.get(int(house), house)} дом" if house else ""
    heading = f"{name} в {sign_ru(sign, 'prep')}{house_label}"
    degree = _safe_float(data.get("sign_degree"))
    motion = "ретроградная" if data.get("retrograde") else "директная"
    if key not in {"moon", "venus"}:
        motion = "ретроградный" if data.get("retrograde") else "директный"
    fact_line = f"Положение: {degree:.2f}° внутри знака; {motion}."
    prompt_fact = (
        f"{name}: знак {sign}; градус внутри знака {degree:.2f}; "
        f"дом {house if house else 'не используется'}; ретроградность {bool(data.get('retrograde'))}"
    )
    return _FactItem(key, heading, fact_line, prompt_fact)


def _build_fact_groups(
    *,
    sun_sign: str,
    moon_sign: str,
    ascendant_sign: str | None,
    planets: dict[str, dict[str, Any]],
    houses: list[dict[str, Any]],
    aspects: list[dict[str, Any]],
    nodes: dict[str, dict[str, Any]] | None,
    birth_time_known: bool,
) -> dict[str, list[_FactItem]]:
    asc = ascendant_sign if birth_time_known else None
    foundation_parts = [f"Солнце — {sun_sign}", f"Луна — {moon_sign}"]
    if asc:
        foundation_parts.append(f"Асцендент — {asc}")
    core = [
        _FactItem(
            "foundation",
            "Основа личности",
            "; ".join(foundation_parts) + ".",
            "; ".join(foundation_parts),
        ),
        _FactItem(
            "dominants",
            "Главные темы карты",
            "",
            "Сопоставь повторяющиеся темы всех переданных положений, не называя их заново",
        ),
    ]

    node_rows: list[str] = []
    for key, label in (
        ("true_north_lunar_node", "Северный узел"),
        ("mean_north_lunar_node", "Северный узел"),
        ("true_south_lunar_node", "Южный узел"),
        ("mean_south_lunar_node", "Южный узел"),
    ):
        data = (nodes or {}).get(key)
        if not data or any(row.startswith(label) for row in node_rows):
            continue
        sign = sign_ru(data.get("sign_ru") or data.get("sign"))
        house = data.get("house") if birth_time_known else None
        suffix = f", {_ROMAN_HOUSES.get(int(house), house)} дом" if house else ""
        node_rows.append(f"{label}: {sign}{suffix}")
    if node_rows:
        core.append(
            _FactItem(
                "lunar_nodes",
                "Лунные узлы",
                "; ".join(node_rows) + ".",
                "; ".join(node_rows),
            )
        )

    core.extend(
        [
            _FactItem(
                "synthesis",
                "Заключительный синтез",
                "",
                "Собери главные сильные стороны, внутренние противоречия и общий вектор карты",
            ),
            _FactItem(
                "recommendations",
                "Практические ориентиры",
                "",
                "Дай конкретные, негарантирующие рекомендации для самонаблюдения",
            ),
        ]
    )

    planet_items = [
        _planet_fact(key, planets[key], include_house=birth_time_known)
        for key in _PLANET_ORDER
        if key in planets
    ]

    occupied: dict[int, list[str]] = {}
    if birth_time_known:
        for key in _PLANET_ORDER:
            data = planets.get(key) or {}
            if data.get("house"):
                occupied.setdefault(int(data["house"]), []).append(PLANET_RU.get(key, key))
    house_items: list[_FactItem] = []
    if birth_time_known:
        for house in sorted(houses, key=lambda item: int(item.get("number") or 99)):
            number = int(house.get("number") or 0)
            if not 1 <= number <= 12:
                continue
            sign = sign_ru(house.get("sign_ru") or house.get("sign"))
            degree = _safe_float(house.get("degree")) % 30
            planets_here = occupied.get(number, [])
            occupied_text = ", ".join(planets_here) if planets_here else "нет классических планет"
            heading = f"{_ROMAN_HOUSES[number]} дом: куспид в {sign_ru(sign, 'prep')}"
            fact_line = f"Куспид: {degree:.2f}° внутри знака; планеты: {occupied_text}."
            house_items.append(
                _FactItem(
                    str(number),
                    heading,
                    fact_line,
                    f"Дом {number}; знак куспида {sign}; планеты внутри: {occupied_text}",
                )
            )

    aspect_items: list[_FactItem] = []
    seen_aspects: set[str] = set()
    for aspect in aspects:
        p1 = str(aspect.get("p1") or "").lower()
        p2 = str(aspect.get("p2") or "").lower()
        kind = str(aspect.get("aspect") or "").lower()
        if p1 not in PLANET_RU or p2 not in PLANET_RU or kind not in _ASPECT_RU:
            continue
        aspect_id = f"{p1}__{p2}__{kind}"
        if aspect_id in seen_aspects:
            continue
        seen_aspects.add(aspect_id)
        orb = _safe_float(aspect.get("orb"))
        heading = (
            f"{PLANET_RU[p1]} — {_ASPECT_RU[kind]} — {PLANET_RU[p2]}, "
            f"орб {orb:.2f}°"
        )
        aspect_items.append(
            _FactItem(
                aspect_id,
                heading,
                "",
                f"{PLANET_RU[p1]}; {_ASPECT_RU[kind]}; {PLANET_RU[p2]}; орб {orb:.2f}",
            )
        )

    return {
        "core": core,
        "planets": planet_items,
        "houses": house_items,
        "aspects": aspect_items,
    }


def build_natal_report_input_hash(
    *,
    sun_sign: str,
    moon_sign: str,
    ascendant_sign: str | None,
    planets: dict[str, Any],
    houses: list[dict[str, Any]],
    aspects: list[dict[str, Any]],
    gender: str | None,
    nodes: dict[str, Any] | None = None,
) -> str:
    """Stable invalidation key for the durable report, independent of provider."""
    payload = {
        "schema_version": NATAL_REPORT_SCHEMA_VERSION,
        "prompt_version": NATAL_REPORT_PROMPT_VERSION,
        "content_version": CONTENT_VERSION,
        "gender": gender,
        "sun_sign": sun_sign,
        "moon_sign": moon_sign,
        "ascendant_sign": ascendant_sign,
        "planets": planets,
        "houses": houses if ascendant_sign else [],
        "aspects": aspects,
        "nodes": nodes or {},
    }
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _tool_schema(expected_count: int) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "items": {
                "type": "array",
                "minItems": expected_count,
                "maxItems": expected_count,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "narrative": {"type": "string"},
                    },
                    "required": ["id", "narrative"],
                },
            }
        },
        "required": ["items"],
    }


def _gender_instruction(gender: str | None) -> str:
    if gender == "male":
        return "Обращайся на «вы» и согласуй формы в мужском роде."
    if gender == "female":
        return "Обращайся на «вы» и согласуй формы в женском роде."
    return "Обращайся на «вы», используя нейтральные формулировки."


def _group_prompt(
    group: str,
    facts: list[_FactItem],
    gender: str | None,
    *,
    repair_errors: dict[str, list[str]] | None = None,
) -> str:
    targets = [
        {"id": item.id, "calculated_fact": item.prompt_fact}
        for item in facts
    ]
    target_lengths = {
        "core": "foundation 130–190 слов, dominants 90–140, synthesis 180–260, recommendations 100–160; lunar_nodes 80–120",
        "planets": "80–120 слов на каждый элемент",
        "houses": "70–100 слов на каждый элемент",
        "aspects": "90–130 слов на каждый элемент",
    }[group]
    repair = ""
    if repair_errors:
        repair = (
            "\nЭто локальный повтор только для отклонённых элементов. Исправь ошибки:\n"
            + json.dumps(repair_errors, ensure_ascii=False, indent=2)
        )
    return f"""Ты пишешь самостоятельные смысловые интерпретации для натального отчёта.

Группа: {group}.
{_gender_instruction(gender)}

Backend уже рассчитает и напечатает точные заголовки, планеты, знаки, дома,
градусы и аспекты. В narrative НЕ повторяй и НЕ переименовывай эти факты:
пиши «это положение», «эта сфера», «эта связка», «такой внутренний мотив».
Не добавляй других планет, знаков, домов, градусов или аспектов.

Для каждого входного id верни ровно один содержательный narrative.
Требуемый объём: {target_lengths}.
Текст по-русски, без markdown, заголовков и списков. Каждая интерпретация
должна описывать возможные проявления, сильную сторону, риск и практический
ориентир. Это символическая интерпретация, а не факт биографии.

Запрещены диагнозы, утверждения о семье/детстве/зависимостях/прошлых жизнях,
гарантированные события, запугивание и финансовые обещания.

Входные элементы:
{json.dumps(targets, ensure_ascii=False, indent=2)}
{repair}

Вызови submit_{group} ровно один раз. Верни только items с исходными id и narrative."""


def _extract_response(message: Any, tool_name: str) -> _NarrativeResponse:
    for block in getattr(message, "content", None) or []:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == tool_name:
            return _NarrativeResponse.model_validate(getattr(block, "input", None))
    for block in getattr(message, "content", None) or []:
        raw = getattr(block, "text", None)
        if isinstance(raw, str) and raw.strip():
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I)
            return _NarrativeResponse.model_validate_json(cleaned)
    raise ValueError(f"LLM did not return {tool_name}")


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def _quality_errors(
    group: str,
    item_id: str,
    narrative: str,
    context: AstroFactContext,
) -> list[str]:
    text = " ".join(str(narrative or "").split()).strip()
    errors: list[str] = []
    bounds = {
        "planets": (50, 180),
        "houses": (40, 160),
        "aspects": (50, 190),
    }
    if group == "core":
        bounds_for_core = {
            "foundation": (80, 260),
            "dominants": (60, 220),
            "lunar_nodes": (50, 180),
            "synthesis": (110, 360),
            "recommendations": (60, 240),
        }
        minimum, maximum = bounds_for_core.get(item_id, (60, 260))
    else:
        minimum, maximum = bounds[group]
    words = _word_count(text)
    if words < minimum:
        errors.append(f"too short: {words} words, minimum {minimum}")
    if words > maximum:
        errors.append(f"too long: {words} words, maximum {maximum}")
    if text and text[-1] not in ".!?…»”":
        errors.append("text is not complete")
    letters = _LETTER_RE.findall(text)
    if letters and len(_CYRILLIC_RE.findall(text)) / len(letters) < 0.65:
        errors.append("text is not predominantly Russian")
    if _FACT_RE.search(text):
        errors.append("narrative repeats or invents an astrology fact")
    errors.extend(validate_generated_text(text, context))
    return list(dict.fromkeys(errors))


def _fallback_narrative(group: str, item_id: str, ordinal: int = 1) -> str:
    common = (
        "Интерпретация описывает возможный внутренний сценарий, а не неизменную "
        "черту или заранее определённое событие. Полезно наблюдать, в каких "
        "ситуациях эта тема помогает действовать увереннее, а где заставляет "
        "повторять привычную реакцию. Сильная сторона раскрывается через "
        "осознанный выбор и проверку выводов на собственном опыте. Практический "
        "ориентир — замечать повторяющийся мотив, отделять импульс от решения и "
        "оставлять себе несколько вариантов действия."
        " Это развлекательная интерпретация, не медицинский, финансовый или "
        "фактический прогноз."
        f" Практический фокус этого раздела {ordinal}: записать одно наблюдение "
        "и проверить его в нескольких разных ситуациях."
    )
    if group == "core" and item_id == "synthesis":
        return common + " Общий рисунок лучше использовать как карту вопросов для дальнейшего самонаблюдения."
    if group == "core" and item_id == "recommendations":
        return common + " Выбирайте один небольшой проверяемый шаг вместо категоричного вывода о себе."
    return common


async def _call_group(
    client: Any,
    group: str,
    facts: list[_FactItem],
    gender: str | None,
    repair_errors: dict[str, list[str]] | None = None,
) -> _NarrativeResponse:
    tool_name = f"submit_{group}"
    max_tokens = max(1200, min(4500, len(facts) * 260 + 600))
    async with llm_semaphore, LLMLimiter(max_tokens):
        message = await client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=max_tokens,
            temperature=0.5,
            messages=[
                {
                    "role": "user",
                    "content": _group_prompt(
                        group,
                        facts,
                        gender,
                        repair_errors=repair_errors,
                    ),
                }
            ],
            tools=[
                {
                    "name": tool_name,
                    "description": "Return validated narrative items for this natal report group.",
                    "input_schema": _tool_schema(len(facts)),
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
        )
    return _extract_response(message, tool_name)


async def _generate_group(
    client: Any,
    group: str,
    facts: list[_FactItem],
    gender: str | None,
    context: AstroFactContext,
) -> tuple[list[ReportItem], bool]:
    if not facts:
        return [], False
    expected = {item.id: item for item in facts}
    accepted: dict[str, str] = {}
    errors: dict[str, list[str]] = {item.id: ["missing"] for item in facts}

    for attempt in range(2):
        requested = [expected[item_id] for item_id in expected if item_id not in accepted]
        try:
            response = await _call_group(
                client,
                group,
                requested,
                gender,
                repair_errors=errors if attempt else None,
            )
        except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
            log.warning(
                "natal_report.group_response_invalid",
                group=group,
                attempt=attempt + 1,
                error=str(exc)[:300],
            )
            errors = {item.id: ["malformed structured response"] for item in requested}
            continue
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "natal_report.group_call_failed",
                group=group,
                attempt=attempt + 1,
                error=str(exc)[:300],
            )
            errors = {item.id: ["provider request failed"] for item in requested}
            continue

        candidates: dict[str, list[str]] = {}
        for item in response.items:
            cleaned = sanitize_ru_text(item.narrative)
            candidates.setdefault(item.id, []).append(" ".join(cleaned.split()).strip())

        next_errors: dict[str, list[str]] = {}
        seen_texts = {" ".join(value.lower().split()) for value in accepted.values()}
        for fact in requested:
            values = candidates.get(fact.id, [])
            if len(values) != 1:
                next_errors[fact.id] = [
                    "missing item" if not values else "duplicate item id"
                ]
                continue
            narrative = values[0]
            item_errors = _quality_errors(group, fact.id, narrative, context)
            normalized = " ".join(narrative.lower().split())
            if normalized in seen_texts:
                item_errors.append("duplicate narrative")
            if item_errors:
                next_errors[fact.id] = item_errors
                continue
            accepted[fact.id] = narrative
            seen_texts.add(normalized)
        errors = next_errors
        if not errors:
            break

    used_fallback = False
    output: list[ReportItem] = []
    for ordinal, fact in enumerate(facts, start=1):
        stored_narrative = accepted.get(fact.id)
        fallback = stored_narrative is None
        if stored_narrative is None:
            used_fallback = True
            final_narrative = _fallback_narrative(group, fact.id, ordinal)
            log.error(
                "natal_report.item_fallback",
                group=group,
                item_id=fact.id,
                errors=errors.get(fact.id),
            )
        else:
            final_narrative = stored_narrative
        output.append(
            ReportItem(
                id=fact.id,
                heading=fact.heading,
                fact_line=fact.fact_line,
                narrative=final_narrative,
                fallback=fallback,
            )
        )
    return output, used_fallback


def render_natal_report_text(payload: dict[str, Any] | NatalReportPayload) -> str:
    report = (
        payload
        if isinstance(payload, NatalReportPayload)
        else NatalReportPayload.model_validate(payload)
    )
    chunks: list[str] = []
    core_by_id = {item.id: item for item in report.core}

    def append_item(item: ReportItem) -> None:
        body = "\n".join(part for part in (item.fact_line, item.narrative) if part)
        chunks.append(f"**{item.heading}**\n{body}")

    for item_id in ("foundation", "dominants"):
        if item := core_by_id.get(item_id):
            append_item(item)
    for item in report.planets:
        append_item(item)
    for item in report.houses:
        append_item(item)
    if item := core_by_id.get("lunar_nodes"):
        append_item(item)
    for item in report.aspects:
        append_item(item)
    for item_id in ("synthesis", "recommendations"):
        if item := core_by_id.get(item_id):
            append_item(item)
    return "\n\n".join(chunks).strip()


def render_natal_core_text(payload: dict[str, Any] | NatalReportPayload) -> str:
    report = (
        payload
        if isinstance(payload, NatalReportPayload)
        else NatalReportPayload.model_validate(payload)
    )
    chunks: list[str] = []
    for item in report.core:
        body = "\n".join(part for part in (item.fact_line, item.narrative) if part)
        chunks.append(f"**{item.heading}**\n{body}")
    return "\n\n".join(chunks).strip()


def report_descriptions(payload: dict[str, Any] | NatalReportPayload) -> dict[str, Any]:
    report = (
        payload
        if isinstance(payload, NatalReportPayload)
        else NatalReportPayload.model_validate(payload)
    )

    def short(text: str) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return " ".join(sentences[:2]).strip()

    return {
        "_version": NATAL_REPORT_SCHEMA_VERSION,
        "planets": {
            item.id: {"short": short(item.narrative), "full": item.narrative}
            for item in report.planets
        },
        "houses": {
            item.id: {"short": short(item.narrative), "full": item.narrative}
            for item in report.houses
        },
        "aspects": [
            {
                "p1": item.id.split("__", 2)[0],
                "p2": item.id.split("__", 2)[1],
                "type": item.id.split("__", 2)[2],
                "short": short(item.narrative),
                "full": item.narrative,
            }
            for item in report.aspects
            if len(item.id.split("__", 2)) == 3
        ],
    }


async def generate_natal_report(
    *,
    sun_sign: str,
    moon_sign: str,
    ascendant_sign: str | None,
    planets: dict[str, dict[str, Any]],
    houses: list[dict[str, Any]],
    aspects: list[dict[str, Any]],
    api_key: str,
    gender: str | None = None,
    nodes: dict[str, dict[str, Any]] | None = None,
) -> GeneratedNatalReport:
    """Generate one durable report via 4 parallel batches (3 for date-only)."""
    birth_time_known = ascendant_sign is not None
    groups = _build_fact_groups(
        sun_sign=sun_sign,
        moon_sign=moon_sign,
        ascendant_sign=ascendant_sign,
        planets=planets,
        houses=houses if birth_time_known else [],
        aspects=aspects,
        nodes=nodes,
        birth_time_known=birth_time_known,
    )
    context = AstroFactContext.from_chart(
        planets=planets,
        aspects=aspects,
        birth_time_known=birth_time_known,
    )
    client = create_llm_client(api_key)
    group_names = ["core", "planets", "aspects"]
    if birth_time_known:
        group_names.insert(2, "houses")
    results = await asyncio.gather(
        *(
            _generate_group(client, name, groups[name], gender, context)
            for name in group_names
        )
    )
    generated = dict(zip(group_names, results, strict=True))
    used_fallback = any(result[1] for result in results)
    report = NatalReportPayload(
        chart_mode="full" if birth_time_known else "date_only",
        core=generated["core"][0],
        planets=generated["planets"][0],
        houses=generated.get("houses", ([], False))[0],
        aspects=generated["aspects"][0],
        used_fallback=used_fallback,
    )
    payload = report.model_dump(mode="json")
    text = render_natal_report_text(report)
    input_hash = build_natal_report_input_hash(
        sun_sign=sun_sign,
        moon_sign=moon_sign,
        ascendant_sign=ascendant_sign,
        planets=planets,
        houses=houses,
        aspects=aspects,
        gender=gender,
        nodes=nodes,
    )
    status: Literal["ready", "ready_with_fallback"] = (
        "ready_with_fallback" if used_fallback else "ready"
    )
    log.info(
        "natal_report.generated",
        chart_mode=report.chart_mode,
        planets=len(report.planets),
        houses=len(report.houses),
        aspects=len(report.aspects),
        used_fallback=used_fallback,
        words=_word_count(text),
    )
    return GeneratedNatalReport(payload, text, status, input_hash)
