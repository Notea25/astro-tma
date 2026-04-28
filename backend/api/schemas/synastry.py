from datetime import date, datetime

from pydantic import BaseModel, Field


class SynastryManualInput(BaseModel):
    """Partner birth data for one-off synastry calculation (no invite flow)."""
    partner_name: str = Field(..., min_length=1, max_length=64)
    birth_date: date
    birth_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")  # HH:MM
    birth_time_known: bool = True
    birth_city: str = Field(..., min_length=1, max_length=128)
    birth_lat: float
    birth_lng: float
    # Optional — backend resolves from lat/lng if missing.
    birth_tz: str | None = None


class SynastryAspectOut(BaseModel):
    p1_name: str
    p2_name: str
    p1_name_ru: str
    p2_name_ru: str
    aspect: str
    aspect_ru: str
    orb: float
    weight: int


class SynastryScores(BaseModel):
    love: int
    communication: int
    trust: int
    passion: int
    overall: int


class SynastryResult(BaseModel):
    aspects: list[SynastryAspectOut]
    scores: SynastryScores
    total_aspects: int
    initiator_name: str | None = None
    partner_name: str | None = None


class SynastryRequestOut(BaseModel):
    id: int
    token: str
    invite_url: str
    status: str
    expires_at: datetime
    initiator_name: str | None = None


class SynastryPending(BaseModel):
    id: int
    token: str
    initiator_name: str
    expires_at: datetime
