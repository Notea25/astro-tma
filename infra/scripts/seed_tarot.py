#!/usr/bin/env python3
"""
Seed all 78 tarot cards into the database.
Run: docker compose exec backend python infra/scripts/seed_tarot.py
"""
import asyncio
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from sqlalchemy import delete
from db.database import AsyncSessionLocal
from db.models import TarotCard, TarotArcana
from services.tarot.seed_data import get_all_cards_seed, MAJOR_ARCANA

async def seed():
    cards_data = get_all_cards_seed()
    async with AsyncSessionLocal() as session:
        await session.execute(delete(TarotCard))
        for i, card in enumerate(cards_data):
            arcana_str = "major" if i < 22 else card["element"]
            # Map to TarotArcana enum
            arcana_map = {"fire": "wands", "water": "cups", "air": "swords", "earth": "pentacles", "major": "major"}
            arcana = TarotArcana(arcana_map.get(card.get("element", "major") if i >= 22 else "major", "major"))
            session.add(TarotCard(
                name_ru=card["name_ru"], name_en=card["name_en"],
                arcana=arcana, number=card["number"],
                emoji=card["emoji"],
                upright_ru=card["upright_ru"], reversed_ru=card["reversed_ru"],
                keywords_ru=card["keywords_ru"],
                element=card.get("element"),
            ))
        await session.commit()
        print(f"✅ Seeded {len(cards_data)} tarot cards")

asyncio.run(seed())
