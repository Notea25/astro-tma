from datetime import date
from typing import Literal

from pydantic import BaseModel

TransitCategory = Literal["support", "tension", "transformation", "neutral"]


class TransitAspect(BaseModel):
    transit_planet: str
    natal_planet: str
    aspect: str
    orb: float
    weight: int
    transit_planet_ru: str
    natal_planet_ru: str
    aspect_ru: str
    transit_retrograde: bool = False
    applying: bool | None = None  # True = сходящийся (усиливается), False = расходящийся, None = неизвестно
    text_ru: str | None = None  # LLM-cached interpretation of this transit-planet pair
    category: TransitCategory = "neutral"


class EnergyScores(BaseModel):
    love: int
    career: int
    health: int
    luck: int


class SkyPosition(BaseModel):
    sign: str
    sign_ru: str
    degree: float
    retrograde: bool


class RetrogradeInfo(BaseModel):
    planet: str
    planet_ru: str
    glyph: str
    sign: str
    sign_ru: str
    description_ru: str


class TransitsResponse(BaseModel):
    date: date
    aspects: list[TransitAspect]
    energy: EnergyScores
    sky: dict[str, SkyPosition]
    retrogrades: list[RetrogradeInfo] = []


class TransitDetailsRequest(BaseModel):
    transit_planet: str
    natal_planet: str
    aspect: str


class TransitDetailsResponse(BaseModel):
    text_ru: str
    advice_do: str | None = None
    advice_avoid: str | None = None
    affirmation: str | None = None
    ritual: str | None = None
    # Only emitted for hard aspects (square / opposition / conjunction
    # with Mars/Saturn/Pluto/outer). None for soft aspects.
    risk_warning: str | None = None
    affected_house: int | None = None
    affected_house_topic: str | None = None


class PeriodEvent(BaseModel):
    date: date
    kind: Literal["aspect", "ingress"]
    title_ru: str
    category: TransitCategory = "neutral"
    weight: int = 0
    # Aspect-specific
    transit_planet: str | None = None
    natal_planet: str | None = None
    aspect: str | None = None
    transit_planet_ru: str | None = None
    natal_planet_ru: str | None = None
    aspect_ru: str | None = None
    orb: float | None = None
    text_ru: str | None = None
    # Ingress-specific
    planet: str | None = None
    planet_ru: str | None = None
    from_sign: str | None = None
    from_sign_ru: str | None = None
    to_sign: str | None = None
    to_sign_ru: str | None = None


class PeriodEventsResponse(BaseModel):
    start_date: date
    end_date: date
    events: list[PeriodEvent]
