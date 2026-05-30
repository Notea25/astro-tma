"""Pydantic schemas for the /api/destiny-matrix endpoints.

Структура соответствует MATRIX_DESTINY_SPEC.md §4.2 + §5.1 — то что
возвращает `calculator.calculate_matrix(birth_date)`.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

# ── Подблоки positions ──────────────────────────────────────────────────────

class PersonalityBlock(BaseModel):
    """§2.1 Личностный (диагональный) ромб."""
    day: int
    month: int
    year: int
    bottom: int
    center: int


class AncestralSquareBlock(BaseModel):
    """§2.2 Родовой (прямой) квадрат."""
    top_left: int
    top_right: int
    bottom_right: int
    bottom_left: int


class LinesBlock(BaseModel):
    """§2.3 Земля/Небо + мужская/женская линии рода."""
    sky: int
    earth: int
    father: int
    mother: int


class PurposesBlock(BaseModel):
    """§2.3 Предназначения: личное (<40), социальное (40-60),
    духовное (60+), планетарное (миссия)."""
    personal: int
    social: int
    spiritual: int
    planetary: int


class ChannelsBlock(BaseModel):
    """§2.4 Десять каналов по 3 энергии (start/middle/outcome)."""
    karmic_tail: list[int]
    talents: list[int]
    relationships: list[int]
    finance: list[int]
    material_karma: list[int]
    parental: list[int]
    ancestral_father_talents: list[int]
    ancestral_father_karma: list[int]
    ancestral_mother_talents: list[int]
    ancestral_mother_karma: list[int]


class VarnaBlock(BaseModel):
    """§2.5 Варна — касты по числам кармы (1..9), четыре доли."""
    varnas: dict[str, int]   # {"Брахман": 40, "Кшатрий": 40, ...}
    expression: int


class DestinyMatrixPositions(BaseModel):
    personality: PersonalityBlock
    ancestral_square: AncestralSquareBlock
    lines: LinesBlock
    purposes: PurposesBlock
    channels: ChannelsBlock
    varna: VarnaBlock


# ── Ответы эндпоинтов ───────────────────────────────────────────────────────

class DestinyMatrixResponse(BaseModel):
    positions: DestinyMatrixPositions
    birth_date: date
    computed_at: datetime
    has_full_access: bool


class ArcanaResponse(BaseModel):
    """Все 9 контекстных трактовок для одного аркана — payload для
    bottom-sheet'а по тапу узла октаграммы. Клиент сам выбирает какой
    контекст показывать (по тому какой узел тапнули)."""
    arcana_num: int
    arcana_name: str
    keywords: list[str]
    contexts: dict[str, str]   # context_key → meaning_ru


class InterpretationResponse(BaseModel):
    """LLM-сгенерированный 8-секционный личный разбор. Кешируется per reading_id."""
    reading_id: int
    sections: dict[str, str]   # who_you_are, karmic_tail, talents, purpose,
                               # relationships, finance, parental, advice
    model: str
    generated_at: datetime
