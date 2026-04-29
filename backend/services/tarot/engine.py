"""
Tarot spread engine.

Responsibility: shuffle deck, pick cards for a spread, assemble interpretation.
Pure logic — no DB access. DB queries are in tarot/repository.py.
"""

import random
from dataclasses import dataclass
from typing import Any

from core.logging import get_logger

log = get_logger(__name__)


# ── Spread definitions ─────────────────────────────────────────────────────────
@dataclass(frozen=True)
class SpreadPosition:
    index: int
    name_ru: str
    description_ru: str


SPREADS: dict[str, list[SpreadPosition]] = {
    "single": [
        SpreadPosition(0, "Карта дня", "Послание дня — энергия, которую стоит принять"),
    ],
    "three_card": [
        SpreadPosition(0, "Прошлое",    "То, что привело вас к нынешней ситуации"),
        SpreadPosition(1, "Настоящее",  "Текущее положение дел и актуальные энергии"),
        SpreadPosition(2, "Будущее",    "Вероятное развитие событий при нынешнем курсе"),
    ],
    "celtic_cross": [
        SpreadPosition(0, "Ситуация",      "Суть текущей ситуации — ядро вопроса"),
        SpreadPosition(1, "Препятствие",   "Что мешает или бросает вызов"),
        SpreadPosition(2, "Сознание",      "Осознанная цель, мысли и видимый ориентир"),
        SpreadPosition(3, "Подсознание",   "Корни ситуации, подсознательные причины"),
        SpreadPosition(4, "Ближайшее прошлое", "Что уходит, прошлые влияния"),
        SpreadPosition(5, "Будущее",       "Ближайшее будущее, что приходит"),
        SpreadPosition(6, "Я сам",         "Ваше отношение к ситуации и личная позиция"),
        SpreadPosition(7, "Другие",        "Влияние людей и окружения"),
        SpreadPosition(8, "Надежды и опасения", "Ваши ожидания, желания и страхи"),
        SpreadPosition(9, "Итог",          "Финальный результат при текущем курсе"),
    ],
    "week": [
        SpreadPosition(i, name, desc)
        for i, (name, desc) in enumerate([
            ("Луна", "Эмоциональный тон ближайшего периода"),
            ("Марс", "Где потребуется действие и смелость"),
            ("Меркурий", "Мысли, разговоры и важные решения"),
            ("Юпитер", "Рост, поддержка и возможности"),
            ("Венера", "Отношения, удовольствие и ценности"),
            ("Сатурн", "Ответственность, границы и урок недели"),
            ("Солнце", "Итоговая ясность и главный фокус"),
        ])
    ],
    "relationship": [
        SpreadPosition(0, "Вы",          "Ваша роль и энергия в отношениях"),
        SpreadPosition(1, "Партнёр",     "Роль и энергия партнёра"),
        SpreadPosition(2, "Связь",       "Природа связи между вами"),
        SpreadPosition(3, "Вызов",       "Главное препятствие или урок"),
        SpreadPosition(4, "Потенциал",   "Возможный исход и потенциал союза"),
    ],
}

PREMIUM_SPREADS = {"celtic_cross", "week", "relationship"}
FREE_SPREADS = {"three_card", "single"}


@dataclass
class DrawnCard:
    card_id: int
    position: int
    position_name_ru: str
    reversed: bool


@dataclass
class TarotSpreadResult:
    spread_type: str
    cards: list[DrawnCard]
    positions: list[SpreadPosition]


def draw_spread(
    spread_type: str,
    all_card_ids: list[int],
    *,
    reversed_probability: float = 0.25,
    seed: int | None = None,
) -> TarotSpreadResult:
    """
    Randomly draw cards for a spread.

    Args:
        spread_type: key from SPREADS dict
        all_card_ids: list of available card IDs (78 for full deck)
        reversed_probability: chance each card lands reversed (0.0–1.0)
        seed: optional seed for reproducible draws (useful in tests)
    """
    if spread_type not in SPREADS:
        raise ValueError(f"Unknown spread type: {spread_type!r}. Valid: {list(SPREADS)}")

    positions = SPREADS[spread_type]
    rng = random.Random(seed)

    if len(all_card_ids) < len(positions):
        raise ValueError(f"Not enough cards. Need {len(positions)}, got {len(all_card_ids)}")

    chosen_ids = rng.sample(all_card_ids, len(positions))

    cards = [
        DrawnCard(
            card_id=card_id,
            position=pos.index,
            position_name_ru=pos.name_ru,
            reversed=rng.random() < reversed_probability,
        )
        for card_id, pos in zip(chosen_ids, positions, strict=True)
    ]

    log.debug(
        "tarot.drawn",
        spread=spread_type,
        cards=[c.card_id for c in cards],
        reversed_count=sum(1 for c in cards if c.reversed),
    )
    return TarotSpreadResult(spread_type=spread_type, cards=cards, positions=positions)


def to_reading_json(result: TarotSpreadResult) -> list[dict[str, Any]]:
    """Serialise for DB storage in TarotReading.cards_json."""
    return [
        {
            "card_id": c.card_id,
            "position": c.position,
            "reversed": c.reversed,
        }
        for c in result.cards
    ]
