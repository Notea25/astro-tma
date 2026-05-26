"""LLM-backed personal narrative for a Destiny Matrix reading.

Generates a 7-section warm Russian portrait (~700 words total) from the
computed matrix numbers. Cached forever per reading_id in
destiny_matrix_interpretations.

Used by the /destiny-matrix/interpretation endpoint — never raises on
LLM failure (caller gets either real text or a generic fallback).
"""

from __future__ import annotations

import json
import re
from typing import Any

from core.logging import get_logger
from services.destiny_matrix.arcana_names import ARCANA_NAMES_RU
from services.llm_utils import first_text_block

log = get_logger(__name__)

_MODEL = "claude-haiku-4-5-20251001"

SECTION_KEYS = (
    "who_you_are",
    "mission",
    "money",
    "love",
    "health",
    "karma",
    "advice",
)

SECTION_LABELS_RU = {
    "who_you_are": "Кто вы",
    "mission": "Ваше предназначение",
    "money": "Деньги и реализация",
    "love": "Любовь и отношения",
    "health": "Тело и здоровье",
    "karma": "Карма и род",
    "advice": "Совет",
}


_SYSTEM_PROMPT = """Ты — астролог-практик с глубоким знанием Матрицы Судьбы и арканов Таро.
Твоя задача — написать тёплый, поддерживающий и конкретный персональный
разбор матрицы пользователя.

Стиль:
- Обращайся на «ты», тепло, без формализма.
- Избегай канцеляризма («в данном контексте», «представляется важным»).
- Каждая секция — связный текст, а не список значений арканов.
- Не давай медицинских/юридических/инвестиционных советов.
- Не предсказывай конкретные события и даты.
- Не используй фразы типа "звёзды говорят", "судьба предначертала" —
  говори как наставник, а не предсказатель.

Длина: 700-900 слов всего, по ~100 слов на каждую из 7 секций.

Структура ответа — строго JSON:
{
  "who_you_are": "...",
  "mission": "...",
  "money": "...",
  "love": "...",
  "health": "...",
  "karma": "...",
  "advice": "..."
}"""


def _name(num: int) -> str:
    return ARCANA_NAMES_RU.get(num, f"Аркан {num}")


def _build_user_prompt(positions: dict[str, Any], first_name: str | None) -> str:
    """Compose the user-facing payload — the numbers + arcana names that
    feed into the LLM. Numbers cited explicitly so the model anchors its
    interpretation to the actual computed matrix rather than free-styling."""

    name_line = f"Имя: {first_name}\n" if first_name else ""

    e = positions["E"]
    d = positions["D"]
    a, b, c = positions["A"], positions["B"], positions["C"]
    f, g, h, i = positions["F"], positions["G"], positions["H"], positions["I"]

    lines = [
        f"- Центр (главная задача жизни): аркан {e} — {_name(e)}",
        f"- Личность (Я в этой жизни): {d} — {_name(d)}",
        f"- Энергия дня (что получили при рождении): {a} — {_name(a)}",
        f"- Энергия месяца (эмоциональный план): {b} — {_name(b)}",
        f"- Энергия года (опыт рода): {c} — {_name(c)}",
        f"- Малый квадрат (отношения и социум): F={f}, G={g}, H={h}, I={i}",
        f"- Линия Земли (тело, материя): {positions['line_earth']} — {_name(positions['line_earth'])}",
        f"- Линия Неба (миссия, дух): {positions['line_sky']} — {_name(positions['line_sky'])}",
        f"- Личное предназначение (до ~40 лет): {positions['purpose_personal']} — {_name(positions['purpose_personal'])}",
        f"- Социальное предназначение (40-60 лет): {positions['purpose_social']} — {_name(positions['purpose_social'])}",
        f"- Духовное предназначение (после 60): {positions['purpose_spiritual']} — {_name(positions['purpose_spiritual'])}",
        f"- Линия денег: {positions['line_money']}",
        f"- Линия любви: {positions['line_love']}",
        f"- Линия здоровья: {positions['line_health']}",
        f"- Линия кармы: {positions['line_karma']}",
        f"- Линия миссии: {positions['line_mission']}",
        f"- Кармический хвост (мужской род): {positions['karmic_tail_male']} — {_name(positions['karmic_tail_male'])}",
        f"- Кармический хвост (женский род): {positions['karmic_tail_female']} — {_name(positions['karmic_tail_female'])}",
    ]

    return f"""{name_line}Матрица Судьбы — ключевые позиции:

{chr(10).join(lines)}

Напиши персональный разбор по 7 секциям согласно системному промпту."""


def _extract_json(raw: str) -> dict[str, str]:
    """Strip code fences and return parsed dict. Tolerant to common LLM
    formatting mistakes."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?\s*```\s*$", "", cleaned).strip()
    # Find outermost JSON braces if there's prose leading/trailing.
    if not cleaned.startswith("{"):
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)
    return json.loads(cleaned)


def _fallback_sections(positions: dict[str, Any]) -> dict[str, str]:
    """Static fallback if LLM is unavailable. Generic, but matches the
    actual matrix numbers so user still sees their personal data."""
    e_name = _name(positions["E"])
    d_name = _name(positions["D"])
    return {
        "who_you_are": (
            f"Ваша личность тяготеет к энергии {d_name}. Это про то, как вы "
            "проявляетесь в обычной жизни и какой образ себя несёте в мир. "
            "Полная интерпретация этой позиции будет добавлена в следующем "
            "обновлении приложения."
        ),
        "mission": (
            f"Центральная задача вашей жизни связана с энергией {e_name}. "
            "Это та область, где вам важно проявить себя глубже всего."
        ),
        "money": "Описание финансового канала готовится.",
        "love": "Описание линии отношений готовится.",
        "health": "Описание линии здоровья готовится.",
        "karma": "Описание родовых программ готовится.",
        "advice": "Доверьтесь своему центру и не торопите главные перемены.",
    }


async def generate_interpretation(
    positions: dict[str, Any],
    first_name: str | None,
    api_key: str | None,
) -> tuple[dict[str, str], str]:
    """Returns (sections_dict, model_name_used). Falls back to static text
    if api_key is missing or LLM call fails — never raises."""
    if not api_key:
        log.warning("destiny_matrix.interp.no_api_key")
        return _fallback_sections(positions), "fallback"

    import anthropic

    user_prompt = _build_user_prompt(positions, first_name)
    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model=_MODEL,
            max_tokens=2000,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = first_text_block(message.content).strip()
        parsed = _extract_json(raw)
        # Ensure every section is present — fill blanks with a stub
        sections: dict[str, str] = {}
        for key in SECTION_KEYS:
            text = str(parsed.get(key, "")).strip()
            sections[key] = text if text else "Описание скоро появится."
        return sections, _MODEL
    except Exception as e:  # noqa: BLE001
        log.error("destiny_matrix.interp.failed", error=str(e)[:200])
        return _fallback_sections(positions), "fallback"
