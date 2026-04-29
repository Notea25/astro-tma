from datetime import datetime

from pydantic import BaseModel


class MacCardResponse(BaseModel):
    id: int
    name_ru: str
    category: str
    emoji: str
    description_ru: str
    question_ru: str
    affirmation_ru: str
    image_url: str | None


class MacReadingResponse(BaseModel):
    reading_id: int
    card: MacCardResponse


# ── Client-driven 48-card deck (new flow) ────────────────────────────────────

class MacPickRequest(BaseModel):
    card_number: int
    card_name: str
    category: str


class MacPickResponse(BaseModel):
    pick_id: int
    card_number: int
    card_name: str
    category: str
    created_at: datetime
    next_reset_at: datetime
    reused_existing: bool = False


class MacPickHistoryItem(BaseModel):
    pick_id: int
    card_number: int
    card_name: str
    category: str
    created_at: datetime


class MacTodayResponse(BaseModel):
    pick: MacPickHistoryItem | None
    next_reset_at: datetime
