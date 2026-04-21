from datetime import datetime

from pydantic import BaseModel


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
