from datetime import datetime
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    id: int
    name: str
    sun_sign: str | None
    birth_city: str | None
    birth_time_known: bool
    push_enabled: bool
    is_premium: bool
    created_at: datetime


class SetupBirthDataRequest(BaseModel):
    birth_date: datetime
    birth_time_known: bool = False
    birth_city: str = Field(..., min_length=2, max_length=128)


class SetupBirthDataResponse(BaseModel):
    sun_sign: str
    moon_sign: str | None
    ascendant_sign: str | None
    city_resolved: str
    lat: float
    lng: float
