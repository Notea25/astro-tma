from datetime import date
from pydantic import BaseModel


class EnergyScores(BaseModel):
    love: int
    career: int
    health: int
    luck: int


class HoroscopeResponse(BaseModel):
    sign: str
    sign_ru: str
    date: date
    period: str
    text_ru: str
    energy: EnergyScores
    is_personalised: bool   # True if calculated against natal chart


class MoonPhaseResponse(BaseModel):
    phase_name: str
    phase_name_ru: str
    emoji: str
    description_ru: str
    illumination: float
    date: date
    favorable_actions: list[str] = []
    avoid_actions: list[str] = []


class MoonCalendarDay(BaseModel):
    day: int
    phase_name: str
    phase_name_ru: str
    emoji: str
    illumination: float
    favorable_actions: list[str] = []
    avoid_actions: list[str] = []


class MoonCalendarResponse(BaseModel):
    year: int
    month: int
    days: list[MoonCalendarDay]
