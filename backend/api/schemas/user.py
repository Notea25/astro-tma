from datetime import datetime

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    id: int
    name: str
    gender: str | None
    sun_sign: str | None
    birth_city: str | None
    birth_time_known: bool
    # ISO "YYYY-MM-DD" and "HH:MM", read from User.birth_date directly
    # (NOT from natal_chart) so the Profile editor pre-fills even if
    # the natal chart hasn't been computed or failed.
    birth_date: str | None = None
    birth_time: str | None = None
    push_enabled: bool
    is_premium: bool
    created_at: datetime


class SetGenderRequest(BaseModel):
    gender: str  # "male" | "female"


class SetPushRequest(BaseModel):
    enabled: bool


class UpsertMeRequest(BaseModel):
    """Optional payload on POST /users/me — used for first-touch attribution."""
    start_param: str | None = Field(default=None, max_length=64)


class SetAcquisitionRequest(BaseModel):
    source: str = Field(..., min_length=1, max_length=64)


class SetupBirthDataRequest(BaseModel):
    birth_date: datetime
    birth_time_known: bool = False
    birth_city: str = Field(..., min_length=2, max_length=128)
    # Optional: pre-resolved coordinates from frontend autocomplete
    lat: float | None = None
    lng: float | None = None


class SetupBirthDataResponse(BaseModel):
    sun_sign: str
    moon_sign: str | None
    ascendant_sign: str | None
    city_resolved: str
    lat: float
    lng: float
