"""
Provider-neutral LLM-based tarot narrative interpretation.

Supports all 4 spread types: three_card, celtic_cross, week, relationship.
Each subsequent card is explained in the context of previous cards to build
one coherent story, plus a final summary with practical suggestions.

Result is structured data (positions + summary), cached by reading_id.
"""

from __future__ import annotations

import json
import re
from typing import Any

from core.logging import get_logger
from core.settings import settings
from services.llm_client import create_llm_client
from services.llm_utils import first_text_block

log = get_logger(__name__)


# ── Per-spread metadata ───────────────────────────────────────────────────────

_SPREADS: dict[str, dict[str, Any]] = {
    "three_card": {
        "title": "Прошлое · Настоящее · Будущее",
        "intro": (
            "Классический трёхкарточный расклад: корни ситуации, "
            "текущее состояние и направление движения."
        ),
        "positions": {
            1: "Прошлое — события и энергии, приведшие к текущей ситуации",
            2: "Настоящее — актуальное состояние, ключевые силы момента",
            3: "Будущее — вероятное развитие при сохранении траектории",
        },
    },
    "celtic_cross": {
        "title": "Кельтский крест",
        "intro": (
            "Глубокий 10-карточный расклад. Позиции 1–6 — Крест, "
            "исследует текущую реальность. Позиции 7–10 — Посох, "
            "раскрывает путь к разрешению."
        ),
        "positions": {
            1: "Суть — текущее состояние, центральный вопрос",
            2: "Препятствие — то, что мешает или противодействует",
            3: "Сознание — осознанная цель, мысли и видимый ориентир",
            4: "Подсознание — фундамент ситуации и скрытые причины",
            5: "Прошлое — уходящие события, ещё влияющие на настоящее",
            6: "Будущее — ближайшая фаза развития",
            7: "Я сам — ваше отношение и самовосприятие",
            8: "Другие — внешние влияния, люди и обстоятельства",
            9: "Надежды и опасения — то, чего желаете или боитесь",
            10: "Исход — вероятное разрешение, если энергии сохранятся",
        },
    },
    "week": {
        "title": "Карта на каждый день",
        "intro": (
            "Энергетический рисунок ближайших семи дней: где лёгкость, "
            "где сопротивление, на что направить внимание."
        ),
        "positions": {
            1: "Луна — эмоциональный тон ближайшего периода",
            2: "Марс — где потребуется действие и смелость",
            3: "Меркурий — мысли, разговоры и важные решения",
            4: "Юпитер — рост, поддержка и возможности",
            5: "Венера — отношения, удовольствие и ценности",
            6: "Сатурн — ответственность, границы и урок недели",
            7: "Солнце — итоговая ясность и главный фокус",
        },
    },
    "relationship": {
        "title": "Расклад на отношения",
        "intro": (
            "Пять карт показывают позиции обоих партнёров, качество связи, "
            "главный вызов и потенциал развития отношений."
        ),
        "positions": {
            1: "Вы — ваша роль и состояние в отношениях",
            2: "Партнёр — позиция и состояние другого человека",
            3: "Связь — качество и природа того, что между вами",
            4: "Вызов — главное препятствие или напряжение",
            5: "Потенциал — куда могут развиться отношения",
        },
    },
}


# ── Prompt construction ───────────────────────────────────────────────────────

def _build_prompt(
    spread_type: str, cards: list[dict[str, Any]], gender: str | None = None
) -> str:
    meta = _SPREADS[spread_type]
    positions_meta: dict[int, str] = meta["positions"]
    expected_n = len(positions_meta)

    lines: list[str] = []
    for i, c in enumerate(cards, start=1):
        orient = "перевёрнута" if c.get("reversed") else "прямая"
        lines.append(
            f"Позиция {i} ({positions_meta[i]}):\n"
            f"  card_id: {c['card_id']}\n"
            f"  Карта: {c['name_ru']} ({orient})\n"
            f"  Базовое значение в этой ориентации: {c.get('meaning_ru', '')}\n"
            f"  Ключевые слова: {', '.join(c.get('keywords_ru') or [])}"
        )
    cards_block = "\n\n".join(lines)

    context_clause = (
        "Для позиции 1 опиши просто её значение в контексте позиции. "
        "Начиная с позиции 2, в каждой интерпретации ЯВНО связывай карту "
        "с тем, что уже было открыто (минимум одна отсылка к карте из предыдущих позиций)."
    ) if expected_n > 1 else (
        "Это одна карта — раскрой её значение в контексте позиции."
    )

    json_positions = ",\n    ".join(
        f'{{"n": {i}, "card_id": {cards[i - 1]["card_id"]}, '
        f'"reversed": {str(bool(cards[i - 1].get("reversed"))).lower()}, '
        '"narrative": "<2–3 предложения>"}'
        for i in range(1, expected_n + 1)
    )

    gender_directive = ""
    if gender == "male":
        gender_directive = (
            "\nПол читателя: МУЖЧИНА. Все прилагательные, причастия и "
            "глаголы прошедшего времени — в МУЖСКОМ роде («вы внимательный», "
            "«вы сделали выбор», «настоящий»). Если карта говорит о партнёре, "
            "это партнёрша (или партнёр — пол партнёра неизвестен, формулируй нейтрально).\n"
        )
    elif gender == "female":
        gender_directive = (
            "\nПол читателя: ЖЕНЩИНА. Все прилагательные, причастия и "
            "глаголы прошедшего времени — в ЖЕНСКОМ роде («вы внимательная», "
            "«вы сделали выбор» с дальнейшими женскими формами, «настоящая»). "
            "Если карта говорит о партнёре, не предполагай его пол без оснований.\n"
        )

    return f"""Ты делаешь расклад «{meta["title"]}» для популярного приложения. Читатели — обычные люди, не тарологи и не эзотерики.
{gender_directive}
{meta["intro"]}

Расклад ({expected_n} карт):

{cards_block}

Составь интерпретацию в виде ОДНОЙ цельной истории. {context_clause}

Верни СТРОГО валидный JSON без markdown-обёрток, следующей формы:
{{
  "positions": [
    {json_positions}
  ],
  "summary": "<80–120 слов: финальное зеркало по всему раскладу — точное наблюдение или открытый вопрос, с которым читатель уйдёт думать. БЕЗ прямых советов «сделайте X».>"
}}

КАК ПИСАТЬ — это «ТЕКСТ НА ПОДУМАТЬ», не инструкция:
- Карты НЕ ДАЮТ указаний «сделайте X». Они НАЗЫВАЮТ то, что происходит в жизни и внутри читателя, ставят зеркало — а ответ читатель ищет в себе сам.
- Будь конкретным В НАБЛЮДЕНИЯХ, а не в советах. Вместо «обратите внимание на близких» — «эта карта в прошлом указывает на разговор, который вы так и не довели до конца — внутри он всё ещё открыт». Вместо «следите за финансами» — «эта карта говорит о том, за что вы держитесь не из нужды, а из страха потерять».
- ЗАПРЕЩЕНО:
  • Пустые мотивационные банальности и хеджирование: «всё будет хорошо», «доверьтесь процессу», «поверьте в себя — и получится», «вселенная подскажет», «вы сами знаете ответ», «всё в ваших руках», «прислушайтесь к интуиции».
  • Прямые команды и пошаговые инструкции: «позвоните маме», «сделайте список», «откажитесь от X», «начните вести дневник». Это не текст-инструкция — это текст для саморефлексии.
  • Эзотерический жаргон: «энергии», «архетипы», «вибрации», «эманации», «послание вселенной», «карты предупреждают».
  • Пересказ описания карты вместо её смысла именно в этой позиции.
- Строго сохраняй ориентацию: прямая карта трактуется по прямому базовому значению, перевёрнутая — по перевёрнутому. Не меняй ориентацию и не противоречь указанному значению.
- Не утверждай как факт события биографии, состояние семьи, зависимость или диагноз. Будущее — только вероятный сценарий, не гарантия.
- Используй конкретные образы обычной жизни: невысказанный разговор; решение, отложенное «на потом»; роль, которую больше не хочется играть; место, где вы давите на газ, хотя пора снять ногу. Без абстракций.
- Где уместно — задавай вопрос, который читатель задаст сам себе («где вы сейчас держитесь сильнее, чем нужно?», «что вы перестали себе говорить вслух?»). Не больше одного такого вопроса на позицию.
- Связывай карты в одну историю: начиная со 2-й позиции — отсылка к предыдущим.
- Summary (80–120 слов) — это финальное зеркало. Собери историю расклада и закончи её НЕ советом «сделайте X», а одним точным наблюдением или открытым вопросом, с которым читатель уйдёт думать.
- Обращайся на «вы», по-человечески, без официоза и без гуру-тона."""


def _extract_json(text: str) -> dict[str, Any]:
    """Strip potential code fences and return parsed JSON."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    if not cleaned.startswith("{"):
        l = cleaned.find("{")
        r = cleaned.rfind("}")
        if l >= 0 and r > l:
            cleaned = cleaned[l : r + 1]
    return json.loads(cleaned)


# ── Public entry point ────────────────────────────────────────────────────────

def is_supported_spread(spread_type: str) -> bool:
    return spread_type in _SPREADS


def expected_card_count(spread_type: str) -> int:
    return len(_SPREADS[spread_type]["positions"])


async def generate_spread_interpretation(
    spread_type: str,
    cards: list[dict[str, Any]],
    api_key: str,
    gender: str | None = None,
) -> dict[str, Any]:
    """
    Call the configured LLM to generate a narrative interpretation for the spread.

    `cards` must have exactly `expected_card_count(spread_type)` items, each
    a dict with at least: name_ru, reversed, keywords_ru.
    Returns dict: {"positions": [...N...], "summary": str}.
    Raises on API / JSON / count mismatch — caller should handle.

    ``gender`` ('male' / 'female' / None) anchors grammatical forms in the
    output. Caller should record it next to the cached payload so a
    profile change triggers a regen.
    """
    if not is_supported_spread(spread_type):
        raise ValueError(f"unsupported spread: {spread_type!r}")

    expected_n = expected_card_count(spread_type)
    if len(cards) != expected_n:
        raise ValueError(
            f"expected {expected_n} cards for {spread_type}, got {len(cards)}"
        )

    from services.llm_pool import llm_semaphore

    prompt = _build_prompt(spread_type, cards, gender)

    # max_tokens scaled to spread size: ~70 tokens per position (3 sentences)
    # + 200 tokens summary + a safety margin. Caps growth on big spreads
    # (celtic 10 cards) without truncating the smaller ones.
    cap = 600 + expected_n * 180

    from services.astro.fact_context import TarotFactContext, validate_tarot_payload

    client = create_llm_client(api_key)

    async def _call(request_prompt: str) -> dict[str, Any]:
        async with llm_semaphore:
            message = await client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=cap,
                messages=[{"role": "user", "content": request_prompt}],
            )
        return _extract_json(first_text_block(message.content))

    def _safety_errors(payload: dict[str, Any]) -> list[str]:
        return validate_tarot_payload(payload, TarotFactContext.from_cards(cards))

    parsed = await _call(prompt)
    errors = _safety_errors(parsed)
    if errors:
        parsed = await _call(
            prompt + "\n\nПредыдущий ответ отклонён. Исправь:\n- " + "\n- ".join(errors)
        )
        if _safety_errors(parsed):
            parsed = {
                "positions": [
                    {
                        "n": index,
                        "card_id": int(card["card_id"]),
                        "reversed": bool(card.get("reversed")),
                        "narrative": (
                            f"{card['name_ru']} в этой позиции символически отражает "
                            f"тему: {card.get('meaning_ru') or 'самонаблюдение'}. "
                            "Это возможность для размышления, а не фактический прогноз."
                        ),
                    }
                    for index, card in enumerate(cards, start=1)
                ],
                "summary": (
                    "Расклад предлагает сопоставить темы карт с текущей ситуацией. "
                    "Это развлекательная символическая интерпретация, а не "
                    "медицинский, финансовый или фактический прогноз."
                ),
            }

    positions_raw = parsed.get("positions", [])
    by_n = {int(p["n"]): str(p.get("narrative", "")).strip() for p in positions_raw}
    positions = [
        {"n": n, "narrative": by_n.get(n, "")}
        for n in range(1, expected_n + 1)
    ]
    summary = str(parsed.get("summary", "")).strip()

    log.info(
        "tarot.interpret.done",
        spread=spread_type,
        chars_summary=len(summary),
        pos_filled=sum(1 for p in positions if p["narrative"]),
    )
    return {"positions": positions, "summary": summary}


# Backwards compatibility — existing import path in routes/tarot.py
async def generate_celtic_cross_interpretation(
    cards: list[dict[str, Any]],
    api_key: str,
) -> dict[str, Any]:
    return await generate_spread_interpretation("celtic_cross", cards, api_key)
