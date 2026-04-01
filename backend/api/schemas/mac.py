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
