from pydantic import BaseModel


_IMAGE_BASE = "https://ip-194-99-21-53-142250.vps.hosted-by-mvps.net/static/tarot/"


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
    image_url: str | None


class TarotSpreadResponse(BaseModel):
    reading_id: int
    spread_type: str
    cards: list[TarotCardDetail]
    is_premium: bool


class DrawSpreadRequest(BaseModel):
    spread_type: str     # "three_card" | "celtic_cross" | "week" | "relationship"


class TarotPositionNarrative(BaseModel):
    n: int
    narrative: str


class TarotInterpretationResponse(BaseModel):
    reading_id: int
    spread_type: str
    positions: list[TarotPositionNarrative]
    summary: str
