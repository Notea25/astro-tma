#!/usr/bin/env python3
"""Seed the `arcana_base` table from `infra/content/book_arcana_base.json`.

The file holds the canonical 22 Major Arcana reference text from the
Ладини book — what V3 section generators pull as LLM context. Re-runs
are idempotent (ON CONFLICT DO UPDATE), so editing one card and
re-running is the recommended workflow.

Run on prod:
    docker compose exec backend python /app/scripts/seed_arcana_base.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402

from db.database import AsyncSessionLocal  # noqa: E402
from db.models import ArcanaBase  # noqa: E402


def _find_json() -> Path:
    """Locate book_arcana_base.json. Inside the container this script is
    copied to /app/scripts/, the JSON to /app/scripts/content/. Locally
    the layout is `infra/content/book_arcana_base.json` and the script
    is at `infra/scripts/`."""
    here = Path(__file__).resolve().parent
    for candidate in [
        here / "content" / "book_arcana_base.json",  # in-container layout
        here.parent / "content" / "book_arcana_base.json",  # repo layout
    ]:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "book_arcana_base.json not found — checked /app/scripts/content/ "
        "and infra/content/"
    )


async def main() -> None:
    path = _find_json()
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"Loaded {len(data)} arcana from {path}", flush=True)

    rows = []
    for num_str, arc in data.items():
        rows.append({
            "num": int(num_str),
            "name_ru": arc["name"],
            "essence": arc["essence"],
            "mission": arc["mission"],
            "shadow": arc["shadow"],
            "healing": arc["healing"],
            "activities": arc["activities"],
            "famous_people": arc.get("famous_people"),
        })

    async with AsyncSessionLocal() as session:
        stmt = pg_insert(ArcanaBase).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["num"],
            set_=dict(
                name_ru=stmt.excluded.name_ru,
                essence=stmt.excluded.essence,
                mission=stmt.excluded.mission,
                shadow=stmt.excluded.shadow,
                healing=stmt.excluded.healing,
                activities=stmt.excluded.activities,
                famous_people=stmt.excluded.famous_people,
            ),
        )
        await session.execute(stmt)
        await session.commit()

    print(f"Upserted {len(rows)} rows into arcana_base.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
