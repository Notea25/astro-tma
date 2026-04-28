#!/usr/bin/env python3
"""
Seed all 78 tarot cards into the database.
Run: docker compose exec backend python scripts/seed_tarot.py
"""
import asyncio
import os
import sys

# Script lives in backend/scripts/, so backend/ is one level up
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import delete

from db.database import AsyncSessionLocal
from db.models import TarotArcana, TarotCard
from services.tarot.seed_data import get_all_cards_seed

_ARCANA_MAP = {
    "fire": "wands", "water": "cups",
    "air": "swords", "earth": "pentacles",
    "major": "major",
}


async def seed() -> None:
    cards_data = get_all_cards_seed()
    async with AsyncSessionLocal() as session:
        await session.execute(delete(TarotCard))
        for i, card in enumerate(cards_data):
            element = card.get("element", "major")
            arcana_str = "major" if i < 22 else _ARCANA_MAP.get(element, "major")
            session.add(TarotCard(
                name_ru=card["name_ru"],
                name_en=card["name_en"],
                arcana=TarotArcana(arcana_str),
                number=card["number"],
                emoji=card["emoji"],
                upright_ru=card["upright_ru"],
                reversed_ru=card["reversed_ru"],
                keywords_ru=card["keywords_ru"],
                element=card.get("element"),
            ))
        await session.commit()
        print(f"Seeded {len(cards_data)} tarot cards")


asyncio.run(seed())
