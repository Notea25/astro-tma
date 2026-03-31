from pydantic import BaseModel


class CompatibilityRequest(BaseModel):
    sign_a: str
    sign_b: str


class CompatibilityResponse(BaseModel):
    sign_a: str
    sign_b: str
    overall: int
    love: int
    communication: int
    trust: int
    passion: int
    tier: str
    description_ru: str
    strengths_ru: list[str]
    challenges_ru: list[str]
    is_deep_analysis: bool   # True = natal synastry (premium)
