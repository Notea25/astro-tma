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
