from pydantic import BaseModel


class TarotCardDetail(BaseModel):
    id: int
    name_ru: str
    name_en: str
    emoji: str
    arcana: str
    reversed: bool
    meaning_ru: str      # upright or reversed based on drawn orientation
    position_name_ru: str
    position_meaning_ru: str | None
    keywords_ru: list[str]


class TarotSpreadResponse(BaseModel):
    reading_id: int
    spread_type: str
    cards: list[TarotCardDetail]
    is_premium: bool


class DrawSpreadRequest(BaseModel):
    spread_type: str     # "three_card" | "celtic_cross" | "week" | "relationship"
