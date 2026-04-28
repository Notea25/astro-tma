#!/usr/bin/env python3
"""
Update tarot card meanings from tarot_full.md.
Parses the markdown and updates upright_ru/reversed_ru in the database.

Run: docker compose exec backend python scripts/update_tarot_meanings.py
"""
import asyncio
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from db.database import AsyncSessionLocal
from db.models import TarotCard

# --- Markdown parser ---

def parse_cards(md_text: str) -> dict[str, dict]:
    """Parse markdown into dict keyed by English name."""
    cards = {}
    card_blocks = re.split(r'\n## ', md_text)

    for block in card_blocks[1:]:
        lines = block.strip().split('\n')
        header = lines[0].strip()

        # Extract English name from parentheses
        en_match = re.search(r'\(([^)]+)\)', header)
        if not en_match:
            continue
        name_en = en_match.group(1)

        # Parse sections
        sections = {}
        current_section = None
        current_text = []

        for line in lines[1:]:
            if line.startswith('### '):
                if current_section:
                    sections[current_section] = ' '.join(current_text).strip()
                current_section = line[4:].strip()
                current_text = []
            elif line.startswith('**') or line.startswith('---'):
                continue
            elif not line.strip():
                continue
            else:
                if current_section:
                    current_text.append(line.strip())

        if current_section:
            sections[current_section] = ' '.join(current_text).strip()

        cards[name_en] = sections

    return cards


def compose_upright(s: dict) -> str:
    """Compose upright_ru with emoji markers for MeaningText component."""
    parts = []

    gen = s.get('Общее значение (прямое)', '')
    if gen:
        parts.append(gen)

    topics = []
    for emoji, label, key in [
        ('💕', 'Любовь', 'Любовь (прямое)'),
        ('💼', 'Карьера', 'Карьера (прямое)'),
        ('🩺', 'Здоровье', 'Здоровье (прямое)'),
        ('🔮', 'Духовность', 'Духовность'),
    ]:
        text = s.get(key, '')
        if text:
            topics.append(f"{emoji} {label}: {text}")

    if topics:
        parts.append('\n'.join(topics))

    advice = s.get('Совет дня', '')
    if advice:
        parts.append(f"✨ Совет дня: {advice}")

    return '\n\n'.join(parts)


def compose_reversed(s: dict) -> str:
    """Compose reversed_ru with emoji markers."""
    parts = []

    gen = s.get('Общее значение (перевёрнутое)', '')
    if gen:
        parts.append(gen)

    topics = []
    for emoji, label, key in [
        ('💕', 'Любовь', 'Любовь (перевёрнутое)'),
        ('💼', 'Карьера', 'Карьера (перевёрнутое)'),
        ('🩺', 'Здоровье', 'Здоровье (перевёрнутое)'),
    ]:
        text = s.get(key, '')
        if text:
            topics.append(f"{emoji} {label}: {text}")

    if topics:
        parts.append('\n'.join(topics))

    return '\n\n'.join(parts)


# --- Database update ---

async def update_meanings():
    md_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'tarot', 'tarot_full.md')

    # Also check Desktop path
    if not os.path.exists(md_path):
        md_path = '/app/services/tarot/tarot_full.md'

    print(f"Reading {md_path}")
    with open(md_path, encoding='utf-8') as f:
        md_text = f.read()

    cards = parse_cards(md_text)
    print(f"Parsed {len(cards)} cards from markdown")

    updated = 0
    not_found = []

    async with AsyncSessionLocal() as session:
        # Get all cards from DB
        result = await session.execute(select(TarotCard))
        db_cards = result.scalars().all()
        print(f"Found {len(db_cards)} cards in database")

        for db_card in db_cards:
            sections = cards.get(db_card.name_en)
            if not sections:
                not_found.append(db_card.name_en)
                continue

            new_upright = compose_upright(sections)
            new_reversed = compose_reversed(sections)

            if new_upright and new_reversed:
                db_card.upright_ru = new_upright
                db_card.reversed_ru = new_reversed
                updated += 1
                print(f"  ✓ {db_card.name_en}: upright={len(new_upright)}ch, reversed={len(new_reversed)}ch")
            else:
                print(f"  ⚠ {db_card.name_en}: empty content, skipped")

        await session.commit()

    print(f"\nUpdated: {updated} cards")
    if not_found:
        print(f"Not found in markdown: {not_found}")


asyncio.run(update_meanings())
