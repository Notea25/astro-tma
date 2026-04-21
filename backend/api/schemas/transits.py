from datetime import date

from pydantic import BaseModel


class TransitAspect(BaseModel):
    transit_planet: str
    natal_planet: str
    aspect: str
    orb: float
    weight: int
    transit_planet_ru: str
    natal_planet_ru: str
    aspect_ru: str


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


class TransitsResponse(BaseModel):
    date: date
    aspects: list[TransitAspect]
    energy: EnergyScores
    sky: dict[str, SkyPosition]
