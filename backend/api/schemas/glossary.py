from pydantic import BaseModel


class GlossaryTermShort(BaseModel):
    slug: str
    title_ru: str
    category: str
    short_ru: str


class GlossaryTermFull(BaseModel):
    slug: str
    title_ru: str
    category: str
    short_ru: str
    full_ru: str
    related: list[GlossaryTermShort] = []
