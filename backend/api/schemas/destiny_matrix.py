"""Pydantic schemas for the /api/destiny-matrix endpoints."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class ChakraRow(BaseModel):
    physics: int
    energy: int
    emotion: int


class DestinyMatrixPositions(BaseModel):
    # Big diamond (rhombus) — 5 free positions
    A: int
    B: int
    C: int
    D: int
    E: int
    # Small ancestral square — 4 paid positions
    F: int
    G: int
    H: int
    I: int
    # Earth / sky / purpose triple
    line_earth: int
    line_sky: int
    purpose_personal: int
    purpose_social: int
    purpose_spiritual: int
    # Chakras 7 × {physics, energy, emotion} + totals row
    chakras: dict[str, ChakraRow]
    # 5 life lines (3 points each: start, middle, outcome)
    line_karma: list[int]
    line_mission: list[int]
    line_money: list[int]
    line_love: list[int]
    line_health: list[int]
    # Karmic tails + extra anchor points
    karmic_tail_male: int
    karmic_tail_female: int
    point_comfort: int
    point_socialization: int
    point_love: int


class DestinyMatrixResponse(BaseModel):
    positions: DestinyMatrixPositions
    birth_date: date
    computed_at: datetime
    has_full_access: bool


class ArcanaContextMeaning(BaseModel):
    """Single (arcana, context) row from arcana_meanings table."""
    arcana_num: int
    arcana_name: str
    context: str
    meaning: str
    keywords: list[str]


class ArcanaResponse(BaseModel):
    """All contexts for one arcana — payload for the bottom-sheet on
    the result screen. Lets the client decide which context to show
    (based on which node the user tapped)."""
    arcana_num: int
    arcana_name: str
    keywords: list[str]
    contexts: dict[str, str]   # context_key → meaning_ru
