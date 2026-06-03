"""Phase 5 smoke test: import v3_interpreter, build a context for Юля,
and generate the smallest section ("anahata", ~280 words) via Sonnet.

Confirms:
  1. Module imports cleanly (no key/attr typos in prompt builders).
  2. load_v3_context() round-trips through arcana_base + karmic_programs.
  3. The LLM call works end-to-end and writes to destiny_interpretations_v3.

Run on prod:
    docker compose exec backend python /app/scripts/smoke_v3_interpreter.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from db.database import AsyncSessionLocal  # noqa: E402
from services.destiny_matrix.calculator import calculate_matrix  # noqa: E402
from services.destiny_matrix.v3_interpreter import (  # noqa: E402
    SECTIONS,
    load_v3_context,
    regenerate_sections,
)


SMOKE_USER_ID = 1
SMOKE_BIRTH = date(2002, 7, 8)
SMOKE_GENDER = "female"
SMOKE_NAME = "Юля"
SMOKE_SECTION = "anahata"


async def main() -> None:
    print(f"Found {len(SECTIONS)} sections registered", flush=True)
    print(f"Section keys: {[s.key for s in SECTIONS]}", flush=True)

    positions = calculate_matrix(SMOKE_BIRTH)
    async with AsyncSessionLocal() as session:
        ctx = await load_v3_context(
            session,
            user_id=SMOKE_USER_ID,
            birth_date=SMOKE_BIRTH,
            gender=SMOKE_GENDER,
            name=SMOKE_NAME,
            positions=positions,
        )
        print(
            f"Context built: karmic={ctx.karmic.name if ctx.karmic else None}, "
            f"year={ctx.year_energy.current}→{ctx.year_energy.upcoming}, "
            f"purposes={len(ctx.purposes)}, arcana={len(ctx.arcana)}",
            flush=True,
        )

        print(f"\nGenerating section: {SMOKE_SECTION} …", flush=True)
        out = await regenerate_sections(session, ctx=ctx, keys=[SMOKE_SECTION])
        text = out.get(SMOKE_SECTION, "")
        if not text:
            print("FAIL — section returned empty content", flush=True)
            sys.exit(1)
        print(f"\n──── {SMOKE_SECTION} ({len(text)} chars) ────")
        print(text)
        print("\n────────────")
        print("PHASE 5 SMOKE PASS — section generated + cached.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
