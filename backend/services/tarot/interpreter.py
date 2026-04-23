"""
LLM-based Celtic Cross narrative interpretation via Anthropic Claude.

Produces one coherent story across all 10 positions — each subsequent card
is explained in the context of previous cards already drawn.

Result is returned as structured data (positions + summary). The caller
is expected to cache by reading_id (deterministic per reading).
"""

from __future__ import annotations

import json
import re
from typing import Any

from core.logging import get_logger

log = get_logger(__name__)


_POSITION_NAMES: dict[int, str] = {
    1:  "Суть — текущее состояние, центральный вопрос",
    2:  "Препятствие — то, что мешает или противодействует",
    3:  "Идеал — осознанная цель, лучший возможный исход",
    4:  "Основа — подсознательный фундамент ситуации",
    5:  "Прошлое — уходящие события, ещё влияющие на настоящее",
    6:  "Будущее — ближайшая фаза развития",
    7:  "Вы сами — ваше отношение и самовосприятие",
    8:  "Окружение — внешние влияния, люди и обстоятельства",
    9:  "Надежды и страхи — то, чего желаете или боитесь",
    10: "Исход — вероятное разрешение, если энергии сохранятся",
}


def _build_prompt(cards: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for i, c in enumerate(cards, start=1):
        orient = "перевёрнута" if c.get("reversed") else "прямая"
        lines.append(
            f"Позиция {i} ({_POSITION_NAMES[i]}):\n"
            f"  Карта: {c['name_ru']} ({orient})\n"
            f"  Ключевые слова: {', '.join(c.get('keywords_ru') or [])}"
        )
    cards_block = "\n\n".join(lines)

    return f"""Ты — опытный таролог, делающий расклад «Кельтский крест». Отвечай только на русском языке.

Расклад из 10 карт:

{cards_block}

Составь интерпретацию в виде ОДНОЙ цельной истории, где каждая следующая карта читается с учётом предыдущих. Для позиции 1 опиши просто её значение в контексте позиции. Начиная с позиции 2, в каждой интерпретации ЯВНО связывай карту с тем, что уже было открыто (минимум одна отсылка к карте из предыдущих позиций).

Верни СТРОГО валидный JSON без markdown-обёрток, следующей формы:
{{
  "positions": [
    {{"n": 1, "narrative": "<2–4 предложения, что эта карта значит в этой позиции>"}},
    {{"n": 2, "narrative": "<2–4 предложения, связываем с позицией 1>"}},
    ...
    {{"n": 10, "narrative": "<2–4 предложения, итоговое разрешение с учётом всего расклада>"}}
  ],
  "summary": "<120–180 слов: общий вывод и практические предложения на основе всего расклада>"
}}

Требования:
- Пиши тепло, образно, конкретно. Второе лицо («вы», «ваш»).
- Избегай банальностей и общих фраз.
- Не повторяй описание карты — раскрывай её смысл именно в этой позиции и в контексте уже выпавших карт.
- Summary должен синтезировать историю, а не пересказывать позиции."""


def _extract_json(text: str) -> dict[str, Any]:
    """Strip potential code fences and return parsed JSON."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    # Fallback: find first { and last } if stray text surrounds it
    if not cleaned.startswith("{"):
        l = cleaned.find("{")
        r = cleaned.rfind("}")
        if l >= 0 and r > l:
            cleaned = cleaned[l : r + 1]
    return json.loads(cleaned)


async def generate_celtic_cross_interpretation(
    cards: list[dict[str, Any]],
    api_key: str,
) -> dict[str, Any]:
    """
    Call Claude to generate a Celtic Cross narrative interpretation.

    `cards` must be 10 dicts with at least: name_ru, reversed, keywords_ru.
    Returns dict: {"positions": [...10...], "summary": str}.
    Raises on API / JSON error — caller should handle.
    """
    import anthropic

    if len(cards) != 10:
        raise ValueError(f"expected 10 cards, got {len(cards)}")

    prompt = _build_prompt(cards)

    client = anthropic.AsyncAnthropic(api_key=api_key)
    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2400,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text
    parsed = _extract_json(text)

    # Normalise: ensure positions are sorted 1..10 and contain expected keys
    positions_raw = parsed.get("positions", [])
    by_n = {int(p["n"]): str(p.get("narrative", "")).strip() for p in positions_raw}
    positions = [
        {"n": n, "narrative": by_n.get(n, "")}
        for n in range(1, 11)
    ]
    summary = str(parsed.get("summary", "")).strip()

    log.info(
        "tarot.interpret.done",
        chars_summary=len(summary),
        pos_filled=sum(1 for p in positions if p["narrative"]),
    )
    return {"positions": positions, "summary": summary}
