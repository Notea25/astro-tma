from datetime import datetime

from pydantic import BaseModel


class NewsItem(BaseModel):
    id: int
    date: datetime
    title_ru: str
    body_md: str
    category: str
    priority: int


class NewsPreview(BaseModel):
    id: int
    date: datetime
    title_ru: str
    category: str
    priority: int
    preview: str
